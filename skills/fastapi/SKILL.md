---
name: fastapi
description: Load when building or reviewing a FastAPI backend service — endpoints, persistence, concurrency, transactions, testing.
---
<!-- status: BLESSED — ratified. -->

## The blessed way

A FastAPI service in Harness Studio is **async-first**, **feature-structured**, and **transaction-explicit**. Pydantic v2 for the wire, SQLAlchemy 2.0 (async) for persistence, Alembic for migrations, `uv` for the environment, `pytest` + `httpx.AsyncClient` for tests. One shape, every service.

## Conventions

1. **Project structure (feature-based):**
   ```
   app/
     main.py            # app factory + router registration
     core/              # settings (pydantic-settings), db engine/session, deps
     <feature>/         # one folder per feature/domain
       router.py        # endpoints (thin — no business logic)
       service.py       # business logic + transactions
       models.py        # SQLAlchemy ORM models
       schemas.py       # Pydantic request/response models
     migrations/        # Alembic
   tests/
   ```
2. **Layering is strict.** Router → Service → Models. Routers never touch the DB directly; services own transactions; business logic never lives in a router or a schema.
3. **Async end to end.** `async def` endpoints; async DB driver (e.g., asyncpg) + `async_sessionmaker`. Don't mix sync DB calls into async paths.
4. **DB sessions via dependency injection.** One session per request via `Depends`; the service receives the session, never creates global ones.
5. **Schemas ≠ models.** Pydantic schemas are the API contract; ORM models are persistence. Never return ORM objects directly.
6. **Transactions are explicit and owned by the service.** A unit of work = one transaction. For operations that must be atomic across rows, use an explicit transaction; for "must not lose a write" counters, prefer an atomic DB operation (atomic increment or row lock) over read-modify-write in Python.
7. **Settings via `pydantic-settings`**, never `os.getenv` scattered around.
8. **Consistent error model:** a single exception→HTTP mapping; services raise domain errors, a handler maps them.

## Gotchas & AI failure modes

- **The #1 trap: read-modify-write under concurrency.** AI happily writes `count = get(); count += 1; save()` — which loses writes under concurrent requests. Blessed fix: atomic `UPDATE ... SET x = x + 1` or a locked row. This is exactly where overconfidence ships a race.
- **"Atomic" claimed, not delivered.** AI calls a multi-step mutation "atomic" without a real transaction boundary. Demand the transaction + the correct isolation level.
- **Async that isn't.** A sync DB driver or a blocking call inside an `async def` silently serializes everything and hides concurrency bugs until load.
- **Aggregates computed unsafely.** Per-status counts maintained as mutable counters race; deriving them on read (`GROUP BY`) is consistent by construction — prefer it unless proven too slow.
- **Tests that don't exercise concurrency.** A test that calls the endpoint once "passes" while the race is wide open. The concurrency AC needs `asyncio.gather` firing simultaneous requests.

## How "done" is proven (tests)

- **`pytest` + `httpx.AsyncClient`** against the app; a real (test) DB, not mocks, for anything touching persistence/transactions.
- **Concurrency is proven by stress test:** fire N simultaneous requests with `asyncio.gather` and assert the invariant (e.g., `count == N`, or "exactly one mission cancelled").
- **Round-trip tests** for persistence (write → read back).
- Evidence = the test output. No "it should work."

## Out of scope (sanctioned paths or absent)

- **Sync FastAPI / sync DB:** not blessed. If a hard dependency forces sync, that's a documented exception in the engagement's ADR — not a default.
- **Django REST:** a different blessed substrate; if chosen, it's a separate skill, not a config flag here.
- **Auth provider specifics, deployment, observability stack:** out of this skill (separate skills when needed).

## Examples

Atomic counter (the blessed shape for "every event counted"):
```python
# service.py — atomic, race-safe
async def increment(session: AsyncSession, counter_id: str) -> None:
    await session.execute(
        update(Counter).where(Counter.id == counter_id).values(value=Counter.value + 1)
    )
    await session.commit()
```

Concurrency stress test (the blessed shape for proving it):
```python
# test — proves no write is lost
async def test_concurrent_events(client):
    await asyncio.gather(*[client.post("/events", json={"counter": "alpha"}) for _ in range(100)])
    r = await client.get("/counters")
    assert r.json()["alpha"] == 100
```
