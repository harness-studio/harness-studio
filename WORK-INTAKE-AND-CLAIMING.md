# Harness Studio — Work Intake & Claiming

> The blessed way work starts and gets coordinated. Two laws: **no project without project management**, and **no work without a tracked work item**. Traceability is the precondition for any action — if it isn't traceable, it doesn't happen.

## The concept model (platform-agnostic)

One model, multiple backends:

```
Work Item  →  Feature Branch  →  PR / MR  →  Merge
 (origin)     (named by item)   (links item)  (closes item)
```

Every step links to the previous one, so any line of code traces back to its origin. This is invariant across whatever PM/VCS platform a project uses.

## The PM Port and the canonical spine (the definitive model)

The framework's core talks to exactly **one interface — the PM Port** (create item, get, claim, transition status, link branch, list open). It **never knows which platform is behind it.** That uniformity *is* "everyone has the same behavior" — agents and workflows speak only the Port.

The **default Port implementation is the local SQLite store, and it is the canonical coordination spine — not a fallback.** The framework always reads/writes claim and status here, because a local SQLite transaction gives **truly atomic claiming on every project**, regardless of the external platform's concurrency semantics. This resolves the GitHub/GitLab TOCTOU window by design.

External platforms (GitHub / GitLab / ADO / Trello) attach as **sync adapters** layered on the spine — and **those adapters are exactly what the MCP connectors become.** So MCPs are an enhancement of the sync layer, never a core dependency.

**Field-level authority (resolves the two-master / sync-conflict problem):**
- **SQLite spine owns coordination state:** status/claim, assignee, branch link, lane, WIP. Atomic, framework-owned.
- **The platform owns the human narrative:** title, description, comments, human-facing labels. Where the team reads and collaborates.
- The sync adapter mirrors between them; conflicts are avoided because each side owns different fields.

**The adaptive role of the local store (this resolves the team question).** The local SQLite is **always the Port interface** the core talks to — but its *role* adapts to what's connected:
- **No robust PM connected →** the local SQLite is the **canonical source of truth** (spine). Perfect for solo / PoC.
- **A robust PM connected (via `harness-sd pm-add`) →** the local SQLite becomes a **consistent cache** of that external PM, which is now the shared source of truth — the answer for a multi-human team (e.g. an enterprise on GitLab). The core still speaks only the Port, so behavior is identical; reads stay local and fast; the external holds the shared truth.

**`harness-sd pm-add` (alias `hssd pm-add`) is the blessed command** to attach a robust PM: it wires the platform's MCP/connector and flips the local store from *canonical* to *cache*. It's the first of the framework's blessed commands (they live under `commands/`). Field-level authority still applies — even as a cache, the local store runs the coordination/claim semantics and syncs them outward.

## Backends (Port implementations / sync adapters)

All of these implement the same PM Port. The SQLite spine is always present; the others sync to it.

| Backend | When | Notes |
|---|---|---|
| **GitHub Issues** | Gabriel's personal projects | Issues + PRs + branches |
| **GitLab Issues** | enterprise / self-hosted teams | Issues + MRs + branches (same model, different names) |
| **Azure DevOps (via MCP)** | orgs with ADO | Work items have revision-based optimistic concurrency (best claim semantics) |
| **Trello** | quick PoC, non-dev stakeholders | Cards as work items |
| **Local SQLite mini-PM** | PoC / no platform / zero-dependency | Ships with the framework; the claim is a real SQLite transaction (atomic) |

> The local SQLite mini-PM (`.harness/pm.sqlite`) is the fallback that makes "no project without PM" always true — even a throwaway PoC gets traceability. Bonus: a local transactional claim is *more* atomic than GitHub's, where a TOCTOU window exists.

## The Work Item Schema (this kills "issues used wrong")

A work item is **not free-form text**. It has a required shape, validated at intake. Platform issue templates (GitHub `.github/ISSUE_TEMPLATE`, GitLab description templates) enforce the shape at creation; the local SQLite PM enforces it by columns.

Required fields:
- `id` — stable identifier (platform-native or local).
- `title`
- `type` — feature | bug | tech-debt | audit-finding | chore.
- `problem` — what and why (not the solution).
- `acceptance_seeds` — the obligation phrases to turn into AC in P1.
- `status` — open | in-progress | in-review | done.
- `assignee` — the worker (human or agent run) holding the claim.
- `branch` — the feature branch once claimed (the traceability link).
- `lane` — fast | standard | deliberate (from triage).

Intake validates the item against this schema before anything proceeds. A malformed item is rejected, not worked.

## Entry points

Three ways work originates — all converge to a validated work item:
1. **A platform issue/task** (GitHub/GitLab/ADO/Trello) — already an item; validate the schema.
2. **The janitor/audit** — creates items (dedup'd) automatically.
3. **Manual** ("I just want to do something here") — **not a side door**: the first step creates a work item. The common-default manual start still produces traceability. No untracked work, ever.

## Claiming (so two workers don't start the same thing)

Layered, because no single platform gives perfect distributed locking:

1. **Source of truth = the PM backend.** Claiming = assign + move to `in-progress`. Check `open` & unassigned before claiming. (Local SQLite: this is a single atomic transaction — truly race-free. ADO: revision-based compare-and-swap. GitHub/GitLab: assignment + label, with a TOCTOU window.)
2. **The branch is the durable lock + link.** Create and push `harness/<source>-<id>-<slug>` to origin. **If the branch already exists on origin, it's already claimed** — abort. Creating a new git ref is atomic, so this is the tiebreaker that closes GitHub/GitLab's window.
3. **WIP limit** caps concurrent claims (cost + aggregate blast radius).
4. **Worktree per item** lets parallel claims run without colliding on files.

**Honest bound:** on GitHub/GitLab this is "double-start caught early and cheaply" (branch conflict / assignment check), not "mathematically impossible." On the local SQLite PM and ADO it's genuinely atomic. State the guarantee at the level it actually holds.

## Git & branching model (blessed, enforced by pre-commit)

- **Never `master`.** New project → default branch is `main`. (`master` is renamed/forbidden.)
- **Protected by default:** `main`, `develop`, `homolog`. No development directly on them — ever.
- **Feature branches are mandatory** and **must link to a work item** (named by its id).
- **Pre-commit hook enforces:**
  1. Not committing on a protected branch.
  2. Branch name matches `harness/<source>-<id>-<slug>` (i.e., tied to a task).
  3. No secret/ENV leak in the diff (see Security in `STANDARDS.md`).
- **Commits are atomic and tell the story** — grouped by logical operation, readable history (detailed in `STANDARDS.md`).

## Avoiding double-work (summary)

- Claim (assign + in-progress + branch-exists) → two can't *start*.
- Janitor dedups → the same finding isn't filed twice.
- WIP limit → bounded concurrency.
- Worktree isolation → parallel claims don't corrupt each other.

## Where MCPs come in (later)

The claim/transition operations (read status, assign, move state, open PR/MR) are exactly what the **GitHub / GitLab / ADO MCP connectors** automate. For now (Claude Code as the work environment, no connectors), the local SQLite PM + `git`/`gh`/`glab` CLI cover it. Connectors are an enhancement of this layer, not a prerequisite.
