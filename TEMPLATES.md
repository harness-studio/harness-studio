# Harness Studio — Templates & Composition

> Templates are **separate git repos**, imported by URL. This unifies behavior (built-in vs external are both "just a git repo") and gives infinite extensibility — the philosophy's "extend by adding, not configuring". The hard part is **composition**: when two templates touch the same files. This document defines the merge model.

## Templates are git repos

```bash
hssd new --from=git@github.com:hssd/hssd-sample-python-fastapi.git   # new project from a template
hssd template import --from=git@github.com:hssd/hssd-sample-react-vite-spa.git   # add a template to an existing project
hssd template list
```

- The official/blessed templates are just **blessed git repos** maintained by us — no special "built-in" status, and **not bundled inside this package** (the framework ships no application code). Currently: [`hssd-template-fastapi-sqlite`](https://github.com/harness-studio/hssd-template-fastapi-sqlite) and [`hssd-template-vite-react-ts`](https://github.com/harness-studio/hssd-template-vite-react-ts). The CLI resolves templates **only** via `--from=<git-url>`; `hssd template list` prints the blessed catalog.
- Anyone can publish a template repo and import it. Brought-in templates are **wrapped to conform** to the governance files (ADR, AI log, pre-commit, `.harness/`) on import.

## Composition config — default is append, declare only the exceptions

**The default is additive (append / union).** Common files just combine automatically — no declaration needed (convention over configuration). A template author declares only the **deviations** from append:

| Strategy | When to declare it | Example |
|---|---|---|
| *(default)* `append` / union | never — it's the default | deps (union), `.vscode`, `.gitignore`, pre-commit hooks |
| `create-if-absent` | a file must not be overwritten | `app/main.py`, source files |
| `replace` | a file must be overwritten (rare; flagged to the user) | — |

**Where config lives:**
- **`template.yaml`** (in the template repo) — minimal: only the template's deviations from append + what it contributes.
- **`hssd.yaml`** (in the project — the **central config**) — anything complex, required, or project-wide: `conflict_policy`, stack tiers, enabled skills/roles, complexity thresholds, the imported-template list, required settings. Prefer `hssd.yaml`; keep `template.yaml` tiny.
- **`.harness/`** (gitignored) — runtime state only: the pm.sqlite spine, logs, ad-hoc remembered choices. Never committed config.

## The merge model

**Importing a template ≠ invalidating the previous one.** Composition combines them:

- **Non-conflicting (additive) → combine automatically.** Two templates needing different deps → the dependency set is the **union**. `.vscode` recommendations → union. `.gitignore` → union of lines. Pre-commit hooks → union. No prompt needed.
- **Conflicting (same key, different value) → ask the user.** E.g., template A sets `ruff line-length = 100`, B sets `88`; or A pins SQLAlchemy 2.0, B pins 1.4. The framework **prompts** with the conflict and the options.

## Conflict resolution (with memory, à la Claude Code)

When a real conflict appears, the prompt offers — exactly like Claude Code's permission model:

- **Use A** / **Use B** (this occurrence)
- **…for this session** (remember within the run)
- **…always** (remember in the project — written to `.harness/`)

Plus a project-level policy so the user isn't asked every time:

- `conflict_policy: prompt` (default) — ask on each genuine conflict.
- `conflict_policy: always-latest` — the most recently imported template wins (the user's "always-use-latest" idea).
- `conflict_policy: always-first` — the existing value wins.

The `conflict_policy` lives in **`hssd.yaml`** (committed project config); ad-hoc remembered choices live in `.harness/` (runtime). So repeated imports are deterministic and quiet.

## Why this is safe (and on-philosophy)

- Composition is **additive by default** — adding a template enriches, rarely breaks.
- Genuine conflicts are **explicit decisions**, never silent overwrites (escape hatches are described, not hidden).
- Every import is recorded in the **session log** (see `ARCHITECTURE.md` → Session & activity logging), so "which template changed what" is always auditable.

## Open question (flagged, not yet decided)
Cross-stack mono-repos (backend template + frontend template in one project) need a **path-scoping** convention (e.g., template targets `apps/api/` vs `apps/web/`) so their merges don't even meet. Decide the mono-repo layout convention when we build the second scaffold.
