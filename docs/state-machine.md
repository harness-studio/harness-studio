# Harness Studio — Project State Machine

Every Harness Studio project moves through a linear sequence of phases. Each phase has a clear entry condition, a defined set of things that happen inside it, explicit gates that must pass before moving forward, and a single next state. The project never moves backward through phases — it only advances.

```
not_initialized
      │  hssd init   (new project)
      │  hssd adopt  (existing project)
      ▼
initialized
      │  understand project → write project.md → human approves
      │  hssd project approve
      ▼
identified
      │  architect subagent → draft ADR → iterate with human
      │  hssd architecture approve
      ▼
architected
      │  first intake processed
      ▼
operational ──────────────────────────────────────────────┐
      │  hssd intake add / analyze / split / approve      │
      │  hssd iteration plan / activate                   │
      │  P0 → P4 per story                                │
      │  janitor runs continuously                        │
      └──────────────────────────────────────────────────-┘
```

---

## `not_initialized`

**What it means:** The project has no `.harness/` directory and no `hssd.yaml`. Harness Studio does not exist here yet.

**What can happen:**
- The developer decides to start a new project under Harness Studio governance.
- The developer has an existing codebase and wants to adopt Harness Studio into it.

**What cannot happen:** Nothing. There is no state, no commands, no governance — the project is operating outside the framework entirely.

**Exit commands:**

| Command | When to use |
|---|---|
| `hssd init` | New project — empty or near-empty repo, starting from scratch |
| `hssd adopt` | Existing project — codebase already exists, adding governance to it |

Both commands create `.harness/`, write `hssd.yaml`, initialize `pm.sqlite`, and transition to `initialized`.

**Next state:** `initialized`

---

## `initialized`

**What it means:** The framework infrastructure is present, but the project's identity has not been established. The framework does not yet know what this project is trying to achieve, what its boundaries are, or what technologies it uses.

This is the **understanding phase**. It looks different depending on how the project entered:

- **New project path:** There is no existing codebase to read. The developer (or an AI product analyst) writes the project brief from scratch — vision, objectives, non-goals, target users, known constraints.
- **Existing project path:** The codebase already exists. An exploration agent reads the repository, infers objectives from the code and existing documentation, proposes `project.md`, and a human reviews it. The framework validates existing technologies and notes any concerns (deprecated dependencies, missing tests, architectural inconsistencies).

**What happens inside:**

1. **Exploration** — read the codebase (if it exists) and any existing documentation. Understand what the project already is before proposing what it should be.
2. **Draft `project.md`** — capture vision, objectives, non-goals, and principles. This document is the stable identity anchor for all future intake validation.
3. **Human review** — the developer reads the draft and corrects anything the AI misunderstood or missed. The project identity must be human-approved — it cannot be inferred and locked automatically.

**What can happen:**
- Multiple rounds of drafting `project.md` with the human.
- Running an exploration agent over an existing codebase.
- Discovering that the project has no clear objectives — this surfaces a problem early rather than building in the wrong direction.

**What cannot happen:**
- Architecture decisions (ADR) cannot be locked — there is no project identity to anchor them to yet.
- Intakes cannot be processed — there is no definition of what work is in-scope vs. out-of-scope.
- Iterations cannot be planned or activated.

**Gate:** Human reads and approves `project.md`.

**Exit command:** `hssd project approve`

**Next state:** `identified`

---

## `identified`

**What it means:** The project has a locked identity. `project.md` exists and is human-approved. Every future intake will be validated against these objectives — work that does not serve them is out of scope.

This is the **architecture phase**. Before any code is written, the technical foundation must be decided and locked by a human.

**What happens inside:**

1. **Architect subagent** — proposes the stack (language, framework, data model, concurrency strategy, deployment tier). Produces a draft `docs/ADR.md`. Justifies each decision and names the simplest alternative considered.
2. **Architecture adversary** — attacks the proposed architecture. Finds failure modes, scale concerns, and decisions that are convenient but not robust. Returns findings with a recommended fix for each. Advisory — it proposes, the human decides.
3. **Human iteration** — the developer reads both documents, asks questions, pushes back. The architect and adversary can run multiple times. The ADR evolves until the human is satisfied.
4. **Lock** — `hssd architecture approve` versions and immutably locks the ADR (`docs/adr/ADR-v1.md`). It cannot be edited after this point. A future pivot requires `hssd architecture reopen`, which creates a new version.

**What can happen:**
- Multiple architect + adversary cycles before approval.
- Discovering that the proposed stack conflicts with an existing codebase (existing project path) — this surfaces architectural debt early.
- A human deciding to change the stack before locking — this is expected and correct.

**What cannot happen:**
- Intakes cannot be processed — without a locked ADR, the architecture review inside an intake has no baseline to inherit from.
- Iterations cannot be planned or activated.
- Code cannot be written (no spec, no stories, no tests).

