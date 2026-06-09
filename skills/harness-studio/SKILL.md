---
name: harness-studio
description: Operate an hssd-governed repo through the Harness Studio CLI. Use whenever the user wants to manage work items, run the engagement flow (overview/plan/build/verify), import or register project templates, generate the AI Interaction Log, or see dev-time/token/cost — drive it via the `hssd` command instead of ad-hoc git/file operations.
---

# Operating a Harness Studio (`hssd`) repo

This repository is governed by Harness Studio (it has an `hssd.yaml` and a `.harness/` directory). Do the work **through the `hssd` command-line tool** — it is the blessed, audited path: it records metrics (time/tokens/cost), enforces the engagement flow and its human gates, and keeps the project-management spine consistent. Do **not** reinvent these with ad-hoc `git clone` / file copying.

## When to reach for `hssd`

| The user wants to… | Run |
|---|---|
| turn Harness Studio on in a repo | `hssd init` |
| register the project brief | `hssd overview add <file>` |
| understand + plan (review-gated) | `hssd overview analyze` → review with the user → `hssd overview split` |
| see / add / claim work items | `hssd work list` · `hssd work add --title "…"` · `hssd work claim <id>` |
| run the 6-phase engagement on an item | `hssd engage <id>` |
| list / import / register a template | `hssd template list` · `hssd template import --from=<git-url>` · `hssd template add --name <n> --from=<git-url> --tech <a,b>` |
| find issues automatically | `hssd janitor` |
| dev-time, tokens, cost | `hssd stats` |
| render the AI Interaction Log | `hssd ailog` |
| the raw activity log | `hssd log` |

## Rules

- **Governance is standing, not an end task.** The AI Interaction Log and the ADR are continuous: run `hssd ailog` anytime to (re)render `docs/AI_LOG.md` from the session metrics — never reconstruct it at the end.
- **No code before Spec Lock** (end of architecture). `hssd engage` stops at the human gates (Spec Lock, merge) — respect them.
- **Maker ≠ checker.** Whoever builds never certifies its own "done"; the adversarial roles in `.claude/agents/` do.
- **Mechanical vs AI commands.** `init`, `work`, `template`, `stats`, `log`, `ailog` are instant and free — run them directly. `overview analyze` and `engage` invoke the AI and **cost tokens** — confirm intent before running.
- **Templates: known paths, never a wall.** Any git URL works via `--from`; `hssd template add` registers one the user trusts (saved to `~/.hssd/templates.json`, shown in `hssd template list`).

## Slash-command shortcuts

These are wired into `.claude/commands/` — the user can type them, or you can follow them: `/overview [brief]`, `/work [list|claim <id>|add "<title>"]`, `/engage <id>`, `/templates [list|add-blessed]`, `/stats`, `/ailog`. They all map to the `hssd` commands above.

## Examples

- "register our blessed templates" →
  ```bash
  hssd template add --name frontend --from=https://github.com/harness-studio/hssd-template-vite-react-ts --tech react,typescript
  hssd template add --name backend  --from=https://github.com/harness-studio/hssd-template-fastapi-sqlite --tech python,fastapi
  ```
- "what's on the backlog?" → `hssd work list`
- "let's plan the project from the brief" → `hssd overview add docs/brief.md` then `hssd overview analyze` (review the plan with the user, then `hssd overview split`)
- "how much time/tokens have we spent?" → `hssd stats`
