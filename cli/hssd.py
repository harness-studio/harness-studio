#!/usr/bin/env python3
"""hssd — Harness Studio CLI: the engine that drives the governed, adversarial workflow.

Long name: harness-sd. Short alias: hssd. Targets Python 3.12; uses only the stdlib so it
runs anywhere. The AI backend is pluggable: HSSD_AGENT_BACKEND=claude (default, real agents
via Claude Code) or mock (deterministic, for tests).

Surface: new · init · sync · status · template (list|import|add|rm) · skill (list|import|add|rm) ·
overview (add|architect|analyze|split) · architecture (approve|status|reopen) · sprint
(plan|status|review|close) · work (add|list|show|claim|done) · engage · janitor · reset ·
update · log · stats · ailog. See `hssd <cmd> --help` and CLI.md.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("harness-studio")
except Exception:
    __version__ = "0.2.0a1"

PKG_ROOT = Path(__file__).resolve().parent.parent  # the harness-studio package
TEMPLATES = PKG_ROOT / "templates"
AGENTS = PKG_ROOT / "agents"

# Blessed template repos. Templates are SEPARATE git repos (see TEMPLATES.md); the CLI resolves
# them only via --from=<git-url>. This catalog powers `template list` + the recommendations.
TEMPLATE_CATALOG = [
    {"name": "hssd-template-fastapi-sqlite",
     "url": "https://github.com/harness-studio/hssd-template-fastapi-sqlite",
     "tech": ["python", "fastapi", "sqlite"]},
    {"name": "hssd-template-vite-react-ts",
     "url": "https://github.com/harness-studio/hssd-template-vite-react-ts",
     "tech": ["typescript", "react", "vite"]},
]

# Blessed skill catalog. Skills are framework-shipped and live under skills/ in the package.
# This catalog powers `skill list` + dedup in `skill add`.
SKILL_CATALOG = [
    {"name": "api-conventions",
     "url": "https://github.com/harness-studio/hssd-skill-api-conventions",
     "tech": []},
    {"name": "datetime-utc",
     "url": "https://github.com/harness-studio/hssd-skill-datetime-utc",
     "tech": []},
    {"name": "fastapi",
     "url": "https://github.com/harness-studio/hssd-skill-fastapi",
     "tech": ["python", "fastapi"]},
    {"name": "harness-studio",
     "url": "https://github.com/harness-studio/hssd-skill-harness-studio",
     "tech": []},
    {"name": "push-over-pull",
     "url": "https://github.com/harness-studio/hssd-skill-push-over-pull",
     "tech": []},
    {"name": "python",
     "url": "https://github.com/harness-studio/hssd-skill-python",
     "tech": ["python"]},
    {"name": "resilience",
     "url": "https://github.com/harness-studio/hssd-skill-resilience",
     "tech": []},
    {"name": "sql-indexing",
     "url": "https://github.com/harness-studio/hssd-skill-sql-indexing",
     "tech": ["sql"]},
    {"name": "sqlite-concurrency",
     "url": "https://github.com/harness-studio/hssd-skill-sqlite-concurrency",
     "tech": ["sqlite"]},
    {"name": "typescript",
     "url": "https://github.com/harness-studio/hssd-skill-typescript",
     "tech": ["typescript"]},
]


def _user_catalog_path() -> Path:
    """User-registered templates (the ones *you* trust), shared across all your projects."""
    return Path.home() / ".hssd" / "templates.json"


def _load_catalog_file(path: Path) -> list[dict]:
    """Generic helper: load a JSON catalog file, returning a list of dicts (or [] on error)."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _load_user_catalog() -> list[dict]:
    return _load_catalog_file(_user_catalog_path())


def _full_catalog() -> list[dict]:
    """Blessed templates + the user's own registered ones. Any git URL still works via --from."""
    return ([dict(t, source="blessed") for t in TEMPLATE_CATALOG]
            + [dict(t, source="user") for t in _load_user_catalog()])


# ── Skill catalog helpers ──────────────────────────────────────────────────────────────────

def _skill_user_catalog_path() -> Path:
    return Path.home() / ".hssd" / "skills.json"


def _load_skill_user_catalog() -> list[dict]:
    return _load_catalog_file(_skill_user_catalog_path())


def _full_skill_catalog() -> list[dict]:
    return ([dict(s, source="blessed") for s in SKILL_CATALOG]
            + [dict(s, source="user") for s in _load_skill_user_catalog()])


def _blessed_skill_names() -> set[str]:
    skills_root = PKG_ROOT / "skills"
    if not skills_root.exists():
        return {s["name"] for s in SKILL_CATALOG}
    return {d.name for d in skills_root.iterdir() if d.is_dir()}


# Template repos can't ship dotfiles, so they're stored under dotfiles/ and renamed here.
DOTFILE_MAP = {
    "vscode-extensions.json": ".vscode/extensions.json",
    "vscode-settings.json": ".vscode/settings.json",
    "pre-commit-config.yaml": ".pre-commit-config.yaml",
}

CLAUDE_MD = """# CLAUDE.md — governed by Harness Studio (hssd)

This project runs a governed, adversarial process. **Whoever builds never grades their own "done."**
The roles live in `.claude/agents/`; the blessed conventions in `.claude/skills/`.

Non-negotiables:
- **Spec-driven:** no code before the spec/ADR is locked (Spec Lock, end of architecture).
- **Evidence over assertion:** "done" means test output, a diff, or a screenshot — never a claim.
- **Maker != checker:** the author never certifies its own work; an independent adversary tries to break it.
- **Governance is standing, not an end task:** the AI Interaction Log is captured *continuously from the
  first interaction* (run `hssd ailog` anytime to render `docs/AI_LOG.md` from the session metrics); the
  ADR (`docs/ADR.md`) is assembled across phases. Never reconstruct them at the end.

Engagement loop: P0 Intake -> P1 Stories & Acceptance Criteria -> P2 Architecture -> [Spec Lock]
-> P3 Build (test-first: red -> green) -> P4 adversarial verification (loop-until-dry) -> [Merge].

Two runners over one state spine (`.harness/`):
- **Interactive: you are the MAESTRO.** Drive the loop through the `harness-studio` skill — run each
  role (product-analyst, definition-skeptic, story-writer, ac-adversary, architect, test-author,
  backend-dev, the P4 adversaries...) as a **native subagent**, and call the `hssd` CLI only for
  STATE: `hssd status`, `hssd work claim|done <id>`, `hssd architecture approve`, `hssd sprint ...`,
  `hssd overview split`, `hssd ailog`. Honor the human gates (Spec Lock, Merge) conversationally.
  Do **NOT** run `hssd engage`, `hssd overview architect`, or `hssd overview analyze` interactively —
  those are the *headless* runner and will nest a second Claude inside you (slow, not streamed).
- **Headless / CI:** `hssd engage <id> --accept-recommended [--budget N]` runs the same roles + gates
  unattended via `claude -p`. Run it in a real terminal (the human gates need a TTY).

Python: always use **uv** (`uv run pytest`, `uv add`) — never bare `python`/`pip`/`pytest`.

Framework: https://github.com/harness-studio/harness-studio
"""


HARNESS_GITIGNORE = (
    "# .harness — COMMIT the auditable state (engagements, decisions/assumptions, the backlog,\n"
    "# logs that feed the AI Interaction Log & ADR). Ignore only ephemeral / secret / large bits.\n"
    "cache/\n"
    "tmp/\n"
    "*.tmp\n"
    "*.lock\n"
    ".env\n"
    "*.env\n"
    "secrets*\n"
)


# Scoped permissions so the headless builder/test roles run UNATTENDED (no "allow this write?" prompt
# that stalled the P3 build) — without a global bypass and without breaking login auth (unlike --bare).
# Claude Code reads `.claude/settings.local.json` from the project: edits/writes are auto-approved,
# only a whitelist of build commands runs without a prompt, and dangerous/secret/recursive ops are
# denied outright. Read-only roles (analysts/adversaries) are further constrained by --allowedTools.
CLAUDE_SETTINGS_LOCAL = json.dumps({
    "permissions": {
        "allow": [
            "Read", "Glob", "Grep", "Edit", "Write",
            "Bash(hssd *)", "Bash(harness-sd *)",  # let the human drive hssd via Claude Code unprompted
            "Bash(uv *)", "Bash(uvx *)", "Bash(python *)", "Bash(python3 *)",
            "Bash(pytest *)", "Bash(ruff *)", "Bash(npm *)", "Bash(npx *)", "Bash(node *)",
            "Bash(git add *)", "Bash(git commit *)", "Bash(git status*)", "Bash(git diff*)",
            "Bash(ls *)", "Bash(cat *)", "Bash(mkdir *)", "Bash(mv *)", "Bash(cp *)", "Bash(echo *)",
        ],
        # Recursion of NESTED build agents is prevented by the Isolation guard in their composed
        # prompt (not by denying hssd here, which would also block the human driving hssd via Claude
        # Code — the project settings are shared by both).
        "deny": [
            "Bash(rm -rf *)", "Bash(sudo *)",
            "Bash(git push*)", "Bash(git reset --hard*)",
            "Read(.env)", "Read(.env.*)", "Read(**/.env)",
            "Write(.env)", "Write(.env.*)", "Write(.git/**)",
        ],
    }
}, indent=2)


def _mirror_if_absent(src: Path, dst: Path) -> tuple[int, int]:
    """Copy every file under src into dst, create-if-absent (never overwrite). Returns (created, skipped)."""
    created = skipped = 0
    for f in sorted(src.rglob("*")):
        if f.is_dir():
            continue
        target = dst / f.relative_to(src)
        if target.exists():
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, target)
        created += 1
    return created, skipped


def _wire_claude(dest: Path) -> tuple[int, int]:
    """Install the subagents + skills into the project's .claude/ so Claude Code sees them.

    Non-destructive (create-if-absent) -> safe on a legacy repo and idempotent.
    """
    created = skipped = 0
    if AGENTS.exists():
        c, s = _mirror_if_absent(AGENTS, dest / ".claude" / "agents")
        created += c
        skipped += s
    skills_root = PKG_ROOT / "skills"
    if skills_root.exists():
        for d in sorted(skills_root.iterdir()):
            if d.is_dir():  # a real skill (<name>/SKILL.md); skip top-level meta files
                c, s = _mirror_if_absent(d, dest / ".claude" / "skills" / d.name)
                created += c
                skipped += s
    commands_root = PKG_ROOT / "commands"
    if commands_root.exists():  # slash commands so Claude Code drives hssd via /overview, /engage, ...
        c, s = _mirror_if_absent(commands_root, dest / ".claude" / "commands")
        created += c
        skipped += s
    settings = dest / ".claude" / "settings.local.json"  # unattended-but-scoped tool permissions
    if not settings.exists():
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(CLAUDE_SETTINGS_LOCAL, encoding="utf-8")
        created += 1
    return created, skipped


def _detect_stack(dest: Path) -> str:
    """Coarse stack sniff for hssd.yaml (overview/analyze refines it later)."""
    hits: list[str] = []
    if (dest / "pyproject.toml").exists() or (dest / "requirements.txt").exists() or any(dest.glob("*.py")):
        hits.append("python")
    if (dest / "package.json").exists():
        hits.append("node")
    if (dest / "go.mod").exists():
        hits.append("go")
    if (dest / "Cargo.toml").exists():
        hits.append("rust")
    return ", ".join(hits) or "unknown"


def _log(project: Path, action: str, detail: str) -> None:
    """Append to the project's session log (the audit trail / free AI log)."""
    logs = project / ".harness" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (logs / "session.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{ts}\t{action}\t{detail}\n")


