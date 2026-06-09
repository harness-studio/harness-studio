# Backend scaffold — FastAPI + SQLite (lightweight tier)

A minimal, blessed starting shape for a FastAPI service. Demonstrates the conventions, not a finished app — the team fills in logic under this structure.

## Why this tier
SQLite **serializes writes** (single writer), so "every entry is counted" comes almost for free — no lost updates — at the cost of write throughput. Combined with the **atomic `UPDATE ... +1`** pattern (never read-modify-write) and **WAL + busy_timeout**, concurrent writers queue instead of erroring. For real concurrency/scale, switch to the `backend-fastapi-postgres` tier (and justify it in the ADR).

## Run
**Requires Python 3.12.**
```bash
uv sync
uv run uvicorn app.main:app --reload
# tests (incl. the concurrency proof):
uv run pytest
```

## Structure
```
app/
  main.py          # app factory + endpoints (thin)
  core/db.py       # async SQLite engine/session (WAL)
  counters/service.py # blessed race-safe counter (atomic increment)
tests/
  test_counter_concurrency.py # the crux: N simultaneous events → count == N
docs/
  ADR.md           # filled as the engagement runs (from templates/)
  AI_LOG.md        # captured live (from templates/)
.vscode/           # configures existing extensions (no custom plugin)
.pre-commit-config.yaml   # the gate: protected branch + task-linked branch + secret scan + ruff
pyproject.toml     # uv deps + ruff (UP=no Optional, C90=complexity ceiling, S=security)
```

## Governance from minute zero
`docs/ADR.md` and `docs/AI_LOG.md` exist before any code — the graded deliverables are filled as the process runs, never reconstructed at the end.
