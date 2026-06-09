# Harness Studio — CLI Reference

> The CLI is the primary surface (alongside VS Code configuration). Long name: **`harness-sd`**. Short alias: **`hssd`**. Examples below use `hssd`.
> Every command maps to a framework concept; nothing here is generic flexibility (per `PHILOSOPHY.md`).

## The canonical lifecycle (how the lib acts in a project)

```bash
# 1. Initialize a project with blessed defaults
hssd new [name]
#    Drops: local SQLite PM spine (.harness/pm.sqlite), governance files
#    (docs/ADR.md, docs/AI_LOG.md), pre-commit gate, git init on `main`
#    (protected-branch model), and .vscode/ config (existing extensions).
hssd new --from=git@github.com:org/template.git   # init from an external template repo
hssd new --template=backend-fastapi-sqlite         # init from a built-in blessed template

# 2. Configure the IDE (also run by `new`; available standalone)
hssd vscode setup
#    Writes .vscode/settings.json + extensions.json (recommends EXISTING
#    extensions — Ruff, Python, ESLint, Tailwind…), sets up the env. No custom plugin.

# 3. Register the project overview (the project-level intake artifact)
hssd overview add specs/overview.md

# 4. Analyze it → decompose into work items (the project -> backlog step)
hssd overview analyze --split-concerns
#    Runs Product Analyst + Definition Skeptic on the overview.
#    --split-concerns decomposes it into work items in the backlog.
#    Surfaces ambiguities -> they become the ADR's assumptions.

# 5. (Optional) Attach a robust PM — flips the local store canonical -> cache
hssd pm add --source=azure --api-key=<secret>      # github | gitlab | azure | trello
hssd pm status

# 6. Work loop, per work item
hssd work list                 # the backlog
hssd work claim <id>           # atomic claim + create feature branch (branch-as-lock)
hssd engage <id>               # run the 6-phase engagement under Spec Lock + gates
#    -> deliver via PR/MR linked to the work item

# 7. Keep the framework current
hssd update                    # pull framework improvements (self-update)
```

## Templates & logs

```bash
# Templates are separate git repos (see TEMPLATES.md)
hssd template import --from=git@github.com:hssd/hssd-sample-react-vite-spa.git
hssd template list
#    Composition: additive merges combine automatically (deps = union);
#    real conflicts prompt with memory (this session / always / always-latest).

# Session & activity logs (who did what; feeds the AI log for free)
hssd log                  # key actions + errors (default)
hssd log --verbose        # every action
```

## Command → concept map

| Command | Concept it realizes |
|---|---|
| `new` | scaffold/template (STANDARDS §3) + governance day-zero |
| `new --from=<url>` | external templates from a git URL |
| `vscode setup` | IDE config via existing extensions (no custom plugin) |
| `overview add` | project-level intake artifact |
| `overview analyze --split-concerns` | intake + **decomposition into work items** (scale spectrum) |
| `pm add` | PM Port sync adapter (= the MCP connector); canonical→cache flip |
| `work claim` | claiming — branch-as-lock + assignment (WORK-INTAKE) |
| `engage` | the 6-phase SOP (PROCESS-GATES-DOD) |
| `template import` | compose an external template (additive merge + conflict resolution) |
| `log` | session/activity audit trail (feeds the AI Interaction Log) |
| `update` | self-update ("fix the harness, not the code" → everyone benefits) |

## Decisions / notes

- **No `--no-pm`.** The local SQLite PM spine is **non-negotiable** — the laws are *no project without PM* and *no work without a work item* (WORK-INTAKE). The default is already **local-only** (no external platform); `pm add` upgrades to a shared robust PM. "No PM at all" would break traceability, so it isn't offered. *(Architecture Adversary call: convenience that breaks an invariant is rejected.)*
- **Credentials are never committed.** `pm add --api-key` stores the secret in a secure local store / env, never in code, logs, or git (security-first; enforced by the secret-scan gate).
- **CLI names (final):** `harness-sd` (long) / `hssd` (short).
- Blessed commands live conceptually under `commands/`; new needs are met by **adding a command**, never by piling flags on an existing one (PHILOSOPHY).
