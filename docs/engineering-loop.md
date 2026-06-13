# Harness Studio — The Engineering Loop

## What is the Engineering Loop

The engineering loop is the innermost delivery cycle in Harness Studio. It runs once per story, inside an active iteration. It takes a single story from the backlog — with locked acceptance criteria and a locked spec — and produces verified, merged code.

The loop has six phases and two human gates. It never skips a phase. It never self-certifies. The person or agent who builds something is never the one who verifies it.

```
P0  ──  Intake
P1  ──  Stories & Acceptance Criteria
P2  ──  Architecture
        ◆ SPEC LOCK  (human gate — no code before this)
P3a ──  Red   (failing tests)
P3b ──  Green (passing implementation)
P4  ──  Verify (adversarial, loop-until-dry)
        ◆ MERGE  (human gate — evidence reviewed)
```

---

## The Core Principle: Maker ≠ Checker

The most important rule in the engineering loop is structural, not procedural:

**The agent that builds never certifies its own work.**

This is not a guideline — it is enforced at the process level. Each phase runs in an independent agent context. The test-author that writes the tests does not see the implementation. The adversaries that run P4 do not share context with the backend-dev that wrote the code. The independent-verifier checks every acceptance criterion against every test without knowing which tests the builder thought were sufficient.

The reason this matters: an agent asked to both build and verify will unconsciously fit the verification to the implementation. It will write tests that cover what it built rather than what was specified. It will find the adversary role unconvincing because it already "knows" the code is correct. Self-certification is not verification — it is rationalization.

Maker ≠ checker is the structural guarantee that "done" means something.

---

## Evidence Over Assertion

"Done" in Harness Studio is never a claim. It is always evidence:

| What "done" means | Evidence required |
|---|---|
| Tests were written before implementation | Red log committed to the branch |
| Tests pass | Green log — actual `pytest` output |
| Every AC is covered | Independent-verifier verdict |
| Nothing was missed | Completion-challenger verdict |
| Tests are real, not vacuous | Test-adversary verdict |
| Nothing broke | Regression-hunter verdict |
| Code is safe | Security-adversary verdict (API/auth surfaces) |

Evidence is written to `.harness/engagements/<story-id>/` during the loop. It is not reconstructed at the end — it is captured continuously as each phase produces it.

---

## Phase 0 — Intake

**Role:** product-analyst + definition-skeptic  
**Input:** the story, the locked AC from intake, the project ADR  
**Output:** `assumptions.md`

The product analyst reads the story in its full context: what does the project need this story to accomplish? What does it depend on? What is already built that this story must integrate with?

The definition skeptic challenges the story scope. Before a single line of spec is written, it surfaces:
- Assumptions that are being made implicitly
- Edge cases not mentioned in the AC
- Concurrency concerns (what happens when two users do this simultaneously?)
- Security implications (what data is touched? who can call this?)
- Dependencies on other stories that are not yet merged

Every finding is resolved and recorded in `assumptions.md`. This document travels with the story through every subsequent phase — it is the running record of what was decided and why.

**Gate:** all assumptions are explicit and recorded. No hidden decisions.

---

## Phase 1 — Stories & Acceptance Criteria

**Role:** story-writer + ac-adversary  
**Input:** the story, `assumptions.md`, the project ADR  
**Output:** locked acceptance criteria (Gherkin)

The story-writer produces the final acceptance criteria. These are the contract — everything in P3 and P4 refers back to them. A test that is not traceable to an AC is not a required test. An AC that has no corresponding test is a gap.

Acceptance criteria are written in Gherkin format:
```
Given [initial context]
When  [action taken]
Then  [expected outcome]
```

The AC must be:
- **Testable** — a machine can verify them without human judgment
- **Complete** — they cover the happy path, the error paths, and the edge cases
- **Bounded** — they define what is in scope and what is out

