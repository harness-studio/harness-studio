# Harness Studio — Iteration

## What is an Iteration

An iteration is a bounded unit of delivery. It contains a set of stories selected from the backlog, runs the full P0→P4 engineering loop for each story, and produces verified, merged code.

Iterations are not time-boxed — they end when the stories in them are done, not when a calendar slot expires. They are scope-bounded: the scope is defined at planning time and does not change once the iteration is activated.

A project in `operational` state can have any number of iterations in different stages at once: some planned, some active, some waiting for a human gate, some converging.

---

## Iteration vs. Sprint

These terms are often confused. In Harness Studio they mean different things:

| | Iteration | Sprint |
|---|---|---|
| **Bounded by** | Scope (a set of stories) | Review cycle (a set of iterations) |
| **Ends when** | All stories pass P4 and merge | Human calls sprint review |
| **Parallelism** | Multiple iterations can run simultaneously | Sprint groups iterations for retrospective |
| **Time** | No calendar — done is done | Optional cadence for review rhythm |

A sprint in Harness Studio is a collection of iterations reviewed together. It provides the human with a periodic moment to look at what was delivered, what escaped to production, and what new guards the team should adopt. The sprint review is a retro, not a planning meeting — planning happens at intake and iteration level.

---

## Planning an Iteration

Iteration planning is the act of selecting which stories from the backlog go into which iteration, and deciding when each iteration activates.

```
backlog (open stories)
    │
    ├── iteration 1: [story-A, story-B, story-C]   ← activate now
    ├── iteration 2: [story-D, story-E]             ← activate after iteration 1 merges
    └── iteration 3: [story-F ... story-T]          ← planned, no activation date
```

Planning decisions belong to the human. The framework can suggest groupings — related stories, dependency chains, stories that share a module — but the developer decides what runs when.

Stories within an iteration are not necessarily sequential. The iteration activates as a unit; individual story loops may run in parallel within the iteration depending on their dependencies.

**Commands:**
```
hssd iteration plan --from-intake <id> --stories <id1,id2,id3>
hssd iteration plan --pick                  # interactive selection from backlog
hssd iteration list                         # show all iterations and their status
hssd iteration show <id>                    # detail view — stories, status, active loops
```

---

## Activating an Iteration

Activation starts the engineering loop for every story in the iteration. Each story gets its own isolated worktree — it cannot accidentally affect another story's files.

The activation command is variadic. Parallelism is implicit in how many iteration IDs you pass:

```bash
# One iteration — sequential, focused
hssd iteration activate iter-001

# Two iterations in parallel — caller manages both
hssd iteration activate iter-001 iter-002

# Fleet mode — 20 iterations, 20 worktrees, 20 parallel loops
hssd iteration activate iter-001 iter-002 ... iter-020
```

The CLI starts each iteration process and returns immediately. It does not wait. The caller — Claude Code (maestro mode), the headless CLI (`hssd engage`), or an external CI orchestrator — owns the coordination: watching for gates, handling completions, managing convergence.

**Caller models:**

| Caller | How it orchestrates |
|---|---|
| Claude Code (interactive) | Maestro watches PIDs, handles human gates conversationally, coordinates convergence in real time |
| `hssd engage` (headless) | Runs the full loop unattended via `claude -p`, accepts recommended resolutions at gates, reports results |
| CI pipeline | Calls `hssd iteration activate` in parallel jobs, waits on completion signals, triggers convergence |
| External orchestrator | Any system that can spawn processes and read state from `.harness/pm.sqlite` |

---

## The Engineering Loop (P0 → P4)

Each story in an active iteration runs through six phases. The phases are always sequential for a single story — no story skips a phase or runs phases out of order.

```
P0  INTAKE          Understand the story in context
P1  STORIES & AC    Write verifiable acceptance criteria
P2  ARCHITECTURE    Design the story-level implementation
    ◆ SPEC LOCK     Human approves the spec — no code before this
P3a RED             Write failing tests (maker: test-author)
P3b GREEN           Implement until tests pass (maker: backend/frontend dev)
P4  VERIFY          Independent adversaries attack the implementation
    ◆ MERGE         Human approves the merge — hssd work done <id>
```

### P0 — Intake

The product analyst and definition skeptic run in story context. They read the story, the locked acceptance criteria from intake, and the project ADR. They produce `assumptions.md` — a record of every assumption made and every ambiguity resolved before the spec is written.

### P1 — Stories & Acceptance Criteria

The story writer produces the final acceptance criteria in Gherkin format. The AC adversary attacks them — are they complete? testable? do they cover edge cases and concurrency? A BLOCK returns to the story writer. The output of P1 is the contract that tests will be written against.

