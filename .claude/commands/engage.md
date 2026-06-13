---
description: Run the 6-phase Harness Studio engagement on a work item
argument-hint: <work-item-id>
---
Work item: $ARGUMENTS

If empty, run `hssd work list` first and ask me which item to engage.

Otherwise run `hssd engage $ARGUMENTS`. This runs the 6 phases (intake → stories & acceptance criteria → architecture → build → adversarial verification) and **stops at the human gates** (Spec Lock — no code before it — and merge). Wait for my approval at each gate; never bypass them. The maker never grades its own "done" — the adversarial roles do.

If an adversary gate **BLOCKs** with questions, surface them to me. Once I answer, write the resolutions to a file and re-run `hssd engage $ARGUMENTS --answers <file>` — the answers are recorded as the ADR's assumptions and reused so the agents don't re-raise them.
