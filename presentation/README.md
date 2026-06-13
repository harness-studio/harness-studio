# Presentation materials

Explainer materials for Harness Studio — for an engineering audience, dark theme.
Generated from the framework docs; kept here, versioned with the project.

## Binary assets (design files)

| File | What it is | Status |
|---|---|---|
| `Harness-Studio-Infographic.png` / `.pdf` | One-page system map: project state machine + operational cycle + engineering loop + human gates | **Needs update** — see `infographic-update-brief.md` |
| `Harness-Studio-Overview.pptx` | Slide deck: the framework, the roles, the loop, the scaling model | **Needs recreation** — use `deck-framework-overview.md` as source |
| `The-New-Role-of-the-Software-Engineer.docx` | Short document on the shift from code author to engagement lead | **Needs update** — role shift content is still valid; update terminology |

## Markdown sources (canonical content)

| File | What it is |
|---|---|
| `infographic-state-machine.md` | Content brief + Mermaid diagram for the state machine infographic |
| `infographic-operational-loop.md` | Content brief + Mermaid diagram for the operational loop infographic |
| `infographic-update-brief.md` | Section-by-section diff: what changes in the existing PNG/PDF |
| `deck-framework-overview.md` | Full slide deck source — 14 slides, Marp-compatible markdown |
| `deck-use-cases.md` | Use cases slide deck source — 13 slides, 6 real-world scenarios |

## What changed from the previous version

The framework model was redesigned. Key differences:

| Old model | New model |
|---|---|
| `briefed` state | Replaced by `identified` — project.md is a distinct artifact from the brief |
| No project identity document | `project.md` — vision, objectives, non-goals, principles (human-approved) |
| `overview add` one-time brief | `hssd intake` — recurring, any form, any time |
| Sprint as primary delivery unit | Iteration as primary delivery unit (scope-bounded, not time-boxed) |
| One story at a time | Variadic activation: `hssd iteration activate id1 id2 ... idN` |
| No parallel execution model | Fleet mode: N parallel iterations, N worktrees, caller orchestrates |
| No explicit adopt path | `hssd adopt` for existing projects |
| 3 human gates | 4 human gates: Project Approve · Architecture Lock · Spec Lock · Merge |

## Updating the infographic

See `infographic-update-brief.md` for the complete section-by-section change guide.

The design language (dark theme, three-layer layout, color coding, monospace font) stays the same.
The structure (foundation layer → operational cycle → engine) stays the same.
The content updates are surgical — the brief maps every panel to its new content.

## Rendering the markdown decks

The `deck-*.md` files are [Marp](https://marp.app/)-compatible. To render:

```bash
# Install Marp CLI
npm install -g @marp-team/marp-cli

# Export to PDF
marp deck-framework-overview.md --pdf

# Export to PPTX
marp deck-framework-overview.md --pptx

# Preview in browser
marp deck-framework-overview.md --preview
```

Mermaid diagrams in the infographic sources render natively on GitHub and via [mermaid.live](https://mermaid.live) for export to PNG/SVG.
