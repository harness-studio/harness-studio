---
description: Register an intake demand and plan an iteration via hssd
argument-hint: [path-to-brief.md]
---
Brief path: $ARGUMENTS  (if empty, ask me for one).

Operate via the `hssd` CLI — do not decompose work by hand.

1. `hssd intake add <brief>` — register the demand.
2. Present the intake id to me and **STOP** — ask if I want to approve it or edit the brief first.
3. Once I agree: `hssd intake approve <id>` — releases the stories to the backlog.
4. `hssd iteration plan --goal "…" --intake <id>` — plan an iteration from this intake.
5. Show me `hssd work list` and **STOP** — wait for me to say which iteration to activate.
6. Only after I agree: `hssd iteration activate <id>`.
