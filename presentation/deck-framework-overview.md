---
title: "Harness Studio: Governed AI Delivery at Any Scale"
subtitle: From individual contributor to parallel AI fleets — without losing rigor
format: slide deck (Marp / Slidev / PowerPoint)
theme: dark, monospace code blocks, accent #58a6ff
audience: developers, engineering leads, technical stakeholders
---

<!-- SLIDE 1 — COVER -->
# Harness Studio
## Governed AI Delivery at Any Scale

*From a single developer with one AI assistant to a fleet of parallel agents — with full governance at every step.*

---

<!-- SLIDE 2 — THE PROBLEM -->
# The problem with AI-assisted development today

AI writes code fast. That's not the problem.

The problem is **what happens after**:

- The developer describes what they want → the agent builds something
- "Done" is whatever the agent claims
- Nobody checks the checker
- There's no paper trail when something breaks in production

**This works for demos. It breaks for real projects.**

Teams solved this with process: intake, architecture review, testable acceptance criteria, independent QA, merge gates. But those processes were designed for humans — they don't compose naturally with AI agents.

---

<!-- SLIDE 3 — THE TWO FAILURE MODES -->
# Two failure modes, one framework solves both

```
FAILURE MODE 1: Too fast, no structure
─────────────────────────────────────
  request → agent builds → "done" → ships
  Missing: scope validation, architecture, tests, verification
  Result: bugs in prod, no audit trail, no confidence

FAILURE MODE 2: Too slow, too manual
─────────────────────────────────────
  request → weeks of planning → committees → reviews → finally builds
  Missing: leverage, speed, the actual benefit of AI
  Result: AI becomes a fancy autocomplete in a slow process
```

**Harness Studio is the third path:**
Structure that multiplies AI speed instead of fighting it.

---

<!-- SLIDE 4 — WHAT HARNESS STUDIO IS -->
# What Harness Studio is

An open-source framework that turns AI agents into a **disciplined delivery team**.

**Three things, working together:**

1. **A state machine** — every project moves through defined phases (identified → architected → operational). No code before the spec is locked. No merge without adversarial verification.

2. **A cycle** — every demand enters through intake, gets groomed and split into stories, runs through the engineering loop, and converges as verified code. Then the next demand enters.

3. **A role system** — 14 specialized agent roles (product analyst, architect, test-author, adversaries, janitor...). The maker never certifies their own work. Every role runs in an independent context.

---

<!-- SLIDE 5 — THE PROJECT STATE MACHINE -->
# The project state machine

```
  not_initialized  →  no framework yet

  initialized      →  framework installed
                      reading codebase, understanding the project

  identified       →  project.md approved by human
                      vision, objectives, non-goals locked

  architected      →  ADR approved by human
                      stack, data model, decisions locked

  operational  ∞   →  intake → iteration → engineering loop
                      runs forever, never "done"
```

Two entry paths: **`hssd init`** (new project) or **`hssd adopt`** (existing codebase).

The architecture decision record (ADR) is immutable once locked. A pivot creates a new version.

---

<!-- SLIDE 6 — THE OPERATIONAL CYCLE -->
# The operational cycle

```
  DEMAND  ──►  INTAKE  ──►  ITERATION PLANNING  ──►  ITERATIONS  ──►  CONVERGE
    ▲                                                                      │
    │                                                                      │
    └──────────────────── next demand ◄───────────────────────────────────┘
                   ▲
              JANITOR (always on)
              discovers drift, debt, bugs
              → files new intakes automatically
```

**Intake** transforms demand into stories: grooming → architecture lite → split.

**Iteration** runs stories through the full P0→P4 engineering loop.

**Convergence** merges verified worktrees back to main.

---

<!-- SLIDE 7 — THE ENGINEERING LOOP -->
# The engineering loop (P0 → P4)

Every story, every time. No shortcuts.

```
  P0  Intake          Understand the story, surface assumptions
  P1  Stories & AC    Write verifiable acceptance criteria (Gherkin)
  P2  Architecture    Design the implementation (not the code)
      ◆ SPEC LOCK     Human approves — no code before this gate
  P3a Red             Tests written, must FAIL before implementation
  P3b Green           Implement until tests pass
  P4  Verify          5 independent adversaries attack the result
      ◆ MERGE         Human reviews evidence, approves merge
```

P4 is **loop-until-dry**: any adversary BLOCK returns to P3b. Done = all adversaries pass.

---

<!-- SLIDE 8 — MAKER ≠ CHECKER -->
# The one rule that makes it real

## Maker ≠ Checker

**The agent that builds never certifies its own work.**

This is structural, not procedural:
- The **test-author** reads the spec. It never sees the implementation it is writing tests for.
- The **adversaries** in P4 run in independent contexts — they do not know what the builder "intended."
- The **independent-verifier** checks every AC against every test from scratch.

An agent asked to both build and verify will unconsciously fit the verification to the implementation. Self-certification is not verification — it is rationalization.

This is the structural guarantee that "done" means something.

---

<!-- SLIDE 9 — PARALLEL DELIVERY -->
# Parallel delivery: from solo to fleet

**Individual contributor mode:**
```bash
hssd iteration activate iter-001
# 1 iteration, 1 worktree, 1 process
```

