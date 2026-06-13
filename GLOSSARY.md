# Harness Studio — Glossary

> Every term and abbreviation used across the framework, defined once. This is the canonical reference required by [PHILOSOPHY](PHILOSOPHY.md) tenet 10 ("no unexplained acronyms"). Short texts spell terms out inline; the longer documents keep the short form and point here.

## Core concepts

- **Engagement** — one unit of governed work taken end to end through the six phases (intake → delivery). The framework's basic "job".
- **Engagement Lead** — the human who runs an engagement: sets direction, holds the budget, and decides at the human gates. The role a software engineer steps into (see [`The New Role of the Software Engineer`](presentation/)).
- **Maker / Checker** — the maker is whoever builds something; the checker is the independent role that judges it. Golden rule: **the maker never grades its own work**.
- **Adversary** — a role rewarded for *finding problems*, never for approving. The opposite incentive to the builder. Examples: AC Adversary, Architecture Adversary, Security Adversary.
- **Gate** — a checkpoint a phase must pass before the next begins — wherever possible an independent adversary plus an evidence-backed check, not a self-review.
- **Spec Lock** — the hard human gate at the end of architecture (Phase 2). The problem, the acceptance criteria, and the design are settled and approved. **No code is written before it.**
- **loop-until-dry** — the stop condition of verification: keep iterating (build → adversaries attack → fix) until the adversaries find nothing more.
- **Right-sizing** — matching rigor and ceremony to the *cost of being wrong*. Quality invariants never scale; scope, stack tier, and ceremony do.
- **Fast lane / Deliberate lane** — the two execution paths. Fast lane: trivial, reversible work with light gates. Deliberate lane: high-risk work (concurrency, security, money) with the full adversarial rigor.
- **Evidence over assertion** — "done" only counts with proof (test output, a diff, a screenshot), never a confident claim.

## Phases & process

- **P0–P5 / Phase 0–5** — the six engagement phases: **P0 Intake**, **P1 Stories & Acceptance Criteria**, **P2 Architecture**, **P3 Build** (P3a Red → P3b Green), **P4 Verify**, **P5 Integration & Delivery** (the human MERGE gate).
- **AC — Acceptance Criteria** — the objective, *testable* conditions that define when work is done. Every "guarantee/atomic/concurrency" requirement must become a concrete test.
- **DoD — Definition of Done** — the full set of acceptance criteria for an engagement; the objective contract for "finished".
- **Story** — a deliverable described from the user's point of view; paired with its acceptance criteria in Phase 1.

## Artifacts & records

- **ADR — Architecture Decision Record** — a one-page record of the few most important decisions: what was decided, why, the alternative, and the trade-off.
- **AI Interaction Log (AI log)** — the live record of every meaningful prompt, a summary of the output, and the corrections/redirections made along the way.

## Work intake & coordination

- **PM Port — Project-Management Port** — the single interface the framework uses for work items. A local store by default; robust project-management tools (GitHub, GitLab, Azure DevOps) attach as sync adapters.
- **Work item** — a unit of work in the backlog. Rule: no work without a work item.
- **Atomic claim** — taking a work item via a compare-and-swap, so two agents can never grab the same task.
- **Janitor** — the scheduled discovery loop: it audits the codebase, de-duplicates findings, and files work items.
- **`.harness/`** — the project's durable runtime memory: the work-item store, logs, and engagement state. The agent forgets between runs; this doesn't.
- **Fingerprint** — a stable signature the janitor uses to recognize a finding it has already filed (so it doesn't create duplicates).

## Agents, skills & templates

- **Subagent** — an AI role running within one session that reports back to the parent.
- **Agent team** — peer agents in separate sessions that push to each other (a Claude Code capability).
- **Skill** — a blessed, written convention for a technology (e.g., Python, FastAPI), loaded by its description when relevant.
- **Template** — a known-good project skeleton, imported as a git repository and composed (additively merged) into a project.
- **Scaffold** — the concrete starting shape a template or stack tier drops into a new project (folders, governance files, tests).
- **Model tiering** — using expensive models for ambiguous/adversarial work (design, intake) and cheap models for well-defined work (implementation under a locked spec).

## Technology abbreviations

- **API — Application Programming Interface** — the programmatic surface of a service.
- **CLI — Command-Line Interface** — a tool run from the terminal. Harness Studio's is `hssd`.
- **UI — User Interface** — the visual front end (e.g., a dashboard).
- **CRUD — Create, Read, Update, Delete** — the four basic operations on stored data.
- **TDD — Test-Driven Development** — write a failing test first, then the code that passes it.
- **SQL — Structured Query Language** — the language used to query relational databases.
- **SQLi — SQL injection** — an attack that smuggles malicious SQL through an input; tested by the Security Adversary.
- **MCP — Model Context Protocol** — the standard by which external tools/services connect to an AI agent.
- **OpenAPI / Swagger** — a machine-readable description of a web API's endpoints.
- **`hssd`** — the Harness Studio command-line tool (long form: `harness-sd`).

## Roles (the team)

The full role cards live in [`01-ROLES.md`](01-ROLES.md). In short: **Specialists** build (Product Analyst, Story Writer, Architect, Backend/Frontend developers); **Adversaries** try to break the work (Definition Skeptic, AC Adversary, Architecture Adversary, Test/Concurrency Adversary, Security Adversary, Independent Verifier, Completion Challenger, Regression Hunter).
