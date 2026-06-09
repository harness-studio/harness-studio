---
description: Register the project brief and produce a review-gated plan via hssd
argument-hint: [path-to-brief.md]
---
Brief path: $ARGUMENTS  (if empty, use `docs/brief.md`).

Operate via the `hssd` CLI (see the harness-studio skill) — do not decompose the work by hand.

1. Run `hssd overview add <brief>` to register the brief.
2. Run `hssd overview analyze` (this calls the AI and costs tokens) to get the understanding + the proposed work items.
3. Present the plan to me and **STOP**. Do not create tasks yet.
4. Only after I agree, run `hssd overview split` to create the work items, then `hssd work list` and show me the backlog (governance items lead — that's expected).
