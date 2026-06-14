# Skill Loading — Role Composition Guide

Every subagent invocation in Harness Studio is a composition of three layers.
Understanding what each layer does — and which skills belong at each layer — is
what separates a role that executes well from one that just follows a prompt.

---

## The three layers

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 1 — Agent card  (.claude/agents/<name>.md)       │
│  Defines WHAT the role IS                               │
│  • Identity and scope                                   │
│  • What it is rewarded for (find bugs, not approve)     │
│  • Output type (JSON structure, prose, ADR section)     │
└─────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 2 — Role skill  (.claude/skills/roles/<name>/)   │
│  Defines HOW the role EXECUTES                          │
│  • Non-negotiables (always / never)                     │
│  • Exact output format with field-level constraints     │
│  • Failure modes to explicitly avoid                    │
│  • Loop discipline (PASS/BLOCK criteria, round cap)     │
└─────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 3 — Engineering skills  (.claude/skills/<name>/) │
│  Defines WHAT the role must CATCH                       │
│  • Domain knowledge: concurrency, indexing, UTC, APIs   │
│  • Anti-pattern catalogue with proposed fixes           │
│  • Review checklists the role applies to its output     │
└─────────────────────────────────────────────────────────┘
```

**Why three layers?**

An agent card alone answers "what should I do?" but not "how should I do it well?"
and "what specific mistakes should I avoid?" The role skill closes the first gap;
the engineering skills close the second. Together they produce behavioral guarantees
that a prompt alone cannot.

---

## The composition rule

When invoking any subagent, build its prompt as:

```
[role skill content]
[engineering skill content — one block per loaded skill]
---
Task: <the specific work for this invocation>
Context: <upstream artifacts — AC, ADR section, brief, etc.>
```

Read the relevant skill files and paste their content before the task description.
The role skill governs how the agent executes; the engineering skills govern what
it must enforce. Never delegate this to the agent itself — compose the prompt, then
invoke.

---

## Per-role skill loading map

### Intake roles

**`product-analyst`**
- Role skill: `roles/product-analyst` — separates problem from solution, never invents requirements
- Engineering skills: _(none)_ — this role operates on problem framing, not technical domain

**`definition-skeptic`**
- Role skill: `roles/definition-skeptic` — five criteria, VERDICT/FINDINGS format, 3-round cap
- Engineering skills: _(none)_ — scope and logic validation, not technical review

---

### Architecture roles

**`architect`**
- Role skill: `roles/architect` — simplest design first, every decision justified, read-only, no code
- Engineering skills — load ALL that apply to the story's stack:

| Skill | Why it matters for the architect |
|---|---|
| `complexity-guard` | Catches over-abstraction and speculative design before it's proposed |
| `sqlite-concurrency` | Ensures the data model proposes correct WAL, transaction modes, ownership |
| `sql-indexing` | Catches missing indexes at design time, not after performance complaints |
| `datetime-utc` | Ensures datetime fields are specified as UTC-aware from the start |
| `api-conventions` | Ensures endpoint contracts follow the blessed response shapes |
| `api-design` | Ensures versioning, auth placement, idempotency keys are in the design |
| `resilience` | Catches missing retry logic, timeout design, circuit breaker needs |
| `push-over-pull` | Catches polling-where-push-fits at the design stage |

**`architecture-adversary`**
- Role skill: `roles/architecture-adversary` — structural failures only, advisory verdict
- Engineering skills: same set as architect — to catch what the architect missed

---

### Delivery roles

**`story-writer`**
- Role skill: `roles/story-writer` — Gherkin AC, stress tests for guarantees, no happy-path-only
- Engineering skills: _(none)_ — AC writing is not a technical domain task

**`ac-adversary`**
- Role skill: `roles/ac-adversary` — attack all five dimensions, always propose rewrites
- Engineering skills: _(none)_ — attacks the AC structure, not the technical implementation

**`test-author`**
- Role skill: `roles/test-author` — red step mandatory, one test per AC, never write production code
- Engineering skills:

| Skill | Why it matters for the test-author |
|---|---|
| `python` or `typescript` | Correct runner invocation (`uv run pytest`), test framework conventions |
| `sqlite-concurrency` | Writes correct stress tests for concurrency ACs (N concurrent → assert invariant) |
| `api-conventions` | Knows the expected response shapes so assertions target the right fields |

**`backend-dev`**
- Role skill: `roles/backend-dev` — implement until green, uv only, never declare without evidence
- Engineering skills:

| Skill | Why it matters for the backend-dev |
|---|---|
| `python` | Correct environment usage (`uv run`, `uv add`), Python idioms |
| `fastapi` | FastAPI-specific patterns (dependency injection, lifespan, exception handlers) |
| `sqlite-concurrency` | Implements WAL, `BEGIN IMMEDIATE`, no `INSERT OR REPLACE`, single-writer ownership |
| `sql-indexing` | Adds indexes the design specified; catches missing ones during implementation |
| `datetime-utc` | Stores and returns tz-aware UTC datetimes; rejects naive inputs at validation |
| `api-conventions` | Implements the blessed response shapes, status codes, error bodies |
| `resilience` | Implements retry with backoff, timeout handling, circuit breaker where specified |
| `complexity-guard` | Prevents scope creep and over-abstraction during implementation |

**`frontend-dev`**
- Role skill: `roles/frontend-dev` — all three states (loading/error/empty), own only frontend
- Engineering skills:

| Skill | Why it matters for the frontend-dev |
|---|---|
| `typescript` | TypeScript conventions, type safety, build tooling |
| `complexity-guard` | Prevents component over-abstraction and premature generalization |

---

### P4 verification roles

**`independent-verifier`**
- Role skill: `roles/independent-verifier` — run every covering test, never accept claims
- Engineering skills:

| Skill | Why it matters |
|---|---|
| `python` or `typescript` | Correct test runner invocation and output interpretation |

**`completion-challenger`**
- Role skill: `roles/completion-challenger` — compare brief × AC × what exists
- Engineering skills: _(none)_ — completeness check against the spec, not a technical scan

**`test-adversary`**
- Role skill: `roles/test-adversary` — real concurrent requests, hunt vacuous tests, repro required
- Engineering skills:

| Skill | Why it matters |
|---|---|
| `sqlite-concurrency` | Knows the exact race patterns to attack (dual-writer, lost increment, no `BEGIN IMMEDIATE`) |

**`regression-hunter`**
- Role skill: `roles/regression-hunter` — full suite + all callers + characterization tests
- Engineering skills:

| Skill | Why it matters |
|---|---|
| `python` or `typescript` | Correct full-suite invocation (`uv run pytest`) and output interpretation |

**`security-adversary`**
- Role skill: `roles/security-adversary` — active attack, not polite review
- Engineering skills:

| Skill | Why it matters |
|---|---|
| `api-conventions` | Knows expected auth patterns, status codes — spots deviations that signal vulnerabilities |
| `api-design` | Knows token placement rules, rate-limit expectations, idempotency — catches auth design flaws |

---

### Continuous role

**`janitor`**
- Role skill: `roles/janitor` — discover and file, never fix, stable fingerprints, high-signal only
- Engineering skills: **ALL** — the janitor scans for violations of every blessed convention

| Skill | What the janitor scans for |
|---|---|
| `sqlite-concurrency` | Missing WAL/busy_timeout, `INSERT OR REPLACE`, read-modify-write counters, dual-writer races |
| `sql-indexing` | Missing indexes on foreign keys and filter columns; unindexed sort columns |
| `datetime-utc` | Naive datetime storage, missing tz-aware validation, timezone-blind comparisons |
| `api-conventions` | Wrong status codes, envelope where bare array fits, unspecified sort order |
| `api-design` | API keys in query params, missing rate limits on auth endpoints, unsigned webhooks |
| `resilience` | Missing retry logic, no timeout on external calls, unbounded queues |
| `push-over-pull` | Polling loops where a push/event pattern would serve |
| `complexity-guard` | Functions > 50 lines, files > 300 lines, nesting > 3, speculative abstractions |
| `python` | Wrong environment usage, bare `pytest` calls, missing `uv` wrappers |
| `fastapi` | Anti-patterns specific to FastAPI services |
| `typescript` | Anti-patterns specific to TypeScript/frontend code |

---

## Skill directory reference

```
.claude/
  agents/                          ← Layer 1: role identity (15 cards)
    product-analyst.md
    definition-skeptic.md
    story-writer.md
    ac-adversary.md
    architect.md
    architecture-adversary.md
    test-author.md
    backend-dev.md
    frontend-dev.md
    independent-verifier.md
    completion-challenger.md
    test-adversary.md
    regression-hunter.md
    security-adversary.md
    janitor.md

  skills/                          ← Layer 2 + Layer 3
    roles/                         ← Layer 2: behavioral guardrails
      product-analyst/SKILL.md
      definition-skeptic/SKILL.md
      story-writer/SKILL.md
      ac-adversary/SKILL.md
      architect/SKILL.md
      architecture-adversary/SKILL.md
      test-author/SKILL.md
      backend-dev/SKILL.md
      frontend-dev/SKILL.md
      independent-verifier/SKILL.md
      completion-challenger/SKILL.md
      test-adversary/SKILL.md
      regression-hunter/SKILL.md
      security-adversary/SKILL.md
      janitor/SKILL.md

    sqlite-concurrency/SKILL.md    ← Layer 3: engineering domain
    sql-indexing/SKILL.md
    datetime-utc/SKILL.md
    api-conventions/SKILL.md
    api-design/SKILL.md
    resilience/SKILL.md
    push-over-pull/SKILL.md
    complexity-guard/SKILL.md
    python/SKILL.md
    fastapi/SKILL.md
    typescript/SKILL.md
```
