<p align="center">
  <img src="assets/hssd-wordmark.png" alt="Harness Studio — hssd" width="380">
</p>

# Harness Studio (`hssd`)

> A **governed, adversarial framework for delivering software with AI agents** — where *whoever does the work never judges their own "done"*, every result is proven by evidence, and autonomy is earned, not switched on.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.12-blue)
![status](https://img.shields.io/badge/status-research--preview-orange)

Harness Studio is a **framework on top of Claude Code**. The `hssd` CLI is the engine — it holds the project state and drives the AI-coding workflow end-to-end — and the framework is the opinionated, batteries-included layer that gives a project a *governed engineering team*: specialists that build, adversaries that try to break the work, and gates that hold the quality line.

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

**From GitHub (no clone needed):**

```bash
GIT_LFS_SKIP_SMUDGE=1 uv tool install git+https://github.com/harness-studio/harness-studio
hssd --help
```

`GIT_LFS_SKIP_SMUDGE=1` skips downloading binary assets (presentation slides, cover images) that the CLI doesn't need. Without it, git-lfs will try to fetch them and may fail or slow down the install.

To upgrade later:

```bash
GIT_LFS_SKIP_SMUDGE=1 uv tool install --reinstall git+https://github.com/harness-studio/harness-studio
```

**Editable install (to hack on the framework itself):**

```bash
git clone https://github.com/harness-studio/harness-studio
cd harness-studio
uv tool install --editable .      # or: pipx install -e .
```

Both forms put `hssd` (short) and `harness-sd` (long) on your PATH.

## Quickstart — the whole flow

A project moves through a **state machine** (`hssd status` always shows where you are), then lives in operation forever, delivering through bounded **sprints**.

```bash
hssd new my-service                         # initialized — scaffold a project (governance from minute zero)
cd my-service

hssd overview add specs/overview.md         # briefed — register the project brief

hssd overview architect                     # propose the ADR (data model, ownership, stack tier);
                                            #   an adversary advises, you iterate on docs/ADR.md
hssd architecture approve                   # architected — LOCK the ADR as an immutable version

hssd overview analyze                       # decompose the brief; then:
hssd overview split                         # planned — the product backlog

hssd sprint plan --goal "first slice"       # operational — open a sprint (pull scope from backlog)
hssd work list                              # the sprint's stories (via the PM Port)
hssd work claim LOC-1                        # atomic claim + feature branch
hssd engage LOC-1                            # run the 6-phase engagement loop on a story

hssd sprint review                          # fix-the-harness retro when the stories are done
hssd sprint close                           # close the sprint — the project stays operational; repeat
```

The project never reaches a terminal "done": once `operational`, it loops sprints (deliver → review → close → plan again) across operation and maintenance. The AI backend is pluggable: `HSSD_AGENT_BACKEND=claude` (default, real agents via Claude Code) or `mock` (deterministic, for tests).

---

## Commands

| Command | What it does |
|---|---|
| `hssd new <name> [--from=<git>]` | Scaffold a project; drops governance (ADR, AI log), pre-commit, `.harness/` PM spine, git on `main`. |
| `hssd init` | Turn ON Harness Studio in an existing repo (non-destructive). |
| `hssd status` | Show the **project state machine** (initialized → briefed → architected → planned → operational) + the next command. |
| `hssd overview add <file>` | Register the project overview (the project-level intake). |
| `hssd overview architect` | **Propose** the ADR (data model + ownership, stack tier, concurrency/isolation); an adversary advises. |
| `hssd architecture approve` | The **human architecture gate**: LOCK the ADR as an immutable version (`docs/adr/ADR-vN.md`). Unlocks split/analyze/engage. |
| `hssd overview analyze [--split-concerns]` | Analyze the overview; `--split-concerns` decomposes it into work items in one shot (skips the review gate). |
| `hssd overview split` | Decompose the brief into the product backlog (after the architecture lock). |
| `hssd sprint plan / status / review / close` | The **sprint loop**: pull scope from the backlog (with an architecture-delta check), run it, retro, close. The project stays operational across sprints. |
| `hssd work list / show / add / claim` | Manage work items via the **PM Port** (local SQLite, or a synced robust PM). Claim is atomic. |
| `hssd engage <id> [--auto] [--accept-recommended] [--max-calls N] [--budget USD] [--no-security]` | Run the **6-phase engagement loop** on a work item. |
| `hssd template list / import --from=<git>` | List or compose an external template (additive merge + conflict resolution). |
| `hssd janitor` | The **discovery heartbeat**: audit the codebase → dedup → file work items. |
| `hssd log [--verbose]` / `hssd stats` / `hssd ailog` | The session log; time/token/cost analytics; render the AI Interaction Log. |
| `hssd update [--check]` | Self-update the framework (`git pull`) / show version. |

---

## How it works

### The 6-phase engagement loop (`hssd engage`)

```
P0 Intake        product-analyst → Definition Skeptic (gate)
P1 Stories & AC  story-writer → Criteria/AC Adversary (gate)
P2 Architecture  architect → Architecture Adversary (gate)
── SPEC LOCK ──  human approval · NO CODE before this (spec-driven)
P3a Red          test-author writes failing tests from the LOCKED AC — the CLI runs them; they MUST fail
P3b Green        backend-dev / frontend-dev implement until the CLI sees the tests pass  ⇄
P4 Verify        [ Security · Independent Verifier · Completion Challenger · Test/Concurrency · Regression Hunter ]
                 loop-until-dry — iterate until the adversaries find nothing
── MERGE ──      human approval → done
```

**TDD is enforced, not hoped for.** P3 splits in two: P3a Red writes the tests *before any code* (tests that pass with no implementation are vacuous → blocked); P3b Green implements until they pass. Both outputs are captured as evidence in `.harness/engagements/<id>/`. Maker ≠ checker holds throughout: `test-author` ≠ builder ≠ the P4 adversaries. Every gate is **bounded loop-forward** — it retries a capped number of rounds under a per-run AI-call ceiling (`--max-calls`, default 40) and optional `--budget`, then converges on the recommended resolutions rather than looping forever. The maker never grades itself: the **P4 adversarial fan-out** is the goal-condition (loop-until-dry), checked by roles separate from the builders.

### The loops (this is loop engineering)

The project state machine is **non-terminal**: `initialized → briefed → architected → planned → operational(∞)`. Once operational, delivery happens in bounded **sprints** (plan → engage stories → review → close), while the project itself keeps living. Inside each story, the 6-phase engagement loop runs; the janitor feeds it discovered work.

```
SPRINT (bounded: plan → engage → review → close)   ·   project stays operational, never "done"
JANITOR (discovery, scheduled)  →  work items  →  ENGAGE (remediation, 6 phases)
        ▲                                                    │
        └──────────────  .harness/  (durable memory)  ───────┘
```

You don't prompt the steps — you design the loops and decide at the leverage points (the architecture lock, Spec Lock, merge, sprint close). See [`LOOPS.md`](LOOPS.md).

---

## Core ideas

- **Adversarial** — the author never judges their own "done"; independent adversaries try to break it. ([`01-ROLES.md`](01-ROLES.md))
- **Spec-driven** — no code before the spec/ADR is locked (the human architecture gate, then Spec Lock). ([`STANDARDS.md`](STANDARDS.md))
- **TDD enforced** — a dedicated `test-author` writes failing tests from the locked criteria (P3a Red), the builder makes them pass (P3b Green); the CLI runs both and captures the evidence. ([`STANDARDS.md`](STANDARDS.md))
- **Fix the harness, not the code** — every escaped defect becomes a standing guard. The blessed **engineering skills** (`sqlite-concurrency`, `sql-indexing`, `datetime-utc`, `api-conventions`, `resilience`, `push-over-pull`) are find-and-propose checklists adversaries use to catch a violation and propose the fix. ([`skills/`](skills))
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
  ARCHITECTURE.md           # the CLI engine, agent mechanisms, skill routing, delivery
  LOOPS.md                  # loop engineering — the engagement & janitor loops
  STANDARDS.md              # engineering standards (TDD, spec-driven, security, model tiering)
  WORK-INTAKE-AND-CLAIMING.md  # PM Port, claiming, git/branch model
  TEMPLATES.md              # templates-as-repos + composition/merge
  CLI.md                    # full CLI reference
  00–04 + VALUE-RISK-ROI    # operating manual, roles, process, deliverables, kickoff, ROI
  agents/                   # the team — 15 subagents (specialists, adversaries + the janitor)
  skills/                   # python, fastapi, typescript + 6 blessed engineering guards + SKILL-AUTHORING
  templates/                # ADR, AI log, stories/AC, Definition of Done (doc templates)
  workflows/                # engagement.yaml, janitor.yaml (reference SOP encoding — the CLI runs the loop)
  examples/                 # illustrative example engagements (NOT the framework — outputs of it)
  cli/hssd.py               # the CLI
```

---

## Status

Research preview. The full flow is implemented and its orchestration verified end-to-end (with the `mock` backend); real agent execution runs via the `claude` backend.

- ✅ `new`, `init` (adopt any repo), `status` (the project state machine), `overview` (add → architect → analyze → split), `architecture` (the human ADR lock, versioned), `sprint` (plan → review → close), `work` (atomic claim), `engage` (6 phases, enforced P3a Red → P3b Green TDD, 5-checker P4, bounded loop-forward), `template` (list/import via `--from`), `janitor` (dedup), `log`, `stats` (time/tokens/cost), `ailog` (AI Interaction Log), `update`.
- ✅ Blessed templates are **separate git repos** (`github.com/harness-studio/hssd-template-*`), resolved via `--from`.
- ⏳ Next: `pm add` / `vscode setup`, native Claude-Code subagent backend, and the runtime-execution gate ([`proposals/`](proposals)).

---

## Contributing

This kit is meant to be used, tested, and improved. See [`CONTRIBUTING.md`](CONTRIBUTING.md). The evolution rule: every escaped defect becomes a new guard — *fix the harness, not just the code.*

> **Git LFS:** binary assets (`presentation/`, `assets/`) are tracked with [Git LFS](https://git-lfs.com). Install `git-lfs` before cloning (`git lfs install`); if you cloned without it, run `git lfs pull` to fetch the real files instead of pointers.

## License

MIT — see [`LICENSE`](LICENSE).
