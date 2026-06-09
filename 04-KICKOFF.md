# Harness Studio — Engagement Kickoff

> Paste the **kickoff prompt** below into a NEW (clean-context) conversation, together with the kit documents (`00`–`03`) and this one. Then follow the phases. This document also carries the **budget plan**. Paste **your own** brief into the kickoff; for an illustrative end-to-end example, see [`examples/`](examples/).

---

## 1. Kickoff prompt (copy & paste)

```
You are the AI assistant of Harness Studio, a software studio that delivers client
work through a governed, adversarial process. I am the Engagement Lead.

Read and follow these kit documents (attached / in the harness-studio folder):
- 00-OPERATING-MANUAL.md   (principles and how we operate)
- 01-ROLES.md              (the team's roles)
- 02-PROCESS-GATES-DOD.md  (the 6 phases, gates, and deriving the Definition of Done)
- 03-DELIVERABLE-PROTOCOLS.md (AI log, ADR, README)

Non-negotiable rules:
1. Whoever builds never judges their own "done" — use the adversarial roles.
2. Evidence over assertion. Concurrency/atomicity only count with a stress test.
3. Capture the AI Interaction Log LIVE (format in doc 03), including my corrections.
4. Stack decisions belong to the Architect (proposes) challenged by the Architecture
   Adversary — do NOT choose a stack without that tension. Record proposal + challenge + choice in the ADR.
5. Stop at the human gates and wait for my approval (architecture plan; ready-to-deliver).
6. Right-size to the budget: max rigor on concurrency and on the graded deliverables.

We'll run the engagement (brief below) phase by phase. Start with PHASE 0 (Intake):
run the Product Analyst and then the Definition Skeptic, and present me the problem
statement and the list of ambiguities/assumptions. Do not advance to Phase 1 without my OK.

[paste the engagement brief here]
```

---

## 2. Budget plan (example: 5-6h) — a guide, not a solution

Protect the time of the two things that win the evaluation: **the concurrency proof (P4)** and **the graded deliverables (P5)**. Don't let the build eat everything.

| Block | Phases | Target time | Focus |
|---|---|---|---|
| Frame | P0 + P1 | 30–45 min | Problem statement, assumptions (→ADR), testable AC (the "done") |
| Decide | P2 | 45–60 min | Architect proposes ↔ Adversary challenges; ADR decisions; **your OK** |
| Build | P3 | 2h–3h | Backend + frontend slices; tests per AC |
| Break | P4 | 45–60 min | Test Adversary on the concurrency points; Verifier; Completion Challenger |
| Package | P5 | 30–45 min | README, ADR (1 pg), final AI log, public repo; **your final OK** |
| Buffer | — | ~30 min | Surprises |

Budget rules:
- If the build overruns, **cut scope consciously** (and record it in the ADR's "left out"), don't cut P4 or P5.
- "A partial but well-documented submission beats a complete but undocumented one" (the client said so). So: better one fewer endpoint with proven concurrency and a strong ADR than everything half-baked.
- Token/time is a gate: if a role is spinning without progress, the Lead intervenes (human decision).

---

## 3. The engagement brief

Paste **your** brief where the kickoff prompt says `[paste the engagement brief here]`. Phase 0 (intake + Definition Skeptic) turns it into a problem statement + assumptions; Phase 1 turns every "must" into a testable AC (the Definition of Done) — no solutions, just the contract.

> For an illustrative, end-to-end **example** engagement (a generic link-shortener with click analytics + a worked requirements→DoD extraction), see [`examples/example-engagement.md`](examples/example-engagement.md). It's only an illustration — the framework is domain-agnostic; concrete cases are outputs, not part of it.

---

## 4. Pre-flight (before pasting the kickoff)
- [ ] The 4 kit docs (`00`–`03`) are accessible in the new conversation (in the folder or attached).
- [ ] You have somewhere to create the repo and run code (environment ready).
- [ ] A timer / awareness of the budget.
- [ ] Willingness to be the Engagement Lead: approve the plan, stop at gates, record corrections in the AI log.
