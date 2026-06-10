# hssd CLI (skeleton)

A stdlib-only Python skeleton of the Harness Studio CLI. Production targets Python 3.12 and ships as `harness-sd` (long) / `hssd` (short).

## Install (run `hssd` in your terminal)
Requires Python 3.12. From the `harness-studio/` folder:
```bash
uv tool install --editable .      # or: pipx install -e .   (editable: data dirs resolve from the repo)
hssd new my-project
hssd update                       # git pull the framework + report version
hssd update --check               # just show the version
```
Entry points install both `hssd` (short) and `harness-sd` (long). Verified: the entry point puts
`hssd` on PATH and the data dirs (agents/skills/templates/scaffolds) resolve via the editable install.
A fully-bundled wheel (package data via importlib.resources) is the productization step.

## Run without installing (skeleton)
```bash
python3 cli/hssd.py template list
python3 cli/hssd.py new ../my-project --template=backend-fastapi-sqlite
python3 cli/hssd.py new ../x --from=git@github.com:hssd/hssd-sample-react-vite-spa.git
(cd ../my-project && python3 /path/to/cli/hssd.py log)
```

## What `new` does (verified end-to-end)
1. Materializes the template (local blessed scaffold, or `--from` a git repo).
2. Renames `dotfiles/*` → real dotfiles (`.vscode/`, `.pre-commit-config.yaml`).
3. Drops governance day-zero: `docs/ADR.md` + `docs/AI_LOG.md` (from `templates/`).
4. Writes `hssd.yaml` with **`type: project`** (a managed project, not a template).
5. Creates `.harness/` (gitignored runtime spine) + `git init` on `main`.
6. Logs the action to `.harness/logs/session.log` (the audit trail).

## Agent runner (how skills + subagents "work")
`_run_role(role, prompt)` composes the subagent definition (`agents/<role>.md`) + the role's
scoped skills (`ROLE_SKILLS`) + the task, then hands it to the AI runtime:
- `HSSD_AGENT_BACKEND=claude` (default) → shells out to Claude Code (`claude -p`). Real agents.
- `HSSD_AGENT_BACKEND=mock` (+ `HSSD_MOCK_OUTPUT`) → deterministic, for tests.

## Status
- **Implemented & verified:** `new`, `work add/list/show/claim` (atomic claim),
  `overview add`, `overview analyze --split-concerns` (→ work items + tech/template recommendation),
  `template import` (additive merge), **`engage`** (the 6-phase loop with the P4 goal-condition
  loop-until-dry + human gates + durable state in `.harness/engagements/<id>/`), `log`.
- **Next:** `pm add` (sync adapters), `vscode setup`, `update`, and the `janitor` loop.
- **Engage testing:** `HSSD_AGENT_BACKEND=mock HSSD_MOCK_FILE=<role→output.json> hssd engage <id> --auto`.
- **Decision (ratifiable):** Python (stdlib) for zero-dep portability and easy testing.
