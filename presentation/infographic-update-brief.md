# Infographic Update Brief

Existing file: `Harness-Studio-Infographic.png` / `.pdf`
Design: dark theme, three-layer layout, color-coded sections — keep the design language.
This brief describes exactly what changes and what stays the same.

---

## What stays the same

- Dark background, monospace font, color legend system
- Three-layer vertical structure (foundation → operational cycle → engine)
- Bottom four-panel strip (concepts row)
- Three human gates at the bottom: `Architecture Lock · Spec Lock · Merge`
- P4 adversarial fan-out structure (Independent Verifier, Completion Challenger, Regression Hunter, Test/Concurrency)
- Maker ≠ Checker panel

---

## Section 1 — PROJECT STATE BAR (top right)

**Current:**
```
initialized → briefed → architected → planned → operational
```

**New:**
```
not_initialized → initialized → identified → architected → operational
```

Color coding remains the same (blue dots for foundation states, green for operational).

---

## Section 2 — FOUNDATION (top layer)

**Current label:** `FOUNDATION — ONCE`
**New label:** `FOUNDATION — ONCE (per project)`

**Current flow:**
```
Brief → Architect → Adversary → [Human: Architecture Lock] → Product Backlog → split into stories
```

**New flow:**
```
[NEW PROJECT]                     [EXISTING PROJECT]
hssd init                         hssd adopt
    │                                 │
    ▼                                 ▼
Brief / goals              Read codebase + infer
    │                                 │
    └──────────────┬──────────────────┘
                   ▼
           project.md draft
           (vision · objectives · non-goals · principles)
                   │
           [Human: Project Approve] ← NEW human gate label
                   │
                   ▼
           Architect → ADR draft
           Adversary → challenges
                   │
           [Human: Architecture Lock]  ← existing gate, keep
                   │
                   ▼
           PROJECT READY FOR INTAKES
```

Key changes:
- Add `project.md` step before architect
- Add `[Human: Project Approve]` gate (new, 4th human gate total)
- Show two entry paths (new project / existing project) merging at `project.md`
- Remove "Product Backlog" from foundation — backlog is populated by intakes, not by foundation

---

## Section 3 — OPERATIONAL CYCLE (middle layer)

**Current label:** `SPRINT LOOP — REPEATS ∞`
**New label:** `OPERATIONAL CYCLE — REPEATS ∞`

**Current flow:**
```
Plan → Engage each story → Review → Close
```

**New flow:**
```
INTAKE  →  ITERATION PLANNING  →  ACTIVATE  →  CONVERGE  →  (repeat)
  │              │                    │              │
  │         pick stories         1 id = 1        worktrees
  │         assign to            N ids = N       merge to
  │         iterations           parallel        main
  │
  ↑── JANITOR (continuous) ──────────────────────────────────┐
      scans: drift · debt · latent bugs                      │
      files new intakes automatically                        │
      ────────────────────────────────────────────────────────┘
```

Inside INTAKE (expand as sub-steps):
```
  1. Grooming:  Product Analyst + Definition Skeptic
  2. Arch lite: Architect + Adversary (inherits ADR)
  3. Split:     Story Writer → stories in backlog
```

Key changes:
- "Plan / Engage / Review / Close" → "Intake / Planning / Activate / Converge"
- Add JANITOR as a side element feeding INTAKE
- Show variadic activation: 1 id → 1 process, N ids → N parallel
- Show that multiple iterations can run simultaneously (show 2 parallel tracks)

---

## Section 4 — INSIDE THE ENGINE (bottom layer, the 6-phase loop)

**Current label:** `INSIDE "ENGAGE" — THE 6-PHASE ENGAGEMENT LOOP (the engine)`
**New label:** `INSIDE AN ITERATION — THE ENGINEERING LOOP (per story)`

**Current flow:**
```
P0 Intake → P1 Stories & AC → P2 Architecture → [Human: Spec Lock] → P3 Build (red→green) → P4 Verify → [Human: Merge]
```

**New flow:** Same structure, minor label updates:

| Phase | Current label | New label |
|---|---|---|
| P0 | "frame the story" | "understand the story · surface assumptions" |
| P1 | "what 'done' means" | "write verifiable AC · ac-adversary validates" |
| P2 | "design the story" | "design implementation · skills applied here" |
| Spec Lock | same | same |
| P3 | "test-author writes failing tests from locked AC, the builder makes them green — both kept as evidence" | same content, add: "red log committed before implementation" |
| P4 | same fan-out | add: `security-adversary` explicitly (currently implied) |
| Merge | same | same |

---

## Section 5 — BOTTOM CONCEPT PANELS (four panels)

**Current panels:**
1. Maker ≠ Checker
2. Skills that find & propose
3. Fix the harness, not the code
4. .harness/ — durable memory

**New panels (same 4 slots):**

**Panel 1 — Maker ≠ Checker** (keep, no changes)
> "The builder never certifies its own work; an independent adversary tries to break it. Every role runs in its own context."

**Panel 2 — Project Identity** (replace "Skills that find & propose")
> "project.md anchors everything. Intakes are validated against it. Architecture inherits from it. The janitor uses it to prioritize findings. It changes rarely — identity is not a sprint goal."

**Panel 3 — Fix the harness, not the code** (keep, no changes)
> "Every escaped defect becomes a new guard; the same bug can never return."

**Panel 4 — .harness/ — durable memory** (keep, update text)
> "On-disk project spine: decisions, logs & evidence. The AI interaction log is captured continuously — not reconstructed at the end. Every intake, every verdict, every assumption is traceable."

---

## Human gates (footer strip)

**Current:** `Three human gates: Architecture Lock · Spec Lock · Merge`

**New:** `Four human gates: Project Approve · Architecture Lock · Spec Lock · Merge`

---

## Color legend (top right)

**Current:**
- Blue = Foundation (once)
- Green = Sprint loop (∞)
- Orange = Engagement phases
- ◆ = Human gate

**New:**
- Blue = Foundation (once)
- Green = Operational cycle (∞)
- Orange = Engineering loop phases
- Teal/Cyan = Intake cycle (new color for the intake sub-cycle)
- ◆ = Human gate

---

## New element: Parallel iterations callout

Add a small callout panel in the ACTIVATE step of the operational cycle showing:

```
  hssd iteration activate id1           → 1 process
  hssd iteration activate id1 id2 id3   → 3 parallel
  hssd iteration activate id1 ... id20  → fleet mode
```

This is the key scaling insight and should be visually highlighted.
