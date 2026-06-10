# Workflows — a reference encoding of the SOP

These are the Harness Studio process written down as **declarative YAML — a reference encoding of the SOP, not an executed artifact**. The loop itself is implemented and run by the `hssd` CLI (`cmd_engage` in `cli/hssd.py`). These files document the phases, agents, and gates the CLI drives; they're useful for reading the SOP at a glance and as a target shape for tooling.

## `engagement.yaml`
The 6-phase SOP for one work item: intake → stories/AC → architecture (**Spec Lock**) → build → adversarial verification → integration. Maps directly to `02-PROCESS-GATES-DOD.md`.

- **Agents** = the role cards in `01-ROLES.md` (subagent definitions).
- **Gates** = `bash` nodes (computational) + `interactive` nodes (human: Spec Lock, merge).
- **Spec Lock** = the hard gate; **no code before it** (spec-driven design, STANDARDS §1).
- **P4** is an adversarial fan-out (verifier + completion challenger + security + test + regression), `on_blockers: goto` for **loop-until-dry**.
- `synthesize` and `open-pr` are light coordinator steps (the Lead or a light agent).

## Mechanism mapping (see ARCHITECTURE.md)
- **P4 adversarial debate** → best as **agent teams** (interactive, peer-to-peer).
- **Everything else / unattended** → **subagents driven by the `hssd` CLI**.

## Lanes (right-sizing)
- **fast:** skip `design`/`spec-lock` ceremony and most P4 adversaries; keep verifier + completion-challenge + the suite. (Trivial, low-risk work.)
- **standard / deliberate:** the full workflow above; deliberate adds heavier review + human at more gates.

## Status
Illustrative/declarative — a reference encoding of the SOP, not executed. The loop lives in the `hssd` CLI; these files are documentation that mirrors what it runs. `janitor.yaml` (scheduled codebase-health audit) is the planned companion.
