# Harness Studio — Architecture (a framework on top of Archon)

> How Harness Studio relates to Archon, why it's a layer and not a competitor, and the planned package structure for a future `uv add` / `npm install`.

## The layering

```
┌─────────────────────────────────────────────────────────┐
│  YOUR PROJECT                                            │
│  gains: a governed dev team, adversarial QA,            │
│  auto ADR + AI-log, integrity gates, health auditor     │
└───────────────────────────┬─────────────────────────────┘
                            │  adds
                            ▼
┌─────────────────────────────────────────────────────────┐
│  HARNESS STUDIO  (this framework — opinionated)         │
│  • roles (specialists + adversaries)                    │
│  • the 6-phase engagement process + gates               │
│  • Definition-of-Done method                            │
│  • ADR / AI-log / stories templates                     │
│  • the continuous codebase-health "janitor"            │
└───────────────────────────┬─────────────────────────────┘
                            │  runs on
                            ▼
┌─────────────────────────────────────────────────────────┐
│  ARCHON  (the engine — workflow execution)              │
│  • YAML workflow runtime  • git worktree isolation      │
│  • AI / bash / loop nodes  • multi-platform adapters    │
└───────────────────────────┬─────────────────────────────┘
                            │  drives
                            ▼
┌─────────────────────────────────────────────────────────┐
│  CODING AGENT  (Claude Code / Codex / ...)              │
└─────────────────────────────────────────────────────────┘
```

**The analogy:** Archon is the engine (like Express or FastAPI). Harness Studio is the opinionated framework on top (like Nest on Express, or Rails on Ruby) — it ships the conventions, roles, and guardrails so you don't reinvent a governed process every project.

## Why a layer, not a fork

- **Archon owns execution:** deterministic workflow runtime, worktrees, node types, platform adapters. We don't reimplement any of that.
- **Harness Studio owns opinion:** *which* roles exist, *which* gates are adversarial, *what* "done" means, *how* the ADR and AI log are produced, *how* autonomy graduates. That opinion is the IP.
- **Graceful degradation:** if a user has no Archon, Harness Studio still works on plain Claude Code (subagents + hooks) or even a generic chat (orchestrator wears the hats). Archon makes it deterministic and repeatable; without it, you get the method, run by hand.

## What "super-powers" means concretely

Dropping Harness Studio into a project adds:
- A **governed engagement workflow** (idea/brief → delivery) with adversarial verification baked in.
- **Pre-built roles** (specialists + adversaries) instead of ad-hoc prompting.
- **Integrity gates** that prevent fixing one thing and breaking another (full-suite gate, lock-the-bug test, regression hunter).
- **Auto-generated governance artifacts** (ADR, AI Interaction Log) as first-class outputs.
- A **continuous codebase-health auditor** (the "janitor") that finds issues and files them as well-formed work items.

## The three agent mechanisms (and which phase uses which)

Claude Code + the Agent SDK give three distinct mechanisms. They are NOT interchangeable; Harness Studio assigns each to where it fits.