**Gate:** Human reads, iterates, and approves the ADR.

**Exit command:** `hssd architecture approve`

**Next state:** `architected`

---

## `architected`

**What it means:** The project has a locked identity (`project.md`) and a locked architecture (`docs/ADR.md`). It is ready to receive work. The project transitions to `operational` the moment the first intake is approved and stories enter the backlog.

This is a brief holding state — not a phase with significant work of its own. It exists to make the transition explicit: architecture is locked, the team knows the rules, and now the first real work can begin.

**What can happen:**
- The first `hssd intake add` — adding the first piece of work.
- Running the full intake cycle (grooming → architecture lite → split) to produce the first batch of stories.
- Human approving the first intake.

**Exit condition:** First intake approved, stories in backlog.

**Next state:** `operational`

---

## `operational`

**What it means:** The project is live and running indefinitely. There is no "done" state for a project — it evolves through continuous intake cycles, iterations, and engineering loops. The project remains operational until it is explicitly archived or abandoned.

This is the **delivery phase**, and it runs forever as a cycle:

```
intake ──► grooming ──► architecture lite ──► split ──► iteration planning
                                                               │
                   ◄────────────────────────────── story loop ◄┘
                   │
                   ▼
           iterate (repeat)
```

### What happens in `operational`

**Intake (recurring, from any source):**
- A developer describes a new feature, bug fix, or improvement.
- The janitor discovers drift, debt, or a latent bug and files an intake.
- A structured spec arrives from another tool (Jira, Linear, a design doc).
- An operational intake: import a library, update a skill, adopt a new convention.

All intakes go through the same grooming cycle regardless of source or structure.

**Grooming:**
- Product analyst decomposes the intake into concerns.
- Definition skeptic validates each concern — are the requirements testable? complete? unambiguous?
- Each concern is validated against `project.md` objectives. Out-of-scope work is rejected here, before any investment.

**Architecture lite:**
- For each intake: does this work require new architecture decisions, or does it inherit the locked ADR entirely?
- If it inherits: no action needed, the ADR applies as-is.
- If it extends: the architect subagent proposes an addendum. The architecture adversary reviews it. The human approves.
- If it conflicts (a pivot): `hssd architecture reopen` — the ADR is versioned and a new one is drafted. This is a significant event, not routine.

**Split:**
- Story writer breaks the intake into stories with verifiable acceptance criteria.
- Stories enter the backlog with status `open`.

**Iteration planning:**
- The developer (or orchestrator) picks which stories go into which iteration.
- Iterations can be planned ahead without being activated immediately.
- Activation is variadic: `hssd iteration activate <id>` starts one; `hssd iteration activate <id1> <id2> <id3>` starts three in parallel, each in its own worktree. The caller (Claude Code, the headless CLI, a CI pipeline) manages orchestration.

**Engineering loop (per story, per iteration):**

| Phase | Who | Output |
|---|---|---|
| P0 Intake | product-analyst + definition-skeptic | assumptions.md |
| P1 Stories & AC | story-writer + ac-adversary | locked acceptance criteria |
| P2 Architecture | architect + architecture-adversary | story-level design |
| **Spec Lock** | **human gate** | approved spec |
| P3a Red | test-author | failing tests committed |
| P3b Green | backend-dev / frontend-dev | passing implementation |
| P4 Verify | independent-verifier + completion-challenger + test-adversary + regression-hunter | adversary verdicts |
| **Merge** | **human gate** | `hssd work done <id>` |

P4 is loop-until-dry: any BLOCK returns to P3b, fixes, and re-attacks. Done = all adversaries pass with no new BLOCKs.

**Janitor (continuous):**
- Runs on a schedule (or on demand).
- Scans for drift, debt, latent bugs, stale conventions.
- Writes findings as new intakes — they enter the same grooming cycle as any other work.
- Findings are deduplicated: the janitor never files the same issue twice.

**What can always happen in `operational`:**
- `hssd intake add` — new intake from any source at any time.
- `hssd iteration activate` — start one or many iterations.
- `hssd iteration plan` — plan future iterations without starting them.
- `hssd sprint plan / review / close` — group iterations into sprint-like cycles for review and retrospective.
- `hssd janitor` — run the codebase health scan.
- `hssd ailog` — render the AI interaction log.
- `hssd status` — see what's active, what's planned, what's blocked.

**What cannot happen:**
- The ADR cannot be edited in-place. It can only be extended (addendum) or reopened (pivot, creates a new version).
- `project.md` cannot be silently changed. Any change to project objectives requires human acknowledgment — the identity of the project is not a casual edit.
- A story cannot merge without passing P4 dry. There is no `--skip-adversary` flag.

**This state never ends.** The project evolves; it does not finish.
