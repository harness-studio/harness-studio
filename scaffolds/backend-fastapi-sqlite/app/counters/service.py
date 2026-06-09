"""Counter increments — the blessed race-safe shape.

The atomic DB-side increment is the whole point: NEVER read-modify-write in Python
(`v = get(); v += 1; save()`), which loses concurrent writes. `UPDATE ... +1` is applied
atomically by the database, so simultaneous events for the same counter are all counted.
"""

from sqlalchemy import Integer, String, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Counter(Base):
    __tablename__ = "counters"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)


async def increment(session: AsyncSession, counter_id: str) -> None:
    """Atomically count one event for ``counter_id``. Race-safe by construction."""
    await session.execute(
        update(Counter).where(Counter.id == counter_id).values(value=Counter.value + 1)
    )
    await session.commit()


async def counter_values(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(select(Counter.id, Counter.value))
    return {counter_id: value for counter_id, value in rows.all()}
