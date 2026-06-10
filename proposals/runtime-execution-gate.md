# Proposal — Runtime execution gate for the agent runner

> **Status: PROPOSED** (awaiting Spec Lock — no code before a human approves this; PHILOSOPHY tenet via STANDARDS §1).
> This document eats our own cooking: it records the **Architect's proposal**, the **Architecture Adversary's challenge**, and the resolution — the same P2 tension every engagement goes through. See [`ARCHITECTURE.md` → Related work & layer positioning](../ARCHITECTURE.md).

## 1. Context & problem

Harness Studio *runs* agents: the role runner (`_run_role`), the janitor loop, and the engage loop launch agents that — on the `claude` backend — can touch the repository and the shell (read, write, `bash`, git). Today the framework governs the **delivery process** (maker ≠ checker, gates, Spec Lock) but does **not** govern what those agents are *allowed to do while executing*.

The failure mode this leaves open is concrete. Pappas opens with a coding agent that, told to "tidy a database", dropped the production database and every backup in one API call — *"nothing sat between that judgment and the database to ask whether the judgment was allowed to run."* The same gap exists here once an agent has real tool access. Two specifics:

- **Tool allowlists are declared but not enforced.** Each role's frontmatter names its tools (`backend-dev` → `Read, Edit, Write, Bash, Grep, Glob`; adversaries → `Read, Bash, ...`), but nothing *binds* that list at execution time. A role can reach for a tool it was never granted.
- **Budget is a guideline, not a gate.** The Engagement Lead "holds the budget", but an unattended janitor or engage run has no hard ceiling that *denies* the next step.

This is squarely a *"fix the harness, not the code"* (tenet 9) and *graduated-autonomy* concern: earned autonomy is only safe if a runtime layer can say **no** before an action runs — not just a human at the process gates.

## 2. Architect's proposal

Add a thin **execution gate** between an agent's decision and the tool that runs it — a control plane in the runner, deny-by-default, reusing primitives we already have.

1. **Enforce per-role tool allowlists at the boundary.** The runner binds the role's declared `tools` to the backend's *native* permission mechanism (Claude Code `allowedTools` / `disallowedTools` and the `PreToolUse` hook), so an ungranted tool simply cannot fire. The frontmatter stops being documentation and becomes policy.
2. **Deny-by-default on destructive actions.** A small, named denylist for irreversible operations (e.g. `rm -rf`, `DROP`/`TRUNCATE`, `git push --force`, secret exfiltration) enforced at the same hook. Default deny; an allow is explicit and logged.
3. **A real budget/step ceiling.** A counter the runner reads-and-decrements per step; over the ceiling, the next action is **denied** (not a warning). On the `claude` backend, drive it from real token/cost usage where the backend exposes it; otherwise fall back to a step count.
4. **Named-reason denials.** A denial returns the rule that fired (reuse the existing `{verdict, reason}` shape), and the reason is handed back to the model — exactly like the adversary verdicts.
5. **Reversible isolation for write-capable roles.** Run write/`bash` roles in a git worktree, so a bad action is reverted, not lived with.
6. **Audit every decision** to the existing session log (`.harness/logs/`). The surprise audit already samples this log.
7. **Lightweight policy, no heavy dependency in v1.** Policy lives as a small declarative block in `hssd.yaml` (allowlists, ceilings, the destructive denylist) — *not* a Cedar/OPA engine yet. Defaults favor safety; the Lead dials rigor down for low-risk lanes, never up by accident.

**Alternatives considered:**
- *Adopt Cedar/OPA now* — rejected for v1: a policy-as-code engine is the right shape at enterprise/multi-tenant scale (Pappas), but it is a heavy dependency and enterprise-shaped surface that would dilute a delivery framework's core (tenets 1 & 4). Keep the *pattern* (deny-by-default, named reasons), defer the engine.
- *Rely on the human gates only* — rejected: Spec Lock and Merge govern the *process*, not the *execution*. They don't sit between an agent's judgment and `bash` during an unattended run — which is exactly where the DB-drop happens.
- *Do nothing* — rejected: acceptable only while agents are read-only; a real risk the moment the runner has write/`bash`.

