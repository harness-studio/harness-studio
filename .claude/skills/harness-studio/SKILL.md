---
name: harness-studio
description: Drive an hssd-governed repo as the interactive MAESTRO — run the governed engagement loop (intake → iteration → engineering loop → adversarial verification) conversationally, using Claude Code's native subagents for the AI work and the `hssd` CLI for state. Use whenever the user wants to drive any phase of the loop in a repo that has `hssd.yaml` + `.harness/`.
---

# Operating a Harness Studio repo — you are the MAESTRO

This repo is governed by Harness Studio. There are **two runners over one shared substrate** — you are the maestro:

- **CLI runner** (`hssd engage`) — headless/unattended/CI. Don't use interactively: it nests a `claude -p` inside you (slow, not streamed).
- **Maestro runner (you)** — interactive. You run each role as a **native subagent**, call the **`hssd` CLI only for state**, and honor the human gates conversationally.

**The golden rule:** state + gates live in the CLI / `.harness/`. You never reimplement them — call `hssd` for every state change, run the AI yourself.

**Never run in maestro mode:** `hssd engage`, `hssd overview architect`, `hssd overview analyze`.

---

## How to load skills into a subagent prompt

This is the core composition rule. Every subagent invocation must carry:

1. **Role skill** from `.claude/skills/roles/<name>/SKILL.md` — behavioral guardrails: non-negotiables, exact output format, failure modes, loop discipline
2. **Engineering skills** — domain knowledge to fold in as checklists

Read both files and paste their content into the subagent's prompt under a `## Loaded skills` section before the task description. The role skill defines how the agent executes; the engineering skills define what it must catch.

### Skill loading map — which engineering skills to load per role

| Role | Engineering skills to load |
|---|---|
| `product-analyst` | _(none — problem framing, not technical)_ |
| `definition-skeptic` | _(none — scope/logic, not technical)_ |
| `story-writer` | _(none — AC writing)_ |
| `ac-adversary` | _(none)_ |
| `architect` | `complexity-guard` · `makefile` · `sqlite-concurrency` · `sql-indexing` · `datetime-utc` · `api-conventions` · `api-design` · `resilience` · `push-over-pull` — load ALL relevant to the story's stack |
| `architecture-adversary` | same as architect (to catch what the architect missed) |
| `test-author` | `python` or `typescript` · `sqlite-concurrency` if DB · `api-conventions` if HTTP · `makefile` |
| `backend-dev` | `python` · `fastapi` (if FastAPI) · `sqlite-concurrency` · `sql-indexing` · `datetime-utc` · `api-conventions` · `api-design` · `resilience` · `complexity-guard` · `makefile` |
| `frontend-dev` | `typescript` · `complexity-guard` · `makefile` |
| `independent-verifier` | `python` or `typescript` (for running tests correctly) |
| `completion-challenger` | _(none — completeness check)_ |
| `test-adversary` | `sqlite-concurrency` (for concurrency attack patterns) |
| `regression-hunter` | `python` or `typescript` (for running the full suite) |
| `security-adversary` | `api-conventions` · `api-design` (for auth + injection surface context) |
| `janitor` | ALL engineering skills — it scans for violations of all of them |

**When in doubt, load more.** An engineering skill in the prompt costs little; a missed convention costs a defect.

---

## The shared substrate

- `.harness/pm.sqlite` — work items, intakes, iterations (via CLI)
- `.harness/project.md` — project identity (vision, objectives, non-goals)
- `.harness/locks/project.json` — project identity lock
- `.harness/locks/architecture.json` — ADR lock
- `.harness/engagements/<id>/` — per-story evidence (write here during the loop)
- `.claude/agents/*.md` — role definitions (15 roles)
- `.claude/skills/roles/*/SKILL.md` — role behavior guardrails (load alongside agent cards)
- `.claude/skills/*/SKILL.md` — engineering domain knowledge (load per the map above)

---

## Project state machine

`not_initialized → initialized → identified → architected → operational(∞)`

Run `hssd status` to see where you are and what the next move is.

| State | What you do (maestro) | CLI command |
|---|---|---|
| **initialized** | Help the user write or review `.harness/project.md` (vision, objectives, non-goals, principles) | `hssd project approve` → **identified** |
| **identified** | Run **architect** subagent → write `docs/ADR.md`; run **architecture-adversary** (advisory); iterate with user | `hssd architecture approve` → **architected** |
| **architected** | Open the first intake | `hssd intake add <brief.md>` → after approval → **operational** |
| **operational** | Run the intake → iteration → engineering loop forever | see below |

---

## The intake cycle (operational, recurring)

Every demand enters through intake:

