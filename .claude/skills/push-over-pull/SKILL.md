---
name: push-over-pull
description: Load when designing, building, or reviewing how data or change-events move between components — client/server, service/service, or source/system. The blessed preference: event-driven PUSH (WebSockets, SSE, pub/sub, Kafka, message queues, webhooks) over PULL (polling). Pulling is a justified exception, not a default.
---
<!-- status: BLESSED — ratified. "Whenever push is possible, prefer it over pulling." -->

## The blessed way

**Push is the default; pull must be justified.** When one component needs another's data or state changes, deliver them as **events the moment they happen** — not by repeatedly asking "anything new yet?". Choosing polling is a conscious exception that is recorded in the ADR with its reason. (This mirrors the framework's own bias: one blessed way; the alternative is documented or it doesn't exist.)

## Why push wins by default

- **Latency:** events arrive when they occur, not on the next poll tick.
- **No wasted work:** polling re-asks on every interval even when nothing changed (N clients × frequency × mostly-empty responses); push sends only on change.
- **Scale & backpressure:** a broker/stream fans out and absorbs bursts; a herd of pollers hammers the source at a fixed floor regardless of activity.
- **Intent:** "real-time", "live", "as it happens" in a requirement is a direct signal for push.

## Pick the mechanism by layer

- **Server → client (realtime UI):** WebSocket (bidirectional) or Server-Sent Events (one-way, simpler). 
- **Service → service (decoupled, durable):** a message broker / pub-sub (e.g. Kafka, NATS, Rabbit, Redis Streams) — choose by the delivery guarantee you need (at-least-once, ordering, durability, replay).
- **External source → your system:** webhooks (with signature verification + an idempotent, fast-ack handler).

## When pull is the JUSTIFIED exception (record it in the ADR)

Polling is acceptable — and sometimes correct — when **all** of these hold, and the reason is written down:

- The consumer's perceptual/business resolution is coarse enough that poll-interval latency is invisible (e.g. a status dashboard a human reads every 1–2 s), **and**
- the push infrastructure (connection registry, reconnect, heartbeat, ordering, delivery guarantees) is **not justified by the tier / scale / budget** (a lightweight PoC, a single small dashboard), **or**
- the source simply **cannot push** (a third-party with no webhook/stream), **or**
- the interaction is plain request/response with no ongoing change to deliver.

A justified poll still bounds itself: a sane interval, conditional requests (ETag / `If-Modified-Since` / a `since` cursor) so it isn't re-fetching everything, and it respects `resilience` (timeouts, backoff).

## Anti-patterns to DETECT (and the fix to PROPOSE)

- **Polling chosen as the default with no justification** → propose the push mechanism for the layer, or require the ADR to record why pull is the exception (coarse resolution + tier/budget).
- **A tight poll loop on a low-change resource** → propose push, or at minimum a longer interval + conditional fetch (`since`/ETag).
- **Polling a source that already offers a webhook/stream** → propose consuming the push channel.
- **Service-to-service coupling via periodic DB/API polling** → propose a broker / pub-sub for decoupling + durability.
- **"Real-time"/"live" in the requirement implemented as polling** → propose WebSocket/SSE and flag the mismatch.
- **A webhook handler that does heavy work before acking** → propose fast-ack + enqueue (and signature verification).

## Review checklist

- [ ] Every cross-component data/change flow uses push unless pull is justified in the ADR.
- [ ] The push mechanism matches the layer (WS/SSE for UI; broker for service-to-service; webhook for external).
- [ ] Any polling has a recorded justification (coarse resolution + tier/budget) and is bounded (interval + conditional fetch + backoff).
- [ ] "Real-time/live" requirements are served by push, not polling.
- [ ] Webhook handlers verify signatures and fast-ack.
