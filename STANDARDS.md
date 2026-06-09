# Harness Studio — Engineering Standards

> The non-negotiable craft. These are blessed and enforced by gates — not suggestions. Per `PHILOSOPHY.md`: one way, escape hatches documented or absent, do it well or not at all.

## 1. Universal engineering standards (every project)

- **Spec-driven design (spec before code).** No code is touched until the spec is **locked**: the problem, the acceptance criteria, and the ADR (decisions) are settled and human-approved. This is stronger than TDD — TDD says *test before code*; spec-driven says *spec/ADR before test or code*. The hard gate is **Spec Lock** (end of Phase 2); Phase 3 cannot start before it. Exception: notebooks (exploratory).
- **Atomic programming.** Small, single-purpose units. One function does one thing; one change is one concern.
- **Complexity ceiling (function points).** A unit that crosses a complexity threshold (cyclomatic complexity / length) must be **atomized and refactored** — not left "working but big". Enforced by a complexity linter (ruff for Python, ESLint for TS). Complexity is a defect, even when the tests pass.
- **TDD for applications.** Test-first: a failing test, then the code. **Only exception: notebooks** (exploratory/research — not test-first).
- **Early returns.** Guard clauses over deep nesting. No arrow code.
- **Style consistency (paradigm lock).** Pick a paradigm per module/project — **object-oriented or functional** — and follow it. No mixing styles in the same unit. The chosen paradigm is recorded and enforced; inconsistency is a finding.
- **Atomic, story-telling commits.** Commits are grouped by logical operation and tell the history of *what was done and why*. A reviewer reads the commit log and understands the sequence of operations. No "wip", no dumping unrelated changes in one commit.
- **No unexplained acronyms or jargon (clarity is the writer's job).** No abbreviation ships without an explanation (PHILOSOPHY tenet 10). The rule scales with the text: **short texts** (slides, labels, role cards, READMEs' first mention) **spell the term out inline** — e.g., "Acceptance Criteria (AC)", "SQL injection", "create/read/update/delete (CRUD)". **Long or repetitive documents** keep the short form for readability but **define every term once in [`GLOSSARY.md`](GLOSSARY.md)** and link to it. A reader should never need to already know the vocabulary. An undefined acronym is a finding, the same as an untested guarantee.
- **Split classifies intent: task vs config vs governance.** Decomposing a brief is not just "make work items" — the analyst classifies each concern's `kind`. **`config`** = a capability the harness already provides and only needs *enabling* (the AI Interaction Log / logging / audit — captured automatically); the tool records it satisfied at split (`status=done`, `lane=config`) and **never engages it**. **`standing`** = a governance doc (ADR, README) — produced + rubric-checked. **`task`/`feature`** = engineered through the full loop. The app must understand "build me X" vs "turn on Y" — engineering a capability that's already provided is wasted cost (we learned this the expensive way).
- **Acceptance mode is type-aware (tests for code, rubric for narrative).** "Every requirement becomes a test" is the rule for **code** deliverables — guarantees/atomicity/concurrency MUST become stress tests. But **governance/narrative deliverables** (the AI Interaction Log, the ADR, a README — lane `standing`) are *not* deterministically testable by a script, and demanding that creates an unresolvable gate. They are accepted by a **rubric**: the required elements are enumerated, each with an objective presence check and a stated quality bar, applied by a human or LLM reviewer. The AC Adversary must apply the right bar for the item's kind — never block a narrative artifact for "can't be a deterministic test." **Stronger still: standing governance items skip the adversarial intake (P0-P2) and Spec Lock entirely** — they are *produced and rubric-checked, not engineered*. The AI Interaction Log is captured continuously (always-on metrics) and rendered by `hssd ailog`; running a 6-phase engagement to "design a spec" for it is wasted cost. (Learned in the field: a full engagement on the AI-log item burned ~$4 of adversarial debate before we saw it — the artifact was already being captured automatically the whole time. The fix: don't engineer infrastructure.) The **canonical governance rubric** — stub = blank/`—`/`-`/`<!-- -->`/`<...>`; Interactions ≥3 numbered entries; Corrections ≥1; Reflection 3-5 artifact-grounded bullets; counts scoped to their section — is defined once in the framework and injected into every standing engagement, so adversaries apply it instead of re-deriving it per project. Templates author placeholders as angle-bracket `<...>` so the stub check is deterministic.
- **A blocker proposes; it never just stops (loop-forward).** Any adversary or gate that BLOCKs MUST return, with each finding, **1-3 candidate resolutions and one `recommended`** — the smallest defensible way forward. The process never dead-ends on "this is ambiguous": there is always at least one hypothesis to proceed with. The human picks/edits (recorded as ADR assumptions via `hssd engage --answers`), or — under earned autonomy — the system takes the recommended one and retries (`hssd engage --accept-recommended`). This is loop engineering: hypotheses + adversarial evaluation keep the loop moving, always with an answer (or several).
- **Governance deliverables are standing, not sequenced.** The **AI Interaction Log** and the **ADR** are captured *continuously, from the first interaction* — the AI log via `hssd ailog` over the live session metrics (`.harness/logs/metrics.jsonl`), the ADR assembled across Phases 0 and 2. They are **never** end-of-project tasks. In the backlog they lead (lane `standing`), signalling they are active throughout, not scheduled last. Reconstructing them at the end is exactly the early-completion failure this framework exists to prevent.

