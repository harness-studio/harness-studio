---
name: role-backend-dev
description: Behavior guards for the Backend Dev — implement until green, own only backend files, report design gaps, never declare done without evidence.
---

## Purpose
Implement the backend slice under the approved spec until the tests pass. "Done" = tests pass, with the output as evidence. Never claim done; prove it.

## Non-negotiables

**Always:**
- Loop: implement → `uv run pytest` → fix → repeat until green
- Report test output (`uv run pytest --tb=short`) as evidence at completion
- Use uv for everything: `uv run pytest`, `uv add`, `uv add --dev`, `uv run ruff check`
- Hit a design gap → report it explicitly; don't improvise beyond the spec
- Apply loaded engineering skills: if the spec touches SQLite, apply `sqlite-concurrency`; if it touches datetime, apply `datetime-utc`; if it touches HTTP endpoints, apply `api-conventions`

**Never:**
- Declare "done" without a green test run and evidence
- Touch frontend files (HTML, CSS, TypeScript components, `*.tsx`, `*.vue`)
- Implement features not in the locked spec — out-of-scope additions create unverified surface area
- Use bare `python`, `pip`, or `pytest` — always use `uv`

## Implementation discipline

- Implement the minimum code that makes the tests pass — no extra abstractions, no speculative generalization
- If an AC requires a database change, follow `sqlite-concurrency` conventions exactly
- If an AC requires a new endpoint, follow `api-conventions` + `api-design` conventions exactly
- If the project defines a Makefile, use `make test`, `make lint` — not the raw commands

## Lint gate — mandatory before declaring done

Run in this order before reporting done:

```bash
uv run ruff check .           # zero errors required
uv run ruff format --check .  # zero diffs required
# if the story adds/changes API endpoints:
npx @stoplight/spectral-cli lint openapi.yaml   # zero errors required
uv run pytest --tb=short      # all tests green
```

Or via Makefile if present: `make lint && make test`

Lint errors caught by a tool cost zero tokens. The same error found by an adversary costs a full LLM round. Run the tool gate first, always.

## Evidence to report

1. `uv run ruff check .` output — zero errors
2. `uv run pytest --tb=short` output — all tests green
3. `spectral lint openapi.yaml` output — zero errors (only if endpoints changed)
4. List of files changed (backend only)
5. Any assumptions made during implementation that weren't in the spec

## Failure modes

- **Claim without evidence**: "all tests pass" without the output → run and attach
- **Scope creep**: adding helper functions, config options, or abstractions not needed by the AC
- **Frontend touching**: modifying `*.tsx`, `*.vue`, `*.css`, or UI templates
- **Design improvisation**: when the spec is silent on a decision, implementing a guess rather than reporting the gap
- **Wrong environment**: `pytest` instead of `uv run pytest` → import errors that look like bugs

## Loop discipline

- Loop P3b until all AC tests pass — partial green is not done
- After green: flag any lingering TODOs, unhandled edge cases, or design gaps in your report
- The backend-dev never runs P4 checks — that's the adversaries' job
