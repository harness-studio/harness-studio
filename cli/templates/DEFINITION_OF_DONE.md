# Definition of Done — <engagement title>

> The objective contract for "done". Derived from Phase 1's AC + the graded deliverables. Verified in Phase 5 before delivery. "Done" = all green with evidence, not self-declaration.

## Functional (AC → evidence)
- [ ] All AC green, each with executable evidence (which test covers which AC).
- [ ] Concurrency/atomicity requirements proven by **stress test** (not the happy path).
- [ ] Error paths and edges handled and tested.

## Integrity
- [ ] Full suite green (nothing broken — Regression Hunter).
- [ ] No TODO/FIXME/stub left in scope.
- [ ] Lock-the-bug: for each bug fixed, a test that fails on the old code and passes on the new.

## Graded deliverables
- [ ] 1-page ADR answers the 4 questions (see `templates/ADR.md`).
- [ ] AI Interaction Log complete, captured live, with final reflection.
- [ ] README runs from scratch.

## Adversaries with no pending objection
- [ ] Completion Challenger: nothing missing, no silently cut scope.
- [ ] Independent Verifier: each AC confirmed with evidence.
- [ ] Test/Concurrency Adversary: could not break the guarantees.

## Honesty
- [ ] Whatever was left out is **declared** in the ADR (not hidden).