## 2. Security first (non-negotiable)

- **Never leak ENV/secrets — ever.** No secrets in code, logs, commits, or output. Enforced by a **pre-commit secret scan** (blocks the commit) and reinforced in review.
- **Mandatory API attack stage.** A core, *non-optional* part of the harness: before delivery, the API is actively attacked. At minimum:
  - **SQL injection**
  - **Prompt injection** (for any LLM-touching surface)
  - **Brute force** (auth/rate-limit surfaces)
  This adds a **Security/Attack Adversary** role to the team (Phase 4) and a gate: the service must survive the attack suite, with evidence. Security isn't a review checkbox — it's an adversary that tries to break in.

## 3. Project types & blessed stacks (pick one → get an organized project)

Like Visual Studio forcing a project type that pre-organizes structure. You choose; the framework imposes the shape. The **Architect picks the tier per engagement (right-sizing), justified in the ADR.**

**Deployment shape:**
- **CLI** — local execution accepted (no container required).
- **Containerized service** — Docker by default; docker-compose for local; Kubernetes for prod. Not optional for services.

**Backend stack — two blessed tiers:**
- **Lightweight:** FastAPI + **SQLite** (uv, pytest, asyncio). Fast to stand up; great for PoCs, vertical slices, take-homes. (SQLite's single-writer serialization even simplifies "every entry counted"; the atomic `UPDATE ... +1` pattern still applies.)
- **Full:** FastAPI + **Postgres** (asyncpg, SQLAlchemy async, Alembic, row locks / `SELECT FOR UPDATE` for isolation). For real concurrency and scale.

**Frontend stack — two blessed tiers:**
- **Lightweight:** **Vite + React + TS** (Tailwind; shadcn optional). Simple SPA, polling. Great for dashboards/take-homes.
- **Full:** **Next.js**, server-component-first (shadcn + Tailwind). For real applications.

**Scaffolding (what makes the deliverables *easy*):** each tier has a blessed starting shape (defined by the tech skills). Standing up a project = applying that shape + dropping in the governance files **from minute zero**: `docs/ADR.md`, `docs/AI_LOG.md`, `README.md`, test setup, the pre-commit hook, and the local `.harness/pm.sqlite`. The graded deliverables (ADR, AI log) exist from the start and are filled as the process runs — never an afterthought.

**Templates (multiple, including from a git URL).** A stack tier is realized as a **template** — a known-good project skeleton. The framework ships blessed templates, but a template can also be **brought from a git URL**: our standards by default, others when useful. Template selection is a function of **(stack × complexity level)** — the system proposes the fit — or the Architect customizes. A brought-in template is wrapped to conform to the governance files (ADR, AI log, pre-commit, `.harness/pm.sqlite`) before use.

**Tiers scale scope and ceremony — never quality.** A PoC is not a lower-quality production app; it's a *smaller-scope, lighter-tier* one. The **quality invariants never scale**: spec-before-code (Spec Lock), tests (TDD for apps), no secret leak, atomic functions under the complexity ceiling, and adversarial verification of every stated guarantee. What scales with task complexity is **scope, stack tier, infrastructure, and ceremony** (how many roles, how deep the review) — never the bar.

**The scale spectrum (unit task → real project).** The framework coordinates the whole range under the same invariants:
- A **unit task** = one work item, a light flow, few roles.
- A **real project** = decomposed into many work items (the backlog/esteira), each running the engagement flow, with cross-item integrity.
The OS's job is to help, orient, and coordinate the team at *both* ends — sizing the ceremony to the task while holding the quality line.

(More types/tiers are added as new blessed conventions, never as config flags — per the philosophy.)

## 4. Per-technology conventions (summary; detailed in `skills/`)

These are the headlines; each has a full `skills/<tech>/SKILL.md`.

### Python — `skills/python` + `skills/fastapi`
- **uv** (env/deps), **pydantic**, **pytest**, **asyncio** by default.
- **ruff** (lint + format).
- **Modern, forward-looking typing.** **Target Python 3.12.** Forbid legacy patterns — e.g., **no `Optional[X]`, use `X | None`** (PEP 604).
- **FastAPI for APIs**, with **explicit multi-model schemas** (separate request / response / persistence models).
- **OpenAPI/Swagger mandatory**, and **linted with Spectral** (the spec is a graded artifact, not an afterthought).

### TypeScript — `skills/typescript` + `skills/nextjs`
- **npm**, **Next.js**, **React**.
- **shadcn/ui** + **Tailwind** for UI.
- **Server-component-first** approach (client components only where interactivity requires).

## 5. How standards are enforced (not just stated)

Standards without enforcement are wishes. Each maps to a mechanism:

| Standard | Enforced by |
|---|---|
| Atomic programming, early returns, paradigm lock | `ruff`/linters + Code Reviewer (inferential) |
| TDD (apps) | tests exist & fail-first; Independent Verifier checks AC↔test |
| Atomic commits | commit-message lint + reviewer |
| No secret leak | pre-commit secret scan (blocks) |
| API attack survival | Security/Attack Adversary + attack-suite gate (Phase 4) |
| Containerization | project-type scaffold + CI build gate |
| Python typing / no `Optional` | ruff rule (blocks) |
| OpenAPI quality | Spectral linter gate |
| Branch/work-item discipline | pre-commit hook (see `WORK-INTAKE-AND-CLAIMING.md`) |
| No unexplained acronyms | first-use expansion (short texts) + `GLOSSARY.md` (long docs); doc linter (future) |

## 6. Model tiering by definition-level

Match model cost to task **ambiguity**, not to importance:
- **Expensive models** for the elaborate / ambiguous / adversarial work: intake framing, architecture proposal + challenge, the hardest adversaries — anywhere being wrong is subtle and costly.
- **Cheap models** for well-defined, low-error work: implementation *under a locked spec*, mechanical refactors, routine checks.

The enabler: **front-load expensive cognition into the spec.** Ambiguity lives in design; once the spec/ADR is locked (Spec Lock), implementation is well-defined enough that a cheap model + a good harness produces it reliably. This is simultaneously a **quality** win (no coding before clarity) and a **cost** win (expensive tokens thinking, cheap tokens typing). It only works because the gates catch the cheap model's mistakes — the rigor is what makes cheap execution *safe*. (See `VALUE-RISK-ROI.md`.)

## 7. The reflexive rule

These standards reduce variety on purpose — fewer ways to write the code means fewer ways for an AI (or a human) to be subtly wrong, and a known shape for the gates to check. Limiting is the point. New needs are met by **adding a blessed standard or skill**, never by loosening an existing one into "configurable".
