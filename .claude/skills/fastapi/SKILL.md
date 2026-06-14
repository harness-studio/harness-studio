---
name: fastapi
description: Load when building or reviewing a FastAPI backend service — endpoints, project structure, Annotated style, return types, async/sync rules, persistence, concurrency, transactions, testing.
---
<!-- status: BLESSED — ratified. Merges official FastAPI skill conventions with Harness Studio service architecture. -->

## The blessed way

A FastAPI service in Harness Studio is **async-first**, **feature-structured**, and **transaction-explicit**. Pydantic v2 for the wire, SQLModel (preferred for new projects) or SQLAlchemy 2.0 async (keep if already in the project) for persistence, Alembic for migrations, `uv` for the environment, `pytest` + `httpx.AsyncClient` for tests. One shape, every service.

## CLI — use `fastapi`, not `uvicorn` directly

```bash
fastapi dev    # development: auto-reload, debug mode
fastapi run    # production: optimized workers
```

Declare the entrypoint in `pyproject.toml` so `fastapi` knows where the app lives:

```toml
[tool.fastapi]
entrypoint = "app.main:app"
```

Integrate with the Makefile:
```makefile
dev:
	fastapi dev

prod:
	fastapi run
```

## Use `Annotated` — always

The `Annotated` style is **mandatory** for all parameter and dependency declarations. It keeps function signatures valid outside FastAPI, enables reusability, and respects types.

**Parameters:**
```python
from typing import Annotated
from fastapi import FastAPI, Path, Query

@app.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[int, Path(ge=1, description="The item ID")],
    q: Annotated[str | None, Query(max_length=50)] = None,
):
    ...
```

**Dependencies — create a type alias:**
```python
from typing import Annotated
from fastapi import Depends

def get_current_user(): ...

CurrentUser = Annotated[User, Depends(get_current_user)]

@app.get("/items/")
async def read_item(current_user: CurrentUser): ...
```

**Never use the old style:**
```python
# DO NOT DO THIS
async def read_item(item_id: int = Path(..., ge=1)):  # no ellipsis, no non-Annotated
```

## No ellipsis (`...`) as required marker

`...` is not needed and not recommended for required parameters or Pydantic fields. The absence of a default is sufficient.

```python
# CORRECT
class Item(BaseModel):
    name: str
    price: float = Field(gt=0)

# DO NOT DO THIS
class Item(BaseModel):
    name: str = ...
    price: float = Field(..., gt=0)
```

## Return types — mandatory

Always declare a return type annotation or `response_model`. It validates, filters, documents, and serializes the response via Pydantic (Rust-side). **Return types are the security boundary** — they prevent sensitive fields from leaking.

```python
class Item(BaseModel):
    name: str
    description: str | None = None

@app.get("/items/{id}")
async def get_item(id: int) -> Item:
    ...
```

Use `response_model` when the internal type differs from the public contract (e.g. filtering sensitive fields):
```python
class InternalItem(BaseModel):
    name: str
    secret_key: str  # must not leak

class PublicItem(BaseModel):
    name: str

@app.get("/items/{id}", response_model=PublicItem)
async def get_item(id: int) -> Any:
    return db.get(id)   # returns InternalItem; response_model filters secret_key
```

**Never use `ORJSONResponse` or `UJSONResponse`** — they are deprecated. Declare a return type instead; Pydantic handles serialization on the Rust side with equivalent performance.

## async vs sync path operations

Use `async def` **only** when the function body calls async-compatible code with `await`. Use plain `def` for blocking code or when in doubt — FastAPI runs plain `def` in a threadpool, so it won't block the event loop.

```python
# async: calls async code
@app.get("/items/")
async def read_items():
    return await db.fetch_all()

# plain def: blocking library or in doubt
@app.get("/config/")
def read_config():
    return some_blocking_library.load()
```

**Never put blocking calls inside `async def`** — it silently serializes everything and hides concurrency bugs until load. This includes: sync DB drivers, `requests`, `time.sleep`, CPU-heavy work.

The same rule applies to dependencies.

## Router configuration — on the router, not in `include_router`

Declare `prefix`, `tags`, and shared `dependencies` on the `APIRouter` itself:

```python
# CORRECT
router = APIRouter(prefix="/items", tags=["items"])

@router.get("/")
async def list_items(): ...

# in main.py
app.include_router(router)   # clean, no params needed here
```

Apply shared auth/rate-limit dependencies at the router level:
```python
router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
```

