# Workflows — the SOP, runnable on Archon

These are the Harness Studio process encoded as **Archon workflows** (the deterministic engine layer). The framework (roles/skills/gates) is the opinion; Archon executes it.

## `engagement.yaml`
The 6-phase SOP for one work item: intake → stories/AC → architecture (**Spec Lock**) → build → adversarial verification → integration. Maps directly to `02-PROCESS-GATES-DOD.md`.

- **Agents** = the role cards in `01-ROLES.md` (subagent definitions).
- **Gates** = `bash` nodes (computational) + `interactive` nodes (human: Spec Lock, merge).
- **Spec Lock** = the hard gate; **no code before it** (spec-driven design, STANDARDS §1).
- **P4** is an adversarial fan-out (verifier + completion challenger + security + test + regression), `on_blockers: goto` for **loop-until-dry**.
- `synthesize` and `open-pr` are light coordinator steps (the Lead or a light agent).

## Mechanism mapping (see ARCHITECTURE.md)
- **P4 adversarial debate** → best as **agent teams** (interactive, peer-to-peer).
- **Everything else / unattended** → **subagents driven by Archon**.

## Lanes (right-sizing)
- **fast:** skip `design`/`spec-lock` ceremony and most P4 adversaries; keep verifier + completion-challenge + the suite. (Trivial, low-risk work.)
- **standard / deliberate:** the full workflow above; deliberate adds heavier review + human at more gates.

## Status
Illustrative/declarative. Field names follow Archon conventions; confirm the exact schema against the installed Archon version before running. `janitor.yaml` (scheduled codebase-health audit) is the planned companion.