def _metric(record: dict) -> None:
    """Append one structured per-AI-call metric (time, tokens, cost) for analytics + the AI log."""
    logs = Path(".harness") / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), **record}
    with (logs / "metrics.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def _load_metrics(project: Path) -> list[dict]:
    mf = project / ".harness" / "logs" / "metrics.jsonl"
    if not mf.exists():
        return []
    return [json.loads(ln) for ln in mf.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _totals(rows: list[dict]) -> dict:
    def g(k: str) -> float:
        return sum((r.get(k) or 0) for r in rows)
    span = ""
    ts = [r.get("ts") for r in rows if r.get("ts")]
    if len(ts) >= 2:
        span = str(datetime.datetime.fromisoformat(ts[-1]) - datetime.datetime.fromisoformat(ts[0]))
    return {"calls": len(rows), "wall_s": g("duration_s"), "in": g("input_tokens"),
            "out": g("output_tokens"), "cache_read": g("cache_read_input_tokens"),
            "cost": g("cost_usd"), "span": span}


def _json_loads(text: str) -> object:
    """Parse JSON from an agent reply, tolerating ```json fences or surrounding prose."""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[A-Za-z0-9]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        for opener, closer in (("{", "}"), ("[", "]")):  # last resort: slice the bracketed span
            i, j = t.find(opener), t.rfind(closer)
            if i != -1 and j > i:
                try:
                    return json.loads(t[i:j + 1])
                except json.JSONDecodeError:
                    continue
        raise


def cmd_new(args: argparse.Namespace) -> int:
    dest = Path(args.name).resolve()
    if dest.exists() and any(dest.iterdir()):
        print(f"BLOCK: {dest} exists and is not empty", file=sys.stderr)
        return 1

    # 1. Either clone a template repo (--from=<git-url>) or start an empty governed project.
    if args.from_git:
        subprocess.run(["git", "clone", "--depth", "1", args.from_git, str(dest)], check=True)
        shutil.rmtree(dest / ".git", ignore_errors=True)
    else:
        dest.mkdir(parents=True, exist_ok=True)

    # 2. Rename any dotfiles the template shipped (dotfiles/<x> -> the real dotfile path).
    df = dest / "dotfiles"
    if df.exists():
        for f in df.iterdir():
            target = dest / DOTFILE_MAP.get(f.name, f.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(target))
        df.rmdir()

    # 3. Governance from minute zero (ADR + AI log from the package templates).
    docs = dest / "docs"
    docs.mkdir(exist_ok=True)
    for name in ("ADR.md", "AI_LOG.md"):
        tpl = TEMPLATES / name
        if tpl.exists() and not (docs / name).exists():
            shutil.copy(tpl, docs / name)

    # 4. This is a managed PROJECT (not a template) -> type: project. Stack is sniffed.
    stack = _detect_stack(dest)
    (dest / "hssd.yaml").write_text(f"type: project\nstack: {stack}\n", encoding="utf-8")

    # 5. Local PM spine + runtime dir (gitignored), then git on `main`.
    harness = dest / ".harness"
    harness.mkdir(exist_ok=True)
    (harness / ".gitignore").write_text(HARNESS_GITIGNORE, encoding="utf-8")
    _pm(dest).close()  # initialize the local PM spine (work_items table)
    subprocess.run(["git", "init", "-q", "-b", "main", str(dest)], check=False)

    # 6. Wire the team into .claude/ so Claude Code sees the subagents + skills.
    nclaude, _ = _wire_claude(dest)

    src = args.from_git or "empty governed project"
    _log(dest, "new", f"from={src} stack={stack} claude={nclaude}")
    print(f"OK: created {dest} (type: project, stack: {stack}, from: {src}); {nclaude} .claude file(s) wired")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Turn ON Harness Studio in an EXISTING repo (legacy or new) — non-destructive & idempotent.

    Unlike `new` (which scaffolds a fresh project), `init` adopts whatever is already here:
    it only ever *adds* governance + wiring, never overwrites your files. Safe to re-run.
    """
    dest = Path(args.path or ".").resolve()
    if not dest.is_dir():
        print(f"BLOCK: {dest} is not a directory", file=sys.stderr)
        return 1

    created: list[str] = []
    skipped: list[str] = []

    # 1. Runtime spine (.harness + local PM). We COMMIT the auditable state and ignore only
    #    ephemeral bits via .harness/.gitignore (the whole dir is NOT git-ignored).
    (dest / ".harness").mkdir(exist_ok=True)
    _pm(dest).close()
    hg = dest / ".harness" / ".gitignore"
    if not hg.exists():
        hg.write_text(HARNESS_GITIGNORE, encoding="utf-8")
    # migrate: drop a stale whole-dir ignore from an older init so the state can be committed
    gi = dest / ".gitignore"
    if gi.exists():
        lines = gi.read_text(encoding="utf-8").splitlines()
        kept = [ln for ln in lines if ln.strip() not in (".harness", ".harness/")]
        if len(kept) != len(lines):
            gi.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
            print("  migrated: removed stale '.harness/' ignore so engagement state is committed")

    # 2. Project config — create-if-absent (never clobber an existing hssd.yaml).
    hy = dest / "hssd.yaml"
    if hy.exists():
        skipped.append("hssd.yaml")
    else:
        hy.write_text(f"type: project\nstack: {_detect_stack(dest)}\n", encoding="utf-8")
        created.append("hssd.yaml")

    # 3. Governance artifacts (ADR + AI log), create-if-absent.
    docs = dest / "docs"
    docs.mkdir(exist_ok=True)
    for name in ("ADR.md", "AI_LOG.md"):
        tpl = TEMPLATES / name
        target = docs / name
        if target.exists():
            skipped.append(f"docs/{name}")
        elif tpl.exists():
            shutil.copy(tpl, target)
            created.append(f"docs/{name}")

    # 4. CLAUDE.md — standing instructions (create-if-absent; legacy CLAUDE.md is left alone).
    cm = dest / "CLAUDE.md"
    if cm.exists():
        skipped.append("CLAUDE.md")
    else:
        cm.write_text(CLAUDE_MD, encoding="utf-8")
        created.append("CLAUDE.md")

    # 5. Wire the team into .claude/ so Claude Code sees the subagents + skills.
    nclaude, sclaude = _wire_claude(dest)

    _log(dest, "init", f"created={len(created)} skipped={len(skipped)} claude(+{nclaude}/={sclaude})")

    print(f"OK: Harness Studio is ON in {dest}")
    if created:
        print("  created: " + ", ".join(created))
    if skipped:
        print("  kept (already present): " + ", ".join(skipped))
    print(f"  .claude/: {nclaude} agent/skill file(s) installed, {sclaude} already present")
    if not (dest / ".git").exists():
        print("  note: no git repo here — branch/claim features need git (run: git init -b main)")
    size = _detect_project_size(dest)
    if size == "blank":
        print("  next: write .harness/project.md (vision, objectives, non-goals)")
        print("        then: hssd project approve")
    elif size == "substantial":
        print("  detected: existing project with source files / manifests")
        print("  next: review or create .harness/project.md — the AI can read your codebase and propose it")
        print("        then: hssd project approve")
    else:
        print("  next: write .harness/project.md  (or describe your project so the AI can draft it)")
        print("        then: hssd project approve")
    return 0


def _mirror_force(src: Path, dst: Path) -> int:
    n = 0
    for f in sorted(src.rglob("*")):
        if f.is_dir():
            continue
        t = dst / f.relative_to(src)
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, t)
        n += 1
    return n


def cmd_sync(args: argparse.Namespace) -> int:
    """Re-sync .claude/ (agents, skills, commands) from the framework — OVERWRITES framework-shipped
    skills only, so user-imported skills are preserved across syncs."""
    dest = Path(".").resolve()
    n = 0
    if AGENTS.exists():
        n += _mirror_force(AGENTS, dest / ".claude" / "agents")
    skills_root = PKG_ROOT / "skills"
    if skills_root.exists():
        blessed = _blessed_skill_names()
        for d in sorted(skills_root.iterdir()):
            if d.is_dir() and d.name in blessed:  # only overwrite framework-shipped names
                n += _mirror_force(d, dest / ".claude" / "skills" / d.name)
    commands_root = PKG_ROOT / "commands"
    if commands_root.exists():
        n += _mirror_force(commands_root, dest / ".claude" / "commands")
    _log(dest, "sync", f"files={n}")
    print(f"OK: re-synced {n} file(s) into .claude/ from the framework (agents, skills, commands).")
    return 0


def cmd_project(args: argparse.Namespace) -> int:
    """Human gate: approve project.md → transitions project to 'identified'."""
    project = Path(".").resolve()
    pm_path = project / ".harness" / "project.md"
    lock = project / ".harness" / "locks" / "project.json"

    if args.action == "show":
        if pm_path.exists():
            print(pm_path.read_text(encoding="utf-8"))
        else:
            print("No project.md yet. Create it at .harness/project.md, then run: hssd project approve")
        return 0

    if args.action == "check":
        if lock.exists():
            meta = json.loads(lock.read_text(encoding="utf-8"))
            print(f"project: IDENTIFIED · approved {meta.get('approved_at', '?')} by {meta.get('by', '?')}")
        else:
            print("project: NOT identified. Approve with: hssd project approve")
        return 0

    # approve
    if not pm_path.exists():
        print("BLOCK: .harness/project.md does not exist.\n"
              "  Create it with vision, objectives, non-goals, and principles.\n"
              "  Then run: hssd project approve", file=sys.stderr)
        return 1
    body = pm_path.read_text(encoding="utf-8").strip()
    if len(body) < 80:
        print("BLOCK: .harness/project.md looks like a stub (under 80 chars). "
              "Fill it in before approving.", file=sys.stderr)
        return 1
    _locks_dir(project).mkdir(parents=True, exist_ok=True)
    meta = {
        "approved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "by": os.environ.get("USER") or os.environ.get("USERNAME") or "engineer",
        "project_md_path": ".harness/project.md",
    }
    lock.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    _log(project, "project approve", "project.md locked")
    print("✓ project IDENTIFIED — .harness/project.md approved.")
    print("  next: hssd overview architect  →  hssd architecture approve")
    return 0


def cmd_intake(args: argparse.Namespace) -> int:
    """Intake cycle: add a demand, list intakes, approve to release stories to backlog."""
    project = Path(".").resolve()
    con = _pm(project)

    try:
        if args.action == "list":
            rows = con.execute(
                "SELECT id, title, status, created_at FROM intakes ORDER BY created_at DESC"
            ).fetchall()
            if not rows:
                print("(no intakes yet — run: hssd intake add <brief.md>)")
                return 0
            for iid, title, status, created_at in rows:
                print(f"  {iid}  [{status:<10}]  {title}  ({created_at[:10]})")
            return 0

        if args.action == "show":
            if not args.id:
                print("BLOCK: provide an intake id", file=sys.stderr); return 1
            row = con.execute(
                "SELECT id, title, brief_path, status, created_at FROM intakes WHERE id=?",
                (args.id,)
            ).fetchone()
            if not row:
                print(f"BLOCK: intake {args.id} not found", file=sys.stderr); return 1
            iid, title, brief_path, status, created_at = row
            print(f"intake: {iid}\ntitle:  {title}\nstatus: {status}\ncreated:{created_at}")
            if brief_path and Path(brief_path).exists():
                print(f"\n--- brief ({brief_path}) ---")
                print(Path(brief_path).read_text(encoding="utf-8"))
            return 0

        if args.action == "add":
            brief_path = args.file
            title = args.title or (Path(brief_path).stem if brief_path else "untitled")
            if brief_path and not Path(brief_path).exists():
                print(f"BLOCK: file not found: {brief_path}", file=sys.stderr); return 1
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            iid = f"INT-{now[:10].replace('-','')}-{abs(hash(title)) % 9999:04d}"
            con.execute(
                "INSERT INTO intakes(id, title, brief_path, status, created_at) VALUES(?,?,?,?,?)",
                (iid, title, brief_path, "draft", now)
            )
            con.commit()
            _log(project, "intake add", f"{iid} {title}")
            print(f"✓ intake {iid} added (status=draft)")
            print(f"  next: groom + split stories, then: hssd intake approve {iid}")
            return 0

        if args.action == "approve":
            if not args.id:
                print("BLOCK: provide an intake id", file=sys.stderr); return 1
            row = con.execute("SELECT id, title FROM intakes WHERE id=?", (args.id,)).fetchone()
            if not row:
                print(f"BLOCK: intake {args.id} not found", file=sys.stderr); return 1
            con.execute("UPDATE intakes SET status='approved' WHERE id=?", (args.id,))
            con.commit()
            _log(project, "intake approve", args.id)
            print(f"✓ intake {args.id} approved — stories are now eligible for iteration planning")
            print("  next: hssd iteration plan  →  hssd iteration activate <id>")
            return 0

        print(f"unknown action: {args.action}", file=sys.stderr)
        return 1
    finally:
        con.close()


def cmd_iteration(args: argparse.Namespace) -> int:
    """Iterations: plan → activate (variadic, starts 1 or N in parallel) → list → converge."""
    project = Path(".").resolve()
    con = _pm(project)

    try:
        if args.action == "list":
            rows = con.execute(
                "SELECT id, goal, status, intake_id, created_at FROM iterations ORDER BY created_at DESC"
            ).fetchall()
            if not rows:
                print("(no iterations yet — run: hssd iteration plan)")
                return 0
            for iid, goal, status, intake_id, created_at in rows:
                src = f"  ← {intake_id}" if intake_id else ""
                print(f"  {iid}  [{status:<10}]  {goal or '(no goal)'}{src}")
            return 0

        if args.action == "plan":
            goal = args.goal or ""
            intake_id = args.intake or None
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            iid = f"ITER-{now[:10].replace('-','')}-{abs(hash(goal + now)) % 9999:04d}"
            con.execute(
                "INSERT INTO iterations(id, goal, status, intake_id, created_at) VALUES(?,?,?,?,?)",
                (iid, goal, "planned", intake_id, now)
            )
            con.commit()
            _log(project, "iteration plan", f"{iid} {goal}")
            print(f"✓ iteration {iid} planned")
            print(f"  next: hssd iteration activate {iid}")
            return 0

        if args.action == "activate":
            if not args.ids:
                print("BLOCK: provide one or more iteration ids", file=sys.stderr); return 1
            activated = []
            for iid in args.ids:
                row = con.execute("SELECT id, status FROM iterations WHERE id=?", (iid,)).fetchone()
                if not row:
                    print(f"  SKIP: {iid} not found")
                    continue
                con.execute("UPDATE iterations SET status='active' WHERE id=?", (iid,))
                activated.append(iid)
            con.commit()
            n = len(activated)
            _log(project, "iteration activate", f"{n} iterations: {' '.join(activated)}")
            if n == 1:
                print(f"✓ {activated[0]} activated — 1 engineering loop started")
            else:
                print(f"✓ {n} iterations activated in parallel: {', '.join(activated)}")
                print("  caller manages orchestration — each runs its own P0→P4 loop")
            return 0

        if args.action == "converge":
            # args.ids may capture the id when ids (nargs="*") is greedy
            converge_id = args.id or (args.ids[0] if args.ids else None)
            if not converge_id:
                print("BLOCK: provide an iteration id", file=sys.stderr); return 1
            con.execute("UPDATE iterations SET status='done' WHERE id=?", (converge_id,))
            con.commit()
            _log(project, "iteration converge", converge_id)
            print(f"✓ iteration {converge_id} marked done — worktree ready to merge")
            return 0

        print(f"unknown action: {args.action}", file=sys.stderr)
        return 1
    finally:
        con.close()


def _union_lines(target: Path, incoming: str) -> None:
    """Additive union of lines (e.g., .gitignore)."""
    existing = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
    have = set(existing)
    additions = [ln for ln in incoming.splitlines() if ln.strip() and ln not in have]
    if additions:
        target.write_text("\n".join(existing + additions) + "\n", encoding="utf-8")


def _deep_merge(base: object, incoming: object, conflicts: list[str], path: str) -> object:
    """Dicts merge, lists union, equal scalars keep; scalar conflicts kept (always-first) + recorded."""
    if isinstance(base, dict) and isinstance(incoming, dict):
        for k, v in incoming.items():
            base[k] = _deep_merge(base[k], v, conflicts, f"{path}.{k}") if k in base else v
        return base
    if isinstance(base, list) and isinstance(incoming, list):
        return base + [x for x in incoming if x not in base]
    if base == incoming:
        return base
    conflicts.append(f"{path}: kept {base!r} over {incoming!r}")
    return base


def _merge_json(target: Path, incoming_text: str, conflicts: list[str]) -> None:
    incoming = json.loads(incoming_text)
    merged = (
        _deep_merge(json.loads(target.read_text(encoding="utf-8")), incoming, conflicts, target.name)
        if target.exists()
        else incoming
    )
    target.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")


def cmd_template(args: argparse.Namespace) -> int:
    if args.action == "list":
        for t in _full_catalog():
            tech = ", ".join(t.get("tech", []))
            print(f"{t.get('source', '?'):<8} {t['name']:<32} {tech:<26} {t.get('url', '')}")
        print("\nAny git URL works too:  hssd new <name> --from=<git-url>  |  "
              "hssd template import --from=<git-url>")
        return 0

    if args.action == "add":  # register a template YOU trust (non-official), reusable everywhere
        if not (args.name and args.from_git):
            print("BLOCK: add needs --name and --from=<git-url>", file=sys.stderr)
            return 1
        known = {e.get("url"): e.get("source", "user") for e in _full_catalog()}
        if args.from_git in known:  # dedup against the FULL catalog (blessed + user)
            print(f"already known ({known[args.from_git]} catalog) — no need to re-register: {args.from_git}")
            return 0
        cat = _load_user_catalog()
        tech = [t.strip() for t in (args.tech or "").split(",") if t.strip()]
        cat.append({"name": args.name, "url": args.from_git, "tech": tech})
        p = _user_catalog_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cat, indent=2), encoding="utf-8")
        print(f"OK: registered '{args.name}' -> {args.from_git}\n  use it: hssd new <name> --from={args.from_git}")
        return 0

    if args.action == "rm":  # remove one of YOUR registered templates (blessed ones aren't removable)
        if not (args.name or args.from_git):
            print("BLOCK: rm needs --name or --from=<git-url>", file=sys.stderr)
            return 1
        cat = _load_user_catalog()
        kept = [e for e in cat if e.get("name") != args.name and e.get("url") != args.from_git]
        if len(kept) == len(cat):
            print(f"not in your registry: {args.name or args.from_git}")
            return 0
        _user_catalog_path().write_text(json.dumps(kept, indent=2), encoding="utf-8")
        print(f"OK: removed {len(cat) - len(kept)} entry(ies) from your registry")
        return 0

    # import: clone the template repo, then compose it into the project (additive merge).
    if not args.from_git:
        print("BLOCK: import needs --from=<git-url> (see 'hssd template list')", file=sys.stderr)
        return 1
    project = Path(args.into or ".").resolve()
    tmp = Path(tempfile.mkdtemp())
    incoming_root = tmp / "incoming"
    subprocess.run(["git", "clone", "--depth", "1", args.from_git, str(incoming_root)], check=True)
    shutil.rmtree(incoming_root / ".git", ignore_errors=True)

    conflicts: list[str] = []
    for f in sorted(incoming_root.rglob("*")):
        if f.is_dir():
            continue
        rel = f.relative_to(incoming_root)
        if rel.parts and rel.parts[0] == "dotfiles":
            target = project / DOTFILE_MAP.get(rel.name, rel.name)
        else:
            target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        text = f.read_text(encoding="utf-8", errors="replace")
        if target.name == ".gitignore":
            _union_lines(target, text)                      # additive
        elif target.suffix == ".json":
            _merge_json(target, text, conflicts)            # deep merge / list union
        elif not target.exists():
            shutil.copy(f, target)                          # create-if-absent (default)
        else:
            conflicts.append(f"{target.name}: kept existing (text file, not auto-merged)")

    policy = "prompt"
    hy = project / "hssd.yaml"
    if hy.exists():
        for line in hy.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("conflict_policy:"):
                policy = line.split(":", 1)[1].strip()
    _log(project, "template import", f"src={args.from_git} conflicts={len(conflicts)}")
    if conflicts:
        print(f"composed with {len(conflicts)} conflict(s) [policy={policy}]:")
        for c in conflicts:
            print(f"  - {c}")
    else:
        print("composed cleanly (additive merge, no conflicts)")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


def _rmtree_git(path: Path) -> None:
    """Remove a .git directory robustly on Windows (clears read-only bits before deletion)."""
    if not path.exists():
        return
    if path.is_file():
        path.unlink(missing_ok=True)
        return

    def _on_error(func, path_str, exc_info):
        """Clear read-only flag and retry on Windows PermissionError."""
        try:
            import stat
            os.chmod(path_str, stat.S_IWRITE)
            func(path_str)
        except Exception:
            pass

    shutil.rmtree(str(path), onerror=_on_error)


def cmd_skill(args: argparse.Namespace) -> int:
    """list / import / register skills (blessed catalog + your own; any git URL)."""
    if args.action == "list":
        for s in _full_skill_catalog():
            tech = ", ".join(s.get("tech", []))
            print(f"{s.get('source', '?'):<8} {s['name']:<32} {tech:<26} {s.get('url', '')}")
        return 0

    if args.action == "add":
        if not (args.name and args.from_git):
            print("BLOCK: add needs --name and --from=<git-url>", file=sys.stderr)
            return 1
        known = {e.get("url"): e.get("source", "user") for e in _full_skill_catalog()}
        if args.from_git in known:
            print(f"already known ({known[args.from_git]} catalog) — no need to re-register: {args.from_git}")
            return 0
        cat = _load_skill_user_catalog()
        tech = [t.strip() for t in (args.tech or "").split(",") if t.strip()]
        cat.append({"name": args.name, "url": args.from_git, "tech": tech})
        p = _skill_user_catalog_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cat, indent=2), encoding="utf-8")
        print(f"OK: registered '{args.name}' -> {args.from_git}")
        return 0

    if args.action == "rm":
        if not (args.name or args.from_git):
            print("BLOCK: rm needs --name or --from=<git-url>", file=sys.stderr)
            return 1
        cat = _load_skill_user_catalog()
        kept = [e for e in cat
                if not (e.get("name") == args.name
                        or (args.from_git and e.get("url") == args.from_git))]
        if len(kept) == len(cat):
            print(f"not in your registry: {args.name or args.from_git}")
            return 0
        _skill_user_catalog_path().write_text(json.dumps(kept, indent=2), encoding="utf-8")
        print(f"OK: removed {len(cat) - len(kept)} entry(ies) from your skill registry")
        return 0

    # import: clone the skill repo and install it into the project (create-if-absent).
    if args.action == "import":
        if not args.from_git:
            print("BLOCK: import needs --from=<git-url>", file=sys.stderr)
            return 1
        project = Path(args.into or ".").resolve()
        if args.into and not project.exists():
            print(f"BLOCK: --into directory does not exist: {project}", file=sys.stderr)
            return 1
        tmp = Path(tempfile.mkdtemp())
        try:
            incoming_root = tmp / "incoming"
            subprocess.run(["git", "clone", "--depth", "1", args.from_git, str(incoming_root)],
                           check=True, capture_output=True)
            # Remove .git — handles read-only pack files on Windows
            _rmtree_git(incoming_root / ".git")

            # Resolve name
            repo_dir_name = Path(args.from_git.rstrip("/")).name
            # strip .git suffix if present
            if repo_dir_name.endswith(".git"):
                repo_dir_name = repo_dir_name[:-4]
            name = args.name if args.name else _slug(repo_dir_name.removeprefix("hssd-skill-"))

            if not name:
                print("BLOCK: resolved skill name is empty (repo name after prefix strip is blank)",
                      file=sys.stderr)
                return 1
            if name in _blessed_skill_names():
                print(f"BLOCK: '{name}' is a framework-shipped skill name — cannot import over it "
                      f"(it would be overwritten on next 'hssd sync')", file=sys.stderr)
                return 1
            if not (incoming_root / "SKILL.md").exists():
                print("BLOCK: repo has no SKILL.md at its root (nested SKILL.md not accepted)",
                      file=sys.stderr)
                return 1

            dest = project / ".claude" / "skills" / name
            created, kept = _mirror_if_absent(incoming_root, dest)
            # Ensure no .git artifacts landed in the destination
            _rmtree_git(dest / ".git")
            print(f"OK: skill '{name}' installed (created {created}, skipped {kept})")
            return 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print(f"BLOCK: unknown skill action: {args.action}", file=sys.stderr)
    return 1


def cmd_log(args: argparse.Namespace) -> int:
    logf = Path(".harness/logs/session.log")
    if not logf.exists():
        print("(no session log yet)")
        return 0
    print(logf.read_text(encoding="utf-8"), end="")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Dev-time, token, and cost analytics from .harness/logs/metrics.jsonl."""
    rows = _load_metrics(Path(".").resolve())
    if not rows:
        print("(no metrics yet — run an agent step, e.g. 'hssd overview analyze')")
        return 0
    t = _totals(rows)
    print(f"AI calls:         {t['calls']}")
    print(f"Agent wall time:  {t['wall_s']:.1f}s")
    if t["span"]:
        print(f"Elapsed (span):   {t['span']}")
    print(f"Input tokens:     {int(t['in']):,}  (cache-read {int(t['cache_read']):,})")
    print(f"Output tokens:    {int(t['out']):,}")
    print(f"Cost (USD):       ${t['cost']:.4f}")
    byrole: dict[str, dict] = {}
    for r in rows:
        d = byrole.setdefault(r.get("role", "?"), {"n": 0, "s": 0.0, "in": 0, "out": 0, "cost": 0.0})
        d["n"] += 1
        d["s"] += r.get("duration_s") or 0
        d["in"] += r.get("input_tokens") or 0
        d["out"] += r.get("output_tokens") or 0
        d["cost"] += r.get("cost_usd") or 0
    print("\nBy role:")
    for k, d in sorted(byrole.items()):
        print(f"  {k:<24} {d['n']:>3} calls  {d['s']:>6.1f}s  "
              f"in {int(d['in']):>8,}  out {int(d['out']):>7,}  ${d['cost']:.4f}")
    return 0


AILOG_HUMAN_TEMPLATE = (
    "## Interactions\n\n"
    "> Human-authored. One entry per meaningful prompt YOU issued to an AI tool (Claude Code,\n"
    "> Cursor, Copilot, ...). At least 3 entries for the final submission. Per-entry shape:\n\n"
    "### 1. Human — <ISO date>\n\n"
    "**Prompt:**\n\n```text\n<what you asked>\n```\n\n"
    "**Output (summary):**\n\n```text\n<what came back — a summary is fine>\n```\n\n"
    "**Correction / redirect (if any):** <what you fixed, or \"none\">\n\n"
    "## Corrections & redirections\n\n"
    "> Human-authored. Must not be empty: list each correction/redirect, plus at least one\n"
    "> instance where you checked the AI and it was correct (shows active supervision).\n\n"
    "- <correction or verified-correct instance>\n\n"
    "## Reflection\n\n"
    "> Human-authored. 3-5 bullets, each grounded in a concrete artifact (work item ID, endpoint,\n"
    "> agent role, error class, filename) — no platitudes.\n\n"
    "- <what the AI was strong at — named instance>\n"
    "- <where it failed you — named instance>\n"
    "- <what you double-checked manually>\n"
)


GOVERNANCE_RUBRIC = (
    "## Canonical acceptance rubric (governance/narrative deliverables — apply as-is, don't re-derive)\n"
    "- **Stub = FAIL.** A required section is a stub if its only non-heading, non-blockquote content "
    "is blank, `—`, `-`, an HTML comment `<!-- ... -->`, or an unfilled placeholder matching "
    "`<...>` (angle-bracket) or `_(...)_` (markdown italic). Any real sentence passes.\n"
    "- **Floors.** Interactions: at least 3 numbered entries (`^### [0-9]` *within the Interactions "
    "section only*). Corrections: at least 1 real entry. Reflection: 3-5 bullets, each naming a "
    "concrete artifact (work-item id, endpoint, agent role, error class, or filename).\n"
    "- **Scope counts to the section** (e.g. `sed -n '/^## Interactions/,/^## /p' FILE | grep -c "
    "'^### [0-9]'`), never the whole file.\n"
    "- All checks are reviewer-applicable (human or LLM); no deterministic automated test is required."
)


def cmd_ailog(args: argparse.Namespace) -> int:
    """Render docs/AI_LOG.md. AUTO: Summary + Appendix (harness agent calls) from metrics.jsonl.
    HUMAN (preserved across re-runs): Interactions, Corrections, Reflection."""
    project = Path(".").resolve()
    rows = _load_metrics(project)
    out = project / "docs" / "AI_LOG.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    # Preserve the HUMAN middle (Interactions → Corrections → Reflection) across regenerations.
    human = AILOG_HUMAN_TEMPLATE
    if out.exists():
        old = out.read_text(encoding="utf-8")
        i, j = old.find("## Interactions"), old.find("## Appendix")
        if i != -1:
            human = old[i:(j if j != -1 else len(old))].rstrip() + "\n"

    t = _totals(rows)
    span = f" (elapsed span {t['span']})" if t["span"] else ""
    by: dict[str, dict] = {}
    for r in rows:
        d = by.setdefault(r.get("role", "?"), {"n": 0, "in": 0, "out": 0, "cost": 0.0})
        d["n"] += 1
        d["in"] += r.get("input_tokens") or 0
        d["out"] += r.get("output_tokens") or 0
        d["cost"] += r.get("cost_usd") or 0

    lines = [
        "# AI Interaction Log", "",
        "> **Interactions**, **Corrections**, and **Reflection** are human-authored (preserved "
        "across re-runs). `hssd ailog` regenerates **Summary** and the **Appendix** (harness agent "
        "calls) from `.harness/logs/metrics.jsonl`.", "",
        "## Summary", "",
        f"- Harness AI calls: **{t['calls']}**",
        f"- Agent wall time: **{t['wall_s']:.1f}s**{span}",
        f"- Tokens in/out: **{int(t['in']):,} / {int(t['out']):,}** (cache-read {int(t['cache_read']):,})",
        f"- Cost: **${t['cost']:.4f}**", "",
        human.rstrip(), "",
        "## Appendix — Harness agent calls (auto from metrics.jsonl)", "",
        "Harness-internal governance/agent calls — **not** part of the Interactions count above.", "",
        "| Role | Calls | Tokens in | Tokens out | Cost |",
        "|---|--:|--:|--:|--:|",
    ]
    lines += [f"| `{k}` | {d['n']} | {int(d['in']):,} | {int(d['out']):,} | ${d['cost']:.4f} |"
              for k, d in sorted(by.items())] or ["| _(none yet)_ | | | | |"]
    lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK: wrote {out}. Summary + Appendix auto; fill Interactions/Corrections/Reflection by hand.")
    return 0


def _pm(project: Path) -> sqlite3.Connection:
    """Open (and init) the local PM spine. The PM Port's default backend."""
    path = project / ".harness" / "pm.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA busy_timeout=5000")
    con.execute(
        "CREATE TABLE IF NOT EXISTS work_items ("
        "id TEXT PRIMARY KEY, title TEXT NOT NULL, type TEXT NOT NULL DEFAULT 'feature', "
        "status TEXT NOT NULL DEFAULT 'open', assignee TEXT, branch TEXT, lane TEXT, "
        "created_at TEXT NOT NULL, source TEXT, fingerprint TEXT)"
    )
    # Sprints are the bounded, terminating unit of work; the PROJECT is long-lived and never 'done'.
    # A sprint pulls a scope from the product backlog (work_items) and runs to closed.
    con.execute(
        "CREATE TABLE IF NOT EXISTS sprints ("
        "id TEXT PRIMARY KEY, goal TEXT, status TEXT NOT NULL DEFAULT 'active', "
        "opened_at TEXT NOT NULL, closed_at TEXT)"
    )
    for col in ("source TEXT", "fingerprint TEXT", "sprint_id TEXT"):  # upgrade older DBs in place
        try:
            con.execute(f"ALTER TABLE work_items ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
    con.execute(
        "CREATE TABLE IF NOT EXISTS intakes ("
        "id TEXT PRIMARY KEY, title TEXT NOT NULL, brief_path TEXT, "
        "status TEXT NOT NULL DEFAULT 'draft', "
        "created_at TEXT NOT NULL)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS iterations ("
        "id TEXT PRIMARY KEY, goal TEXT, status TEXT NOT NULL DEFAULT 'planned', "
        "intake_id TEXT, created_at TEXT NOT NULL)"
    )
    # upgrade older DBs
    for col in ("intake_id TEXT",):
        try:
            con.execute(f"ALTER TABLE iterations ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
    con.commit()
    return con


def _current_sprint(con: sqlite3.Connection) -> tuple | None:
    """The latest sprint that hasn't closed (the one you're iterating in), or None."""
    try:
        return con.execute(
            "SELECT id, goal, status FROM sprints WHERE status != 'closed' "
            "ORDER BY opened_at DESC LIMIT 1"
        ).fetchone()
    except sqlite3.OperationalError:
        return None


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def _git_switch(branch: str) -> None:
    """Switch to `branch`, creating it if needed — idempotent across resets (no 'already exists')."""
    made = subprocess.run(["git", "checkout", "-q", "-b", branch], capture_output=True, text=True)
    if made.returncode != 0:
        subprocess.run(["git", "checkout", "-q", branch], check=False)


# ── Project state machine ───────────────────────────────────────────────────────
# One blessed order, each step guarding the next:
#   initialized → briefed → architected (human-locked) → planned → in_progress → delivered
# Nothing engineers before the architecture is locked. The phase is INFERRED from the
# artifacts on disk + the architecture lock, so `hssd status` always shows the truth,
# never a flag that drifted out of sync.

def _locks_dir(project: Path) -> Path:
    return project / ".harness" / "locks"


def _arch_lock_path(project: Path) -> Path:
    return _locks_dir(project) / "architecture.json"


def _adr_path(project: Path) -> Path:
    return project / "docs" / "ADR.md"  # the LIVING, current architecture (canonical name)


def _adr_versions_dir(project: Path) -> Path:
    return project / "docs" / "adr"  # immutable snapshots: ADR-v1.md, ADR-v2.md, ...


def _next_adr_version(project: Path) -> int:
    d = _adr_versions_dir(project)
    existing = [int(m.group(1)) for f in d.glob("ADR-v*.md")
                if (m := re.match(r"ADR-v(\d+)\.md$", f.name))] if d.exists() else []
    return (max(existing) + 1) if existing else 1


def _strip_to_heading(text: str) -> str:
    """Drop any leading narration an agent prefaces before the actual Markdown (the ADR starts at
    the first heading). Keeps the saved proposal clean instead of carrying 'Here is the ADR:' prose."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("#"):
            return "\n".join(lines[i:]).strip() + "\n"
    return text.strip() + "\n"


def _architecture_locked(project: Path) -> bool:
    return _arch_lock_path(project).exists()


def _is_project_identified(project: Path) -> bool:
    """True when project.md has been human-approved (project.json lock exists)."""
    return (project / ".harness" / "locks" / "project.json").exists()


def _detect_project_size(dest: Path) -> str:
    """Returns 'blank', 'substantial', or 'ambiguous' by scanning source files + manifests."""
    sig_exts = {".py", ".ts", ".js", ".go", ".java", ".rb", ".cs", ".php", ".rs", ".swift",
                ".kt", ".scala", ".vue", ".svelte", ".tsx", ".jsx"}
    manifests = {"pyproject.toml", "package.json", "go.mod", "pom.xml", "Cargo.toml",
                 "requirements.txt", "Gemfile", "composer.json", "build.gradle"}
    source_files: list[Path] = []
    found_manifests: list[str] = []
    try:
        for f in dest.rglob("*"):
            if not f.is_file():
                continue
            # skip hidden dirs and common noise
            parts = f.relative_to(dest).parts
            if any(p.startswith(".") or p in ("node_modules", "__pycache__", ".venv", "venv") for p in parts):
                continue
            if f.suffix in sig_exts:
                source_files.append(f)
            if f.name in manifests:
                found_manifests.append(f.name)
    except PermissionError:
        pass
    if found_manifests or len(source_files) > 5:
        return "substantial"
    if len(source_files) == 0:
        return "blank"
    return "ambiguous"


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _adr_is_stub(body: str) -> bool:
    """True while docs/ADR.md is still the scaffold template (headings + blockquote guidance +
    <angle-bracket placeholders>) rather than a filled decision record. `approve` must reject it.
    Counts SUBSTANTIVE content lines (real prose/table cells), ignoring headings, '>' guidance and
    placeholder lines — the init template scores ~0, a real ADR scores well above the floor."""
    real = 0
    for raw in body.splitlines():
        ln = raw.strip()
        if not ln or ln.startswith("#") or ln.startswith(">"):
            continue                          # heading or blockquote guidance
        if "<" in ln and ">" in ln:
            continue                          # an <angle-bracket placeholder> line/cell
        core = re.sub(r"[|>\-*_`\s]", "", ln)  # strip markdown furniture (tables, bullets, emphasis)
        if len(core) >= 15 and re.search(r"[A-Za-z]", core):
            real += 1
    return real < 6


# The PROJECT state machine is NON-TERMINAL: after the foundation it enters 'operational' and stays
# there for life (development → deploy → maintenance → more features). What terminates is a SPRINT.
_STATE_ORDER = ["initialized", "identified", "architected", "operational"]


def _project_state(project: Path) -> dict:
    """Infer the project phase. The project never reaches a terminal 'done':
    once operational it runs intake cycles forever."""
    h = project / ".harness"
    s = {
        "initialized": h.exists(),
        "identified": _is_project_identified(project),
        "architected": _architecture_locked(project),
        "operational": False,
    }
    sprint = None
    sprint_items: list[str] = []
    pm = h / "pm.sqlite"
    if pm.exists():
        con = sqlite3.connect(pm)
        try:
            try:
                n_intakes = con.execute(
                    "SELECT COUNT(*) FROM intakes WHERE status='approved'"
                ).fetchone()[0]
                s["operational"] = s["architected"] and n_intakes > 0
            except sqlite3.OperationalError:
                # intakes table not yet migrated — fall back to sprint count
                try:
                    n_sprints = con.execute("SELECT COUNT(*) FROM sprints").fetchone()[0]
                    s["operational"] = s["architected"] and n_sprints > 0
                except sqlite3.OperationalError:
                    pass
            sprint = _current_sprint(con)
            if sprint:
                sprint_items = [r[0] for r in con.execute(
                    "SELECT status FROM work_items WHERE sprint_id=?", (sprint[0],))]
        except sqlite3.OperationalError:
            pass
        finally:
            con.close()
    if not s["initialized"]:
        phase = "not_initialized"
    elif not s["identified"]:
        phase = "initialized"
    elif not s["architected"]:
        phase = "identified"
    elif not s["operational"]:
        phase = "architected"
    else:
        phase = "operational"
    s["phase"] = phase
    s["sprint"] = sprint
    s["sprint_items"] = sprint_items
    return s


def _project_next(project: Path, s: dict) -> str:
    phase = s["phase"]
    base = {
        "not_initialized": "hssd init",
        "initialized":     "hssd project approve   (after writing / reviewing .harness/project.md)",
        "identified":      "hssd overview architect  →  hssd architecture approve",
        "architected":     "hssd intake add <brief.md>   (first intake → operational)",
    }
    if phase in base:
        return base[phase]
    sprint = s["sprint"]
    if not sprint:
        return "hssd intake add <brief.md>   (or: hssd sprint plan)"
    _sid, _goal, sstatus = sprint
    if sstatus == "review":
        return "hssd sprint close"
    items = s["sprint_items"]
    if items and all(x == "done" for x in items):
        return "hssd sprint review"
    return "hssd engage <id>   (a story in the current sprint)"


def _write_state_snapshot(project: Path, s: dict) -> None:
    """Persist a snapshot for external tools (the inferred phase remains the source of truth)."""
    p = project / ".harness" / "state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    snap = {"phase": s["phase"], "milestones": {k: s[k] for k in _STATE_ORDER},
            "sprint": list(s["sprint"]) if s.get("sprint") else None,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    p.write_text(json.dumps(snap, indent=2), encoding="utf-8")


def cmd_status(args: argparse.Namespace) -> int:
    """Show the project state machine (foundation → operational, never 'done') + the current sprint."""
    project = Path(".").resolve()
    s = _project_state(project)
    _write_state_snapshot(project, s)
    print("Harness Studio · project state\n")
    rows = [
        ("initialized",  "initialized",  "repo adopted (hssd init ran)"),
        ("identified",   "identified",   "project.md approved (human)"),
        ("architected",  "architected",  "architecture locked (human)"),
        ("operational",  "operational",  "live — intake cycles, never 'done'"),
    ]
    # show not_initialized if not yet init
    if not s["initialized"]:
        print("  ▸ not_initialized   run hssd init to get started")
    for key, label, desc in rows:
        mark = "✓" if s[key] else ("▸" if s["phase"] == key else "·")
        here = "   ← project is here" if s["phase"] == key else ""
        print(f"  {mark} {label:<13} {desc}{here}")
    sprint = s["sprint"]
    print()
    if sprint:
        sid, goal, sstatus = sprint
        items = s["sprint_items"]
        done = sum(1 for x in items if x == "done")
        print(f"  ▶ sprint {sid} · {goal or '(no goal)'} — {sstatus.upper()}  "
              f"[{done}/{len(items)} done]")
    elif s["operational"]:
        print("  (no open sprint)")
    print(f"\n  next: {_project_next(project, s)}")
    return 0


def cmd_architecture(args: argparse.Namespace) -> int:
    """The human lock over the SHARED architecture. The system proposes (hssd overview architect);
    the engineer iterates and owns docs/ADR.md; this records the approval that unlocks split."""
    project = Path(".").resolve()
    adr = _adr_path(project)
    lock = _arch_lock_path(project)

    if args.action == "status":
        if not lock.exists():
            print("architecture: NOT locked. Draft + iterate with `hssd overview architect`, then "
                  "`hssd architecture approve`.")
            return 0
        meta = json.loads(lock.read_text(encoding="utf-8"))
        ver = meta.get("version")
        vstr = f" · v{ver}" if ver else ""
        print(f"architecture: LOCKED{vstr} {meta.get('locked_at', '?')} (by {meta.get('by', '?')})")
        if ver:
            print(f"  current: docs/ADR.md   snapshot: docs/adr/ADR-v{ver}.md")
        if _file_sha(adr) != meta.get("adr_sha256", ""):
            print("  ⚠ docs/ADR.md changed since the lock — re-approve to cut a new version (or it's stale).")
        return 0

    if args.action == "reopen":
        if lock.exists():
            lock.unlink()
            _log(project, "architecture reopen", "lock cleared")
            print("architecture: reopened (lock cleared). Amend docs/ADR.md, then re-approve.")
        else:
            print("architecture: already open (no lock).")
        return 0

    # approve — the human lock
    if not adr.exists():
        print("BLOCK: docs/ADR.md does not exist. Run `hssd overview architect` to draft it, "
              "iterate, then approve.", file=sys.stderr)
        return 1
    body = adr.read_text(encoding="utf-8").strip()
    if len(body) < 120 or _adr_is_stub(body):
        print("BLOCK: docs/ADR.md still looks like a stub. Fill in the data model, ownership, tier "
              "and key decisions before approving.", file=sys.stderr)
        return 1
    # Snapshot an immutable version (audit trail of how the architecture evolved across sprints),
    # then retire the scratch draft so only the living docs/ADR.md + the versions remain.
    version = _next_adr_version(project)
    vdir = _adr_versions_dir(project)
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / f"ADR-v{version}.md").write_text(adr.read_text(encoding="utf-8"), encoding="utf-8")
    (project / "docs" / "ADR.draft.md").unlink(missing_ok=True)  # proposal consumed; no stale draft
    _locks_dir(project).mkdir(parents=True, exist_ok=True)
    meta = {"locked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "by": os.environ.get("USER") or os.environ.get("USERNAME") or "engineer",
            "version": version, "adr_path": "docs/ADR.md",
            "snapshot": f"docs/adr/ADR-v{version}.md", "adr_sha256": _file_sha(adr)}
    lock.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    _log(project, "architecture approve", f"v{version} {meta['adr_sha256'][:12]}")
    print(f"✓ architecture LOCKED · v{version}. docs/ADR.md is the living contract; "
          f"docs/adr/ADR-v{version}.md is the immutable snapshot.")
    print("  next: hssd overview analyze → split   (stories inherit the ADR)")
    return 0


def cmd_sprint(args: argparse.Namespace) -> int:
    """Sprints — the bounded, terminating unit of delivery. The PROJECT never finishes; sprints do.
    plan → (engage the stories) → review (fix-the-harness retro) → close. A sprint pulls its scope
    from the product backlog (work items not yet assigned to any sprint)."""
    project = Path(".").resolve()
    con = _pm(project)

    if args.action == "status":
        cur = _current_sprint(con)
        if not cur:
            closed = con.execute("SELECT COUNT(*) FROM sprints WHERE status='closed'").fetchone()[0]
            print(f"No open sprint ({closed} closed). Open one with `hssd sprint plan`.")
            return 0
        sid, goal, sstatus = cur
        print(f"sprint {sid} · {goal or '(no goal)'} — {sstatus.upper()}")
        for r in con.execute(
                "SELECT id, title, status FROM work_items WHERE sprint_id=? ORDER BY id", (sid,)):
            mark = {"done": "✓", "in-progress": "▸"}.get(r[2], "·")
            print(f"  {mark} {r[0]}  {r[1]}  [{r[2]}]")
        return 0

    if args.action == "plan":
        if not _architecture_locked(project):
            print("BLOCK: lock the architecture first (hssd overview architect → approve).",
                  file=sys.stderr)
            return 1
        open_cur = _current_sprint(con)
        if open_cur:
            print(f"BLOCK: sprint {open_cur[0]} is still '{open_cur[2]}'. Close it "
                  "(hssd sprint review → close) before opening another.", file=sys.stderr)
            return 1
        scope = [r[0] for r in con.execute(
            "SELECT id FROM work_items WHERE sprint_id IS NULL AND status != 'done' "
            "AND (lane IS NULL OR lane != 'config')")]
        if not scope:
            print("BLOCK: nothing to plan — no unassigned open items in the backlog. Split the brief "
                  "or add items (hssd work add / janitor) first.", file=sys.stderr)
            return 1
        sid = f"SPR-{con.execute('SELECT COUNT(*) FROM sprints').fetchone()[0] + 1}"
        con.execute("INSERT INTO sprints(id, goal, status, opened_at) VALUES(?,?,'active',?)",
                    (sid, args.goal or "", datetime.datetime.now(datetime.timezone.utc).isoformat()))
        con.executemany("UPDATE work_items SET sprint_id=? WHERE id=?", [(sid, i) for i in scope])
        con.commit()
        _log(project, "sprint plan", f"{sid} scope={len(scope)}")
        print(f"▶ opened {sid} · {args.goal or '(no goal)'} with {len(scope)} item(s): "
              f"{', '.join(scope)}")
        print("\n  Architecture-delta check: if any item needs a NEW table/entity or isolation rule, "
              "amend FIRST — `hssd architecture reopen` → edit docs/ADR.md → approve (cuts v+1). "
              "If it all fits the locked ADR, just engage.")
        print(f"  next: hssd engage {scope[0]}")
        return 0

    if args.action == "review":
        cur = _current_sprint(con)
        if not cur:
            print("BLOCK: no open sprint to review.", file=sys.stderr)
            return 1
        sid = cur[0]
        pending = [i for i, st in con.execute(
            "SELECT id, status FROM work_items WHERE sprint_id=?", (sid,)) if st != "done"]
        if pending and not args.force:
            print(f"BLOCK: {len(pending)} item(s) not done: {', '.join(pending)}. Finish them "
                  "(hssd engage <id>) or --force.", file=sys.stderr)
            return 1
        con.execute("UPDATE sprints SET status='review' WHERE id=?", (sid,))
        con.commit()
        _log(project, "sprint review", sid)
        print(f"sprint {sid} → REVIEW. Retro (fix-the-harness): for every defect that ESCAPED a gate "
              "this sprint, add a guard so it can't recur — that is the framework's core loop.")
        print("  then: hssd sprint close")
        return 0

    if args.action == "close":
        cur = _current_sprint(con)
        if not cur:
            print("BLOCK: no open sprint to close.", file=sys.stderr)
            return 1
        sid, _goal, sstatus = cur
        if sstatus != "review" and not args.force:
            print(f"BLOCK: {sid} is '{sstatus}', not 'review'. Run `hssd sprint review` first "
                  "(or --force).", file=sys.stderr)
            return 1
        con.execute("UPDATE sprints SET status='closed', closed_at=? WHERE id=?",
                    (datetime.datetime.now(datetime.timezone.utc).isoformat(), sid))
        con.commit()
        _log(project, "sprint close", sid)
        print(f"✓ sprint {sid} CLOSED — increment shipped. The project stays operational; open the "
              "next round with `hssd sprint plan`.")
        return 0
    return 1


def cmd_work(args: argparse.Namespace) -> int:
    project = Path(".").resolve()
    con = _pm(project)

    if args.action == "add":
        if not args.title:
            print("BLOCK: --title required", file=sys.stderr)
            return 1
        n = con.execute("SELECT COUNT(*) FROM work_items").fetchone()[0] + 1
        wid = f"LOC-{n}"
        con.execute(
            "INSERT INTO work_items(id, title, type, status, created_at) VALUES(?,?,?,'open',?)",
            (wid, args.title, args.type, datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )
        con.commit()
        _log(project, "work add", wid)
        print(f"OK: {wid} · {args.title}")
        return 0

    if args.action == "list":
        q = "SELECT id, status, type, lane, assignee, title FROM work_items"
        params: tuple[str, ...] = ()
        if args.status:
            q += " WHERE status=?"
            params = (args.status,)
        rows = con.execute(q + " ORDER BY rowid", params).fetchall()  # creation order, not lexical
        if not rows:
            print("(no work items)")
            return 0
        for r in rows:
            print(f"{r[0]:<8} {r[1]:<12} {r[2]:<9} {(r[3] or '-'):<9} {(r[4] or '-'):<8} {r[5]}")
        return 0

    if args.action == "show":
        r = con.execute("SELECT * FROM work_items WHERE id=?", (args.id,)).fetchone()
        print(r if r else f"{args.id} not found")
        return 0

    if args.action == "done":
        # State primitive for the MAESTRO runner: mark a story delivered after it ran the phases
        # (red→green, P4 dry) and the human approved merge. The CLI runner (`hssd engage`) sets this
        # itself; the maestro calls it here so both runners record completion on the same spine.
        if not args.id:
            print("BLOCK: work done needs <id>", file=sys.stderr)
            return 1
        if not con.execute("SELECT 1 FROM work_items WHERE id=?", (args.id,)).fetchone():
            print(f"BLOCK: {args.id} not found", file=sys.stderr)
            return 1
        con.execute("UPDATE work_items SET status='done' WHERE id=?", (args.id,))
        con.commit()
        _log(project, "work done", args.id)
        print(f"OK: {args.id} marked done.")
        return 0

    # claim — atomic compare-and-swap on status (race-safe on the local spine)
    row = con.execute("SELECT title, status FROM work_items WHERE id=?", (args.id,)).fetchone()
    if not row:
        print(f"BLOCK: {args.id} not found", file=sys.stderr)
        return 1
    branch = f"harness/local-{args.id.lower()}-{_slug(row[0])}"
    cur = con.execute(
        "UPDATE work_items SET status='in-progress', assignee=?, branch=? WHERE id=? AND status='open'",
        (args.who, branch, args.id),
    )
    con.commit()
    if cur.rowcount == 0:
        print(f"BLOCK: {args.id} already claimed (status={row[1]})", file=sys.stderr)
        return 1
    _log(project, "work claim", f"{args.id} -> {branch}")
    _git_switch(branch)  # idempotent: re-claim after a reset reuses the existing branch (no silent fail)
    print(f"OK: claimed {args.id} · branch {branch}")
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    """Reset to re-run: one work item, all engineered items, or the whole backlog.

    Keeps logs/metrics (the audit trail) unless --hard. Never touches git branches.
    """
    project = Path(".").resolve()
    con = _pm(project)
    harness = project / ".harness"
    eng = harness / "engagements"

    if args.hard or args.backlog:
        con.execute("DELETE FROM work_items")
        con.commit()
        shutil.rmtree(eng, ignore_errors=True)
        (harness / "plan.json").unlink(missing_ok=True)
        if args.hard:
            shutil.rmtree(harness / "logs", ignore_errors=True)  # also clear cost/AI-log history
        _log(project, "reset", "hard" if args.hard else "backlog")
        extra = "; logs/metrics cleared" if args.hard else "; logs/metrics kept"
        print(f"OK: backlog + plan + engagement state cleared (overview kept{extra}). "
              "Re-run: hssd overview analyze → split.")
        return 0

    if args.all:
        con.execute("UPDATE work_items SET status='open', assignee=NULL, branch=NULL "
                    "WHERE lane IS NULL OR lane != 'config'")  # config capabilities stay enabled
        con.commit()
        shutil.rmtree(eng, ignore_errors=True)
        _log(project, "reset", "all")
        print("OK: all engineered work items → open; engagement state cleared "
              "(config stays enabled; logs/metrics kept).")
        return 0

    if not args.id:
        print("BLOCK: reset needs <id>, or --all / --backlog / --hard", file=sys.stderr)
        return 1
    if not con.execute("SELECT 1 FROM work_items WHERE id=?", (args.id,)).fetchone():
        print(f"BLOCK: {args.id} not found", file=sys.stderr)
        return 1
    con.execute("UPDATE work_items SET status='open', assignee=NULL, branch=NULL WHERE id=?", (args.id,))
    con.commit()
    shutil.rmtree(eng / args.id, ignore_errors=True)
    _log(project, "reset", args.id)
    print(f"OK: {args.id} reset to open; its engagement state cleared. Re-claim/engage when ready.")
    print("  (your git branch, if any, is left as-is — delete it manually if you want.)")
    return 0


def _read_agent(role: str) -> str:
    """Load a subagent definition (project override, else the package)."""
    for base in (Path(".claude/agents"), AGENTS):
        f = base / f"{role}.md"
        if f.exists():
            return f.read_text(encoding="utf-8")
    return f"You are the {role}."


def _agent_tools(role: str) -> str:
    """The role's allowed tools (from its frontmatter `tools:` line) → passed to --allowedTools so
    the headless call is least-privilege. Read-only default for roles that declare none."""
    for line in _read_agent(role).splitlines():
        m = re.match(r"\s*tools:\s*(.+)", line)
        if m:
            return ",".join(t.strip() for t in m.group(1).split(",") if t.strip())
    return "Read,Grep,Glob"


# Role -> blessed skills it loads (the CLI does the skill routing / scoping).
# Engineering skills the harness applies as find-and-propose checklists: an adversary loads them to
# CATCH violations (find the error + propose the fix), the architect/builder load them to be correct
# by construction. Encoding these recurring lessons is the "fix the harness, not the code" loop —
# each was a defect caught by hand once (dual-writer race, INSERT OR REPLACE, aiosqlite/BEGIN
# IMMEDIATE, missing busy_timeout, missing indexes, naive datetimes, ad-hoc API shapes), now a
# standing guard the process applies on every engagement.
_ENG_SKILLS = ["sqlite-concurrency", "sql-indexing", "datetime-utc", "api-conventions", "resilience"]
# Architecture/transport preferences sit one level up from the correctness guards: push-over-pull is
# a design choice the architect proposes and the adversary challenges (and the devs implement).
_ARCH_SKILLS = [*_ENG_SKILLS, "push-over-pull"]
ROLE_SKILLS = {
    "architect": ["python", "fastapi", "typescript", *_ARCH_SKILLS],
    "architecture-adversary": _ARCH_SKILLS,
    "test-author": ["python", "fastapi", *_ENG_SKILLS],  # RED step: tests encode the skills' expectations
    "backend-dev": ["python", "fastapi", *_ENG_SKILLS, "push-over-pull"],
    "frontend-dev": ["typescript", "datetime-utc", "api-conventions", "push-over-pull"],
    "test-adversary": _ENG_SKILLS,
}


# Per-engage budget guard — a hard ceiling so a run NEVER loops forever / burns tokens with no
# progress. cmd_engage resets+configures it; _run_role charges every AI call and aborts on breach.
_BUDGET = {"calls": 0, "max_calls": 0, "cost": 0.0, "max_cost": 0.0}


def _budget_tick(cost: float | None) -> None:
    _BUDGET["calls"] += 1
    _BUDGET["cost"] += cost or 0.0
    mc, mx = _BUDGET["max_calls"], _BUDGET["max_cost"]
    if mc and _BUDGET["calls"] >= mc:
        raise SystemExit(
            f"\n⛔ STOP: hit the {mc}-AI-call ceiling (${_BUDGET['cost']:.2f} this run). Not looping "
            "forever — raise with --max-calls=N, or check why it isn't converging. State is saved; "
            "resume with `hssd engage <id>` or clear with `hssd reset <id>`.")
    if mx and _BUDGET["cost"] >= mx:
        raise SystemExit(
            f"\n⛔ STOP: hit the ${mx:.2f} budget ({_BUDGET['calls']} calls this run). Raise with "
            "--budget=USD. State is saved; resume or `hssd reset <id>`.")


def _claude_argv(exe: str, fmt: str, allowed: str | None = None) -> list[str]:
    argv = [exe, "-p", "--output-format", fmt]
    # NOTE: do NOT add --bare by default — it also disables credential/settings discovery, so
    # subscription (login) auth breaks with "Not logged in". Recursion is instead prevented by
    # --allowedTools (analysts/adversaries get no Bash → can't shell out to hssd) + a prompt guard.
    # HSSD_BARE=1 opts into full isolation for users on ANTHROPIC_API_KEY auth.
    if os.environ.get("HSSD_BARE", "0") == "1":
        argv.append("--bare")
    if allowed:  # least-privilege: the role only gets its declared tools (no Bash → can't shell out)
        argv += ["--allowedTools", allowed]
    if fmt == "stream-json":
        argv.append("--verbose")  # stream-json requires --verbose
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        argv = ["cmd", "/c", *argv]  # CreateProcess can't launch a .cmd shim directly
    return argv


def _claude_blocking(exe: str, composed: str, allowed: str | None = None):
    """Single blocking JSON call (fallback / HSSD_STREAM=0). Returns (text, usage, cost, api_ms)."""
    res = subprocess.run(_claude_argv(exe, "json", allowed), input=composed, capture_output=True,
                         text=True, encoding="utf-8", errors="replace", check=False)
    raw = (res.stdout or "").strip()
    if not raw and (res.stderr or "").strip():
        print(f"  (claude stderr) {res.stderr.strip()[:500]}", file=sys.stderr)
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return (obj.get("result", raw), obj.get("usage") or {},
                    obj.get("total_cost_usd"), obj.get("duration_ms"))
    except json.JSONDecodeError:
        pass
    return raw, {}, None, None


def _claude_stream(exe: str, composed: str, role: str, allowed: str | None = None):
    """Run `claude -p --output-format stream-json` and surface the interaction LIVE so a terminal
    user isn't in the dark. Returns (text, usage, cost, api_ms)."""
    proc = subprocess.Popen(_claude_argv(exe, "stream-json", allowed), stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    if proc.stdin:
        proc.stdin.write(composed)
        proc.stdin.close()
    text, usage, cost, api_ms = "", {}, None, None
    print(f"    · {role} ▸ ", end="", flush=True)
    assert proc.stdout
    for line in proc.stdout:  # newline-delimited JSON events
        s = line.strip()
        if not s:
            continue
        try:
            ev = json.loads(s)
        except json.JSONDecodeError:
            print(f"\n    {s[:200]}", flush=True)  # non-JSON (likely stderr) — surface it
            continue
        et = ev.get("type")
        if et == "assistant":
            for blk in ((ev.get("message") or {}).get("content") or []):
                if isinstance(blk, dict):
                    if blk.get("type") == "text" and blk.get("text"):
                        sys.stdout.write(blk["text"]); sys.stdout.flush()
                    elif blk.get("type") == "tool_use":
                        _inp = blk.get("input") or {}
                        _hint = next((str(_inp[k])[:90] for k in
                                      ("file_path", "path", "pattern", "command", "query", "url", "notebook_path")
                                      if _inp.get(k)), "")
                        print(f"\n    → {blk.get('name', '?')}{(' ' + _hint) if _hint else ''}", flush=True)
        elif et == "result":
            text = ev.get("result", text)
            usage = ev.get("usage") or {}
            cost = ev.get("total_cost_usd")
            api_ms = ev.get("duration_ms")
    proc.wait()
    print()  # newline after the streamed text
    return text, usage, cost, api_ms


def _run_role(role: str, prompt: str, *, expect_json: bool = False) -> str:
    """Invoke a role as a focused agent. Backend: 'claude' (Claude Code) or 'mock' (tests).

    This is what makes skills + subagents 'work': the role's system prompt and its scoped
    skills are composed, then handed to the AI runtime.
    """
    backend = os.environ.get("HSSD_AGENT_BACKEND", "claude")
    parts = [_read_agent(role)]
    for skill in ROLE_SKILLS.get(role, []):
        sk = AGENTS.parent / "skills" / skill / "SKILL.md"
        if sk.exists():
            parts.append(f"\n# Skill: {skill}\n{sk.read_text(encoding='utf-8')}")
    parts.append(f"\n# Task\n{prompt}")
    if expect_json:
        parts.append("\n\nRespond with ONLY valid JSON, no prose.")
    parts.append("\n\n# Isolation\nYou are a single-purpose Harness Studio role. Do NOT run the "
                 "`hssd` CLI, invoke slash commands or skills, or start another engagement. Perform "
                 "ONLY your role above and return exactly the requested output.")
    composed = "\n".join(parts)

    t0 = time.monotonic()

    if backend == "mock":
        mf = os.environ.get("HSSD_MOCK_FILE")
        if mf and Path(mf).exists():
            out = json.loads(Path(mf).read_text(encoding="utf-8")).get(role, "")
        else:
            out = os.environ.get("HSSD_MOCK_OUTPUT", "")
        _metric({"role": role, "backend": "mock", "duration_s": round(time.monotonic() - t0, 3),
                 "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                 "prompt_chars": len(prompt), "result_chars": len(out),
                 "prompt_preview": prompt[:280], "result_preview": out[:280]})
        _budget_tick(0.0)
        return out

    # Real backend. Resolve the CLI via PATHEXT (on Windows it's a `claude.cmd` shim).
    exe = shutil.which("claude")
    if not exe:
        print("BLOCK: 'claude' CLI not found on PATH. Install Claude Code, or set "
              "HSSD_AGENT_BACKEND=mock for a dry run.", file=sys.stderr)
        _metric({"role": role, "backend": "claude", "duration_s": round(time.monotonic() - t0, 3),
                 "error": "claude-not-found", "prompt_chars": len(prompt)})
        return ""

    # Stream the interaction LIVE (silence in a terminal = "in the dark"); fall back to a single
    # blocking call if streaming isn't available. HSSD_STREAM=0 forces the quiet blocking path.
    allowed = _agent_tools(role)  # least-privilege: only this role's declared tools
    if os.environ.get("HSSD_STREAM", "1") != "0":
        try:
            text, usage, cost, api_ms = _claude_stream(exe, composed, role, allowed)
        except Exception as e:  # noqa: BLE001 — any stream hiccup → safe fallback
            print(f"    (stream unavailable: {e}; falling back to a blocking call)", file=sys.stderr)
            text, usage, cost, api_ms = _claude_blocking(exe, composed, allowed)
    else:
        text, usage, cost, api_ms = _claude_blocking(exe, composed, allowed)

    elapsed = round(time.monotonic() - t0, 3)
    _metric({
        "role": role, "backend": "claude", "duration_s": elapsed, "api_ms": api_ms,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        "cost_usd": cost,
        "prompt_chars": len(prompt), "result_chars": len(text),
        "prompt_preview": prompt[:280], "result_preview": text[:280],
    })
    _budget_tick(cost)
    return text.strip()


def _recommend_templates(techs: list[str]) -> None:
    """Suggest blessed template repos (git) for detected tech; else note the agents build directly."""
    if not techs:
        return
    print(f"\nDetected technologies: {', '.join(techs)}")
    techset = {t.lower() for t in techs}
    covered: set[str] = set()
    matches: list[tuple[str, str, list[str]]] = []
    for t in _full_catalog():
        hit = techset & {x.lower() for x in t.get("tech", [])}
        if hit:
            matches.append((t["name"], t.get("url", ""), sorted(hit)))
            covered |= hit
    if matches:
        print("Matching blessed templates (git repos — optional):")
        for name, url, hit in matches:
            print(f"  - {name}  (covers: {', '.join(hit)})")
            print(f"      into this repo:  hssd template import --from={url}")
            print(f"      fresh project:   hssd new <name> --from={url}")
    uncovered = sorted(techset - covered)
    if uncovered:
        print(f"No blessed template for: {', '.join(uncovered)}")
        print("  -> the agents build these directly using the skills (no template needed).")


def _lane_for(c: dict) -> str:
    """Classify a concern at split time:
    - 'config'   — a capability the harness PROVIDES (enable, don't engineer): the AI Interaction
                   Log / logging / audit. Auto-satisfied at split; never engaged.
    - 'standing' — a governance doc (ADR, README): produced + rubric-checked, not code-engineered.
    - 'feature'  — an engineered task (the normal case)."""
    kind = (c.get("kind") or "").lower()
    t = (c.get("title") or "").lower()
    if kind == "config" or "interaction log" in t or ("ai" in t and "log" in t):
        return "config"
    if "adr" in t or "architecture decision" in t or "readme" in t:
        return "standing"
    return "feature"


def _lane_order(lane: str) -> int:
    return {"config": 0, "standing": 1}.get(lane, 2)  # config + governance lead the backlog


def _create_work_items(project: Path, concerns: list[dict]) -> int:
    """Insert each concern. `config` items are capabilities the harness provides → recorded
    'done' (enabled) at split, never engaged. `standing`/`feature` stay 'open'."""
    con = _pm(project)
    base = con.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
    ordered = sorted(concerns, key=lambda c: _lane_order(_lane_for(c)))
    enabled = 0
    for i, c in enumerate(ordered, start=1):
        lane = _lane_for(c)
        status = "done" if lane == "config" else "open"  # config is satisfied by the harness itself
        if lane == "config":
            enabled += 1
        con.execute(
            "INSERT INTO work_items(id, title, type, status, created_at, source, lane) "
            "VALUES(?,?,?,?,?, 'overview', ?)",
            (f"LOC-{base + i}", c.get("title", "(untitled)"), c.get("type", "feature"),
             status, datetime.datetime.now(datetime.timezone.utc).isoformat(), lane),
        )
    con.commit()
    if enabled:
        print(f"  ({enabled} config item(s) auto-enabled by the harness — not engineered; "
              "e.g. the AI log is captured automatically, render with `hssd ailog`)")
    return len(ordered)


def _print_plan(data: dict) -> list[dict]:
    """Print the analyst's understanding + the proposed work items. Returns the concerns."""
    analysis = data.get("analysis", "")
    if analysis:
        print(analysis)
    concerns = data.get("concerns", [])
    if concerns:
        print("\nProposed items (review these — nothing is created yet):")
        for i, c in enumerate(concerns, start=1):
            lane = _lane_for(c)
            tag = {"config": "config · auto-enabled", "standing": "standing · rubric"}.get(
                lane, c.get("type", "feature"))
            print(f"  {i}. [{tag}] {c.get('title', '(untitled)')}")
    _recommend_templates(data.get("technologies", []))
    return concerns


def cmd_overview(args: argparse.Namespace) -> int:
    print("⚠  'hssd overview' is deprecated — use 'hssd intake' for the new intake cycle.", file=sys.stderr)
    project = Path(".").resolve()
    ov = project / ".harness" / "overview.md"
    plan_path = project / ".harness" / "plan.json"

    if args.action == "add":
        src = Path(args.file) if args.file else None
        if not src or not src.exists():
            print(f"BLOCK: file not found: {args.file}", file=sys.stderr)
            return 1
        ov.parent.mkdir(parents=True, exist_ok=True)
        ov.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        _log(project, "overview add", str(args.file))
        print(f"OK: overview stored ({args.file})")
        return 0

    # architect: propose the SHARED project architecture (the contract every story inherits).
    # The system drafts; the engineer iterates and owns docs/ADR.md; the adversary only advises.
    if args.action == "architect":
        if not ov.exists():
            print("BLOCK: no overview yet. Run 'hssd overview add <file>' first.", file=sys.stderr)
            return 1
        brief = ov.read_text(encoding="utf-8")
        # Architecture is a function of the PROBLEM, not of the decomposition — the architect stands
        # on the brief alone (it runs BEFORE analyze/split, which then inherit the locked ADR).
        draft = _run_role(
            "architect",
            "Design the SHARED architecture for this WHOLE project from the brief — the project-level "
            "contract every story will inherit, not one story's design. Output ONLY a 1-page "
            "Architecture Decision Record in Markdown with these sections:\n"
            "## Data model — every entity/table, its fields, AND ownership (which story/migration "
            "creates it, and who writes each mutable column — make cross-story ownership explicit).\n"
            "## Stack tier — lightweight (FastAPI+SQLite) or full (FastAPI+Postgres); justify.\n"
            "## Concurrency & isolation — the strategy for each stated guarantee (atomic counter, "
            "BEGIN IMMEDIATE / SELECT FOR UPDATE, idempotency key).\n"
            "## Key decisions — the 2-3 most important, each with why + the rejected alternative.\n"
            "## Assumptions — everything the brief leaves open, each stated as a decision.\n"
            f"\n{brief}",
        )
        docs = project / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        draft = _strip_to_heading(draft)  # drop any narration before the ADR markdown
        (docs / "ADR.draft.md").write_text(draft, encoding="utf-8")
        # Refresh docs/ADR.md with the new proposal UNLESS the engineer has hand-edited it. We write
        # ADR.md when it's absent, still the init stub, OR byte-identical to the last proposal we
        # emitted (untouched architect output — re-running architect should keep improving it). Once
        # the human diverges ADR.md, we preserve their edits and only refresh the draft.
        existing = _adr_path(project)
        sha_file = _locks_dir(project) / "adr_proposal.sha"
        last = sha_file.read_text(encoding="utf-8").strip() if sha_file.exists() else ""
        untouched = existing.exists() and _file_sha(existing) == last
        refresh = (not existing.exists()) or untouched or (
            existing.exists() and _adr_is_stub(existing.read_text(encoding="utf-8")))
        if refresh:
            existing.write_text(draft, encoding="utf-8")
            _locks_dir(project).mkdir(parents=True, exist_ok=True)
            sha_file.write_text(_file_sha(existing), encoding="utf-8")  # remember what we placed
        _log(project, "overview architect", f"draft written; ADR.md {'refreshed' if refresh else 'preserved (hand-edited)'}")
        print("\n— architecture-adversary (advisory — it informs, you decide) —")
        adv = _run_role(
            "architecture-adversary",
            "Review this PROJECT architecture draft. Return JSON {findings:[{issue, options[], "
            "recommended}]}. You ADVISE the engineer; you do NOT block.\n\n" + draft,
            expect_json=True,
        )
        try:
            findings = _json_loads(adv).get("findings", [])
        except (json.JSONDecodeError, AttributeError):
            findings = []
        for i, f in enumerate(findings, 1):
            if isinstance(f, dict):
                print(f"  {i}. {f.get('issue', '')}")
                if f.get("recommended"):
                    print(f"     ★ {f['recommended']}")
        if not findings:
            print("  (no structured findings)")
        print()
        if refresh:
            print("docs/ADR.md refreshed with this proposal (+ docs/ADR.draft.md). Edit it freely, or "
                  "re-run `hssd overview architect` — it keeps refreshing ADR.md until you hand-edit it.")
        else:
            print("You've hand-edited docs/ADR.md — left it untouched. Fresh proposal is in "
                  "docs/ADR.draft.md; diff and merge what you want.")
        print("When the architecture is yours, lock it:  hssd architecture approve")
        return 0

    # split: create work items from the ALREADY-APPROVED plan (no model re-call).
    if args.action == "split":
        if not _architecture_locked(project):
            print("BLOCK: architecture is not locked. The backlog must inherit a locked architecture "
                  "(else stories plan against an undefined data model — the cross-story ambiguity we "
                  "fix here). Run:\n"
                  "  hssd overview architect → (iterate) → hssd architecture approve",
                  file=sys.stderr)
            return 1
        if not plan_path.exists():
            print("BLOCK: no plan yet. Run 'hssd overview analyze' first, review it, then split.",
                  file=sys.stderr)
            return 1
        concerns = json.loads(plan_path.read_text(encoding="utf-8")).get("concerns", [])
        if not concerns:
            print("BLOCK: the saved plan has no concerns to split.", file=sys.stderr)
            return 1
        n = _create_work_items(project, concerns)
        _log(project, "overview split", f"created={n}")
        print(f"OK: created {n} work item(s) from the approved plan. Review with 'hssd work list'.")
        return 0

    # analyze: decompose the brief INTO the locked architecture, SAVE the plan, but create nothing.
    if not ov.exists():
        print("BLOCK: no overview yet. Run 'hssd overview add <file>' first.", file=sys.stderr)
        return 1
    if not _architecture_locked(project):
        print("BLOCK: architecture is not locked. Decomposition must inherit the architecture (else "
              "stories plan against an undefined data model — the cross-story ambiguity we fix here). "
              "Run:\n  hssd overview architect → (iterate) → hssd architecture approve", file=sys.stderr)
        return 1
    text = ov.read_text(encoding="utf-8")
    adr = _adr_path(project)
    adr_ctx = ("\n\n## Locked architecture (docs/ADR.md) — decompose IN TERMS OF this. Each concern "
               "should name the entities/tables and ownership it touches; do NOT re-open data-model "
               "or tier questions — they are settled here.\n" + adr.read_text(encoding="utf-8")) \
        if adr.exists() else ""
    out = _run_role(
        "product-analyst",
        "Analyze this project brief and decompose it against the locked architecture. Return JSON "
        "with: 'analysis' (understanding + short plan), 'concerns' (a list of {title, type, kind} the "
        "brief decomposes into — kind is 'task' to engineer, or 'config' for a capability the harness "
        "already provides and just needs enabling, e.g. the AI Interaction Log / logging / audit), "
        "and 'technologies' (a list)."
        f"\n\n{text}{adr_ctx}",
        expect_json=True,
    )
    try:
        data = _json_loads(out)
    except json.JSONDecodeError:
        print("BLOCK: analyst did not return valid JSON:\n" + out, file=sys.stderr)
        return 1

    plan_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    concerns = _print_plan(data)
    _log(project, "overview analyze", f"plan saved (concerns={len(concerns)})")

    if args.split_concerns:  # one-shot: analyze + create immediately (from this same plan)
        n = _create_work_items(project, concerns)
        _log(project, "overview split", f"created={n} (one-shot)")
        print(f"\nOK: created {n} work item(s). Review with 'hssd work list'.")
    elif concerns:
        print("\n→ Agree with the plan? Create the tasks with:  hssd overview split")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """Self-update: pull the framework repo (a separate git checkout) and report the version."""
    version = (PKG_ROOT / "VERSION").read_text(encoding="utf-8").strip() if (PKG_ROOT / "VERSION").exists() else "unknown"
    if args.check:
        print(f"harness-studio {version}")
        return 0
    if not (PKG_ROOT / ".git").exists():
        print(f"harness-studio {version} — not a git checkout here; nothing to pull.", file=sys.stderr)
        return 1
    res = subprocess.run(
        ["git", "-C", str(PKG_ROOT), "pull", "--ff-only"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    print((res.stdout or res.stderr).strip())
    new = (PKG_ROOT / "VERSION").read_text(encoding="utf-8").strip() if (PKG_ROOT / "VERSION").exists() else version
    print(f"harness-studio now at {new}")
    return res.returncode


def cmd_janitor(args: argparse.Namespace) -> int:
    """The discovery heartbeat: audit -> dedup by fingerprint -> file work items."""
    project = Path(".").resolve()
    con = _pm(project)
    out = _run_role("janitor", "Audit this codebase and report deduped findings.", expect_json=True)
    try:
        findings = _json_loads(out)
    except json.JSONDecodeError:
        print("BLOCK: janitor did not return valid JSON:\n" + out, file=sys.stderr)
        return 1

    existing = {
        r[0] for r in con.execute("SELECT fingerprint FROM work_items WHERE fingerprint IS NOT NULL")
    }
    base = con.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
    created = skipped = 0
    for f in findings:
        fp = f.get("fingerprint") or _slug(f.get("title", ""))
        if fp in existing:
            skipped += 1
            continue
        base += 1
        con.execute(
            "INSERT INTO work_items(id, title, type, status, created_at, source, fingerprint) "
            "VALUES(?,?,?,'open',?, 'janitor', ?)",
            (f"LOC-{base}", f.get("title", "(finding)"), f.get("type", "tech-debt"),
             datetime.datetime.now(datetime.timezone.utc).isoformat(), fp),
        )
        existing.add(fp)
        created += 1
    con.commit()
    _log(project, "janitor", f"created={created} deduped={skipped}")
    print(f"janitor: {created} new work item(s), {skipped} deduped. Review with 'hssd work list'.")
    return 0


def _gate_ok(out: str) -> bool:
    try:
        return _json_loads(out).get("verdict") == "PASS"
    except (json.JSONDecodeError, AttributeError):
        return False


def cmd_engage(args: argparse.Namespace) -> int:
    """The engagement loop: 6 phases, P4 is the goal-condition (loop-until-dry)."""
    project = Path(".").resolve()
    con = _pm(project)
    _BUDGET.update(calls=0, cost=0.0, max_calls=getattr(args, "max_calls", 0) or 0,
                   max_cost=getattr(args, "budget", 0.0) or 0.0)  # hard ceiling for this run
    row = con.execute("SELECT title, status, lane FROM work_items WHERE id=?", (args.id,)).fetchone()
    if not row:
        print(f"BLOCK: {args.id} not found", file=sys.stderr)
        return 1
    title, status, lane = row
    if (lane or "") == "config":
        # A capability the harness provides — nothing to engineer. Already satisfied at split.
        print(f"▶ {args.id} · {title}  (config — harness-provided capability)")
        print("  Nothing to engineer. The AI Interaction Log is captured continuously in "
              ".harness/logs/metrics.jsonl (always on) — render it with `hssd ailog` and fill the "
              "human sections. Marking enabled.")
        con.execute("UPDATE work_items SET status='done' WHERE id=?", (args.id,))
        con.commit()
        _log(project, "engage", f"{args.id} config-enabled")
        print(f"✓ {args.id} enabled (config) — status=done")
        return 0
    # No story engineers before the architecture gate, and feature work happens INSIDE a sprint
    # (config/standing exempt — config is auto-provided; the ADR/README are continuous governance).
    if (lane or "feature") not in ("config", "standing") and not args.force:
        if not _architecture_locked(project):
            print("BLOCK: architecture is not locked — no story engages before the architecture gate. "
                  "Run `hssd overview architect` then `hssd architecture approve` (or --force).",
                  file=sys.stderr)
            return 1
        srow = con.execute("SELECT sprint_id FROM work_items WHERE id=?", (args.id,)).fetchone()
        sp = srow[0] if srow else None
        cur = _current_sprint(con)
        if not sp:
            print(f"BLOCK: {args.id} is in the backlog, not a sprint. Pull it into one first: "
                  "`hssd sprint plan` (or --force).", file=sys.stderr)
            return 1
        if not cur or cur[0] != sp:
            print(f"BLOCK: {args.id} belongs to {sp}, which isn't the active sprint (or it's closed). "
                  "Re-plan or resume that sprint (or --force).", file=sys.stderr)
            return 1
    if status == "open":
        # Auto-claim (atomic compare-and-swap) so engage is one step; keeps the branch discipline.
        branch = f"harness/local-{args.id.lower()}-{_slug(title)}"
        cur = con.execute(
            "UPDATE work_items SET status='in-progress', assignee='me', branch=? "
            "WHERE id=? AND status='open'",
            (branch, args.id),
        )
        con.commit()
        if cur.rowcount:
            _log(project, "work claim", f"{args.id} -> {branch} (via engage)")
            _git_switch(branch)
            print(f"  claimed {args.id} · branch {branch}")
        elif not args.force:
            print(f"BLOCK: {args.id} could not be claimed (taken concurrently?). "
                  "Use --force to run anyway.", file=sys.stderr)
            return 1
    elif status == "done" and not args.force:
        print(f"BLOCK: {args.id} is already done. Use --force to re-run, or `hssd reset {args.id}`.",
              file=sys.stderr)
        return 1
    elif status != "in-progress" and not args.force:
        print(f"BLOCK: {args.id} is '{status}'. Use --force to run anyway.", file=sys.stderr)
        return 1

    st = project / ".harness" / "engagements" / args.id  # durable memory for this loop
    st.mkdir(parents=True, exist_ok=True)
    assumptions_file = st / "assumptions.md"  # the Lead's resolutions = the ADR "assumptions"

    # --answers: record the Engagement Lead's resolutions so the agents stop re-raising them and
    # the decision is captured (we learn from the interaction; it feeds the ADR).
    if getattr(args, "answers", None):
        ans = Path(args.answers)
        if not ans.exists():
            print(f"BLOCK: answers file not found: {args.answers}", file=sys.stderr)
            return 1
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with assumptions_file.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## Resolution recorded {stamp}\n\n{ans.read_text(encoding='utf-8')}\n")
        _log(project, "engage answers", f"{args.id} <- {args.answers}")
        print(f"  recorded answers from {args.answers} -> {assumptions_file}")

    # Auto-ingest any answer files the Lead dropped in (no flag needed): clarifications*.md /
    # answers*.md in the engagement dir, or answers-<id>*.md in the project root.
    _seen = assumptions_file.read_text(encoding="utf-8") if assumptions_file.exists() else ""
    for cand in (sorted(st.glob("clarifications*.md")) + sorted(st.glob("answers*.md"))
                 + sorted(project.glob(f"answers-{args.id.lower()}*.md"))):
        _txt = cand.read_text(encoding="utf-8").strip()
        if _txt and _txt[:80] not in _seen:
            _stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            with assumptions_file.open("a", encoding="utf-8") as fh:
                fh.write(f"\n## Ingested {cand.name} {_stamp}\n\n{_txt}\n")
            _seen += _txt
            _log(project, "engage ingest", f"{args.id} <- {cand.name}")
            print(f"  auto-ingested answers from {cand.name}")

    # Type-aware acceptance: governance/narrative deliverables are accepted by a rubric, code by tests.
    if (lane or "") == "standing":
        accept = (
            "## Acceptance mode: RUBRIC (governance/narrative deliverable, lane=standing)\n"
            "Acceptance is by rubric, NOT deterministic automated tests. Do NOT block because an item "
            "'cannot be expressed as a deterministic/automated test' — that is expected and fine for a "
            "narrative artifact. Apply the canonical rubric below as-is.\n\n" + GOVERNANCE_RUBRIC
        )
    else:
        accept = (
            "## Acceptance mode: TESTS (code deliverable, lane=feature)\n"
            "Acceptance is by deterministic, executable tests. Any guarantee/atomicity/concurrency "
            "requirement MUST become a stress test."
        )
    adr = _adr_path(project)
    adr_ctx = ""
    if adr.exists():  # the locked shared contract — stories inherit it, the skeptic stops re-deriving it
        adr_ctx = ("\n\n## Locked architecture (docs/ADR.md — the shared contract; treat its data "
                   "model, ownership and tier as SETTLED. Do NOT re-raise them as open questions.)\n"
                   + adr.read_text(encoding="utf-8"))
    base_ctx = (f"Work item {args.id}: {title}\n(Project overview in .harness/overview.md)\n\n"
                f"{accept}{adr_ctx}")

    # The upstream artifact (analyst → skeptic, story-writer → AC adversary, architect → arch
    # adversary) is handed to the reviewer IN CONTEXT, so an adversary never has to hunt the
    # filesystem for it (which made the AC adversary thrash through dozens of phantom reads).
    _upstream = {"label": "", "text": ""}

    def current_ctx() -> str:  # re-read assumptions each call so recorded answers take effect
        c = base_ctx
        if assumptions_file.exists():
            c += ("\n\n## Resolved assumptions (decided by the Engagement Lead — treat as settled; "
                  "do NOT re-raise these)\n" + assumptions_file.read_text(encoding="utf-8"))
        if _upstream["text"]:
            c += (f"\n\n## {_upstream['label']} — the artifact under review. Read it HERE; do NOT "
                  f"search the filesystem for it.\n{_upstream['text']}")
        return c

    def run(role: str, expect_json: bool = False) -> str:
        out = _run_role(role, current_ctx(), expect_json=expect_json)
        (st / f"{role}.out").write_text(out, encoding="utf-8")
        _log(project, "engage", f"{args.id} {role}")
        return out

    def _show_findings(data: dict) -> list[dict]:
        findings = data.get("findings", []) if isinstance(data, dict) else []
        for i, f in enumerate(findings, 1):
            if not isinstance(f, dict):
                continue
            print(f"      {i}. {f.get('issue', f)}")
            for opt in f.get("options", []):
                print(f"           - option: {opt}")
            if f.get("recommended"):
                print(f"           ★ recommended: {f['recommended']}")
        return findings

    def _accept_recommended(findings: list[dict]) -> int:
        recs = [f.get("recommended") for f in findings if isinstance(f, dict) and f.get("recommended")]
        if not recs:
            return 0
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with assumptions_file.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## Auto-accepted recommended resolutions {stamp}\n"
                     + "\n".join(f"- {r}" for r in recs) + "\n")
        return len(recs)

    def passing_gate(role: str, label: str, max_retry: int = 2) -> bool:
        """Adversary gate that never dead-ends. On BLOCK it shows options + the recommended fix.
        With --accept-recommended it records the recommended resolutions and retries (loop-forward);
        when retries are EXHAUSTED it still does not stall — it carries the accumulated assumptions
        forward to the Spec Lock human gate (the natural arbiter), flagging that they need sign-off.
        Rationale (field-learned on LOC-7): a single story pulled from a multi-story system may never
        fully converge in isolation — the skeptic keeps surfacing real cross-story dependencies. That
        is signal for the human reviewing the locked spec, not a reason to dead-end the loop."""
        for attempt in range(max_retry + 1):
            out = run(role, expect_json=True)
            try:
                data = _json_loads(out)
            except json.JSONDecodeError:
                data = {}
            ok = isinstance(data, dict) and data.get("verdict") == "PASS"
            print(f"  {'✓' if ok else '⏸'} {label} {'PASS' if ok else 'BLOCK'}")
            if ok:
                return True
            findings = _show_findings(data if isinstance(data, dict) else {})
            if args.accept_recommended and findings:
                n = _accept_recommended(findings)
                if n and attempt < max_retry:
                    print(f"    ↻ accepted {n} recommended resolution(s) → retrying {label}")
                    continue
                if n:  # retries exhausted but autonomy is on: loop-forward, never stall
                    print(f"    ⚠ {label} still BLOCK after {max_retry + 1} rounds — carried "
                          f"{n} more assumption(s) forward (convergence by exhaustion). They need "
                          f"human sign-off at SPEC LOCK; full trail in "
                          f".harness/engagements/{args.id}/assumptions.md")
                    return True
            print(f"    → resolve & retry: write answers to a file then "
                  f"`hssd engage {args.id} --answers <file>`, or rerun with `--accept-recommended` "
                  f"(auto-take the recommended options). Full output in "
                  f".harness/engagements/{args.id}/{role}.out")
            return False
        return False

    def gate(role: str, label: str) -> bool:  # simple gate for the P4 fan-out (loops back to P3)
        out = run(role, expect_json=True)
        ok = _gate_ok(out)
        print(f"  {'✓' if ok else '⏸'} {label} {'PASS' if ok else 'BLOCK'}")
        if not ok:
            print(f"    {out}")
        return ok

    def human(label: str) -> bool:
        if args.auto:
            print(f"  ✓ {label} (auto-approved)")
            return True
        try:
            return input(f"  ⏸ {label} — approve? [y/N] ").strip().lower() == "y"
        except EOFError:  # run headless (no terminal): don't bypass a human gate, stop cleanly
            print(f"  ⏸ {label} needs a human. Run `hssd engage {args.id}` in a terminal, "
                  "or pass --auto to skip gates (testing only).", file=sys.stderr)
            return False

    print(f"▶ engage {args.id} · {title}")
    if (lane or "") == "standing":
        # Governance/narrative deliverables are produced + rubric-checked, NOT engineered. Skip the
        # adversarial intake (P0-P2) + Spec Lock entirely — debating a "spec" for an auto-captured
        # artifact (the AI log is always-on in metrics.jsonl) is wasted cost.
        print("Standing governance deliverable — skipping adversarial intake (P0-P2 + Spec Lock).")
        print("  the AI Interaction Log is captured continuously; produce it with `hssd ailog`.")
    else:
        print("P0 Intake")
        _upstream.update(label="Problem statement (product-analyst)", text=run("product-analyst"))
        if not passing_gate("definition-skeptic", "Definition Skeptic"):
            return 2
        print("P1 Stories & AC")
        _upstream.update(label="Stories & acceptance criteria (story-writer)", text=run("story-writer"))
        if not passing_gate("ac-adversary", "AC Adversary"):
            return 2
        print("P2 Architecture")
        _upstream.update(label="Story architecture (architect)", text=run("architect"))
        if not passing_gate("architecture-adversary", "Architecture Adversary"):
            return 2
        if not human("SPEC LOCK (no code before this)"):
            print("Stopped at Spec Lock."); return 0

    # P3 + P4 are type-aware. Governance/narrative deliverables produce an artifact and are
    # reviewed against a rubric — no code build, no concurrency/security adversaries.
    if (lane or "") == "standing":
        print("P3 Produce (governance deliverable — no code build)")
        print("  author the artifact: e.g. `hssd ailog` for the AI log, or write docs/ for ADR/README.")
        print("P4 Rubric review")
        rubric_checkers = [
            ("independent-verifier", "Independent Verifier (rubric)"),
            ("completion-challenger", "Completion Challenger (rubric)"),
        ]
        blockers = [label for role, label in rubric_checkers if not gate(role, label)]
        if blockers:
            print(f"BLOCK: rubric not satisfied: {blockers} — produce the missing elements, then "
                  "re-run.", file=sys.stderr)
            return 1
        print("  ✓ rubric satisfied")
    else:
        # Code deliverable. Mandatory TDD: RED (tests written from the locked AC must FAIL first),
        # then GREEN (implement until they pass), then loop-until-dry on the adversaries. The CLI
        # RUNS the tests itself and captures the output — TDD is a verified guarantee, not a claim.
        test_cmd = (getattr(args, "test_cmd", None) or "uv run pytest").split()

        def _run_tests(tag: str) -> int:
            """Run the project's test command; persist output as red/green evidence. Returns the
            exit code (0 = pass, >0 = fail, -1 = couldn't run)."""
            try:
                res = subprocess.run(test_cmd, cwd=project, capture_output=True, text=True,
                                     encoding="utf-8", errors="replace", timeout=900)
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                (st / f"tests-{tag}.log").write_text(f"test run failed: {e}\n", encoding="utf-8")
                return -1
            (st / f"tests-{tag}.log").write_text((res.stdout or "") + (res.stderr or ""),
                                                 encoding="utf-8")
            return res.returncode

        # P3a — RED: author the tests from the locked AC, before any implementation; they MUST fail.
        print("P3a Red — author tests from the locked AC (must fail first)")
        run("test-author")
        rc = _run_tests("red")
        if rc == -1:
            print(f"BLOCK: couldn't run the test command ({' '.join(test_cmd)}). Pass --test-cmd or "
                  f"make it runnable in the project. See .harness/engagements/{args.id}/tests-red.log",
                  file=sys.stderr)
            return 1
        if rc == 0:
            print("  ⏸ tests PASS with no implementation — vacuous (the RED step of TDD failed).")
            print(f"BLOCK: tests must fail before code exists. Strengthen them, then re-run "
                  f"`hssd engage {args.id}`. See .harness/engagements/{args.id}/tests-red.log",
                  file=sys.stderr)
            return 1
        print("  ✓ red: the AC tests fail as expected (no implementation yet)")

        checkers = [
            ("independent-verifier", "Independent Verifier"),
            ("completion-challenger", "Completion Challenger"),
            ("test-adversary", "Test Adversary"),
            ("regression-hunter", "Regression Hunter"),  # always on — integrity is non-negotiable
        ]
        if not args.no_security:  # mandatory for API/auth surfaces (STANDARDS §2); --no-security opts out
            checkers.insert(0, ("security-adversary", "Security/Attack Adversary"))

        # P3b — GREEN: implement until the AC tests pass, then P4 loop-until-dry on the adversaries.
        dry = False
        for attempt in range(1, args.max_iter + 1):
            print(f"P3b Build (attempt {attempt})"); run("backend-dev"); run("frontend-dev")
            green = _run_tests("green") == 0
            print(f"  {'✓ green: AC tests pass' if green else '⏸ AC tests still failing'} "
                  f"(.harness/engagements/{args.id}/tests-green.log)")
            if not green:
                print("  ↻ not green → back to P3b"); continue
            print("P4 Verification")
            blockers = [label for role, label in checkers if not gate(role, label)]
            if not blockers:
                print("  ✓ loop-until-dry: dry (green + all checkers PASS)"); dry = True; break
            print(f"  ↻ blockers {blockers} → back to P3b")
        if not dry:
            print(f"BLOCK: not green-and-dry after {args.max_iter} attempts.", file=sys.stderr)
            return 1

    print("P5 Integration")
    if not human("MERGE"):
        print("Stopped before merge."); return 0
    con.execute("UPDATE work_items SET status='done' WHERE id=?", (args.id,)); con.commit()
    _log(project, "engage", f"{args.id} done")
    print(f"✓ {args.id} delivered (status=done)")
    return 0


def main(argv: list[str] | None = None) -> int:
    # Force UTF-8 on output so glyphs (▶ ✓ ↻ ·) don't crash on Windows when stdout is a pipe
    # (the default there is cp1252, which can't encode them — and mangles even '·' to '�').
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    p = argparse.ArgumentParser(
        prog="hssd",
        description="Harness Studio — the engine for the governed, adversarial AI-coding workflow")
    p.add_argument("--version", action="version", version=f"hssd {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    pn = sub.add_parser("new", help="create a project (empty governed, or from a template repo via --from)")
    pn.add_argument("name")
    pn.add_argument("--from", dest="from_git", default=None, help="git URL of a blessed template repo")
    pn.set_defaults(func=cmd_new)

    pi = sub.add_parser("init", help="turn ON Harness Studio in an existing repo (non-destructive)")
    pi.add_argument("path", nargs="?", default=".", help="repo to adopt (default: current dir)")
    pi.set_defaults(func=cmd_init)

    pproj = sub.add_parser("project", help="project identity: approve project.md (→ 'identified' state)")
    pproj.add_argument("action", choices=["approve", "show", "check"])
    pproj.set_defaults(func=cmd_project)

    pint = sub.add_parser("intake", help="intake cycle: add a demand, list, approve to release stories")
    pint.add_argument("action", choices=["add", "list", "show", "approve"])
    pint.add_argument("id", nargs="?", help="intake id (for show/approve)")
    pint.add_argument("file", nargs="?", help="brief file path (for add)")
    pint.add_argument("--title", default="", help="intake title (for add)")
    pint.set_defaults(func=cmd_intake)

    piter = sub.add_parser("iteration", help="iterations: plan, activate (variadic), list, converge")
    piter.add_argument("action", choices=["plan", "activate", "list", "converge"])
    piter.add_argument("ids", nargs="*", help="iteration id(s) for activate")
    piter.add_argument("id", nargs="?", help="iteration id for converge")
    piter.add_argument("--goal", default="", help="iteration goal (for plan)")
    piter.add_argument("--intake", default=None, help="source intake id (for plan)")
    piter.set_defaults(func=cmd_iteration)

    psy = sub.add_parser("sync", help="re-sync .claude/ (agents, skills, commands) from the framework (overwrites)")
    psy.set_defaults(func=cmd_sync)

    pt = sub.add_parser("template", help="list / import / register templates (blessed catalog + your own; any git URL)")
    pt.add_argument("action", choices=["list", "import", "add", "rm"])
    pt.add_argument("--from", dest="from_git", default=None, help="git URL (to import, or to register/remove)")
    pt.add_argument("--name", default=None, help="name when registering (add) or removing (rm)")
    pt.add_argument("--tech", default=None, help="comma-separated tech tags when registering (add)")
    pt.add_argument("--into", default=None, help="target project dir for import (default: cwd)")
    pt.set_defaults(func=cmd_template)

    psk = sub.add_parser("skill", help="list / import / register skills (blessed catalog + your own; any git URL)")
    psk.add_argument("action", choices=["list", "import", "add", "rm"])
    psk.add_argument("--from", dest="from_git", default=None, help="git URL (to import, or to register/remove)")
    psk.add_argument("--name", default=None, help="name when registering (add), overriding auto-resolve (import), or removing (rm)")
    psk.add_argument("--tech", default=None, help="comma-separated tech tags when registering (add)")
    psk.add_argument("--into", default=None, help="target project dir for import (default: cwd)")
    psk.set_defaults(func=cmd_skill)

    po = sub.add_parser("overview", help="register/analyze the brief, architect the shared design, then split")
    po.add_argument("action", choices=["add", "analyze", "architect", "split"])
    po.add_argument("file", nargs="?")
    po.add_argument("--split-concerns", action="store_true",
                    help="one-shot: analyze AND create the work items (skips the review gate)")
    po.set_defaults(func=cmd_overview)

    pst = sub.add_parser("status", help="show the project state machine + the next command to run")
    pst.set_defaults(func=cmd_status)

    parch = sub.add_parser("architecture",
                           help="the human lock over the shared architecture (approve / status / reopen)")
    parch.add_argument("action", choices=["approve", "status", "reopen"])
    parch.set_defaults(func=cmd_architecture)

    psp = sub.add_parser("sprint",
                         help="iterations: plan / status / review / close (the project never ends; sprints do)")
    psp.add_argument("action", choices=["plan", "status", "review", "close"])
    psp.add_argument("--goal", default="", help="the sprint goal (for plan)")
    psp.add_argument("--force", action="store_true", help="override a precondition")
    psp.set_defaults(func=cmd_sprint)

    pw = sub.add_parser("work", help="work items via the PM Port (local SQLite or synced PM)")
    pw.add_argument("action", choices=["add", "list", "show", "claim", "done"])
    pw.add_argument("id", nargs="?")
    pw.add_argument("--title", default="")
    pw.add_argument("--type", default="feature")
    pw.add_argument("--status", default=None, help="filter for list (e.g. open)")
    pw.add_argument("--as", dest="who", default="me")
    pw.set_defaults(func=cmd_work)

    pr = sub.add_parser("reset", help="reset to re-run: a work item, --all engineered items, or --backlog/--hard")
    pr.add_argument("id", nargs="?", help="work item to reset (back to open + clear its engagement state)")
    pr.add_argument("--all", action="store_true", help="reset every engineered item to open + clear engagement state")
    pr.add_argument("--backlog", action="store_true", help="wipe work items + plan + engagement state (re-split from the brief)")
    pr.add_argument("--hard", action="store_true", help="like --backlog and also clear logs/metrics (fresh cost baseline)")
    pr.set_defaults(func=cmd_reset)

    pe = sub.add_parser("engage", help="run the 6-phase engagement loop on a work item")
    pe.add_argument("id")
    pe.add_argument("--auto", action="store_true", help="auto-approve human gates (testing)")
    pe.add_argument("--force", action="store_true", help="run even if not claimed")
    pe.add_argument("--max-iter", type=int, default=3, dest="max_iter")
    pe.add_argument("--no-security", action="store_true", dest="no_security",
                    help="skip the Security/Attack Adversary (non-API/auth work only)")
    pe.add_argument("--answers", default=None,
                    help="file with the Lead's resolutions to a blocked gate (recorded as ADR "
                         "assumptions and reused on re-run, so agents stop re-raising them)")
    pe.add_argument("--accept-recommended", action="store_true", dest="accept_recommended",
                    help="on a blocked intake/AC/architecture gate, auto-take the adversary's "
                         "recommended resolution and retry (graduated autonomy; loop-forward)")
    pe.add_argument("--test-cmd", default=None, dest="test_cmd",
                    help="command the TDD gate runs for red/green evidence (default: 'uv run pytest')")
    pe.add_argument("--max-calls", type=int, default=40, dest="max_calls",
                    help="hard ceiling on total AI calls for the run — never loop forever (0 = off)")
    pe.add_argument("--budget", type=float, default=0.0,
                    help="hard USD ceiling for the run (0 = off)")
    pe.set_defaults(func=cmd_engage)

    pj = sub.add_parser("janitor", help="discovery heartbeat — audit + dedup + file work items")
    pj.set_defaults(func=cmd_janitor)

    pu = sub.add_parser("update", help="self-update the framework (git pull) / show version")
    pu.add_argument("--check", action="store_true", help="just print the current version")
    pu.set_defaults(func=cmd_update)

    pl = sub.add_parser("log", help="show the session log")
    pl.add_argument("--verbose", action="store_true")
    pl.set_defaults(func=cmd_log)

    ps = sub.add_parser("stats", help="dev-time, token & cost analytics from the metrics log")
    ps.set_defaults(func=cmd_stats)

    pa = sub.add_parser("ailog", help="render docs/AI_LOG.md (the AI Interaction Log deliverable)")
    pa.set_defaults(func=cmd_ailog)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
