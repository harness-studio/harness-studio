# Changelog

All notable changes to Harness Studio are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Pre-1.0: minor version bumps (`0.x`) carry new features and breaking changes.
Patch bumps (`0.x.y`) are bug fixes and non-breaking additions only.

---

## [0.2.0] — 2026-06-13

### Added

- **`hssd project approve|show|check`** — new gate that transitions the project from
  `initialized` to `identified`. Locks `.harness/project.md` as the stable project
  identity anchor (vision, objectives, non-goals, principles).
- **`hssd intake add|list|show|approve`** — recurring intake cycle, replacing the
  one-shot `overview add/split` flow. Any demand (manual, structured, unstructured,
  operational) enters through intake and is groomed before becoming stories.
- **`hssd iteration plan|activate|list|converge`** — iterations as first-class entities.
  `activate` is variadic: `hssd iteration activate id1 id2 id3` starts N parallel
  engineering loops, each in its own worktree. Caller (Claude Code, headless CLI,
  CI) manages orchestration.
- **`hssd skill list|import|add|rm`** — skill management: install skills from git repos,
  add custom entries to the user catalog, remove by name or URL.
- **`hssd --version`** — prints the installed version (`hssd x.y.z`).
- **`__version__`** constant in `cli/hssd.py`, read from `importlib.metadata` with
  fallback for editable installs.
- **Smart `hssd init` detection** — scans the target directory for source files and
  package manifests. Blank projects get "write project.md from scratch" guidance;
  existing projects get "review and approve what the AI found" guidance; ambiguous
  cases ask the developer.
- **`docs/state-machine.md`** — canonical reference for all five project states
  (`not_initialized → initialized → identified → architected → operational`).
- **`docs/intake.md`** — canonical reference for the four intake forms and the
  three-stage grooming cycle.
- **`docs/iteration.md`** — canonical reference for iteration planning, variadic
  activation, parallel execution, and convergence.
- **`docs/engineering-loop.md`** — canonical reference for P0→P4 phases, maker ≠
  checker principle, and all five adversary roles.
- **`docs/project-identity.md`** — canonical reference for `project.md`, two creation
  paths (new vs. adopt), and how identity anchors intake validation.
- **`.harness/project.md`** — project identity document for harness-studio itself
  (the framework dogfooding its own pattern).
- **Presentation layer** — `presentation/` now contains Marp-compatible slide decks
  (`deck-framework-overview.md`, `deck-use-cases.md`) and regenerated infographic
  (`Harness-Studio-Infographic.png`/`.pdf`) reflecting the new model. The infographic
  is generated from `infographic.html` via Puppeteer and can be regenerated with
  `node presentation/screenshot.js`.

### Changed

- **State machine redesign** (breaking) — the project phase sequence is now
  `not_initialized → initialized → identified → architected → operational`.
  The old `briefed` and `planned` states are removed. `identified` replaces `briefed`
  and requires human approval of `project.md` (not just the presence of `overview.md`).
  `operational` is now triggered by the first approved intake rather than the first
  opened sprint.
- **`hssd status` output** — displays the four new states. Shows `not_initialized`
  banner when `.harness/` is absent.
- **`hssd init` next-step guidance** — now uses `_detect_project_size` to give
  context-appropriate guidance instead of always pointing to `hssd overview add`.
- **`pyproject.toml` dependencies** — `matplotlib` and `pillow` added (used by the
  presentation layer Puppeteer alternative; kept as declared dependencies).

### Deprecated

- **`hssd overview add|analyze|architect|split`** — still functional for backwards
  compatibility but prints a deprecation warning (`⚠ use 'hssd intake' instead`).
  Will be removed in `0.3.0`.

### Fixed

- **`rm --from=<url>` latent bug** — predicate `e.get("url") != args.from_git` when
  both are `None` caused over-deletion of entries with no URL. Fixed with explicit
  `args.from_git` guard.
- **`SKILL_CATALOG` duplicate URLs** — all 10 blessed skill entries previously shared
  the same placeholder URL, making dedup tests vacuous. Each entry now has a distinct
  `https://github.com/harness-studio/hssd-skill-<name>` URL.
- **AC15 weak assertion** — `test_ac15_import_idempotent` had an `or "0" in out` branch
  that was trivially true. Assertion tightened to `"created 0" in out.lower()` only.
- **AC24 dead sentinel** — mtime comparison in `test_ac24_real_home_skills_json_untouched`
  had a boolean short-circuit that always passed when `~/.hssd` didn't exist. Fixed
  with a module-level snapshot taken before any test ran.

---

## [0.1.0] — initial release

- `hssd init` — adopt a repo into Harness Studio governance
- `hssd new` — scaffold a new project from a template
- `hssd engage <id>` — run the 6-phase engagement loop (P0→P4) on a work item
- `hssd overview add|analyze|architect|split` — brief registration, product analysis,
  architecture proposal, and story split
- `hssd architecture approve|status|reopen` — human lock over the shared ADR
- `hssd sprint plan|status|review|close` — sprint lifecycle
- `hssd work add|list|show|claim|done` — work item management via SQLite PM
- `hssd janitor` — codebase health scan (drift, debt, latent bugs)
- `hssd skill` — (added mid-cycle, now in 0.2.0)
- `hssd ailog` — render the AI Interaction Log deliverable
- `hssd stats` / `hssd log` — analytics and session log
- 14 agent role cards in `.claude/agents/`
- Engineering skills: `sqlite-concurrency`, `sql-indexing`, `datetime-utc`,
  `api-conventions`, `resilience`, `push-over-pull`, `python`, `fastapi`, `typescript`
