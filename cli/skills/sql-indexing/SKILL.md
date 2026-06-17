---
name: sql-indexing
description: Load when designing, building, or reviewing any SQL schema or query path — index strategy for foreign keys, filter/range queries, and append-only tables that grow without bound. Index analysis is mandatory for any SQL system.
---
<!-- status: BLESSED — ratified. -->

## The blessed way

Every query path that runs in production has an index that serves it. Index design is part of the **schema**, decided when the table is defined — not a later optimization. An unindexed filter on a growing table is a latency cliff that surfaces the moment real data arrives (often live, in a demo).

## Conventions (the blessed patterns)

1. **Index every foreign key.** A FK column is almost always a join/filter key; SQLite (unlike Postgres) does not auto-index FKs.
2. **Index every (filter + range) query path as a composite — equality columns first, the range column last.** Example: querying `anomalies` by `vehicle_id` (equality) within a `detected_at` window (range) → `CREATE INDEX ix_anomalies_vehicle_time ON anomalies(vehicle_id, detected_at)`. Column order matters: equality predicates first so the range can be a contiguous scan.
3. **Append-only tables that grow without bound get indexes from day one.** High-write logs (telemetry, events, anomalies) reach millions of rows fast; any unindexed read full-scans.
4. **Verify with the planner.** `EXPLAIN QUERY PLAN <query>` must show `SEARCH … USING INDEX`, not `SCAN`. Make this part of the test/review evidence for any list/query endpoint.
5. **Don't over-index.** Each index is write cost. Index the paths you actually query; don't speculatively index every column.

## Anti-patterns to DETECT (and the fix to PROPOSE)

- **A query endpoint filtering by a column with no index** (e.g. `GET /anomalies?vehicle_id=&since=`) → propose the composite index, equality-then-range.
- **An append-only / high-write table with no indexes declared** → propose indexes for its known read paths at migration time.
- **A foreign key with no index** → propose `CREATE INDEX` on it.
- **A range filter listed before an equality column in a composite index** → propose reordering (equality first).
- **No `EXPLAIN QUERY PLAN` evidence for a list/query endpoint** → propose adding it to the test as proof the index is used.

## Review checklist

- [ ] Every FK is indexed.
- [ ] Every list/query endpoint's filter+range path has a matching composite index (equality first, range last).
- [ ] Append-only/growing tables declare their read-path indexes at creation.
- [ ] `EXPLAIN QUERY PLAN` shows index use (SEARCH, not SCAN) for each query endpoint.
- [ ] No speculative/unused indexes.
