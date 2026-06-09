<p align="center">
  <img src="assets/hssd-wordmark.png" alt="Harness Studio — hssd" width="380">
</p>

# Harness Studio (`hssd`)

> A **governed, adversarial framework for delivering software with AI agents** — where *whoever does the work never judges their own "done"*, every result is proven by evidence, and autonomy is earned, not switched on.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.12-blue)
![status](https://img.shields.io/badge/status-research--preview-orange)

Harness Studio is a **framework on top of [Archon](https://github.com/coleam00/Archon)** and Claude Code. Archon is the engine that runs AI-coding workflows; Harness Studio is the opinionated, batteries-included layer that gives a project a *governed engineering team* — specialists that build, adversaries that try to break the work, and a CLI (`hssd`) that runs the whole loop.

It's an **AI-first development OS**: AI does the building, but everything is **well-defined and human-in-the-loop**.

---

## Why

Working with AI fails in two expensive ways:

- **Overconfidence** — it claims something works without proof, and because it sounds confident, the rest agree.
- **Early completion** — it declares "done" too soon: skips tests, silently cuts scope, handles only the happy path.

Both share one root: letting *the maker grade its own work*. Harness Studio fixes this structurally — **the author never certifies their own "done"; an independent adversary tries to prove it isn't**, and "done" only counts with evidence (test output, a diff, a screenshot), never a claim.

---

## Install

Requires **Python 3.12**.

```bash
# install straight from GitHub (no clone needed)
uv tool install git+https://github.com/harness-studio/harness-studio
hssd --help
```

Or, to hack on the framework itself, clone and install editable:

```bash
# from the repo root
uv tool install --editable .      # or: pipx install -e .
```

This puts `hssd` (short) and `harness-sd` (long) on your PATH.

## Quickstart — the whole flow

```bash
hssd new my-service                         # scaffold a project (governance from minute zero)
cd my-service

hssd overview add specs/overview.md         # register the project brief
hssd overview analyze --split-concerns      # → work items + tech/template suggestions

hssd work list                              # the backlog (via the PM Port)
hssd work claim LOC-1                        # atomic claim + feature branch

hssd engage LOC-1                            # run the 6-phase engagement loop
```

The AI backend is pluggable: `HSSD_AGENT_BACKEND=claude` (default, real agents via Claude Code) or `mock` (deterministic, for tests).

---

## Commands

| Command | What it does |
|---|---|
| `hssd new <name> [--from=<git>] [--template=<t>]` | Scaffold a project; drops governance (ADR, AI log), pre-commit, `.harness/` PM spine, git on `main`. |
| `hssd overview add <file>` | Register the project overview (the project-level intake). |
| `hssd overview analyze [--split-concerns]` | Analyze the overview; `--split-concerns` decomposes it into work items + recommends matching templates. |
| `hssd work list / show / add / claim` | Manage work items via the **PM Port** (local SQLite, or a synced robust PM). Claim is atomic. |
| `hssd engage <id> [--auto] [--no-security]` | Run the **6-phase engagement loop** on a work item. |
| `hssd template import --from=<git>` | Compose an external template (additive merge + conflict resolution). |
| `hssd janitor` | The **discovery heartbeat**: audit the codebase → dedup → file work items. |
| `hssd log [--verbose]` | The session/activity log (which also feeds the AI Interaction Log). |
| `hssd update [--check]` | Self-update the framework (`git pull`) / show version. |

---

## How it works

### The 6-phase engagement loop (`hssd engage`)

```
P0 Intake        product-analyst → Definition Skeptic (gate)
P1 Stories & AC  story-writer → AC Adversary (gate)
P2 Architecture  architect → Architecture Adversary (gate)
── SPEC LOCK ──  human approval · NO CODE before this (spec-driven)
P3 Build         backend-dev / frontend-dev  ⇄
P4 Verify        [ Security · Independent Verifier · Completion Challenger · Test · Regression ]
                 loop-until-dry — iterate until the adversaries find nothing
── MERGE ──      human approval → done
```

The maker never grades itself: the **P4 adversarial fan-out** is the goal-condition (loop-until-dry), checked by roles separate from the builders.

### Two loops (this is loop engineering)

```
JANITOR (discovery, scheduled)  →  work items  →  ENGAGE (remediation, 6 phases)
        ▲                                                    │
        └──────────────  .harness/  (durable memory)  ───────┘
```

You don't prompt the steps — you design the loops and decide at the leverage points (Spec Lock, merge). See [`LOOPS.md`](LOOPS.md).

---

## Core ideas

- **Adversarial** — the author never judges their own "done"; independent adversaries try to break it. ([`01-ROLES.md`](01-ROLES.md))
- **Spec-driven** — no code before the spec/ADR is locked (Spec Lock). ([`STANDARDS.md`](STANDARDS.md))
- **Opinionated** — one blessed way; escape hatches are documented or absent. ([`PHILOSOPHY.md`](PHILOSOPHY.md))
- **PM Port** — one interface for work items; local SQLite spine by default, robust project-management tools (GitHub, GitLab, Azure DevOps) attach as sync adapters. ([`WORK-INTAKE-AND-CLAIMING.md`](WORK-INTAKE-AND-CLAIMING.md))
- **Templates as git repos** — additive merge, conflict resolution with memory. ([`TEMPLATES.md`](TEMPLATES.md))
- **Skills** — blessed conventions per technology, routed by description. ([`skills/`](skills))
- **Right-sizing** — quality invariants never scale; scope, stack tier, and ceremony do.
- **Plain language** — no unexplained acronyms; every term is spelled out or defined in the [`GLOSSARY.md`](GLOSSARY.md). ([`PHILOSOPHY.md`](PHILOSOPHY.md) tenet 10)

> New here? The [**glossary**](GLOSSARY.md) defines every term and abbreviation used across the framework.

---

## Repo map

```
harness-studio/
  README.md                 # you are here
  GLOSSARY.md               # every term & acronym, defined (tenet 10)
  PHILOSOPHY.md             # the soul — why it's opinionated
  ARCHITECTURE.md           # layering on Archon, agent mechanisms, skill routing, delivery
  LOOPS.md                  # loop engineering — the engagement & janitor loops
  STANDARDS.md              # engineering standards (TDD, spec-driven, security, model tiering)
  WORK-INTAKE-AND-CLAIMING.md  # PM Port, claiming, git/branch model
  TEMPLATES.md              # templates-as-repos + composition/merge
  CLI.md                    # full CLI reference
  00–04 + VALUE-RISK-ROI    # operating manual, roles, process, deliverables, kickoff, ROI
  agents/                   # the team — 13 subagents (specialists + adversaries)
  skills/                   # python, fastapi, typescript + SKILL-AUTHORING
  templates/                # ADR, AI log, stories/AC, Definition of Done (doc templates)
  workflows/                # engagement.yaml, janitor.yaml (Archon-ready)
  examples/                 # illustrative example engagements (NOT the framework — outputs of it)
  cli/hssd.py               # the CLI
```

---

## Status

Research preview. The full flow is implemented and its orchestration verified end-to-end (with the `mock` backend); real agent execution runs via the `claude` backend.

- ✅ `new`, `init` (adopt any repo), `overview` (analyze → split), `work` (atomic claim), `engage` (6 phases + 5-checker P4), `template` (list/import via `--from`), `janitor` (dedup), `log`, `stats` (time/tokens/cost), `ailog` (AI Interaction Log), `update`.
- ✅ Blessed templates are **separate git repos** (`github.com/harness-studio/hssd-template-*`), resolved via `--from`.
- ⏳ Next: `pm add` / `vscode setup`, native Claude-Code subagent backend, and the runtime-execution gate ([`proposals/`](proposals)).

---

## Contributing

This kit is meant to be used, tested, and improved. See [`CONTRIBUTING.md`](CONTRIBUTING.md). The evolution rule: every escaped defect becomes a new guard — *fix the harness, not just the code.*

> **Git LFS:** binary assets (`presentation/`, `assets/`) are tracked with [Git LFS](https://git-lfs.com). Install `git-lfs` before cloning (`git lfs install`); if you cloned without it, run `git lfs pull` to fetch the real files instead of pointers.

## License

MIT — see [`LICENSE`](LICENSE).
