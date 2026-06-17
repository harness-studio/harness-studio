---
description: Run the 6-phase Harness Studio engagement on a work item (MAESTRO mode)
argument-hint: <work-item-id>
---
Work item: $ARGUMENTS

If empty, run `hssd work list` first and ask me which item to engage.

Run the 6 phases as native subagents (MAESTRO mode — do NOT call `hssd engage`, that is the headless runner):

1. `hssd work claim <id>` — atomic claim + feature branch.
2. **P0** product-analyst subagent → definition-skeptic subagent (gate). On BLOCK, surface findings + recommended to me, record my resolution in `.harness/engagements/<id>/assumptions.md`, re-run.
3. **P1** story-writer subagent → ac-adversary subagent (gate).
4. **P2** architect subagent (story design, no code) → architecture-adversary subagent (gate).
5. **◆ SPEC LOCK** — summarize the locked spec and accumulated assumptions, then **ask me to approve before any code**.
6. **P3a Red** — test-author subagent writes tests from the locked AC. Run them (`uv run pytest`) — they MUST fail. If they pass with no implementation, send back to test-author.
7. **P3b Green** — backend-dev / frontend-dev subagents implement. Run tests until green.
8. **P4 Verify (loop-until-dry)** — security-adversary, independent-verifier, completion-challenger, test-adversary, regression-hunter. Any BLOCK → back to P3b. Done = green AND all adversaries dry.
9. **◆ MERGE** — show me the evidence (green tests + adversary verdicts) and **ask me to approve**, then `hssd work done <id>`.

Never bypass a human gate. The maker never grades its own "done".