### P2 — Architecture (Story Level)

The architect subagent designs the implementation — not the code, the design. Data flow, function signatures, modules touched, external calls made. The architecture adversary checks it against the ADR and the skills (concurrency, indexing, datetime conventions, API conventions). A BLOCK returns to the architect. The output is a story-level design that the test-author and builders will follow.

### Spec Lock (Human Gate)

The developer reads: the assumptions, the acceptance criteria, and the story-level design. This is the moment to catch anything the AI got wrong — before tests are written, before code is written. Approval is explicit. No code is written before Spec Lock.

### P3a — Red

The test-author writes one test per acceptance criterion. Tests must fail before any implementation exists — this confirms the tests are real and not vacuous. The test suite is committed to the branch. If any test passes before implementation, it is sent back to the test-author.

### P3b — Green

The backend-dev or frontend-dev implements until all tests pass. This is an inner loop — implement, run, fix, repeat. The tests define done; the implementation is whatever makes them pass. `uv run pytest` (or the equivalent) is the oracle.

### P4 — Verify (Loop Until Dry)

Four independent adversaries attack the implementation. They do not share context with the builders — maker ≠ checker is enforced at the process level.

| Adversary | What it attacks |
|---|---|
| independent-verifier | Every AC ↔ every test. Is each criterion actually covered? |
| completion-challenger | Proves it is NOT done. Missing cases, happy-path only, dead assertions, scope cut without disclosure. |
| test-adversary | Concurrency races, tests that pass for the wrong reason, vacuous assertions, missing edge cases. |
| regression-hunter | What did this change break? Runs the full suite, checks callers. |
| security-adversary | Injection, auth abuse, secret leakage, unvalidated input. (Mandatory for API/auth surfaces.) |

Any BLOCK returns to P3b. The builder fixes, the adversaries re-attack. The loop is complete when no adversary returns a new BLOCK.

### Merge (Human Gate)

The developer reviews the evidence: green test output, adversary verdicts, the diff. This is the final human signature — the developer is accountable for what merges. Approval triggers `hssd work done <id>`, which closes the story and merges the worktree.

---

## Parallel Iterations and Convergence

When multiple iterations are active simultaneously, each runs its own full P0→P4 loop in isolation. They share the same codebase at the point of activation (the same base commit) but diverge as they implement.

Convergence is the moment when parallel worktrees merge back to the main branch. This is where conflicts surface — not just git conflicts but semantic conflicts: two iterations that touched the same module with incompatible changes.

The convergence process:

```
iteration-A (merged first)  ──► main
iteration-B (merges second) ──► conflict check ──► resolve ──► main
iteration-C (merges third)  ──► conflict check ──► resolve ──► main
```

Best practices for parallel iteration planning:
- **Story isolation:** prefer iterations whose stories touch different modules. Stories that touch the same file create merge friction.
- **Dependency order:** if story-B depends on story-A's output, put them in sequential iterations, not parallel ones.
- **Small iterations converge faster:** 3–5 stories per iteration converge more cleanly than 15–20.

The janitor serves a secondary role during parallel execution: it monitors open worktrees for drift between them. If two active worktrees have made incompatible changes to the same module, the janitor flags it as an intake before convergence rather than after.

---

## Iteration Lifecycle

```
planned      stories assigned, not yet active
active       engineering loops running
blocked      one or more stories waiting for a human gate
converging   all stories merged locally, pushing to main
done         all stories at hssd work done, worktree removed
```

Commands:
```
hssd iteration plan                          plan a new iteration
hssd iteration activate <id> [<id2>...]      activate one or many
hssd iteration status                        show all active iterations
hssd iteration show <id>                     detail — stories, phase, gates
hssd iteration converge <id>                 merge worktree to main
```

---

## Example: 20 Screens in Parallel

A product intake describes a new frontend with 20 screens. After grooming and split, the backlog has 20 stories — one per screen.

Iteration planning groups them by shared state and navigation flow:
- Iteration 1–4: authentication screens (login, register, forgot password, email confirmation)
- Iteration 5–8: onboarding flow (4 steps)
- Iteration 9–16: core product screens (8 independent views)
- Iteration 17–20: settings and account screens

Activating all 20 in parallel:
```bash
hssd iteration activate iter-001 iter-002 ... iter-020
```

Twenty worktrees spin up. Twenty P0→P4 loops run simultaneously. Each screen is built, tested, and adversarially verified independently. The maestro (or the CI pipeline) watches all twenty, handles gates as they arrive, and coordinates convergence in dependency order — authentication first, onboarding after, core product after, settings last.

What would have been a multi-sprint sequential project runs as a single parallel delivery. The governance loop runs twenty times in parallel — not once for the whole batch.