The ac-adversary attacks the AC for:
- Missing edge cases ("what if the input is empty? what if it's malformed?")
- Testability failures ("the response looks correct" is not testable)
- Concurrency gaps ("two users submit simultaneously — which AC covers that?")
- Scope creep (ACs that describe behavior beyond what the story is supposed to deliver)

A BLOCK from the ac-adversary returns to the story-writer. The loop repeats until all ACs pass adversarial review.

**Gate:** acceptance criteria are complete, testable, and adversarially validated.

---

## Phase 2 — Architecture (Story Level)

**Role:** architect + architecture-adversary  
**Input:** locked ACs, `assumptions.md`, project ADR, relevant skills  
**Output:** story-level design document

The architect does not write code. It writes a design: which modules are touched, what the data flow looks like, what function signatures are needed, what external calls are made, and how the implementation fits into the existing codebase.

The design inherits the project ADR. It does not re-litigate stack decisions, data ownership, or concurrency strategy — those are locked. The story-level design works within those constraints.

The architecture-adversary reviews the design against:
- The locked ADR (does this violate any architectural decision?)
- The engineering skills (concurrency? indexing? datetime handling? API conventions?)
- The acceptance criteria (does this design actually produce the behavior the ACs require?)
- Failure modes (what happens when an external call fails? when the database is unavailable? when two concurrent requests hit the same record?)

A BLOCK returns to the architect. The design is revised until it passes.

**Skills are applied here.** Before the architecture-adversary runs, the relevant skill checklists are folded into its prompt. If the story touches a database, the `sqlite-concurrency` and `sql-indexing` skills apply. If it touches an API, `api-conventions` applies. The adversary checks the design against every relevant checklist.

**Gate:** design is complete, consistent with the ADR, and adversarially validated.

---

## Spec Lock (Human Gate)

**This is the most important moment in the loop.**

The developer reads three documents:
1. `assumptions.md` — what was decided before the spec was written
2. The locked acceptance criteria — what the implementation must produce
3. The story-level design — how it will be built

This is the last moment to catch something wrong before tests are written and code is implemented. Changing the spec after this point means discarding work — the tests would need to be rewritten, the implementation adjusted, and the adversaries re-run.

**No code is written before Spec Lock.** This is non-negotiable. The purpose of Spec Lock is to ensure that what gets built is what was agreed upon — not what the builder happened to interpret from an ambiguous brief.

Approval is conversational — the developer reads and says yes. The framework records the approval and opens P3.

---

## Phase 3a — Red

**Role:** test-author  
**Input:** locked acceptance criteria, story-level design  
**Output:** failing tests committed to the branch

The test-author writes one test per acceptance criterion. The tests must:
- Reference the AC they cover (by number or description in the test name)
- Fail before any implementation exists
- Test the specified behavior, not the expected implementation

**Tests must fail.** If a test passes before implementation, it is vacuous — it is not testing anything real. The test suite is run (`uv run pytest` or equivalent) and the output is captured in `tests-red.log`. This log is committed to the engagement evidence trail.

If any test passes with no implementation, the entire test suite is sent back to the test-author. Tests that pass vacuously are not tests — they are false confidence.

The test-author does not look at existing code when writing tests. It reads the spec. The tests describe the contract; they do not describe the implementation.

**Gate:** all tests fail. Red log committed and saved.

---

## Phase 3b — Green

**Role:** backend-dev or frontend-dev  
**Input:** failing tests, story-level design, `assumptions.md`  
**Output:** passing implementation

The builder implements until all tests pass. This is an inner loop:

```
implement → run tests → some fail → fix → run tests → repeat
```

The builder follows the story-level design from P2. Deviations from the design that are necessary (the design was wrong about something) are recorded in `assumptions.md` — they do not disappear silently.

The builder does not modify tests to make them pass. The tests are the contract; the implementation is what changes.

When all tests pass, the output is captured in `tests-green.log` and saved to the evidence trail. The green log is the primary evidence that the implementation delivers what was specified.

