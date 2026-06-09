"""The crux acceptance test: many simultaneous events for ONE counter must ALL be counted.

This is the stress test the AC Adversary demands — it fires concurrent requests and asserts no
write is lost. A naive read-modify-write counter fails this; the atomic `UPDATE ... +1` passes it.
"""

import asyncio
import os
import tempfile

import httpx
import pytest
from httpx import ASGITransport

# Fresh, isolated DB per run so counts are deterministic (set BEFORE importing the app).
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tempfile.mktemp(suffix='.db')}"

from app.main import app, init_db  # noqa: E402 — env must be set before import


@pytest.mark.asyncio
async def test_concurrent_same_counter_all_counted() -> None:
    await init_db()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        n = 100
        await asyncio.gather(*(client.post("/events", json={"counter": "alpha"}) for _ in range(n)))
        resp = await client.get("/counters")
        assert resp.json()["alpha"] == n  # every event counted, zero lost
