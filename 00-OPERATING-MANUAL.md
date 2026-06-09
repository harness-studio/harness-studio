# Harness Studio — Operating Manual

> **Read this first.** This is the operating system of Harness Studio: a **governed, adversarial, AI-orchestrated** way to deliver client/engineering work. This kit is **self-contained** — a fresh conversation, with no prior history, can run an engagement from these documents alone.

## What Harness Studio is (in this context)

A team of AI specialists, orchestrated by a human **Engagement Lead** (you, acting as tech lead). The team takes a brief and delivers the product **with evidence, not vibes**. Intelligence comes from the models; reliability comes from the process around them.

## The 5 principles (non-negotiable)

1. **Adversarial: whoever does the work never judges their own "done".** Every decision and deliverable is challenged by an independent role whose job is to *prove it's wrong or incomplete*. Architecture decisions are born from the tension **Architect (proposes) ↔ Architecture Adversary (challenges)** — never from an unchallenged choice.
2. **Evidence over assertion.** "It works" only counts with proof: test output, run log, screenshot. No evidence → the gate treats it as "not done".
3. **Fight overconfidence and early completion.** The two enemies of AI work: declaring victory early, silently cutting scope, solving only the happy path. Adversarial roles exist to puncture this.
4. **Right-size to the budget.** Every engagement has a budget (time/tokens). Don't run the heavy machinery where it isn't needed. Spend rigor on the **highest risk-of-being-wrong points** and on the **graded deliverables**. (See the lane rule in `02`.)
5. **The human (Engagement Lead) decides at the leverage points.** The Lead holds the budget, makes final calls, and owns the AI Interaction Log. The team proposes and proves; the Lead approves.

## The engagement flow (overview)

```
Client brief
   │
[P0] INTAKE          → problem statement + explicit ambiguities (feeds the ADR)
[P1] STORIES & AC    → scope + TESTABLE acceptance criteria (the objective "done")
[P2] ARCHITECTURE    → Architect PROPOSES the stack; Architecture Adversary CHALLENGES → ADR
[P3] BUILD           → specialists (backend/frontend) build their slices
[P4] VERIFICATION    → adversaries try to break it; Independent Verifier demands evidence
[P5] PACKAGE         → repo + README + ADR + AI log; final delivery check
```

Full phase and gate detail in `02-PROCESS-GATES-DOD.md`.

## The team (overview)

Specialists (build) and adversaries (challenge), orchestrated by the Lead. Full cards in `01-ROLES.md`. The roles that make this different from "just prompting": the **Definition Skeptic** (finds what's ambiguous → becomes the ADR's assumptions section), the **Architecture Adversary** (forces a robust stack), the **Concurrency/Test Adversary** (tries to break the system's guarantees), and the **Completion Challenger** (proves it's not done).

## The graded deliverables are first-class

A client may grade the **ADR and AI Interaction Log as much as the code**. Harness Studio treats both as product, not end-of-project paperwork. The adversarial process *generates* these artifacts naturally:
- The **ADR** comes from Phase 2 (decisions + the Skeptic's assumptions + what was left out).
- The **AI Interaction Log** is the record of the orchestration itself, captured **live** (not reconstructed at the end).

Protocols in `03-DELIVERABLE-PROTOCOLS.md`.

## How to run an engagement (operational)

1. Open a clean AI conversation (Claude Code, Cursor, Cowork — your choice).
2. Paste the **kickoff** from `04-KICKOFF.md` and the client brief.
3. The orchestrator (you + AI) walks the phases in `02`, **one at a time**, stopping at the human gate where indicated.
4. For each role, either you "wear the hat" and instruct the AI in that role, or (in Claude Code) spawn a subagent with the card from `01`.
5. **Capture the AI log while you work** (protocol in `03`) — don't leave it for the end.
6. Package and review against the Definition of Done before delivering.

## Kit index

| File | For |
|---|---|
| `00-OPERATING-MANUAL.md` | This. Identity, principles, how to run it. |
| `01-ROLES.md` | The team: cards for each specialist and adversary. |
| `02-PROCESS-GATES-DOD.md` | The 6 phases, gates, and deriving the Definition of Done. |
| `03-DELIVERABLE-PROTOCOLS.md` | Producing the AI log, the ADR, and the README. |
| `04-KICKOFF.md` | Kickoff prompt, time budget, and an example engagement brief. |
| `ARCHITECTURE.md` | How Harness Studio layers on Archon + package vision. |
| `VALUE-RISK-ROI.md` | Why it pays off. |

> Deeper background (optional, not needed to execute) lives in the broader project docs. The kit above is sufficient on its own.
