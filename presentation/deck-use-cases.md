---
title: "Harness Studio in Practice: Real-World Use Cases"
subtitle: How governed AI delivery applies across project types and team sizes
format: slide deck (Marp / Slidev / PowerPoint)
theme: dark, code accent #58a6ff, case accent #f0883e
audience: developers, engineering leads, technical stakeholders
---

<!-- SLIDE 1 — COVER -->
# Harness Studio in Practice
## Real-World Use Cases

*Governed AI delivery — from a single developer building a SaaS to a fleet of agents building a frontend with 20 screens.*

---

<!-- SLIDE 2 — THE SPECTRUM -->
# The spectrum of use

Harness Studio applies at every scale:

```
  SOLO DEVELOPER         SMALL TEAM            AI FLEET
  ───────────────        ───────────────        ─────────────────
  1 developer            2–5 developers         1 developer
  1 AI assistant         shared AI agents       N parallel agents
  sequential             coordinated            fully parallel
  iterations             iterations             iterations

  Use case:              Use case:              Use case:
  SaaS MVP               API platform           Full frontend in
  CLI tool               Microservices          days not weeks
  Internal tool          Mobile app backend
```

Same framework. Same governance. Different activation strategy.

---

<!-- SLIDE 3 — CASE 1: SAAS MVP, SOLO DEVELOPER -->
# Case 1: SaaS MVP — solo developer

**Scenario:** A developer wants to build a B2B SaaS with auth, billing, a dashboard, and an API. Working alone with Claude Code.

**Without Harness Studio:**
- Builds features in whatever order feels right
- Tests written after (if at all)
- "Done" is "it seems to work on my machine"
- Architecture decisions made on the fly, often regretted

**With Harness Studio:**

```
hssd adopt              # reads existing codebase or hssd init
# project.md: B2B SaaS, target: SMBs, north star: revenue in 90 days
# ADR: FastAPI + PostgreSQL + Stripe, no microservices (solo constraint)

# Intake 1: Auth system
hssd intake add auth-brief.md
# grooming: email/password + OAuth, no magic links (out of scope)
# split: 4 stories (register, login, reset password, session management)

hssd iteration activate iter-auth-001    # 1 iteration, 4 stories
# P0→P4 per story, sequential within the iteration
# ◆ Spec Lock: developer reviews and approves the auth contract
# ◆ Merge: developer reviews the evidence for each story
```

**Result:** Auth system with full test coverage, adversarially verified, shipped in hours not days.

---

<!-- SLIDE 4 — CASE 1 CONTINUED: CADENCE -->
# Case 1 continued: the ongoing cadence

After auth, the developer opens new intakes as features become clear:

```
Intake 2: Billing (Stripe integration)
  → 5 stories: subscription plans, checkout, webhook handler,
    invoice history, cancellation flow

Intake 3: Dashboard (read-only analytics)
  → 3 stories: metrics aggregation, chart API, data export

Intake 4: Public API (developer-facing)
  → 6 stories: API key management, rate limiting, endpoints,
    OpenAPI spec generation, SDK example, error format conventions

Janitor (running continuously):
  → finds: no index on subscription.user_id (query slow at 10k rows)
  → files operational intake automatically
  → operational intake: add index + test query performance
```

**The developer's job shifts:** from writing code to defining intakes, approving specs at Spec Lock, and reviewing evidence at Merge.

---

<!-- SLIDE 5 — CASE 2: API PLATFORM, SMALL TEAM -->
# Case 2: API platform — small team

**Scenario:** 3 developers building a multi-tenant API platform with multiple services. Mix of human developers and AI agents.

**The challenge:** Multiple people touching the same codebase. Conflicting interpretations of requirements. Inconsistent code style and error handling.

**With Harness Studio:**

```
# Shared project identity
# project.md: multi-tenant API platform, objectives: consistency + reliability
# ADR: FastAPI microservices, shared auth service, async task queue

# Intake from product team (structured, from Linear)
hssd intake add linear-export.json
# grooming validates: each Linear issue becomes a concern
# architecture lite: 2 new services need to be added to ADR → human approves addendum
# split: 12 stories across 3 services

# Team assignment
hssd iteration plan --stories auth-001,auth-002     # dev A's iteration
hssd iteration plan --stories queue-001,queue-002   # dev B's iteration
hssd iteration plan --stories api-001,api-002,api-003  # AI agent iteration

hssd iteration activate iter-A iter-B iter-C        # all 3 in parallel
```

