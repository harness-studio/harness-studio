# Example engagement — link shortener with click analytics

> An **invented, generic** example to illustrate an engagement end-to-end. Not a real client's assignment and not part of the framework. For real work, paste your own brief into the kickoff (`../04-KICKOFF.md`).

## Brief

**Build a link-shortener service with click analytics.** A vertical slice: users create short links, visitors are redirected, and clicks are counted. Each click event is JSON with: `code`, `timestamp`, `referrer`, `user_agent`.

**Deliverables:**
1. Python backend (FastAPI or Django REST):
   1. `POST /links` to create a short link, handling concurrent creation.
   2. Persist it (SQLite or Postgres — justify).
   3. Detect anomalies in real-time (your definition — e.g. click-spike / bot bursts — justify in the ADR).
   4. Click counter: `GET /{code}` redirects and **atomically increments** that link's `click_count` by 1; **with many visitors hitting the same link in the same instant, the implementation must guarantee every click is counted**; expose `GET /links/{code}/stats`.
   5. Status update: when a link is disabled, it must be **atomically** marked disabled and an audit record created. Think about concurrent writes and correct isolation.
   6. REST endpoint for recent click events filtered by link and time range.
   7. Endpoint for aggregate stats (total clicks across all links) safe under concurrent updates.
2. React + TypeScript dashboard:
   1. Live list of links with their click counts.
   2. Most recent click per link.
   3. Polling or websockets — justify.
   4. Per-link click counts, updating live.
3. 1-page ADR: (a) 2-3 most important decisions and why; (b) what was unclear and what you assumed; (c) what would change at significant scale (you define); (d) what you deliberately left out and why.
4. AI Interaction Log (markdown): every meaningful prompt; the output (summary ok); corrections/redirections; a 3-5 bullet final reflection.

**Constraints:** budget 5-6h; ADR and AI log valued as much as the code; AI use encouraged (and the log is part of it); partial-but-documented > complete-but-undocumented; reviewers will run the code but won't penalize setup if the README is clear. Deliver as **a single git repo** with a README.

## Literal requirements → Definition-of-Done seeds (extraction, NOT solution)

Raw list of the example's "musts" for Phase 1 to convert into AC-tests. **No solutions here on purpose** — which DB, which anomaly definition, which isolation is a P2 decision (Architect↔Adversary).

- [ ] `POST /links` handles **concurrent creation** → stress test: N simultaneous creates, no collision/loss.
- [ ] Persistence works (round-trip) + **choice justified** in the ADR.
- [ ] Anomaly detection: **definition recorded in the ADR** + a test triggering each defined type.
- [ ] Click counter **guarantees every click counted** under simultaneity → test: K simultaneous hits on the same code ⇒ count == K.
- [ ] `GET /links/{code}/stats` returns correct counts.
- [ ] Disable link → **atomically** marked + audit record; **correct isolation** → transactional test with concurrent transitions + idempotency.
- [ ] Recent-clicks endpoint **filters by link and time range**.
- [ ] Aggregate stats **safe under concurrent updates** → consistency test.
- [ ] Dashboard: live list (links + counts), recent click per link, **polling/WS justified**.
- [ ] 1-page ADR answers the 4 questions.
- [ ] AI log with the 4 elements + reflection.
- [ ] README runs from scratch.

> The three **concurrency/atomicity** requirements (concurrent creates, click counter, disable→audit) are the technical heart and where reviewers look for tech-lead level. That's where the Test Adversary should spend its ammunition.