1. `hssd intake add <brief.md>` — registers the demand
2. Run **product-analyst** subagent (ANALYZE mode) → produces problem statement
3. Run **definition-skeptic** subagent → gates on all 5 criteria; BLOCK → resolve + re-run (cap 3 rounds)
4. Run **architect** subagent (architecture lite) → checks fit with ADR; new decisions → human approves addendum
5. Run **story-writer** subagent → produces stories with AC
6. Run **ac-adversary** subagent → gates on AC quality; BLOCK → resolve
7. `hssd intake approve <id>` — intake approved, stories enter backlog

---

## Iteration planning and activation

Group stories into iterations, then activate:

```
hssd iteration plan --stories id1,id2,id3   # one iteration
hssd iteration activate iter-A iter-B iter-C # variadic: N parallel engineering loops
```

Each activated iteration runs the full engineering loop (P0→P4) in its own worktree. The maestro orchestrates across iterations; each story inside an iteration follows the loop below.

---

## The engineering loop — per story (do NOT call `hssd engage`)

Claim first: `hssd work claim <id>`. Write each phase's output to `.harness/engagements/<id>/<role>.out`.

**Always compose the subagent prompt with: role skill + relevant engineering skills.**

- **P0 Intake** — **product-analyst** _(role skill + no eng skills)_ → **definition-skeptic** _(role skill)_ (gate). BLOCK → take `recommended`, record in `assumptions.md`, re-run. Cap 3 rounds → Spec Lock.
- **P1 Stories & AC** — **story-writer** _(role skill)_ → **ac-adversary** _(role skill)_ (gate). AC are the contract; they become the tests.
- **P2 Architecture** — **architect** _(role skill + complexity-guard + all stack skills)_ → **architecture-adversary** _(role skill + same stack skills)_ (gate). Inherits locked ADR — never re-litigate the data model.
- **◆ SPEC LOCK (human gate)** — summarize locked spec + accumulated assumptions, ask the user to approve. **No code before this.**
- **P3a Red** — **test-author** _(role skill + python/typescript + sqlite-concurrency if DB)_ writes tests from locked AC. Run `uv run pytest` yourself — they MUST fail. Save to `tests-red.log`. Vacuous test (passes before implementation) → send back.
- **P3b Green** — **backend-dev** _(role skill + full stack skills)_ / **frontend-dev** _(role skill + typescript + complexity-guard)_ implement until green. Run `uv run pytest`, save `tests-green.log`. Loop until green.
- **P4 Verify (loop-until-dry)** — run all five adversaries, each with role skill + relevant engineering skills:
  - **security-adversary** _(api-conventions + api-design)_ — mandatory for any API/auth surface
  - **independent-verifier** — every AC ↔ test
  - **completion-challenger** — proves NOT done
  - **test-adversary** _(sqlite-concurrency)_ — real races, vacuous tests
  - **regression-hunter** — full suite + all callers
  - Any BLOCK → back to P3b, fix, re-attack. Done = green AND all adversaries pass.
- **◆ MERGE (human gate)** — show evidence (green log + all adversary verdicts), ask the user to approve. Then `hssd work done <id>`.

---

## Gates & loop discipline

- **Adversary gates** loop-forward: BLOCK always returns `recommended`. Take it (or ask the user), record the assumption, re-run. Cap ~3 rounds → escalate to human at Spec Lock.
- **Human gates** (Project Approve · Architecture Lock · Spec Lock · Merge) are conversational — you ask, the user decides. Never skip them.
- **Evidence over assertion** — "done" = test output / diff / verdict in `.harness/engagements/<id>/`. Never a claim.
- **Maker ≠ checker** — each subagent runs in its own context. The builder never certifies its own work.

---

## CLI — state and mechanical commands (call directly, no AI)

```
hssd status
hssd project approve|show|check
hssd intake add <file> | list | show <id> | approve <id>
hssd iteration plan --stories <ids> | activate <id...> | list | converge <id>
hssd architecture approve|status|reopen
hssd work list | show <id> | claim <id> | done <id>
hssd ailog | hssd stats | hssd log
```

---

## Quick examples

- "como tá o projeto?" → `hssd status`
- "vamos criar o project.md" → help write `.harness/project.md` → `hssd project approve`
- "vamos desenhar a arquitetura" → architect subagent (role skill + all stack skills) → `docs/ADR.md` → architecture-adversary (advisory) → user iterates → `hssd architecture approve`
- "tem uma nova demanda" → `hssd intake add brief.md` → run intake cycle → `hssd intake approve <id>`
- "ativa 3 iterações em paralelo" → `hssd iteration activate iter-A iter-B iter-C`
- "engaja a story do banco" → `hssd work claim <id>` → P0–P4 with role skills + engineering skills → Spec Lock → red→green → Merge → `hssd work done <id>`
