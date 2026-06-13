# Proposal — Skills & Tools as importable units (like templates)

> Status: **proposed** (awaiting human ratification — the framework's own rule for architecture).
> Author: phase-2 design pass. Companion to the agent/process determinism backlog.
> One line: make a **skill** a self-contained, importable unit — the way templates already are — that carries *both* the blessed knowledge (SKILL.md) *and* the deterministic tool that enforces it (a declared check + scripts). Importing a skill brings the convention **and** its enforcement.

---

## 1. The insight

We work really well with **templates**: there's a blessed catalog, you `import` one into a project, you can register your own, and composition is additive with conflict memory. Skills don't work that way yet — they're bundled in the framework and copied wholesale, with hardcoded routing.

Two moves, together:

1. **Skills become importable like templates** — discover from a catalog, import the one you want, register your own, route data-driven.
2. **A skill carries its tool** — the deterministic enforcer (a linter command / script) ships *inside* the skill. This is the missing half: today skills are inferential checklists; pairing each with a runnable check is exactly what turns an inferential checker into a deterministic one (the phase-2 goal, and the `computational > inferential` matrix from `plano-harness-v2`).

So "skills e tools" isn't two features — it's one unit. A skill = knowledge + the tool that proves it.

---

## 2. How it works today (grounded)

**Templates** (`cli/hssd.py` → `cmd_template`):
- `TEMPLATE_CATALOG` (blessed, in-code) + `~/.hssd/templates.json` (user-registered) → `_full_catalog()`.
- `hssd template list | import --from=<git> | add | rm`. Import clones the repo, then composes additively: `.gitignore` union, `.json` deep-merge, other files create-if-absent, conflicts recorded (`_union_lines`, `_merge_json`, `_deep_merge`). Templates are **separate git repos** (`hssd-template-*`).

**Skills** (today):
- Live in the framework repo at `skills/<name>/SKILL.md` (format defined in `SKILL-AUTHORING.md`: `name` + `description` frontmatter; *blessed way / conventions / gotchas / how done is proven / out of scope*).
- `_wire_claude` copies **all** bundled skills into the project's `.claude/skills/` at `new`/`init` (create-if-absent); `hssd sync` re-mirrors them (overwrite).
- Routing is **hardcoded**: `ROLE_SKILLS` maps role→skills in `hssd.py`; `_run_role` folds the matched `SKILL.md` text into the role's prompt.
- Gap: no catalog, no `skill import`, no per-project selection, no user-registered skills, and **no first-class tool** — `SKILL-AUTHORING` allows a `scripts/` dir but nothing declares or runs a deterministic check.

The asymmetry is the opportunity: do for skills what we already do for templates.

---

## 3. Proposed design

### 3.1 The `hssd skill` command family (mirror `hssd template`)

| Command | Behavior |
|---|---|
| `hssd skill list` | Blessed `SKILL_CATALOG` + user-registered. Columns: name · trigger (the `description`) · tech tags · ships-a-tool? · source (blessed/user). |
| `hssd skill import --from=<git-url> [--into <dir>]` | Clone a skill repo, install into `.claude/skills/<name>/`, register it in the project skill manifest. Additive / create-if-absent (like templates). |
| `hssd skill add --name <n> --from=<git> [--tech ...]` | Register a skill repo *you* trust → `~/.hssd/skills.json`. Reusable across projects. |
| `hssd skill rm --name <n>` | Unregister one of yours (blessed ones aren't removable). |

Symmetry with `template` keeps the mental model and lets us reuse `_full_catalog`-style code, `_mirror_if_absent`, and the clone path.

### 3.2 The skill package format (extend SKILL-AUTHORING)

```
<skill-name>/
  SKILL.md          # required — unchanged (the blessed knowledge)
  examples/         # optional — unchanged
  scripts/          # optional — the helper scripts the tool invokes
  skill.yaml        # NEW (optional) — machine-readable manifest: routing + the tool
```

`skill.yaml`:

```yaml
name: sqlite-concurrency
kind: guard                 # guard | tech | process
tech: [python, sqlite, fastapi]
roles: [architect, architecture-adversary, backend-dev, test-author, test-adversary]
status: blessed             # blessed | proposed  (mirrors SKILL-AUTHORING ratification)
check:                      # the deterministic tool this skill ships (optional)
  cmd: "ruff check --select=B,S ."     # or: "python scripts/check_dual_writer.py"
  needs: [ruff]             # binaries required → drives the Bash whitelist
  authoritative: true       # true = nonzero exit hard-BLOCKs; false = feed output as evidence only
```

`skill.yaml` is optional — a skill with only `SKILL.md` still works (pure inferential checklist, as today). Adding it upgrades the skill to data-driven routing + a real tool.

### 3.3 Data-driven routing (retire the hardcoded map for imported skills)

- Today: `ROLE_SKILLS` is in `hssd.py`. That can't know about an imported skill.
- Proposed: a per-project manifest `.harness/skills.json`, written/updated by `skill import` (and seeded at `new`/`init` for the bundled blessed skills). It maps skill→roles, taken from `skill.yaml roles:` (explicit) — or, when absent, by matching the skill `description` to the task (the route-by-description idea SKILL-AUTHORING already states).
- `_run_role` reads the manifest in addition to / instead of `ROLE_SKILLS`. Bundled skills keep working via a default manifest.

### 3.4 Tools become first-class — the determinism payoff

This is where it pays for itself (and answers "checkers mais determinísticos"):

- When a role loads a skill that declares `check`, the CLI **runs `check.cmd`** in the project, captures stdout/stderr to `.harness/engagements/<id>/checks/<skill>.log`, and:
  - if `authoritative: true` → nonzero exit is a deterministic **BLOCK** *before* spending an inferential adversary call (computational > inferential);
  - else → the output is folded into the adversary's prompt as **evidence** ("here is what ruff/bandit/spectral found — assess it"), so the LLM judges anchored on real tool output, not vibes.
- `check.needs` declares required binaries → the project's Bash whitelist (`CLAUDE_SETTINGS_LOCAL` in `hssd.py`, today only `ruff/pytest/npm/npx/node`) is **auto-extended** for those tools (`mypy`, `bandit`, `tsc`, `eslint`, `spectral`). This also unblocks the agent-audit's #2.1.

Concretely, this lets us back the blessed guards with real enforcers: `sqlite-concurrency` ships a dual-writer/`INSERT OR REPLACE` grep script; `api-conventions` ships `spectral lint`; a new `code-quality` skill ships `ruff check` + complexity; `security` ships the secret-scan + `bandit`. The adversary stops "judging by eye."

### 3.5 Blessed skills as separate repos (mirror templates-as-repos) — the community hook

Like `hssd-template-*`, blessed skills can live as `hssd-skill-*` repos listed in `SKILL_CATALOG`. The community can publish a skill and have people `hssd skill import --from=<their-repo>` without forking the framework. This is the concrete substrate for "build *with* the community": a skill is the unit of contribution.

---

## 4. Phased rollout (crawl → walk → run)

- **Crawl** — `hssd skill list` + `hssd skill import --from=<git>` installing into `.claude/skills/` (additive). Imported skills route by `description` or a minimal manifest. No tool execution yet. (Smallest slice; mirrors `template list`/`import`.)
- **Walk** — introduce `skill.yaml` + `.harness/skills.json`; data-driven routing; `hssd skill add/rm`; migrate the bundled blessed skills to declare `skill.yaml`.
- **Run** — the CLI runs `check.cmd` as deterministic evidence/blocks inside `engage`; Bash whitelist driven by `check.needs`; extract blessed skills to `hssd-skill-*` repos + populate `SKILL_CATALOG`.

Each step ships value alone and is reversible — same discipline as the rest of the framework.

---

## 5. Open questions (need your ratification)

1. **Packaging:** blessed skills as many `hssd-skill-*` repos (like templates) **or** one `hssd-skills` registry repo with many skills inside? (Templates chose separate repos; skills are smaller, so a registry monorepo may be friendlier to import-by-name.)
2. **Routing:** explicit `skill.yaml roles:` vs automatic `description`-matching vs both (explicit wins, description fills gaps)?
3. **Tool authority:** should `check.cmd` hard-block (computational gate) or only feed evidence? Proposed default: **authoritative for objective tools** (ruff, secret-scan, spectral) → hard-block; **advisory for heuristic ones** → evidence.
4. **Selection model:** import-only (project gets only what it imports) vs bundled-by-default + import-extra? Proposed: keep the 6 blessed guards bundled-by-default (zero-config), import for everything else.
5. **Scope of v1:** ship just Crawl (`skill list`/`import`) now, or go straight to Walk (with `skill.yaml` + manifest)?

---

## 6. Why this is on-philosophy

- **Opinionated, additive:** new need → import a skill, never a config flag (PHILOSOPHY).
- **Computational > inferential:** the tool runs first; the LLM only judges what's left (the controls matrix).
- **Maker ≠ checker preserved:** skills don't build; they arm the existing roles with sharper, deterministic checks.
- **Fix the harness, not the code:** an escaped defect becomes a new *skill+tool* you import everywhere — the guard travels.
- **Community:** a skill is the unit of contribution — free and open source, extended by the people who use it.
