"""FastAPI app factory (lightweight tier scaffold).

Thin endpoints; logic lives in services. `/events` is intentionally minimal here — the team
fills in the full schema, validation, etc. The counter is included because it's the concurrency
crux (atomic increment under concurrent writes).
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Base, SessionLocal, engine, get_session
from app.counters.service import Counter, counter_values, increment

COUNTERS = ["alpha", "beta", "gamma"]  # seed a few named counters at startup


async def init_db() -> None:
    """Create tables + seed counters. Called by lifespan AND by tests.

    Extracted so it's callable outside the ASGI lifespan — httpx's ASGITransport does not run
    lifespan events, so tests call this directly. (This is the bug the concurrency test caught;
    the fix lives in the harness, not the test.)
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        for counter_id in COUNTERS:
            if await session.get(Counter, counter_id) is None:
                session.add(Counter(id=counter_id, value=0))
        await session.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan, title="Counter service (scaffold)")


@app.post("/events")
async def post_event(
    event: dict,  # TODO(team): replace with a Pydantic Event schema
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    counter = event.get("counter")
    if counter:
        await increment(session, counter)
    return {"ok": True}


@app.get("/counters")
async def get_counters(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    return await counter_values(session)