**Gate:** all tests pass. Green log committed and saved.

---

## Phase 4 — Verify (Loop Until Dry)

**Roles:** independent-verifier, completion-challenger, test-adversary, regression-hunter, security-adversary (when applicable)  
**Input:** the diff, the tests, the green log, the locked AC  
**Output:** verdicts (PASS or BLOCK with findings)

P4 is the adversarial verification phase. Five independent roles attack the implementation from five different angles. None of them share context with the builders. None of them are trying to confirm the work is done — they are trying to prove it is not.

### independent-verifier
Checks every acceptance criterion against every test. For each AC: is there a test that covers it? Does the test actually verify the behavior the AC specifies, or does it test a proxy? Does the test pass for the right reason?

A gap between AC and test coverage is a BLOCK. A test that covers the wrong thing is a BLOCK.

### completion-challenger
Tries to prove the implementation is incomplete. Looks for:
- Happy-path-only tests with no error path coverage
- Acceptance criteria that were addressed in tests but not in implementation
- Features described in the spec that do not appear in the diff
- TODOs or placeholder implementations committed as real code
- Scope that was silently cut without disclosure

### test-adversary
Tries to break the tests themselves. Looks for:
- Assertions that are always true (vacuous tests that never fail)
- Tests that pass for the wrong reason (implementation detail rather than behavior)
- Missing concurrency tests for any concurrent behavior in the AC
- Race conditions that the test suite cannot detect because it runs sequentially
- Tests that would pass even if the implementation were completely wrong

### regression-hunter
Checks what the change broke. Runs the full test suite (not just the new tests), checks all callers of modified functions, and looks for behavior changes in modules that were touched but not in the story's scope. A regression is a BLOCK regardless of whether it was mentioned in the AC.

### security-adversary
Mandatory for any story that touches an API endpoint, authentication, authorization, user input, or data storage. Attacks for:
- Injection vulnerabilities (SQL, command, prompt)
- Authorization bypasses (can a user access another user's data?)
- Secret leakage (credentials, tokens, or PII in logs or responses)
- Unvalidated input at system boundaries

**The loop:**

```
P4 runs → any BLOCK → back to P3b → builder fixes → P4 re-runs
P4 runs → no BLOCKs → done
```

The loop is bounded: after three rounds of P4 with unresolved BLOCKs, the issue is escalated to the human. A loop that runs forever is a sign that the spec was wrong, not that the adversaries are too strict.

All verdicts — PASS and BLOCK — are written to `p4-verdicts.md` in the engagement trail. This is the permanent record of what was challenged and how it was resolved.

**Gate:** all adversaries return PASS. No open BLOCKs.

---

## Merge (Human Gate)

The developer reviews the final evidence package:
- `tests-red.log` — tests failed before implementation (they were real)
- `tests-green.log` — tests pass after implementation (it works)
- `p4-verdicts.md` — all adversaries cleared (it is correct)
- The diff — what actually changed

This is the developer's signature. They are accountable for what merges. They have read the evidence, not just the claim.

Approval triggers `hssd work done <id>`. The story is closed, the worktree is merged and removed, and the story moves from `in progress` to `done` in the backlog.

---

## The Loop as a Guarantee

Each phase produces a guarantee:

| Phase | Guarantee produced |
|---|---|
| P0 | No hidden assumptions — everything decided is recorded |
| P1 | The contract is complete, testable, and adversarially validated |
| P2 | The design is sound and consistent with the architecture |
| Spec Lock | The human agreed to this contract before any work began |
| P3a | The tests are real — they failed before implementation |
| P3b | The implementation delivers what the spec required |
| P4 | Nothing was missed, nothing broke, nothing is unsafe |
| Merge | A human reviewed the evidence and accepted accountability |

Together these guarantees mean: when a story merges, everyone — the developer, the team, and the project — can trust that it does what it says, nothing more and nothing less, and that trust is backed by evidence, not by the builder's confidence in their own work.
