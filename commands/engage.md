---
description: Run the 6-phase Harness Studio engagement on a work item
argument-hint: <work-item-id>
---
Work item: $ARGUMENTS

If empty, run `hssd work list` first and ask me which item to engage.

Otherwise run `hssd engage $ARGUMENTS`. This runs the 6 phases (intake → stories & acceptance criteria → architecture → build → adversarial verification) and **stops at the human gates** (Spec Lock — no code before it — and merge). Wait for my approval at each gate; never bypass them. The maker never grades its own "done" — the adversarial roles do.
