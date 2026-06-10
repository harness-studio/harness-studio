---
name: sqlite-concurrency
description: Load when designing, building, or reviewing any Python service backed by SQLite — concurrency, transactions, upserts, single-writer ownership, atomic counters. The blessed correctness rules for FastAPI + SQLite under concurrent writes.
---
<!-- status: BLESSED — ratified. Field-learned on the fleet-telemetry engagement. -->

## The blessed way

SQLite has **one writer at a time**. Correctness under concurrency comes from leaning on that serialization with the right transaction mode — never from read-modify-write in Python. Every mutable column has **exactly one writer path**. Every "must not lose a write" is a single atomic SQL statement or a row-locking transaction.

## Conventions (the blessed patterns)

1. **WAL + busy_timeout at connection open, always.** `PRAGMA journal_mode=WAL` (concurrent readers alongside the single writer) and `PRAGMA busy_timeout=5000` (a blocked writer waits up to 5 s then errors, instead of hanging forever or raising `database is locked` immediately).
2. **Atomic counter, never read-modify-write.** A counter increment is `UPDATE t SET n = n + 1 WHERE id = ?` — one statement. The value never enters Python memory, so concurrent increments can't lose updates.
3. **Read-modify-write that must be atomic across rows → `BEGIN IMMEDIATE`.** It takes the write lock at transaction *start*, so no other writer can interleave between your read and your writes. Use it for "check then act" (e.g., cancel the active mission AND insert a maintenance record as one unit).
4. **Run a whole transaction in ONE executor/connection slice.** With `aiosqlite` (or any thread-pool driver), a transaction that spans multiple `await`s can be serviced by different OS threads → the `BEGIN` and the later statements hit different connections → `cannot commit - no transaction is active`. Run the entire `BEGIN IMMEDIATE … COMMIT` as a single `run_in_executor` callable (or hold one dedicated write connection on one thread).
5. **Upsert with `INSERT … ON CONFLICT(key) DO UPDATE SET …`** — never `INSERT OR REPLACE`. `INSERT OR REPLACE` DELETEs then re-INSERTs: it resets columns you didn't supply to their defaults, changes the rowid, and fires delete triggers / cascades. A real upsert touches only the columns you name.
6. **Single-writer ownership per mutable column.** Each mutable column is written by exactly one code path; document it. If two paths write the same column (e.g. telemetry ingestion AND a fault handler both writing `status`), that is a **dual-writer race**: the later writer silently clobbers the earlier one *after* any transaction protecting it has committed.

## Anti-patterns to DETECT (and the fix to PROPOSE)

- **`INSERT OR REPLACE` for an upsert** → propose `INSERT … ON CONFLICT(key) DO UPDATE SET <only the changed cols>`.
- **A column written by two paths** (the dual-writer race) → propose a single owner: one path writes it; others read it (inside the transaction) or write a *conditional* update (`… WHERE status != 'fault'`). State who the sole owner is.
- **Read in Python → compute → write back** for a counter/aggregate → propose the atomic `SET n = n + 1` (or an `INSERT … ON CONFLICT DO UPDATE SET n = n + 1`).
- **`BEGIN` (deferred) for a check-then-act** → propose `BEGIN IMMEDIATE` (deferred lets a concurrent committer slip in after your read).
- **An async transaction spanning multiple `await`s on a pooled driver** → propose collapsing the transaction into a single executor call.
- **No `busy_timeout` / no WAL** → propose setting both at connection init.
- **`datetime.now()` / app-level mutex (`asyncio.Lock`) to serialize writes** → propose the DB-level mechanism (atomic SQL / `BEGIN IMMEDIATE`); an in-process lock breaks under multiple workers/processes.
- **A bootstrap that switches a fresh DB to WAL, callable concurrently in-process** → guard it with a module-level `threading.Lock` (the WAL-switch lock bypasses `busy_timeout` — see below).

## WAL pragma cold-start: the Windows / busy_timeout blind spot

`PRAGMA journal_mode=WAL` on a **fresh file** (still in DELETE mode) needs an **exclusive lock** to rewrite the file header — and that lock is taken on a path that **bypasses `busy_timeout`** in CPython's `sqlite3` on Windows (and some Linux/tmpfs setups). So when N threads simultaneously open the same brand-new database and each issues `PRAGMA journal_mode=WAL`, N-1 get `OperationalError: database is locked` **immediately** — not after the 5 s timeout. `busy_timeout` (PRAGMA or `connect(timeout=…)`) does **not** protect this path. (Known CPython `sqlite3`/SQLite limitation — confirm on your platform; it bit the fleet-telemetry bootstrap stress test on Windows.)

### The fix: serialize `init_db` in-process with a module-level `threading.Lock`

```python
_init_lock = threading.Lock()   # module-level, one per process

def init_db(path=None):
    """Serialize in-process: the WAL switch on a fresh file bypasses busy_timeout on Windows."""
    with _init_lock:
        conn = connect(path)
        try:
            _create_schema(conn)
            _seed_zones(conn)
        finally:
            conn.close()
```

This is **not** the anti-pattern "use an app-level mutex instead of DB-level atomics" — it guards the **bootstrap** (a one-time write to the file header), where the DB-level mechanism silently fails on this platform. The distinction:

| | `threading.Lock` in `init_db` | `asyncio.Lock` around business writes |
|---|---|---|
| **Guards** | the one-time WAL file-header switch at startup | ongoing business-data writes |
| **Breaks under multiple workers?** | No — each process bootstraps itself | Yes — the lock is per-process, invisible across workers |
| **Verdict** | **Blessed** for `init_db`-class routines | **Anti-pattern** — use `BEGIN IMMEDIATE` instead |

Cross-process cold-start (two workers starting against the same file) still needs `BEGIN IMMEDIATE` + `busy_timeout`; the `threading.Lock` only covers threads within one process.

### Detection heuristic

A concurrency stress test (`ThreadPoolExecutor` / `multiprocessing`) that fails in **under 1 s** despite `busy_timeout=5000` is almost always this WAL cold-start race, not a `BEGIN IMMEDIATE` race. The tell: the failure count equals N-1 (every thread except the first), raised before any seed SQL runs.

## Review checklist

- [ ] WAL + `busy_timeout` set at connection open.
- [ ] Every counter/aggregate increment is a single atomic SQL statement.
- [ ] Every check-then-act is one `BEGIN IMMEDIATE` transaction, run in a single executor slice.
- [ ] No `INSERT OR REPLACE`; upserts use `ON CONFLICT DO UPDATE`.
- [ ] Every mutable column has one documented writer; no dual-writer races.
- [ ] Concurrency guarantees are covered by a **stress test** (N concurrent tasks → asserted invariant), not a happy-path test.
- [ ] Any bootstrap that switches a fresh DB to WAL and can run concurrently in-process is guarded by a module-level `threading.Lock` (the WAL-switch lock bypasses `busy_timeout`).
