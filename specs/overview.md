# Brief — Skills & Tools as importable units (hssd, self-hosted)

## Context
hssd is a stdlib-only Python 3.12 CLI (`cli/hssd.py`) that drives a governed, adversarial
AI-coding workflow. We are **dogfooding**: using hssd to build a new hssd feature.

## Problem
Templates are importable — there is a blessed catalog plus `hssd template list / import / add / rm`.
**Skills are not:** they're bundled in the framework and copied wholesale into a project, routed by a
hardcoded `ROLE_SKILLS` map. We want skills to be importable like templates.

## Goal — this slice ("Crawl")
Add an `hssd skill` command family that mirrors `hssd template`:
- `hssd skill list` — show the blessed skill catalog + any user-registered skills (name · trigger · tech · source).
- `hssd skill import --from=<git-url> [--into <dir>]` — clone a skill repo and install it into
  `.claude/skills/<name>/` (additive, create-if-absent; idempotent on re-run).
- `hssd skill add --name <n> --from=<git-url> [--tech a,b]` — register a skill repo you trust → `~/.hssd/skills.json`.
- `hssd skill rm --name <n>` — unregister one of yours (blessed skills aren't removable).

## Constraints & conventions
- stdlib only (no new dependencies); Python 3.12.
- Reuse the existing template code paths where possible (`_full_catalog`-style catalog, `_mirror_if_absent`,
  clone-then-strip-`.git`).
- Non-destructive / idempotent install; never overwrite an existing skill file.
- Every behavior covered by tests. NOTE: the repo currently has **no test suite** — standing up
  `pytest` (and a `tests/` dir runnable via `uv run pytest`) is a prerequisite of this work.

## Out of scope (later slices, see proposals/skills-and-tools-as-importable.md)
- `skill.yaml` manifest + data-driven routing (Walk).
- Running a skill's `check.cmd` as deterministic evidence inside `engage`, with the Bash whitelist
  driven by `check.needs` (Run).
- Extracting the blessed skills into separate `hssd-skill-*` repos.

## Acceptance (high level)
- `hssd skill list` prints the blessed catalog and any user-registered skills.
- `hssd skill import --from=<git>` installs a skill into `.claude/skills/` and is idempotent (re-run = no dupes, no clobber).
- `hssd skill add` then `hssd skill rm` round-trip cleanly through `~/.hssd/skills.json`.
- Tests cover list / import / add / rm, including dedup against the full catalog and the create-if-absent merge.
