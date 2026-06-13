# Harness Studio — Intake

## What is an Intake

An intake is the entry point for all work in Harness Studio. Every feature, bug fix, improvement, library adoption, skill import, or debt item — regardless of origin or form — enters the delivery cycle through an intake.

The intake is not a ticket and not a task. It is a **raw demand** that needs to be understood, scoped, and validated before it becomes actionable stories. The intake cycle is what transforms ambiguous intent into a verified backlog.

Intakes are available from the moment the project reaches `operational` state and remain available forever. The project is never "closed to new work" — it receives intakes continuously.

---

## Forms of Intake

Not all work arrives in the same shape. Harness Studio recognizes four intake forms, and the grooming cycle adapts to each:

### 1. Manual
A developer or stakeholder describes what they want in natural language. This is the most common form.

Examples:
- "I want users to be able to reset their password by email."
- "The search results page is too slow — we need to fix it."
- "Add dark mode support."

The grooming cycle does the most work here: clarifying intent, surfacing assumptions, and turning vague descriptions into testable concerns.

### 2. Structured
The intake arrives pre-organized from an external tool — a Jira export, a Linear issue, a design spec, a product requirements document, or another system. The structure is already there; the grooming cycle validates alignment with project objectives and verifies that acceptance criteria are testable rather than inferred.

Examples:
- A Jira ticket with description, acceptance criteria, and technical notes.
- A product spec document with user stories and wireframes.
- An API contract from a partner team.

### 3. Unstructured
The intake exists but requires significant analytical work before it can be split into stories. The intent is unclear, the scope is undefined, or the problem is described in terms of symptoms rather than goals.

Examples:
- "The app feels slow." (no specific screen, no baseline, no target)
- "We need to improve the onboarding experience." (no definition of current vs. desired state)
- A large discovery document with contradictory requirements.

The grooming cycle here may require multiple rounds of product-analyst + definition-skeptic before the intake is ready to split. If the intake cannot be clarified after three rounds, it is escalated to the human with a list of open questions — it does not enter the backlog until those questions are resolved.

### 4. Operational
Work that is not a feature or a bug but is necessary for the project's health and evolution. The intake mechanism is the same; only the nature of the work is different.

Examples:
- Importing a library or upgrading a dependency.
- Adopting a new skill (`hssd skill import`).
- Applying a new coding convention across the codebase.
- Addressing a janitor-discovered debt item or latent bug.
- Refactoring a module for maintainability.

Operational intakes are often smaller and faster to groom, but they go through the same validation cycle. This ensures that "quick maintenance tasks" are still scoped, tracked, and verified — not silently applied and never documented.

---

## The Intake Cycle

Every intake — regardless of form — moves through the same three-stage cycle before producing stories:

```
raw intake
    │
    ▼
[1] GROOMING ──────────────────────────────────────────────
    │  product-analyst   → decompose into concerns
    │  definition-skeptic → validate each concern
    │
    │  Questions answered:
    │  • What exactly is being asked for?
    │  • Is this aligned with project.md objectives?
    │  • Are the requirements testable?
    │  • What assumptions are we making?
    │  • What is explicitly out of scope?
    │
    │  Gate: all concerns are clear, scoped, and in-scope.
    │  If not: return to human with open questions.
    ▼
[2] ARCHITECTURE LITE ─────────────────────────────────────
    │  architect (lite)          → does this need new decisions?
    │  architecture-adversary    → are those decisions sound?
    │
    │  Three outcomes:
    │  • Inherits ADR entirely → no action, proceed to split
    │  • Extends ADR → addendum proposed, human approves
    │  • Conflicts with ADR (pivot) → hssd architecture reopen
    │
    │  Gate: architecture is clear. New decisions are locked
    │  or explicitly deferred.
    ▼
[3] SPLIT ─────────────────────────────────────────────────
    │  story-writer → breaks concerns into stories
    │                 each story has:
    │                 • a single, clear objective
    │                 • verifiable acceptance criteria (Gherkin)
    │                 • known dependencies on other stories
    │                 • size estimate (small / medium / large)
    │
    │  Gate: human reviews the story list and approves.
    ▼
stories in backlog (status: open)
```

---

## Stage 1 — Grooming

Grooming is run by two roles working in sequence:

**Product analyst** receives the raw intake and produces:
- A decomposition into discrete concerns (one concern = one thing the intake is asking for)
- For each concern: a plain-language description, the user need it serves, and the expected outcome
- A list of assumptions made during decomposition
- A list of things that are explicitly out of scope

