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

## Review checklist

- [ ] WAL + `busy_timeout` set at connection open.
- [ ] Every counter/aggregate increment is a single atomic SQL statement.
- [ ] Every check-then-act is one `BEGIN IMMEDIATE` transaction, run in a single executor slice.
- [ ] No `INSERT OR REPLACE`; upserts use `ON CONFLICT DO UPDATE`.
- [ ] Every mutable column has one documented writer; no dual-writer races.
- [ ] Concurrency guarantees are covered by a **stress test** (N concurrent tasks → asserted invariant), not a happy-path test.
