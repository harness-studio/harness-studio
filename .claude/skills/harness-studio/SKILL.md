---
name: harness-studio
description: Drive an hssd-governed repo as the interactive MAESTRO — run the governed engagement loop (architecture → sprints → the 6 phases → adversarial verification) conversationally, using Claude Code's native subagents for the AI work and the `hssd` CLI for state. Use whenever the user wants to design the architecture, plan/run sprints, engage a story, verify work, or check status in a repo that has an `hssd.yaml` + `.harness/`.
---

# Operating a Harness Studio repo — you are the MAESTRO

This repo is governed by Harness Studio (it has `hssd.yaml` + `.harness/`). There are **two runners over one shared substrate** — pick the maestro path here:

- **CLI runner** (`hssd engage`, `hssd overview architect|analyze`) — headless/unattended/CI. It spawns its own `claude -p` agents. Don't use these interactively: they nest a second Claude inside you (slow, token-heavy, not streamed).
- **Maestro runner (you, right now)** — interactive and fluid. **You** run each role as a **native subagent** (the Task tool, using the role definitions in `.claude/agents/`), and you call the **`hssd` CLI only for state** (status, claim, lock, sprint, done, metrics). One session, streamed, no nesting.

**The golden rule:** state + gates live in the CLI / `.harness/` (the single source of truth). You never reimplement them — you call `hssd` for every state change, and you run the AI yourself. So both runners stay consistent.

**Never run, in maestro mode:** `hssd engage`, `hssd overview architect`, `hssd overview analyze` (those are the headless runner and will nest a `claude -p`). You do that work as subagents instead.

## The shared substrate you operate on
- `.harness/pm.sqlite` — work items + sprints (via the CLI). `.harness/overview.md` — the brief. `.harness/engagements/<id>/` — per-story evidence (you write here). `.harness/locks/architecture.json` — the architecture lock.
- `.claude/agents/*.md` — the roles you invoke as subagents (product-analyst, definition-skeptic, story-writer, ac-adversary, architect, architecture-adversary, test-author, backend-dev, frontend-dev, security-adversary, independent-verifier, completion-challenger, test-adversary, regression-hunter).
- `skills/` — the blessed engineering guards (sqlite-concurrency, sql-indexing, datetime-utc, api-conventions, resilience, push-over-pull) + the tech skills (python, fastapi, typescript). Load the relevant ones and **fold their checklists into the subagent's prompt** so the role applies them.

## The project state machine (run `hssd status` to see where you are)
`initialized → briefed → architected → planned → operational(∞)`. The project never finishes; once operational it runs **sprints** forever. `hssd status` tells you the phase and the next move. Drive in this order:

| Phase | What you do (maestro) | State command you call |
|---|---|---|
| **briefed** | Save the brief | `hssd overview add <file>` |
| **architected** | Run the **architect** subagent → write `docs/ADR.md` (data model + ownership, tier, concurrency); run the **architecture-adversary** subagent (advisory — it finds + proposes, you and the human decide); iterate with the user | then `hssd architecture approve` (locks an immutable versioned ADR) |
| **planned** | Run the **product-analyst** subagent → write the decomposition JSON to `.harness/plan.json` (shape: `{analysis, concerns:[{title,type,kind}], technologies}`); review with the user | then `hssd overview split` (creates the backlog) |
| **operational** | Open/iterate sprints + engage stories (below) | `hssd sprint plan --goal "…"` · `hssd sprint review` · `hssd sprint close` |

## The architecture gate — where the human's strongest work happens
1. Invoke the **architect** subagent with the brief. Have it output a 1-page ADR (data model + per-column ownership, stack tier with justification, concurrency/isolation per guarantee, key decisions, assumptions). Write it to `docs/ADR.md`.
2. Invoke the **architecture-adversary** subagent on that ADR — it returns findings (issue + options + recommended). **Advisory**: present them to the user; it never blocks. Apply the engineering-skill checklists here (it should catch dual-writer races, `INSERT OR REPLACE`, missing indexes, naive datetimes, unbounded retries, polling-where-push-fits).
3. The user iterates on `docs/ADR.md` (their call). When they're happy: `hssd architecture approve` — this versions and locks it (`docs/adr/ADR-vN.md`) and unlocks split.