| Mechanism | Runs as | Communication | In the SDK? | Use it for |
|---|---|---|---|---|
| **Subagents** | Claude Code, within one session | report only to the parent; can't talk to each other | yes | lightweight delegation inside a phase; the automated/scheduled pipeline |
| **Agent Teams** | Claude Code, separate sessions (experimental, v2.1.32+) | peer-to-peer mailbox + shared task list; **push** notifications (lead doesn't poll) | **no** | interactive adversarial collaboration (the P4 verification debate, competing-hypothesis review) |
| **Agent SDK** | Programmatic / headless (Python/TS) | subagents only | — (it *is* the API path) | embedding the framework in your own service / true headless automation |

**Phase mapping:**
- **P4 verification (adversarial debate, multi-lens review)** → **agent teams** (interactive; teammates challenge each other directly). Not available headless.
- **Automated / scheduled paths (the janitor, Archon-driven runs)** → **subagents + Archon orchestration** (or the Agent SDK with subagents). No agent teams here.
- **Within-phase delegation** (e.g., the architect spawning a quick research helper) → **subagents**.

> Consequence: the rich peer-to-peer adversarial collaboration is an *interactive-time* capability; the deterministic, unattended pipeline relies on subagents + Archon. Design each workflow node accordingly.

## Operating modes (`hssd.yaml: type`)

`hssd` doesn't act only on the main project. **Every hssd-managed repo has an `hssd.yaml`**, and its `type` gates *which functionality is offered*:

| `type` | What hssd does |
|---|---|
| `project` (default) | **Full team mode** — the complete SOP, work items, engagements, agents, gates. hssd manages the repo as a governed team. |
| `template` | A template repo (see `TEMPLATES.md`). hssd **assists**: enforces standards, validates structure, runs gates, helps author the template — but does **not** run team/engagement orchestration. |
| *(future types)* | e.g. `library` — added as new blessed modes, never as loose flags. |

The principle: hssd is *always present* (there's always an `hssd.yaml`), but its surface scales to the repo's role. Even the template repos — and hssd's own repo — are hssd-assisted. We eat our own cooking.

## Skill routing & context management (scaling to many skills)

There will be **many skills** — tech (`python`, `fastapi`, `typescript`, ...), process (`write-adr`, `stress-test-concurrency`, ...), and domain-specific. You cannot load them all; doing so drowns the model and it gets lost. The framework + Archon solve this by **narrowing the choice *before* the LLM ever sees it** — structure does the heavy lifting; the model only does the last-mile match. Five layers, from coarse to fine:

1. **Workflow scope (Archon, deterministic).** A phase/node declares which roles and skills are in play. The LLM never picks from the full catalog — only from the phase's relevant subset.
2. **Role scope.** Each subagent's domain narrows further: `backend-dev` → `python` + `fastapi`; `frontend-dev` → `typescript`. A role only sees its slice.
3. **Description-as-router (progressive disclosure).** Only skill *descriptions* are always-on (cheap); the full `SKILL.md` body loads **only on match**. 50 skills ≠ 50 bodies in context — it's 50 one-liners and 1–3 active bodies. This is why **description discipline is load-bearing** (see `skills/SKILL-AUTHORING.md`): a vague description breaks routing.
4. **Context isolation (subagents / teams).** Each worker runs in its own context holding only its relevant skills; the orchestrator never carries everything. Clean contexts by construction.
5. **Taxonomy.** Skills are grouped (`skills/tech/`, `skills/process/`, `skills/domain/`) so selection is hierarchical, not a flat scan.

**The principle:** the model should face a *small, pre-scoped* set at any moment. Routing reliability = workflow scoping (Archon) + role scoping + good skill descriptions + isolation. Getting lost in context is a design failure of these layers, not an inevitability of having many skills.

## Execution model: worker vs trigger

Claude Code is a **worker you invoke, not a server that listens.** While a session is running it works; when it's off, nothing happens. This is the opposite of persistent daemon agents like Hermes or OpenClaw, which stay up on a server listening on a gateway (Telegram/Discord/cron) and react to incoming calls.

That difference is a feature, not a gap — it just means Harness Studio separates two concerns:

- **The worker** (does the work): Claude Code (interactive or `claude -p` headless) / the Agent SDK.
- **The trigger / availability layer** (decides *when* work starts): you (interactive), or an external mechanism — a scheduler (cron/CI), Archon's adapters (GitHub webhook, Slack, etc.), or an SDK-based service you write.

"Always-on" behavior (e.g., the Friday janitor) does **not** come from making Claude Code a daemon; it comes from a trigger that *launches* a Claude Code / SDK run, which does its job and exits. Hermes/OpenClaw bundle the listener into the agent; Harness Studio keeps worker and trigger separate (cleaner, more governable).

**"Continue from current state" = durable artifacts, not session memory.** Don't rely on in-session memory for continuity (agent teams don't even resume in-process). The durable state lives on disk: files, git, the Archon run state, the AI Interaction Log, the shared task list. You re-open, point the agent at those artifacts, and continue. State in the repository, not in the session's head — which is also what makes runs deterministic and resumable.

**For now:** Claude Code is our work environment. Runs are session-based and human-started; the trigger/availability layer is a later concern (introduced when we build the janitor and scheduled audits).

## Delivery: a separate repo, CLI + VS Code, self-updating

Harness Studio is a **separate git project**, installed and referenced — not copy-pasted into each project. The supported project stays clean and gains powers *by reference*; improvements flow in via update.

**Powers are delivered two ways:**
- **A CLI named `harness-sd`** (short alias `hssd`) — `harness-sd new <scaffold>`, `harness-sd pm-add <platform>`, `harness-sd update`, etc. (e.g. `hssd new backend-fastapi-sqlite`). The primary surface.
- **VS Code configuration** — the framework *configures* the editor; it does **not** ship a custom VS Code extension. It writes `.vscode/` (`settings.json`, `extensions.json` recommending existing best-in-class extensions — Ruff, Python, ESLint, Prettier, Tailwind, etc. — and `tasks.json`), sets up the environment, and creates files. **Harness Studio orchestrates existing tools; it doesn't reinvent the IDE.**

**Dynamic & self-updating.** The framework evolves constantly — new skills, gates, standards. It supports `harness-sd update` (optionally auto-update), versioned/pinned per project, so every supported project can pull improvements. This is the operational form of *"fix the harness, not the code"* (PHILOSOPHY tenet 9): a correction lands once in the framework repo (a new validation/skill/gate) and **every project benefits on the next update** — you fix a class of error once, everywhere, for good.

## Session & activity logging (and the free AI log)

Every framework action is recorded as a **session/activity log**: *who* (human / agent / which role), *what* (imported a template, ran `new`, changed app files, ran a gate, claimed a work item), *when*, and the *result*. This is the project's audit trail — and the key insight: **it gives the AI Interaction Log for free**, because the AI's actions are just a subset of the logged activity. (The graded AI log is then a filtered, narrated view of the session log.)

**Levels:**
- `default` — key actions + errors (always on).
- `verbose` — every action (opt-in; for deep monitoring/debugging).

**Storage (kept out of normal commits — logs get large):**
- Local: `.harness/logs/` (gitignored). Always available.
- Remote (optional, for retention/sharing): a durable store — e.g., GitLab's generic package registry / artifacts, Git LFS, or an object store (S3). This is the long-term "lts" the operator can attach.

The session log is also what makes templates auditable ("which import changed what") and what the **surprise audit** samples. View with `hssd log` / `hssd log --verbose`.

## Planned package layout (toward `uv add` / `npm install`)

A future install would scaffold this into the host project:

```
harness-studio/                 # the package
  agents/                       # role definitions (→ .claude/agents/ or workflow nodes)
    product-analyst.md
    definition-skeptic.md
    architect.md
    architecture-adversary.md
    ... (all roles)
  workflows/                    # Archon-ready YAML
    engagement.yaml             # the 6-phase delivery process
    janitor.yaml                # the scheduled codebase-health audit
  templates/                    # ADR, AI log, stories/AC, Definition of Done
  gates/                        # reusable gate scripts (hooks, validators)
  hssd.yaml.example             # project config: roles/gates/lanes/tiers/policy (central config)
  docs/                         # the manual (this kit's 00–04, VALUE-RISK-ROI)
```

The `harness-sd` CLI (e.g. `harness-sd new`) would copy `agents/` into `.claude/agents/`, `workflows/` into `.archon/workflows/`, and `templates/` into the repo, then write a starter `hssd.yaml` (the project's central config). Today these pieces live as the documents in this folder; the packaging is the future step.

## Configuration philosophy

The package should be **opinionated but tunable**: sensible defaults (the full adversarial team, all gates) with **`hssd.yaml`** (the project's central config) to enable/disable roles, set execution lanes (fast / standard / deliberate), set stack tiers, the conflict policy, and the autonomy level per gate. Defaults favor safety; you dial down rigor for low-risk work, never the reverse by accident. (`.harness/` holds runtime state — pm.sqlite, logs, cache — not committed config.)

## Related work & layer positioning

"Harness" is becoming an overloaded word. Two adjacent bodies of work describe a **runtime control plane** for agents — a layer that governs what an agent is *allowed to do while executing*:

- **Adnan Masood — "The Agent Harness"**: a control plane for reliable, governed, economic agentic AI at enterprise scale (Context / Tools / Runtime / State / Trust / Observability planes; human-approval checkpoints; audit trails; the Model Context Protocol for tool access and Agent-to-Agent for delegation).
- **Evangelos Pappas — "Building a Secure Agentic System"**: a concrete parallel sub-agent harness where a deny-by-default control plane authorizes every spawn, tool call, and route (a Cedar policy), enforces a budget ceiling, isolates each sub-agent in a git worktree, routes by policy before price, and puts an injection-detecting proxy on the inference path. Its load-bearing rule: *the sub-agents never decide whether their own actions are allowed.*

**Where Harness Studio sits.** Those govern the **runtime / execution** layer (may this action run, on which model, within what budget). Harness Studio governs the **delivery** layer (how software is specified, built, and proven). They are complementary, not competing — and they share one principle at different layers: **the actor never judges its own action.**

| Layer | Question it answers | The principle |
|---|---|---|
| **Delivery harness** (Harness Studio) | "Is this work actually done and correct?" | maker ≠ checker — an adversary verifies |
| **Runtime control plane** (Masood / Pappas) | "Is this action allowed to run right now?" | actor ≠ authorizer — a control plane decides |

**Boundary (scope discipline, PHILOSOPHY tenets 1 & 4).** A full enterprise runtime control plane — policy-as-code engines (Cedar / OPA), data-residency / jurisdiction routing, Agent-to-Agent, multi-tenant identity — is **out of scope** for Harness Studio's core; that is a different product layer, and absorbing it would dilute the framework. What *is* in scope is hardening Harness Studio's **own** agent execution, so the framework can't (for example) drop a production database while doing its work — the failure that opens Pappas's piece. That lightweight, opt-in runtime gate is specified in [`proposals/runtime-execution-gate.md`](proposals/runtime-execution-gate.md), layered *under* the delivery process, not folded into it.

> References: Adnan Masood, *The Agent Harness* (infographic, 2026). Evangelos Pappas, *Building a Secure Agentic System*, Hyperautomation, 2026 — https://hyperautomation.substack.com/p/building-a-secure-agentic-system

## Relationship to the broader design docs

The deeper rationale lives in the project's design documents (engagement SOP, the continuous-health "esteira", the multi-agent landscape). This package is the **productized, English, installable distillation** of that thinking — the part you hand to a team.
