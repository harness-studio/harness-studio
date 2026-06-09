#!/usr/bin/env python3
"""hssd — Harness Studio CLI (skeleton).

Long name: harness-sd. Short alias: hssd. Targets Python 3.12 in production;
uses only the stdlib so the skeleton runs anywhere.

Implemented (skeleton):
  hssd new <name> [--template=<t>] [--from=<git-url>]
  hssd template list | import --from=<git-url>
  hssd log [--verbose]
"""

from __future__ import annotations

import argparse
import datetime
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


def _user_catalog_path() -> Path:
    """User-registered templates (the ones *you* trust), shared across all your projects."""
    return Path.home() / ".hssd" / "templates.json"


def _load_user_catalog() -> list[dict]:
    p = _user_catalog_path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _full_catalog() -> list[dict]:
    """Blessed templates + the user's own registered ones. Any git URL still works via --from."""
    return ([dict(t, source="blessed") for t in TEMPLATE_CATALOG]
            + [dict(t, source="user") for t in _load_user_catalog()])

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
-> P3 Build -> P4 adversarial verification (loop-until-dry) -> [Merge].
Backlog & flow via the `hssd` CLI (`hssd work list`, `hssd engage <id>`).

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
    print('  next: hssd overview add <brief.md>  ·  hssd work add --title "..."  ·  hssd engage <id>')
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
    """Re-sync .claude/ (agents, skills, commands) from the framework — OVERWRITES, so a project
    picks up framework updates (init is create-if-absent and won't refresh them)."""
    dest = Path(".").resolve()
    n = 0
    if AGENTS.exists():
        n += _mirror_force(AGENTS, dest / ".claude" / "agents")
    skills_root = PKG_ROOT / "skills"
    if skills_root.exists():
        for d in sorted(skills_root.iterdir()):
            if d.is_dir():
                n += _mirror_force(d, dest / ".claude" / "skills" / d.name)
    commands_root = PKG_ROOT / "commands"
    if commands_root.exists():
        n += _mirror_force(commands_root, dest / ".claude" / "commands")
    _log(dest, "sync", f"files={n}")
    print(f"OK: re-synced {n} file(s) into .claude/ from the framework (agents, skills, commands).")
    return 0


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
    _log(project, "template import", f"src={args.from_git or args.template} conflicts={len(conflicts)}")
    if conflicts:
        print(f"composed with {len(conflicts)} conflict(s) [policy={policy}]:")
        for c in conflicts:
            print(f"  - {c}")
    else:
        print("composed cleanly (additive merge, no conflicts)")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


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
    for col in ("source TEXT", "fingerprint TEXT"):  # upgrade older DBs in place
        try:
            con.execute(f"ALTER TABLE work_items ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
    con.commit()
    return con


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


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
    subprocess.run(["git", "checkout", "-q", "-b", branch], check=False)
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


# Role -> blessed skills it loads (the CLI does the skill routing / scoping).
ROLE_SKILLS = {
    "backend-dev": ["python", "fastapi"],
    "frontend-dev": ["typescript"],
    "architect": ["python", "fastapi", "typescript"],
}


def _claude_argv(exe: str, fmt: str) -> list[str]:
    argv = [exe, "-p", "--output-format", fmt]
    if fmt == "stream-json":
        argv.append("--verbose")  # stream-json requires --verbose
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        argv = ["cmd", "/c", *argv]  # CreateProcess can't launch a .cmd shim directly
    return argv


def _claude_blocking(exe: str, composed: str):
    """Single blocking JSON call (fallback / HSSD_STREAM=0). Returns (text, usage, cost, api_ms)."""
    res = subprocess.run(_claude_argv(exe, "json"), input=composed, capture_output=True,
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


def _claude_stream(exe: str, composed: str, role: str):
    """Run `claude -p --output-format stream-json` and surface the interaction LIVE so a terminal
    user isn't in the dark. Returns (text, usage, cost, api_ms)."""
    proc = subprocess.Popen(_claude_argv(exe, "stream-json"), stdin=subprocess.PIPE,
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
    if os.environ.get("HSSD_STREAM", "1") != "0":
        try:
            text, usage, cost, api_ms = _claude_stream(exe, composed, role)
        except Exception as e:  # noqa: BLE001 — any stream hiccup → safe fallback
            print(f"    (stream unavailable: {e}; falling back to a blocking call)", file=sys.stderr)
            text, usage, cost, api_ms = _claude_blocking(exe, composed)
    else:
        text, usage, cost, api_ms = _claude_blocking(exe, composed)

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

    # split: create work items from the ALREADY-APPROVED plan (no model re-call).
    if args.action == "split":
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

    # analyze: understand the brief, propose a decomposition, SAVE the plan, but create nothing.
    if not ov.exists():
        print("BLOCK: no overview yet. Run 'hssd overview add <file>' first.", file=sys.stderr)
        return 1
    text = ov.read_text(encoding="utf-8")
    out = _run_role(
        "product-analyst",
        "Analyze this project brief. Return JSON with: 'analysis' (understanding + short plan), "
        "'concerns' (a list of {title, type, kind} the brief decomposes into — kind is 'task' to "
        "engineer, or 'config' for a capability the harness already provides and just needs "
        "enabling, e.g. the AI Interaction Log / logging / audit), and 'technologies' (a list)."
        f"\n\n{text}",
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
            subprocess.run(["git", "checkout", "-q", "-b", branch], check=False)
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
    base_ctx = f"Work item {args.id}: {title}\n(Project overview in .harness/overview.md)\n\n{accept}"

    def current_ctx() -> str:  # re-read assumptions each call so recorded answers take effect
        c = base_ctx
        if assumptions_file.exists():
            c += ("\n\n## Resolved assumptions (decided by the Engagement Lead — treat as settled; "
                  "do NOT re-raise these)\n" + assumptions_file.read_text(encoding="utf-8"))
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
        """Adversary gate that never dead-ends: on BLOCK it shows options + the recommended fix;
        with --accept-recommended it records the recommended resolutions and retries (loop-forward)."""
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
            if args.accept_recommended and attempt < max_retry and findings:
                n = _accept_recommended(findings)
                if n:
                    print(f"    ↻ accepted {n} recommended resolution(s) → retrying {label}")
                    continue
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
        print("P0 Intake"); run("product-analyst")
        if not passing_gate("definition-skeptic", "Definition Skeptic"):
            return 2
        print("P1 Stories & AC"); run("story-writer")
        if not passing_gate("ac-adversary", "AC Adversary"):
            return 2
        print("P2 Architecture"); run("architect")
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
        # Code deliverable: the goal loop — iterate until the adversarial checkers are dry.
        checkers = [
            ("independent-verifier", "Independent Verifier"),
            ("completion-challenger", "Completion Challenger"),
            ("test-adversary", "Test Adversary"),
            ("regression-hunter", "Regression Hunter"),  # always on — integrity is non-negotiable
        ]
        # Security is mandatory for API/auth surfaces (STANDARDS §2); --no-security opts out for
        # non-API work (the documented escape hatch).
        if not args.no_security:
            checkers.insert(0, ("security-adversary", "Security/Attack Adversary"))
        dry = False
        for attempt in range(1, args.max_iter + 1):
            print(f"P3 Build (attempt {attempt})"); run("backend-dev"); run("frontend-dev")
            print("P4 Verification")
            blockers = [label for role, label in checkers if not gate(role, label)]
            if not blockers:
                print("  ✓ loop-until-dry: dry (all checkers PASS)"); dry = True; break
            print(f"  ↻ blockers {blockers} → back to P3")
        if not dry:
            print(f"BLOCK: still failing after {args.max_iter} attempts.", file=sys.stderr); return 1

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

    p = argparse.ArgumentParser(prog="hssd", description="Harness Studio CLI (skeleton)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pn = sub.add_parser("new", help="create a project (empty governed, or from a template repo via --from)")
    pn.add_argument("name")
    pn.add_argument("--from", dest="from_git", default=None, help="git URL of a blessed template repo")
    pn.set_defaults(func=cmd_new)

    pi = sub.add_parser("init", help="turn ON Harness Studio in an existing repo (non-destructive)")
    pi.add_argument("path", nargs="?", default=".", help="repo to adopt (default: current dir)")
    pi.set_defaults(func=cmd_init)

    psy = sub.add_parser("sync", help="re-sync .claude/ (agents, skills, commands) from the framework (overwrites)")
    psy.set_defaults(func=cmd_sync)

    pt = sub.add_parser("template", help="list / import / register templates (blessed catalog + your own; any git URL)")
    pt.add_argument("action", choices=["list", "import", "add", "rm"])
    pt.add_argument("--from", dest="from_git", default=None, help="git URL (to import, or to register/remove)")
    pt.add_argument("--name", default=None, help="name when registering (add) or removing (rm)")
    pt.add_argument("--tech", default=None, help="comma-separated tech tags when registering (add)")
    pt.add_argument("--into", default=None, help="target project dir for import (default: cwd)")
    pt.set_defaults(func=cmd_template)

    po = sub.add_parser("overview", help="register/analyze the project overview, then split into work items")
    po.add_argument("action", choices=["add", "analyze", "split"])
    po.add_argument("file", nargs="?")
    po.add_argument("--split-concerns", action="store_true",
                    help="one-shot: analyze AND create the work items (skips the review gate)")
    po.set_defaults(func=cmd_overview)

    pw = sub.add_parser("work", help="work items via the PM Port (local SQLite or synced PM)")
    pw.add_argument("action", choices=["add", "list", "show", "claim"])
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