## A sprint, the maestro way
`hssd sprint plan --goal "…"` pulls the open backlog into a sprint. Then engage each story. When all are done: `hssd sprint review` (run the **fix-the-harness retro** with the user — every escaped defect becomes a new guard), then `hssd sprint close`. The project stays operational; open the next sprint when there's more work.

## Engaging a story — you run the 6 phases (do NOT call `hssd engage`)
Claim it first: `hssd work claim <id>`. Then run the phases, writing each role's output to `.harness/engagements/<id>/<role>.out` for the audit trail. Pass each downstream role the upstream artifact in its prompt (so it doesn't hunt the filesystem). Honor the gates.

- **P0 Intake** — **product-analyst** subagent → then **definition-skeptic** subagent (gate). On BLOCK it returns findings with a `recommended`; resolve with the user (or take the recommended), record the decision in `.harness/engagements/<id>/assumptions.md`, and re-run. Cap at ~3 rounds — if still open, carry the assumptions to Spec Lock for the human.
- **P1 Stories & Acceptance Criteria** — **story-writer** subagent → **ac-adversary** subagent (gate). The AC are the contract; they become the tests.
- **P2 Architecture (story-level)** — **architect** subagent (design only, no code) → **architecture-adversary** subagent (gate). It inherits the locked ADR — don't re-litigate the data model.
- **◆ SPEC LOCK (human gate)** — summarize the locked spec + accumulated assumptions and **ask the user to approve**. No code before this.
- **P3a Red** — **test-author** subagent writes the tests from the *locked* AC (one per criterion; stress tests for the guarantees), applying the engineering skills. Then **run them yourself** (`uv run pytest`) — they MUST fail (red). Save output to `.harness/engagements/<id>/tests-red.log`. If they pass with no implementation, they're vacuous — send back to the test-author.
- **P3b Green** — **backend-dev** / **frontend-dev** subagents implement until the tests pass. Run them (`uv run pytest`), save `tests-green.log`. Loop P3b until green.
- **P4 Verify (loop-until-dry)** — run the adversary subagents: **security-adversary** (API/auth surfaces), **independent-verifier** (every AC ↔ test), **completion-challenger** (proves NOT done), **test-adversary** (real races, tests that pass for the wrong reason), **regression-hunter** (what breaks?). Any BLOCK → back to P3b, fix, re-attack. Done = green AND all adversaries dry.
- **◆ MERGE (human gate)** — show the evidence (green tests, adversary verdicts), **ask the user to approve the merge**, then `hssd work done <id>`.

**Maker ≠ checker holds** because each subagent runs in its own isolated context: the test-author, the builders, and the P4 adversaries never share a context — the one who builds never certifies its own work.

## Gates & loop discipline
- **Adversary gates** loop-forward: a BLOCK always returns options + a recommended fix. Take the recommended (or ask the user), record it as an assumption, re-run — but bound it (~3 rounds), then escalate to the human at Spec Lock. Never loop forever; watch the token cost.
- **Human gates** (Architecture Lock, Spec Lock, Merge) are conversational — you ask, the user decides. These are the engineer's signature; never skip them.
- **Evidence over assertion** — "done" = test output / a diff / a verdict, captured under `.harness/engagements/<id>/`. Never a claim.

## State / mechanical commands (instant, free — call these directly)
`hssd status` · `hssd overview add <file>` · `hssd overview split` · `hssd architecture approve|status|reopen` · `hssd work list|show <id>|claim <id>|done <id>` · `hssd sprint plan|status|review|close` · `hssd ailog` · `hssd stats` · `hssd log`. These touch the spine/state only — no AI, no nesting.

## When to fall back to the CLI runner
Unattended/CI/overnight, or a batch with no human at the keyboard: use `hssd engage <id> --accept-recommended [--budget N]`. It runs the same agents + gates headlessly via `claude -p`, with the per-run AI-call/budget ceiling. Same agents, same gates, same state — just no human in the loop.

## Examples
- "vamos desenhar a arquitetura" → architect subagent → write docs/ADR.md → architecture-adversary subagent (advisory) → user iterates → `hssd architecture approve`.
- "como tá o projeto?" → `hssd status`.
- "abre um sprint com a primeira fatia" → `hssd sprint plan --goal "vertical slice"`.
- "engaja a story do banco" → `hssd work claim <id>` → run P0–P4 as subagents with the gates → Spec Lock (ask) → red→green → Merge (ask) → `hssd work done <id>`.