**Each developer (or agent) works independently.** The governance loop catches inconsistencies — the independent-verifier and regression-hunter catch cross-service breakage before it reaches main.

---

<!-- SLIDE 6 — CASE 2 CONTINUED: CONVERGENCE -->
# Case 2 continued: convergence

After parallel iterations complete:

```
  iter-A (auth service)      merged first
  iter-B (queue service)     conflict check → 1 interface mismatch detected
                             → resolution: queue adopts auth service's token format
                             → re-run P4 (regression-hunter) on the fix
                             → merged
  iter-C (API service)       conflict check → clean → merged
```

**The janitor during parallel execution:**
- Detects that iter-A and iter-C both modified `shared/middleware.py` with incompatible changes
- Files an intake before convergence: "middleware conflict — coordinate before merge"
- The team resolves it at planning time, not at merge time

**Result:** 3 parallel workstreams, consistent architecture, no surprises at convergence.

---

<!-- SLIDE 7 — CASE 3: 20 SCREENS FRONTEND, AI FLEET -->
# Case 3: 20-screen frontend — AI fleet

**Scenario:** A product intake describes a complete frontend with 20 screens. One developer with Claude Code as the orchestrator.

**The intake:**
```
hssd intake add frontend-spec.md
# structured: design system defined, wireframes linked, API contracts known
# grooming: fast — structured intake, few open questions
# split: 20 stories, one per screen
```

**Iteration planning — group by shared state:**
```
  iter-1: auth screens (login, register, forgot password, confirm)
  iter-2: onboarding flow (4 steps)
  iter-3: dashboard (analytics, charts, export)
  iter-4–7: core product screens (8 screens in 2 pairs)
  iter-8: settings + account (4 screens)
```

**Fleet activation:**
```bash
hssd iteration activate iter-1 iter-2 iter-3 iter-4 iter-5 iter-6 iter-7 iter-8
```

8 parallel worktrees. 8 governance loops running simultaneously.

---

<!-- SLIDE 8 — CASE 3 CONTINUED: WHAT RUNS IN PARALLEL -->
# Case 3: what's actually happening in parallel

```
  WORKTREE 1 (auth screens)       WORKTREE 2 (onboarding)
  ─────────────────────────       ────────────────────────
  P0: reviewing auth spec    ←→   P0: reviewing onboarding spec
  P1: writing AC for login   ←→   P1: writing AC for step 1
  ◆ Spec Lock (human)        ←→   ◆ Spec Lock (human)
  P3a: failing tests         ←→   P3a: failing tests
  P3b: implementing screens  ←→   P3b: implementing flow
  P4: 5 adversaries attack   ←→   P4: 5 adversaries attack
  ◆ Merge (human)            ←→   ◆ Merge (human)

  WORKTREE 3 (dashboard)          WORKTREE 4 (core screens A)
  ...                             ...
```

**The developer's role:** monitor the 8 loops, handle Spec Lock and Merge gates as they surface, coordinate convergence order (auth first — everything depends on it).

**What doesn't run in parallel:** convergence. Auth merges first. Each subsequent worktree is rebased on main before merging.

**Time saved:** what would be 8 sequential iterations (each 1–3 days) runs as 1 parallel sprint.

---

<!-- SLIDE 9 — CASE 4: ADOPTING AN EXISTING PROJECT -->
# Case 4: adopting an existing project

**Scenario:** A team has been building a product for 2 years without a formal governance process. They want to adopt Harness Studio without stopping existing development.

```bash
hssd adopt
```

**What happens:**
1. Exploration agent reads the codebase, commit history, existing docs
2. Proposes `project.md` based on what it finds
3. Developer corrects the draft (the code knows what was built, not always why)
4. Architecture agent reads the existing stack, proposes the ADR
5. Architecture adversary flags: 3 tables missing indexes, no retry logic in the queue consumer, naive datetime handling in 4 files
6. Developer approves ADR with those findings as known issues