## 3. Architecture Adversary's challenge

*(Rewarded for finding the weak point, not for approving.)*

- **A destructive-verb denylist is theater.** String-matching `rm`/`DROP` is trivially bypassed: `python -c "import os,shutil; shutil.rmtree(...)"`, a base64'd command, an `&&` chain, an MCP tool that deletes. **If the gate is a regex over command strings, it provides false confidence — worse than nothing.** Enforcement must live at the *permission/tool boundary*, not in pattern-matching the payload.
- **"Enforce the allowlist" assumes the runner mediates tool calls.** Does it? If the backend is `claude -p`, the framework must use Claude Code's *own* permission system (allowed/disallowed tools + `PreToolUse` hook with deny) — a homegrown wrapper that shells out can be side-stepped. The proposal must name the exact enforcement point or it's a wish.
- **Budget from "step count" is a poor proxy.** A single step can spend wildly (long context, a huge tool result). The ceiling must read *real* usage from the backend; a step counter will both over- and under-shoot. And the counter must be atomic if the janitor ever fans out (Pappas: read-and-spend with no `await` between, single loop — or an atomic store for multi-process).
- **Deny-by-default breaks legitimate work if allowlists are wrong.** Too tight and every run stalls on denials; the Lead disables the gate out of frustration → security theater again. Needs *good role defaults*, a visible **Lead override that is explicit and audited** (not a silent global off-switch), and a fast feedback loop on false denials.
- **Worktree-per-agent isn't free.** Cheap at a few agents, a serialized cost at scale (Pappas notes the same; a filesystem overlay or container wins at sixty). Fine for v1, but don't claim it scales unqualified.
- **Scope creep risk.** Every item here edges toward rebuilding a runtime control plane. The adversary's job is to hold the line: ship only what hardens *our own* execution; anything tenant/residency/A2A-shaped is out.

## 4. Resolution (what survives the challenge)

The denylist-as-regex idea is **rejected as a primary control**; the gate is redefined to sit at the permission boundary:

- **v1 enforcement = the backend's native permission layer.** Bind each role's frontmatter `tools` to Claude Code `allowedTools`/`disallowedTools`; deny everything else; add a `PreToolUse` hook that can veto a call with a named reason. No regex-over-strings as the load-bearing control (a destructive-name check may exist only as a *secondary* signal, never the gate).
- **Budget ceiling reads real usage** from the backend when available; the step counter is a *fallback* with that limitation documented. Single-loop atomic now; an atomic store is a prerequisite *before* any multi-process fan-out.
- **Lead override is a first-class, audited action** (graduated autonomy), never a silent global disable.
- **Worktree isolation for write/`bash` roles**, with the scaling caveat recorded.
- **Policy in `hssd.yaml`, declarative, no Cedar/OPA dependency in v1.** The deny-by-default + named-reason *pattern* is adopted; the engine is deferred and explicitly out of core scope.

**Open questions (for Spec Lock):**
1. Exactly which `PreToolUse` / permission hooks does the installed Claude Code expose, and can a hook *deny* with a message the model reads back? (Verify against the version before relying on it — same caveat as `LOOPS.md`.)
2. Does the chosen backend report per-step token/cost for a real budget ceiling, or only end-of-run totals?
3. Where do destructive-operation defaults live so they're shared across projects but overridable per repo?
4. MCP tools: how are *their* capabilities allowlisted (they aren't in the frontmatter `tools` list today)?

**Decision:** none yet — this stays **PROPOSED**. Per our own rule, no code is written before a human grants Spec Lock on this spec. When approved, it becomes a work item and runs through the normal engagement (build → P4 adversarial verification, including the Security/Attack Adversary turned on *its own* gate).
