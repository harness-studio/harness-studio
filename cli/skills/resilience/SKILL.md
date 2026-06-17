---
name: resilience
description: Load when designing, building, or reviewing ANY application that does I/O or calls a dependency — timeouts, retry limits, backoff, idempotency, fail-fast. Every app needs defense against hangs and infinite retries. This is the harness instinct applied to runtime.
---
<!-- status: BLESSED — ratified. "Defense against timeouts and infinite retries is harness in the vein." -->

## The blessed way

Nothing waits forever and nothing retries forever. Every I/O call has a **bounded timeout**; every retry loop has a **maximum attempt count with backoff**; every repeated-failure path **fails fast and observably** instead of hanging or spinning. This is the same loop-engineering discipline the framework applies to its own agents (the per-run AI-call/budget ceiling) — applied to the application's runtime.

## Conventions (the blessed patterns)

1. **Every external/I/O call has an explicit timeout.** HTTP clients, DB connections, locks, queue waits — all bounded. No default-infinite waits. For SQLite, that means `PRAGMA busy_timeout` (see `sqlite-concurrency`); for HTTP, an explicit client timeout; for locks, a wait budget.
2. **Every retry loop is bounded: max attempts + backoff + jitter.** Exponential backoff with jitter, a hard attempt cap, then give up with a clear error. Never `while True: retry`.
3. **Retried writes are idempotent.** A retry must not double-apply (no duplicate row, no double increment). Use an idempotency key, a unique constraint, or a conditional update so re-delivery is safe.
4. **Fail fast and observable.** When the budget/attempts are exhausted, return a clear error (e.g. `503` for an unavailable dependency or lock) — never an indefinite hang. Log the exhaustion with enough context to diagnose.
5. **A persistently failing path has a circuit-break / kill-switch.** Repeated failure stops hammering the dependency and surfaces the condition, rather than retrying into the ground.

## Anti-patterns to DETECT (and the fix to PROPOSE)

- **An I/O call with no timeout** (HTTP client, DB, lock acquire) → propose an explicit bounded timeout.
- **`while True` / unbounded retry, or retry with no backoff** → propose max-attempts + exponential backoff + jitter, then fail.
- **A retried write with no idempotency guard** → propose an idempotency key / unique constraint / conditional update.
- **A blocking wait that can hang indefinitely** (e.g. SQLite without `busy_timeout`) → propose the bounded wait + a `503` on exhaustion.
- **Exhaustion that returns a misleading success or silently swallows the error** → propose an explicit, logged, observable failure.

## Review checklist

- [ ] Every I/O/dependency call has an explicit timeout.
- [ ] Every retry loop has a max attempt count + backoff; none can spin forever.
- [ ] Retried writes are idempotent (no double-apply).
- [ ] Exhaustion fails fast with a clear, logged error (not a hang, not a fake success).
- [ ] Hot failure paths have a circuit-break / kill-switch.