**Team mode:**
```bash
hssd iteration activate iter-001 iter-002 iter-003
# 3 parallel iterations, 3 worktrees, caller orchestrates
```

**Fleet mode (20 screens, 20 agents):**
```bash
hssd iteration activate iter-001 iter-002 ... iter-020
# 20 parallel iterations
# each running the full P0→P4 governance loop independently
# converge in dependency order
```

The caller — Claude Code, `hssd engage`, or a CI pipeline — manages orchestration.
Parallelism is implicit in how many IDs you pass. No flags, no modes.

---

<!-- SLIDE 10 — THE ROLE SYSTEM -->
# 14 specialized roles, each in isolation

**Intake roles:**
- `product-analyst` — decompose demand into concerns
- `definition-skeptic` — validate: testable? complete? in-scope?

**Architecture roles:**
- `architect` — propose design, justify decisions
- `architecture-adversary` — find failure modes, attack the design

**Delivery roles:**
- `story-writer` — write stories with verifiable AC
- `ac-adversary` — attack the acceptance criteria
- `test-author` — write failing tests from the spec
- `backend-dev` / `frontend-dev` — implement until green

**Verification roles (P4):**
- `independent-verifier` — every AC ↔ every test
- `completion-challenger` — proves NOT done
- `test-adversary` — vacuous tests, races, false confidence
- `regression-hunter` — what broke?
- `security-adversary` — injection, auth, leaks

**Continuous:**
- `janitor` — drift, debt, latent bugs → new intakes

---

<!-- SLIDE 11 — EVIDENCE OVER ASSERTION -->
# Evidence over assertion

"Done" is never a claim. It is always evidence.

| What "done" means | Evidence |
|---|---|
| Tests were real | Red log — they failed before implementation |
| Implementation works | Green log — actual test output |
| Every AC is covered | Independent-verifier verdict |
| Nothing was missed | Completion-challenger verdict |
| Tests are not vacuous | Test-adversary verdict |
| Nothing broke | Regression-hunter verdict |
| Code is safe | Security-adversary verdict |

Evidence is written to `.harness/engagements/<id>/` **during** the loop.
It is not reconstructed at the end — it is captured continuously.

---

<!-- SLIDE 12 — WHAT CHANGES FOR THE DEVELOPER -->
# What changes for the developer

**What you stop doing:**
- Writing first drafts of code
- Writing first drafts of tests
- Manual code review for logic errors (adversaries do this)
- Wondering if you missed something (P4 tells you)

**What you become:**
- The person who defines objectives clearly enough for an agent to act on them
- The person who reads and approves the spec at Spec Lock
- The person who reviews the evidence at Merge
- The person who decides what the next intake is

**What does not change:**
- Accountability. The developer's signature is on every merge.
- Judgment. The human gates exist because some decisions require human judgment, not just correctness.
- Architecture. The ADR is yours. The agents advise; you decide.

---

<!-- SLIDE 13 — GETTING STARTED -->
# Getting started

**New project:**
```bash
pip install harness-studio
hssd init                    # creates .harness/, hssd.yaml
# write project.md → hssd project approve
# architecture review → hssd architecture approve
# first intake → operational
```

**Existing project:**
```bash
hssd adopt                   # reads your codebase, infers project.md
# review and correct the draft → hssd project approve
# validate existing tech → hssd architecture approve
# first intake → operational
```

**Then:**
```bash
hssd intake add brief.md     # any demand, any form
hssd iteration activate id   # start the engineering loop
hssd status                  # see everything in flight
```

---

<!-- SLIDE 14 — SKILL COMPOSITION -->
# Three layers of role quality

A role card alone answers "what should I do?" — not "how should I do it well?" or "what must I catch?"

```
LAYER 1 — Agent card   (.claude/agents/<name>.md)
  Defines WHAT the role IS
  Identity, scope, output type, reward signal

LAYER 2 — Role skill   (.claude/skills/roles/<name>/SKILL.md)
  Defines HOW the role EXECUTES
  Non-negotiables · exact output format · failure modes · loop discipline

LAYER 3 — Engineering skills   (.claude/skills/<name>/SKILL.md)
  Defines WHAT the role must CATCH
  Domain knowledge: concurrency, indexing, UTC, APIs, complexity
```

**The composition rule:** every subagent prompt = role skill + relevant engineering skills + task.

| Role | Engineering skills loaded |
|---|---|
| `architect` / `architecture-adversary` | ALL stack skills + `complexity-guard` |
| `backend-dev` | python · fastapi · sqlite · sql-indexing · datetime-utc · api-conventions · resilience · complexity-guard |
| `test-author` | python/typescript · sqlite-concurrency · api-conventions |
| `security-adversary` | api-conventions · api-design |
| `janitor` | **ALL** engineering skills |
| intake/AC roles | _(none — problem framing, not technical)_ |

---

<!-- SLIDE 15 — PRINCIPLES -->
# Five principles

**Evidence over assertion.**
Done means test output, a diff, or a verdict — never a claim.

**Maker ≠ checker.**
The agent that builds never certifies its own work.

**Governance is standing, not an end task.**
Every intake, every story, every merge — the loop is always on.

**Simple scales.**
`hssd iteration activate id1 id2 id3` starts 3 parallel processes. No flags.

**Documentation is the product.**
A tool without clear docs is a tool no one uses. Rigor means nothing if no one can find it.
