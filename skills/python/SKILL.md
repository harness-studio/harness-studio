---
name: python
description: Load for any Python work — project setup, typing, async, testing, style. Base layer under fastapi and other Python skills.
---
<!-- status: BLESSED — ratified. -->

## The blessed way

Modern, forward-looking Python: **uv** for env/deps, **ruff** for lint+format, **pytest** with **TDD**, **pydantic** for data models, **asyncio** for IO-bound work, strict and modern typing. One paradigm per module (object-oriented *or* functional) — never mixed.

## Conventions

1. **Environment & deps: `uv` only.** `uv add` / `uv run`; `pyproject.toml` is the source of truth. No bare `pip`, no `requirements.txt` as the primary.
2. **Layout:** `src/` layout (`src/<package>/`), `tests/` mirrors it.
3. **Typing is mandatory and modern.** Type every function signature. **Target Python 3.12.** **No legacy typing: use `X | None` not `Optional[X]`, `list[str]` not `List[str]`.** No bare `Any` without justification.
4. **Models = pydantic** (v2) for anything crossing a boundary (API, config, IO). Plain dataclasses only for internal value objects.
5. **Async for IO.** IO-bound code is `async`; don't block the event loop with sync IO. CPU-bound work goes to a worker/threadpool, never inline in an async path.
6. **Style:** early returns / guard clauses (no deep nesting); small single-purpose functions (atomic programming); **paradigm lock** — pick OO or functional per module and stay consistent.
7. **Errors:** narrow exceptions; never a bare `except:`; raise domain errors, handle at the edge.
8. **Lint/format: `ruff`** (both). Code must be ruff-clean.
9. **Settings: `pydantic-settings`**, never scattered `os.getenv`.

## Gotchas & AI failure modes

- **Legacy typing creep.** AI defaults to `Optional[...]`, `List[...]`, `Dict[...]`. Blessed: `X | None`, `list[...]`, `dict[...]`. (Enforce with a ruff rule.)
- **Sync/async mixing.** AI drops a blocking call (sync DB driver, `requests`, `time.sleep`) inside `async def` — silently serializes and hides concurrency bugs.
- **God functions.** AI writes one 80-line function. Demand atomic decomposition.
- **Broad `except Exception`** that swallows errors — hides failures the gates should catch.
- **Mutable default args** (`def f(x=[])`) — a classic latent bug AI still emits.
- **`pip`/venv drift** instead of `uv` — breaks reproducibility.
- **Tests written after** (or asserting trivially) — violates TDD; the AC Adversary/Verifier checks the test actually fails on broken code.

## How "done" is proven (tests)

- **TDD:** a failing `pytest` first, then code (exception: notebooks).
- `pytest` green + **`ruff check` clean** + type check passes = the minimum bar.
- Evidence = the command output. No "should pass".

## Out of scope (sanctioned paths or absent)

- **Non-`uv` environments:** not blessed. A forced exception (e.g., a constrained CI) is documented in the engagement's ADR — never a silent default.
- **Packaging/publishing to PyPI, Cython, etc.:** separate concern/skill when needed.
- **Notebooks:** exempt from TDD (exploratory); still follow typing/style where practical.

## Examples

Typed, guard-claused, modern (the blessed shape):
```python
async def get_active_mission(session: AsyncSession, vehicle_id: str) -> Mission | None:
    if not vehicle_id:
        return None
    result = await session.execute(
        select(Mission).where(Mission.vehicle_id == vehicle_id, Mission.active.is_(True))
    )
    return result.scalar_one_or_none()
```

TDD test-first shape:
```python
async def test_fault_cancels_active_mission(session):
    # arrange: a vehicle with an active mission
    # act: transition to fault
    await set_status(session, "v-12", "fault")
    # assert: mission cancelled + maintenance record exists
    assert await get_active_mission(session, "v-12") is None
    assert await maintenance_exists(session, "v-12")
```
