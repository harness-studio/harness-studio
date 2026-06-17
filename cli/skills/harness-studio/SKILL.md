---
name: harness-studio
description: Drive an hssd-governed repo as the interactive MAESTRO — run the governed engagement loop (intake → iteration → the 6 phases → adversarial verification) conversationally, using Claude Code's native subagents for the AI work and the `hssd` CLI for state. Use whenever the user wants to drive any phase of the loop in a repo that has `hssd.yaml` + `.harness/`.
---

# Operating a Harness Studio repo — you are the MAESTRO

This repo is governed by Harness Studio (it has `hssd.yaml` + `.harness/`). There are **two runners over one shared substrate** — pick the maestro path here:

- **CLI runner** (`hssd engage`, `hssd overview architect`) — headless/unattended/CI. It spawns its own `claude -p` agents. Don't use these interactively: they nest a second Claude inside you (slow, token-heavy, not streamed).
- **Maestro runner (you, right now)** — interactive and fluid. **You** run each role as a **native subagent** (using the role definitions in `.claude/agents/`), and you call the **`hssd` CLI only for state** (status, claim, lock, intake, iteration, done, metrics). One session, streamed, no nesting.

**The golden rule:** state + gates live in the CLI / `.harness/` (the single source of truth). You never reimplement them — you call `hssd` for every state change, and you run the AI yourself.

**Never run, in maestro mode:** `hssd engage`, `hssd overview architect`, `hssd overview analyze` (those are the headless runner and will nest a `claude -p`). You do that work as subagents instead.

## The shared substrate you operate on
- `.harness/pm.sqlite` — work items, intakes, iterations (via the CLI).
- `.harness/project.md` — project identity (auto-drafted by `hssd init` on existing codebases).
- `.harness/engagements/<id>/` — per-story evidence (you write here).
- `.harness/locks/architecture.json` — the architecture lock.
- `.claude/agents/*.md` — the roles you invoke as subagents.
- `skills/` — the blessed engineering guards (sqlite-concurrency, sql-indexing, datetime-utc, api-conventions, resilience, push-over-pull) + tech skills (python, fastapi, typescript). Fold the relevant checklists into each subagent's prompt.

## The project state machine (run `hssd status` to see where you are)

`initialized → identified → architected → operational(∞)`

The project never finishes; once operational it runs **intake cycles** (intake → iteration → engage) forever.

| Phase | What you do (maestro) | CLI command |
|---|---|---|
| **initialized** | Review/edit `.harness/project.md` (auto-drafted by `init` on existing codebases; write it for new ones) | `hssd project approve` |
| **identified** | Run the **architect** subagent → write `docs/ADR.md`; run **architecture-adversary** (advisory); iterate with user | `hssd architecture approve` |
| **architected** | Register a demand brief | `hssd intake add <brief.md>` then `hssd intake approve <id>` |
| **operational** | Plan and activate iterations, engage stories (below) | `hssd iteration plan` · `hssd iteration activate <id>` · `hssd iteration converge <id>` |

## Onboarding an existing (legacy) project
`hssd init` detects source files and automatically drafts `.harness/project.md` by reading the codebase — no brief needed. Then:
1. User reviews and edits `.harness/project.md` → `hssd project approve`
2. Run the **architect** subagent with `--from-codebase` mode (it reads the codebase snapshot, not a brief) → write `docs/ADR.md` → **architecture-adversary** (advisory)
3. `hssd architecture approve` → project is `architected` and ready for intake

The ADR for a legacy project documents **what IS** (the actual stack, real data model, observed decisions) — not what should be built.

## The architecture gate
1. Invoke the **architect** subagent. For new projects: pass the brief. For legacy: pass the codebase snapshot + `.harness/project.md`. Have it output a 1-page ADR (data model + per-column ownership, stack tier with justification, concurrency/isolation per guarantee, key decisions, assumptions). Write it to `docs/ADR.md`.
2. Invoke the **architecture-adversary** subagent on that ADR — it returns `{findings:[{issue, options[], recommended}]}`. **Advisory**: present findings to the user; it never blocks. Apply engineering-skill checklists (dual-writer races, `INSERT OR REPLACE`, missing indexes, naive datetimes, unbounded retries, polling-where-push-fits).
3. User iterates on `docs/ADR.md`. When satisfied: `hssd architecture approve` — versions and locks it (`docs/adr/ADR-vN.md`).