## One HTTP operation per function

One function per HTTP method. Never mix GET and POST in `api_route`:

```python
# CORRECT
@router.get("/items/")
async def list_items(): ...

@router.post("/items/")
async def create_item(item: Item): ...

# DO NOT DO THIS
@app.api_route("/items/", methods=["GET", "POST"])
async def handle_items(request: Request): ...
```

## No `RootModel`

Use `Annotated` + Pydantic validators instead of `RootModel`. FastAPI creates a `TypeAdapter` automatically:

```python
# CORRECT
@app.post("/items/")
async def create_items(items: Annotated[list[int], Field(min_length=1), Body()]):
    return items

# DO NOT DO THIS
class ItemList(RootModel[Annotated[list[int], Field(min_length=1)]]): pass
```

## Project structure (feature-based)

```
app/
  main.py            # app factory, router registration, lifespan
  core/              # settings (pydantic-settings), db engine/session factory, shared deps
  <feature>/         # one folder per domain (users/, orders/, products/…)
    router.py        # endpoints — thin, no business logic
    service.py       # business logic + transactions
    models.py        # ORM models (SQLModel or SQLAlchemy)
    schemas.py       # Pydantic request/response schemas (the API contract)
  migrations/        # Alembic
tests/
  conftest.py        # async client, test DB, fixtures
```

**Layering is strict:** Router → Service → Models. Routers never query the DB; services own transactions; business logic never lives in a router or schema.

**Schemas ≠ models.** Pydantic schemas are the API contract; ORM models are persistence. Never return ORM objects directly from endpoints.

## Persistence — SQLModel (preferred) or SQLAlchemy 2.0

**New project:** use **SQLModel** — combines SQLAlchemy and Pydantic, eliminates the model/schema duplication for simple cases, officially recommended by FastAPI.

**Existing project with SQLAlchemy:** keep SQLAlchemy 2.0 async (`async_sessionmaker`, `AsyncSession`) — do not migrate mid-engagement.

DB session via dependency injection — one session per request, never global:
```python
# core/db.py
async_engine = create_async_engine(settings.db_url)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

**Settings:** always `pydantic-settings`, never scattered `os.getenv`.

## Transactions and concurrency — the critical rules

- **Never read-modify-write for counters** — `count = get(); count += 1; save()` loses writes under concurrent requests. Use atomic SQL: `UPDATE t SET n = n + 1 WHERE id = ?`
- **Multi-step mutations that must be atomic** → explicit transaction with the correct isolation level
- **"Atomic" must be proven** — a test that fires N concurrent requests and asserts the invariant (see below)
- **Aggregates on read** (`GROUP BY`) are race-free by construction; prefer them over mutable counters unless proven too slow

## Error handling

One exception→HTTP mapping: services raise domain errors, a single handler maps them. Never return error details in `200` responses.

```python
# services raise
raise ItemNotFoundError(item_id)

# handlers map (in main.py)
@app.exception_handler(ItemNotFoundError)
async def _(req, exc): return JSONResponse(status_code=404, content={"error": ...})
```

## How "done" is proven

```bash
uv run pytest --tb=short   # or: make test
uv run ruff check .
```

- **`pytest` + `httpx.AsyncClient`** against the real app; real (test) DB for anything touching persistence
- **Concurrency proven by stress test** for any "guarantee" AC:
  ```python
  async def test_concurrent_increments(client):
      await asyncio.gather(*[client.post("/events") for _ in range(100)])
      r = await client.get("/counter")
      assert r.json()["count"] == 100
  ```
- **Round-trip tests** for persistence (write → read back)
- Evidence = `uv run pytest --tb=short` output. No "it should work."

## Gotchas & AI failure modes

- **`Annotated` forgotten** — AI defaults to `= Path(...)` style; rewrite with `Annotated`
- **Ellipsis as required marker** — `Field(..., gt=0)` → `Field(gt=0)`
- **Missing return type** — sensitive fields leak; response performance not optimal
- **`ORJSONResponse` used** — deprecated; remove and declare return type instead
- **Router params in `include_router`** — move `prefix`/`tags` to the `APIRouter`
- **Blocking call in `async def`** — use plain `def` or run in threadpool via `asyncio.run_in_executor`
- **`RootModel` used** — replace with `Annotated` + `Body()` + `Field`
- **Read-modify-write counter** — loses writes under concurrency; atomic SQL only
- **`api_route` with multiple methods** — one function per HTTP operation