**First intake after adoption:**
```
Intake: address architecture adversary findings
  → 3 operational stories (indexes, retry logic, datetime)
  → all small, all independent → 1 iteration, parallel stories
```

**From this point on:** every new feature goes through intake. The janitor scans continuously. The existing codebase is not rewritten — it is improved incrementally through the governed cycle.

---

<!-- SLIDE 10 — CASE 5: THE JANITOR AS CONTINUOUS INTAKE SOURCE -->
# Case 5: the janitor as continuous intake source

**The janitor runs on a schedule.** It does not wait to be asked.

```
Janitor scan — sprint 3 findings:

  DRIFT
  → skill sqlite-concurrency: busy_timeout not set in 2 new services added this sprint
  → files intake: "apply WAL mode + busy_timeout to queue-service and report-service"

  DEBT
  → 3 functions > 200 lines, no tests, modified this sprint
  → files intake: "refactor + add coverage for payment_processor.py"

  LATENT BUG
  → INSERT OR REPLACE on user_settings: silently drops created_at on update
  → files intake: "fix user_settings update — preserve created_at"

  STALE CONVENTION
  → 6 files using naive datetime after datetime-utc skill was adopted
  → files intake: "migrate naive datetimes in legacy modules"
```

**All 4 findings become intakes.** They enter grooming. They get prioritized. They ship with the same governance as every feature — not as "quick fixes" that bypass the loop.

**The result:** technical debt is not ignored, not batched into a "debt sprint." It surfaces continuously, gets governed, gets fixed.

---

<!-- SLIDE 11 — CASE 6: AI-GENERATED INTAKES FROM UPSTREAM SYSTEMS -->
# Case 6: structured intakes from other AI systems

Harness Studio is designed to receive intakes from external systems.

**Scenario A — Product AI:**
```
  Product AI analyzes user research → generates feature specs
  → specs exported as structured JSON
  → hssd intake add product-ai-output.json
  → grooming validates alignment with project.md
  → stories enter backlog
```

**Scenario B — Monitoring system:**
```
  APM detects: p99 latency on /api/search spiked after last deploy
  → monitoring system files intake: "investigate + fix search latency regression"
  → grooming: definition-skeptic asks for baseline and target (added as assumptions)
  → stories: 1. reproduce with test, 2. identify root cause, 3. fix + benchmark
```

**Scenario C — Security scanner:**
```
  SAST scan finds: SQL query built with string concatenation in reports module
  → scanner files operational intake automatically
  → grooming: confirms scope (1 module, 3 functions)
  → story: parameterize queries, add regression test
  → security-adversary in P4 re-scans the fix
```

**The intake interface is the integration point.** Any system that can produce a demand — in any form — can feed Harness Studio.

---

<!-- SLIDE 12 — WHAT YOU GET -->
# What you get across all use cases

**Consistency.** Every feature, every fix, every operational change follows the same cycle. No "quick fixes" that bypass governance.

**Traceability.** Every decision — from intake assumptions to ADR decisions to adversary verdicts — is written to `.harness/engagements/<id>/`. The audit trail is automatic.

**Confidence.** When a story merges, it has passed 5 independent adversaries, has full test coverage, and has been reviewed by a human. Not because someone checked a box — because the loop requires it.

**Scale.** The same governance loop that works for 1 story works for 20 in parallel. The framework does not change; only the activation command changes.

**Continuity.** The janitor ensures the codebase doesn't quietly accumulate debt while the team is heads-down on features. Drift surfaces as intakes, not as incidents.

---

<!-- SLIDE 13 — STARTING POINT FOR ANY PROJECT -->
# Starting point for any project

| Project type | Entry point | First intake |
|---|---|---|
| New greenfield | `hssd init` | Define the MVP scope |
| Existing codebase | `hssd adopt` | Address architecture adversary findings |
| Legacy with no tests | `hssd adopt` | Add test coverage to highest-risk modules |
| Monorepo, multiple services | `hssd adopt` | One ADR per service (or shared ADR with service addenda) |
| Open source project | `hssd adopt` | project.md = the project's stated goals + CONTRIBUTING guide |
| AI-native product | `hssd init` | Design the intake pipeline that feeds Harness Studio |

**One rule:** every project starts with `project.md` approved by a human. Work that cannot be grounded in a project identity is work that should not be started.