## Intake cycle (demand → backlog)
```
hssd intake add <brief.md>       # register a demand
hssd intake approve <id>         # release its stories to the backlog
```
Run the **product-analyst** subagent on the brief to decompose it into work items, then `hssd intake approve` to release them. The locked ADR is the shared contract — stories inherit it; don't re-litigate the architecture.

## Iteration cycle (backlog → delivery)
```
hssd iteration plan --goal "…" [--intake <id>]   # pull scope into an iteration
hssd iteration activate <id>                      # start the engineering loop
hssd iteration converge <id>                      # close when all stories are done
```
One or more iterations can run in parallel (`hssd iteration activate id1 id2 …`). Each iteration contains stories that go through the 6-phase engagement loop below.

## Engaging a story — you run the 6 phases (do NOT call `hssd engage`)
Claim it first: `hssd work claim <id>`. Then run the phases, writing each role's output to `.harness/engagements/<id>/<role>.out` for the audit trail. Pass each downstream role the upstream artifact in its prompt.

- **P0 Intake** — **product-analyst** subagent → **definition-skeptic** subagent (gate). On BLOCK: surface findings + recommended to user, record resolution in `.harness/engagements/<id>/assumptions.md`, re-run. Cap ~3 rounds then carry to Spec Lock.
- **P1 Stories & AC** — **story-writer** subagent → **ac-adversary** subagent (gate). The AC are the contract; they become the tests.
- **P2 Architecture (story-level)** — **architect** subagent (design only, no code) → **architecture-adversary** subagent (gate). Inherits the locked ADR — don't re-litigate the data model.
- **◆ SPEC LOCK (human gate)** — summarize locked spec + accumulated assumptions, **ask the user to approve**. No code before this.
- **P3a Red** — **test-author** subagent writes tests from the locked AC (one per criterion; stress tests for concurrency/atomicity guarantees), applying engineering skills. **Run them yourself** (`uv run pytest`) — they MUST fail. Save to `.harness/engagements/<id>/tests-red.log`. If they pass with no implementation, they're vacuous — back to test-author.
- **P3b Green** — **backend-dev** / **frontend-dev** subagents implement until tests pass. Run tests, save `tests-green.log`. Loop P3b until green.
- **P4 Verify (loop-until-dry)** — **security-adversary** (API/auth), **independent-verifier** (every AC ↔ test), **completion-challenger** (proves NOT done), **test-adversary** (real races, tests that pass for the wrong reason), **regression-hunter** (what breaks?). Any BLOCK → back to P3b, fix, re-attack. Done = green AND all adversaries dry.
- **◆ MERGE (human gate)** — show evidence (green tests, adversary verdicts), **ask user to approve**, then `hssd work done <id>`.

**Maker ≠ checker:** test-author, builders, and P4 adversaries each run in isolated subagent contexts — the builder never certifies its own work.

## Gates & loop discipline
- **Adversary gates** loop-forward: a BLOCK returns options + recommended fix. Take the recommended (or ask the user), record as assumption, re-run. Bound it (~3 rounds) then escalate to the human at Spec Lock. Never loop forever.
- **Human gates** (Architecture Lock, Spec Lock, Merge) are conversational — you ask, the user decides. Never skip them.
- **Evidence over assertion** — "done" = test output / diff / verdict captured in `.harness/engagements/<id>/`. Never a claim.

## State / mechanical commands (instant, no AI — call these directly)
`hssd status` · `hssd project approve|show|check` · `hssd architecture approve|status|reopen` · `hssd intake add|list|show|approve` · `hssd iteration plan|activate|list|converge` · `hssd work list|show|claim|done` · `hssd ailog` · `hssd stats` · `hssd log` · `hssd sync`

## When to fall back to the CLI runner
Unattended/CI/overnight: `hssd engage <id> --accept-recommended [--budget N]`. Same agents, same gates, same state — just no human in the loop.

## Examples
- "vamos desenhar a arquitetura" → architect subagent → write `docs/ADR.md` → architecture-adversary (advisory) → user iterates → `hssd architecture approve`
- "como tá o projeto?" → `hssd status`
- "tenho um novo requisito" → `hssd intake add brief.md` → `hssd intake approve <id>` → `hssd iteration plan`
- "ativa a iteração" → `hssd iteration activate <id>`
- "engaja a story do banco" → `hssd work claim <id>` → P0–P4 como subagents com gates → Spec Lock (ask) → red→green → Merge (ask) → `hssd work done <id>`
- "é um projeto legado, quero começar" → `hssd init` (auto-drafta `project.md` do codebase) → user revisa → `hssd project approve` → architect subagent (reverse-engineers ADR) → `hssd architecture approve`
