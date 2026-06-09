# Harness Studio — Process, Gates & Definition of Done

> The 6 phases of an engagement, what each one delivers (handoff), the adversarial gate that closes it, and how to derive an **objective Definition of Done** from the client brief.
> Master rule: **a phase only advances when its gate passes.** The gate is, wherever possible, an independent adversary + an evidence-backed check.

## The 6 phases

### P0 — Intake
- **Does:** Product Analyst → problem statement (problem, users, value, out-of-scope, open questions).
- **Gate:** Definition Skeptic lists the ambiguities and the assumptions we'll be forced to make. **That list is saved — it becomes the "assumptions" section of the ADR.**
- **Output:** problem statement + assumptions list.

### P1 — Stories & Acceptance Criteria
- **Does:** Story Writer → deliverables + testable AC.
- **Gate (the most important):** AC Adversary requires every "guarantee/atomicity/concurrency" requirement to become a **concrete test**. Without this, "done" stays subjective and the AI declares victory early.
- **Output:** the engagement's **Definition of Done** (list of AC = tests). The objective contract.

### P2 — Architecture (the heart of the decision)
- **Does:** Architect **proposes** stack + design, each decision with justification, alternative, trade-off.
- **Gate:** Architecture Adversary **tears down / challenges** — robustness vs convenience, failure modes, whether it really meets the brief's guarantees, what changes at scale.
- **Output:** recorded decisions (proposal + challenge + final choice) = **the ADR material**.
- **Spec Lock (hard gate):** the Engagement Lead approves the spec (problem + AC + ADR). **No code is written before this gate passes** — spec-driven design (see `STANDARDS.md`). Phase 3 cannot start until Spec Lock is granted.

### P3 — Build
- **Does:** specialists (backend, frontend) implement their slices, **owning distinct files** (no collision), each with tests for their AC.
- **Internal gate:** green validation per slice (tests pass, with evidence). "Done" = tests pass, not self-declaration.
- **Output:** code + tests + run evidence.

### P4 — Verification (adversarial)
- **Does:** the quality core. Independent of whoever built it.
  - Test/Concurrency Adversary tries to **break** the guarantees (fires real concurrency).
  - Independent Verifier confirms each AC with executable evidence.
  - Completion Challenger proves something is missing (including ADR and AI log!).
  - Regression Hunter ensures cohesion (nothing broken).
- **Gate:** any blocker → back to P3 (loop until adversaries find nothing more).
- **Output:** green verification report + evidence.

### P5 — Package & Deliver
- **Does:** assemble the public repo, run-it README, final ADR (1 page), final AI Interaction Log.
- **Gate:** delivery checklist (below) + Engagement Lead's final approval.
- **Output:** the deliverable repo link.

## How to derive the Definition of Done (method, in P1)

Don't invent "done": **extract it from the brief**. For each client sentence with an obligation verb ("accepts", "persists", "detects", "guarantees", "atomic", "safe under concurrency", "exposes", "shows"), create an AC in the form:

> `[ID] Given <context>, when <action>, then <verifiable result>` — proven by `<test/evidence>`.

Special attention to **guarantee-under-concurrency** requirements: the matching AC **must be a stress test** (fire real simultaneity and assert nothing is lost / the transaction is atomic / the aggregate is consistent). If the AC has no concurrency test, the AC Adversary rejects it.

### Requirements → AC mapping (fill in during P1 — form, NOT solution)
- "accepts events via POST under concurrent bursts" → test firing N simultaneous writes, assert zero loss.
- "persists (justify the choice)" → decision recorded in the ADR + data actually written (round-trip test).
- "detects anomalies in real-time (your definition, justify)" → definition recorded in the ADR + a test that triggers each defined anomaly type.
- "click counter must guarantee every click is counted, even simultaneous hits on the same code in the same instant" → stress test: K simultaneous hits on the same code → count == K.
- "disable link → atomically marked + audit record; correct isolation" → transactional test: concurrent transition, assert atomicity (both happen or neither) and idempotency.
- "aggregate stats safe under concurrent updates" → test: concurrent updates + read → consistent counts.
- "query recent clicks by link and time range" → filter test.
- "dashboard: live list of links + counts, recent click per link, polling/WS justified" → demonstrable UI AC + decision in the ADR.
- "1-page ADR with the 4 questions" / "AI log with the 4 elements" → deliverables verified by the Completion Challenger.

> The Lead/AI fills in the concrete AC in P1; the **solutions** (which DB, which anomaly definition, which isolation) are decided in P2 by Architect↔Adversary, not here.

## Delivery checklist (P5 gate)
- [ ] All Definition-of-Done AC green, with evidence.
- [ ] Concurrency requirements proven by stress test (not just the happy path).
- [ ] 1-page ADR answers the 4 questions (see `03`).
- [ ] AI Interaction Log complete, captured live, with final reflection (see `03`).
- [ ] README explains how to run it; public repo; runs from scratch.
- [ ] Completion Challenger has no pending objection.
- [ ] No silently cut scope; whatever was left out is **declared** in the ADR.

## Right-sizing to the budget
On a short engagement, concentrate rigor where the risk of being wrong is high and where the grading happens:
- **Deliberate lane (max rigor):** the concurrency/atomicity/isolation points + the graded deliverables (ADR, AI log).
- **Fast lane (light):** simple CRUD, scaffolding, basic UI — minimal gates (green + completeness).
Don't spend the budget running the whole cast on the trivial. Spend it breaking the guarantees and polishing the graded artifacts.
