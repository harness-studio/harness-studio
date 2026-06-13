---
title: Harness Studio — The Operational Loop
description: One-page infographic. The full cycle from demand to merged code, with parallel iteration model.
format: infographic (landscape poster, A3 or 16:9)
theme: dark, monospace accents
---

# The Operational Loop

## Mermaid Source

```mermaid
flowchart TD
    DEMAND["📥 DEMAND\nmanual · structured · unstructured · operational"]

    subgraph INTAKE ["INTAKE CYCLE"]
        G1["Product Analyst\ndecompose into concerns"]
        G2["Definition Skeptic\nvalidate: testable? in-scope? complete?"]
        G3["Architect (lite)\ninherits ADR · adds only what's new"]
        G4["Story Writer\nstories + acceptance criteria → backlog"]
        G1 --> G2 --> G3 --> G4
    end

    subgraph PLANNING ["ITERATION PLANNING"]
        P1["Pick stories from backlog"]
        P2["Assign to iterations\nsequence or parallel"]
        P1 --> P2
    end

    subgraph PARALLEL ["ACTIVE ITERATIONS (1 or N in parallel)"]
        subgraph ITER1 ["Iteration A"]
            E1["P0 Intake\nP1 AC\nP2 Architecture\n◆ Spec Lock"]
            E2["P3a Red\nP3b Green"]
            E3["P4 Adversarial\nverify · loop until dry\n◆ Merge"]
            E1 --> E2 --> E3
        end
        subgraph ITER2 ["Iteration B"]
            F1["P0 → P2\n◆ Spec Lock"]
            F2["P3a → P3b"]
            F3["P4 · loop until dry\n◆ Merge"]
            F1 --> F2 --> F3
        end
    end

    CONVERGE["CONVERGENCE\nworktrees merge → main\nconflicts resolved"]

    JANITOR["🔍 JANITOR\ncontinuous scan\ndrift · debt · latent bugs\n→ new intakes"]

    DEMAND --> INTAKE
    INTAKE --> PLANNING
    PLANNING --> PARALLEL
    PARALLEL --> CONVERGE
    CONVERGE -->|"next demand"| DEMAND
    JANITOR -->|"files intakes"| DEMAND
```

---

## Visual Layout Brief (for designer)

**Canvas:** 1600 × 900px landscape, dark background (#0d1117)

**Flow: left to right, 5 columns**

```
[DEMAND]  →  [INTAKE]  →  [PLANNING]  →  [ITERATIONS]  →  [CONVERGE]
                                                ↑
                                           [JANITOR]
                                         (always on)
```

---

### Column 1 — DEMAND

**Header:** "A demand arrives"
**Four intake forms as chips:**
- 📝 Manual — natural language from developer or stakeholder
- 📋 Structured — spec doc, Jira, Linear, design brief
- 🔍 Unstructured — symptoms, vague goals, contradictory requirements
- ⚙️ Operational — import lib, adopt skill, upgrade dependency

**Bottom note:** "All forms enter the same cycle. Origin does not change governance."

---

### Column 2 — INTAKE CYCLE

**Header:** "Grooming + Architecture + Split"

Three stages as vertical stack with connecting arrows:

```
  1. GROOMING
     ├── Product Analyst
     │   decompose into concerns
     │   identify assumptions
     └── Definition Skeptic
         testable? in-scope? unambiguous?
         → BLOCK if not → return to analyst

  2. ARCHITECTURE LITE
     └── Architect + Adversary
         inherits locked ADR
         adds only new decisions
         pivot? → reopen ADR (human gate)

  3. SPLIT
     └── Story Writer
         1 story = 1 clear objective
         + verifiable AC in Gherkin
         + size: small or medium only
         → stories enter backlog
```

**Gate callout:** "Out-of-scope work is rejected here, not at review time."

---

### Column 3 — ITERATION PLANNING

**Header:** "Pick. Sequence. Activate."

```
  BACKLOG
  ┌─────────────────────────┐
  │  story-A  story-B       │  ← iteration 1 (activate now)
  │  story-C  story-D       │  ← iteration 2 (activate after 1)
  │  story-E ... story-T    │  ← iteration 3 (planned, not yet)
  └─────────────────────────┘

  hssd iteration activate iter-1 iter-2
  → 2 processes, caller orchestrates
```

**Key insight callout:**
> "1 ID → 1 process. N IDs → N parallel processes. No flags, no modes."

---

### Column 4 — ACTIVE ITERATIONS

**Header:** "Each iteration runs its own full loop"

Show 2 parallel tracks side by side:

```
  ITERATION A              ITERATION B
  (worktree-A)             (worktree-B)

  P0 Intake                P0 Intake
  P1 Stories & AC          P1 Stories & AC
  P2 Architecture          P2 Architecture
  ◆ SPEC LOCK ←human       ◆ SPEC LOCK ←human
  P3a Red (fail)           P3a Red (fail)
  P3b Green (pass)         P3b Green (pass)
  P4 Adversarial ──┐       P4 Adversarial ──┐
    independent-   │         independent-   │
    verifier       │ BLOCK?   verifier       │ BLOCK?
    completion-    │ → P3b    completion-    │ → P3b
    challenger     │         challenger     │
    test-adversary │         test-adversary │
    regression-    │         regression-    │
    hunter         │         hunter         │
  ◆ MERGE ←human ◆┘       ◆ MERGE ←human ◆┘
```

**Adversary panel (sidebar):**

| Adversary | What it attacks |
|---|---|
| independent-verifier | Every AC ↔ every test |
| completion-challenger | Proves NOT done |
| test-adversary | Vacuous tests, races |
| regression-hunter | What broke? |
| security-adversary | Injection, auth, leaks |

---

### Column 5 — CONVERGENCE

**Header:** "Worktrees merge to main"

```
  iter-A merged first  → main ✓
  iter-B checks diff   → conflict? resolve → main ✓
  iter-C checks diff   → conflict? resolve → main ✓
```

**Arrow back to Column 1:** "→ next demand"

---

### Always-On Element — JANITOR (bottom strip)

```
┌─────────────────────────────────────────────────────────────────────┐
│  🔍  JANITOR  (continuous, scheduled)                               │
│  Scans: drift · debt · latent bugs · stale conventions              │
│  Deduplicates: same finding never filed twice                       │
│  Output: new operational intakes → enters Column 1                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Numbers (pull stats for the infographic)

- **2 human gates** per story (Spec Lock + Merge) — everything else is governed automatically
- **5 adversaries** in P4 — each independent, each attacking a different failure mode
- **0 self-certification** — maker ≠ checker is structural, not a guideline
- **N parallel iterations** — `hssd iteration activate id1 id2 ... idN`
- **∞ operational** — the project never finishes, it evolves

---

## Pull Quotes

> "The janitor finds the work. The intake governs it. The iteration delivers it. The adversaries verify it. The human approves it."

> "Parallel fleets of AI agents, each running the full governance loop independently, converging on a shared codebase."

> "Evidence is captured continuously — not reconstructed at the end."
