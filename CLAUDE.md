# CLAUDE.md — governed by Harness Studio (hssd)

This project runs a governed, adversarial process. **Whoever builds never grades their own "done."**
The roles live in `.claude/agents/`; the blessed conventions in `.claude/skills/`.

Non-negotiables:
- **Spec-driven:** no code before the spec/ADR is locked (Spec Lock, end of architecture).
- **Evidence over assertion:** "done" means test output, a diff, or a screenshot — never a claim.
- **Maker != checker:** the author never certifies its own work; an independent adversary tries to break it.
- **Governance is standing, not an end task:** the AI Interaction Log is captured *continuously from the
  first interaction* (run `hssd ailog` anytime to render `docs/AI_LOG.md` from the session metrics); the
  ADR (`docs/ADR.md`) is assembled across phases. Never reconstruct them at the end.

Engagement loop: P0 Intake -> P1 Stories & Acceptance Criteria -> P2 Architecture -> [Spec Lock]
-> P3 Build (test-first: red -> green) -> P4 adversarial verification (loop-until-dry) -> [Merge].

Two runners over one state spine (`.harness/`):
- **Interactive: you are the MAESTRO.** Drive the loop through the `harness-studio` skill — run each
  role (product-analyst, definition-skeptic, story-writer, ac-adversary, architect, test-author,
  backend-dev, the P4 adversaries...) as a **native subagent**, and call the `hssd` CLI only for
  STATE: `hssd status`, `hssd work claim|done <id>`, `hssd architecture approve`, `hssd sprint ...`,
  `hssd overview split`, `hssd ailog`. Honor the human gates (Spec Lock, Merge) conversationally.
  Do **NOT** run `hssd engage`, `hssd overview architect`, or `hssd overview analyze` interactively —
  those are the *headless* runner and will nest a second Claude inside you (slow, not streamed).
- **Headless / CI:** `hssd engage <id> --accept-recommended [--budget N]` runs the same roles + gates
  unattended via `claude -p`. Run it in a real terminal (the human gates need a TTY).

Python: always use **uv** (`uv run pytest`, `uv add`) — never bare `python`/`pip`/`pytest`.

Framework: https://github.com/harness-studio/harness-studio