**Definition skeptic** receives the product analyst's output and attacks it:
- Are the acceptance criteria testable, or do they rely on subjective judgment? ("The page looks good" fails; "The page loads in under 500ms on a 4G connection" passes.)
- Are there missing edge cases? What happens when a user does X and Y at the same time?
- Are there concurrency concerns that weren't surfaced?
- Are there security or privacy implications that weren't mentioned?
- Is anything in this intake actually out of scope for this project?

When the definition skeptic finds a problem, it returns a BLOCK with a description and a recommended resolution. The recommended resolution is taken by default unless the human overrides it. The resolution is recorded in `assumptions.md` for the engagement audit trail.

The grooming cycle repeats until all BLOCKs are resolved. After three rounds without resolution, the intake is escalated to the human — it does not enter the backlog in an unclear state.

---

## Stage 2 — Architecture Lite

Most intakes inherit the locked ADR without any new decisions. The architect lite review is fast in these cases: confirm that nothing in the intake requires a new technology, a new data ownership pattern, a new concurrency strategy, or a new deployment tier.

When the intake does introduce something new, the architect subagent proposes a decision in the same format as the ADR: what is decided, why, and what the simplest alternative considered was. The architecture adversary reviews it. If the human approves, it is appended to the ADR as a versioned addendum.

A pivot — a decision that contradicts the existing ADR — is a significant event. It triggers `hssd architecture reopen`, which versions the current ADR as immutable and starts a new one. Pivots are expected to be rare. If they are happening frequently, the original architecture review was not thorough enough.

---

## Stage 3 — Split

The story writer receives the groomed concerns and produces a set of stories. Each story is independently deliverable — it has a clear objective, verifiable acceptance criteria, and a known relationship to other stories (blocks / blocked by).

Story size is estimated at split time:
- **Small:** one engineer (or one AI agent), one iteration, half a day to a day of work.
- **Medium:** one engineer / agent, one iteration, one to three days.
- **Large:** too big — must be split further before entering an iteration.

Large stories do not enter the backlog. The story writer must break them down until every story is small or medium.

The human reviews the story list before it enters the backlog. This is a fast review — not a re-grooming. The human checks that the split makes sense and that nothing obvious is missing. Approval takes the intake from `approved` to `in backlog`.

---

## Intake Lifecycle

```
draft        intake added, not yet groomed
grooming     product-analyst + definition-skeptic running
blocked      grooming found open questions, waiting for human
reviewed     grooming complete, architecture lite cleared
splitting    story-writer running
approved     human approved the story list
in backlog   stories visible to iteration planning
```

Commands:
```
hssd intake add <brief.md>          add a new intake (enters draft)
hssd intake analyze <id>            run grooming + architecture lite
hssd intake split <id>              run story writer
hssd intake approve <id>            human gate — moves stories to backlog
hssd intake list                    show all intakes and their status
hssd intake show <id>               show intake detail + story list
```

---

## Intake Sources

Intakes can come from anywhere. Harness Studio does not care about the source — it cares about what the intake contains and whether it can be groomed into actionable stories.

| Source | Form | Notes |
|---|---|---|
| Developer request | Manual | Most common — natural language description |
| Stakeholder brief | Manual or Structured | May need translation into technical concerns |
| External tool (Jira, Linear) | Structured | Validate alignment with project.md |
| Design document | Structured or Unstructured | Often has scope not yet reflected in the ADR |
| Janitor finding | Operational | Drift, debt, latent bugs → automatic intake creation |
| Skill import | Operational | `hssd skill import` triggers an operational intake |
| Dependency upgrade | Operational | Version bumps with breaking changes go through intake |
| Another AI system | Structured | Intakes can be generated by upstream AI pipelines and consumed directly |

The last row is intentional: Harness Studio is designed to receive structured intakes from other systems. A product AI that generates feature specs, a monitoring system that detects anomalies, or an upstream orchestrator that decomposes a large goal into sub-goals — all of these can produce intakes that Harness Studio consumes and governs.

---

## What Intake Is Not

- **Not a sprint.** An intake produces stories; a sprint (iteration) executes them. They are different cycles with different cadences.
- **Not a ticket.** A ticket is a unit of work. An intake may produce many tickets (stories). Or one. Or none — if grooming finds that the demand is out of scope.
- **Not a guarantee of work.** An intake that fails grooming does not become stories. Work that is out of scope, untestable, or architecturally incompatible is rejected at the grooming gate, not at review time.
- **Not time-boxed.** Intakes have no deadline. They move at the pace of the work.
