# Harness Studio — CLI Reference

> The CLI is the engine: it holds the project state and drives the workflow. Long name: **`harness-sd`**. Short alias: **`hssd`**. Examples below use `hssd`.
> Every command maps to a framework concept; nothing here is generic flexibility (per `PHILOSOPHY.md`). The reference below tracks the implemented surface in `cli/hssd.py` — run `hssd <cmd> --help` for the exact flags.

## The canonical lifecycle (how the project moves)

A project advances through a **state machine** — `hssd status` always shows where you are and the single next command. Nothing engineers before the architecture is locked.

```bash
# 1. Start a project (governance from minute zero: ADR + AI log, .harness/ PM spine, git on main)
hssd new my-service
hssd new my-service --from=https://github.com/org/template.git   # start from a template repo (git URL)
#    or adopt an EXISTING repo, non-destructively:
hssd init                                                         # turn hssd ON in the current repo
cd my-service

# 2. Register the project brief (the project-level intake)
hssd overview add specs/overview.md

# 3. Architect the SHARED design, then LOCK it (the human architecture gate)
hssd overview architect            # propose docs/ADR.md (data model, ownership, tier); an adversary advises
hssd architecture approve          # LOCK it as an immutable snapshot docs/adr/ADR-vN.md (unlocks analyze/split/engage)

# 4. Decompose the brief into the product backlog (requires the lock — stories inherit the ADR)
hssd overview analyze              # save the plan (review it), then:
hssd overview split                # create the work items
#    one-shot: hssd overview analyze --split-concerns   (analyze AND create, skips the review gate)

# 5. Open a sprint and deliver its stories
hssd sprint plan --goal "first slice"   # pull unassigned backlog items into a bounded sprint
hssd work list                          # the work items (via the PM Port)
hssd work claim LOC-1                    # atomic claim + feature branch (branch-as-lock)
hssd engage LOC-1                        # run the 6-phase engagement loop (engage auto-claims if needed)

# 6. Close the loop — the project stays operational forever; sprints terminate
hssd sprint review                 # fix-the-harness retro: every escaped defect becomes a new guard
hssd sprint close                  # increment shipped; open the next round with `hssd sprint plan`

# 7. Keep the framework current
hssd update                        # self-update (git pull); `hssd update --check` just prints the version
```

## Engage — the 6-phase loop

```bash
hssd engage <id> [--auto] [--force] [--max-iter N] [--no-security] \
                 [--answers <file>] [--accept-recommended] [--test-cmd "<cmd>"] \
                 [--max-calls N] [--budget USD]
```

- `--accept-recommended` — on a blocked intake/AC/architecture gate, auto-take the adversary's recommended resolution and retry (graduated autonomy; loop-forward).
- `--answers <file>` — record the Engagement Lead's resolutions to a blocked gate (kept as ADR assumptions and reused on re-run, so agents stop re-raising them).
- `--test-cmd` — the command the TDD gate runs for red/green evidence (default: `uv run pytest`).
- `--max-calls` (default **40**) / `--budget` — hard ceilings so a run never loops forever / burns tokens. State is saved; resume with `hssd engage <id>` or clear with `hssd reset <id>`.
- `--no-security` — skip the Security/Attack Adversary (non-API/auth work only; it is mandatory otherwise, STANDARDS §2).
- `--auto` — auto-approve the human gates (testing only).

## Templates, work & logs

```bash
# Templates are separate git repos (see TEMPLATES.md)
hssd template list                                    # blessed catalog + your registered ones
hssd template import --from=<git-url> [--into <dir>]  # compose into a project (additive merge)
hssd template add --name <n> --from=<git-url> [--tech py,fastapi]   # register one YOU trust
hssd template rm  --name <n>                          # remove one of yours (blessed ones aren't removable)

# Work items (PM Port — local SQLite spine by default)
hssd work add --title "..." [--type feature]
hssd work list [--status open]
hssd work show <id>
hssd work claim <id> [--as <who>]
hssd work done <id>          # mark delivered (the maestro runner uses this; `engage` sets it itself)

# Re-run / reset
hssd reset <id>              # one item → open + clear its engagement state
hssd reset --all            # every engineered item → open (config stays enabled)
hssd reset --backlog        # wipe work items + plan + engagement state (re-split from the brief)
hssd reset --hard           # like --backlog, and also clear logs/metrics (fresh cost baseline)

# Discovery, logs & analytics
hssd janitor                # discovery heartbeat: audit → dedup by fingerprint → file work items
hssd sync                   # re-sync .claude/ (agents, skills, commands) from the framework (overwrites)
hssd log [--verbose]        # session/activity audit trail (feeds the AI Interaction Log)
hssd stats                  # dev-time, token & cost analytics from .harness/logs/metrics.jsonl
hssd ailog                  # render docs/AI_LOG.md (auto Summary + Appendix; human sections preserved)
```

## Command → concept map

| Command | Concept it realizes |
|---|---|
| `new` | scaffold + governance day-zero (STANDARDS §3) |
| `new --from=<url>` | start from an external template (git URL) |
| `init` | adopt an existing repo (non-destructive, idempotent) |
| `status` | the project state machine (initialized → … → operational) + the next command |
| `overview add` | project-level intake artifact |
| `overview architect` | propose the SHARED architecture (the ADR every story inherits) |
| `architecture approve` | the **human architecture gate** — lock the ADR as a version |
| `overview analyze` / `split` | decompose the brief into work items (after the lock) |
| `sprint plan/status/review/close` | the bounded delivery iteration (the project never ends; sprints do) |
| `work claim` | claiming — branch-as-lock + assignment (WORK-INTAKE) |
| `engage` | the 6-phase SOP (PROCESS-GATES-DOD), enforced TDD + 5-checker P4 |
| `janitor` | discovery heartbeat → deduped work items |
| `template import/add/rm/list` | compose / register external templates (additive merge + conflict resolution) |
| `reset` | re-run a single item, all items, or the whole backlog |
| `log` / `stats` / `ailog` | audit trail · cost analytics · the AI Interaction Log deliverable |
| `update` | self-update ("fix the harness, not the code" → everyone benefits) |

## Decisions / notes

- **No `--no-pm`.** The local SQLite PM spine is **non-negotiable** — the laws are *no project without PM* and *no work without a work item* (WORK-INTAKE). The default is already **local-only** (no external platform), so "no PM at all" is never offered. *(Architecture Adversary call: convenience that breaks an invariant is rejected.)*
- **Architecture-first.** `analyze`, `split`, and `engage` are blocked until `hssd architecture approve` locks the ADR — stories must inherit a defined data model, not plan against an undefined one.
- **CLI names (final):** `harness-sd` (long) / `hssd` (short).
- Blessed commands live conceptually under `commands/`; new needs are met by **adding a command**, never by piling flags on an existing one (PHILOSOPHY).

## Planned (not yet implemented)

These appear on the roadmap (`proposals/`) and are **not** in the CLI today:

- `hssd pm add --source=<github|gitlab|azure>` — attach a robust PM as a sync adapter (flips the local store canonical → cache). Credentials would be stored in a secure local store / env, never committed.
- `hssd vscode setup` — write `.vscode/` config recommending existing extensions (Ruff, Python, ESLint…), no custom plugin.
- Native Claude-Code subagent backend + the runtime-execution gate.
