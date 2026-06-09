# Harness Studio — Loops (loop engineering)

> **Loop engineering** = you stop prompting the agent and instead design the system that prompts it. The loop finds work, hands it out, checks it, records what's done, and decides the next thing — on a cadence, feeding itself. It sits **one floor above the harness**: the harness is the environment one agent runs in; the loop runs on a timer, spawns helpers, and feeds itself.
> Credit: Addy Osmani ("Loop Engineering"), with steipete and bcherny. *"You shouldn't be prompting coding agents anymore. You should be designing loops that prompt your agents."*

## The realization: Harness Studio already has the pieces

A loop needs five building blocks + a memory. We built all of them as we went — we just didn't call it a "loop":

| Loop piece | In Harness Studio |
|---|---|
| **1. Automations** (the heartbeat: scheduled discovery/triage) | the **janitor** (scheduled audit → dedup → files work items); `workflows/janitor.yaml` (planned) + scheduled tasks |
| **2. Worktrees** (parallel isolation) | Archon worktree-per-engagement; agent teams; the branch-as-lock in `WORK-INTAKE` |
| **3. Skills** (project knowledge written down) | `skills/` (SKILL-AUTHORING + python/fastapi/typescript), description-as-router |
| **4. Plugins/connectors** (touch real tools, via MCP) | the **PM Port sync adapters** (`hssd pm add`), `commands/`, MCPs (later) |
| **5. Sub-agents** (maker ≠ checker) | the **whole adversarial design** — the author never judges their own "done"; Independent Verifier, Completion Challenger, Security/Test adversaries |
| **+ Memory** (state on disk, not in context) | `.harness/` — the pm.sqlite spine, session logs, `engagements/<id>/` state |

So Harness Studio isn't *adjacent* to loop engineering — it **is** a loop-engineering framework. The harness (skills/gates/standards) is the floor; the loops are the floor above. The agent forgets between runs; the repo doesn't.

## The blessed loop construct

Every Harness Studio loop has:
- **A goal** — a purpose + a **verifiable stop condition**, never "looks done". E.g. *"all AC tests green AND adversaries find nothing."*
- **Iterate** — do the work; re-run against the condition.
- **A separate checker** — the role/model that decides "done" is **never** the one that did the work (maker ≠ checker). This is the `/goal` pattern: a fresh checker evaluates the stop condition.
- **Memory on disk** — the loop reads/writes durable state in `.harness/`, because the model forgets between runs.
- **Human escalation** — whatever the loop can't resolve lands in a triage inbox / a human gate.

## The two loops in Harness Studio

1. **The engagement loop** (remediation, per work item). `hssd engage <id>` runs the SOP phases; **P4 verification is the goal condition** — *loop-until-dry*, where the adversaries (separate from the maker) are the checker. Stop = AC green **and** adversaries find nothing. That is a `/goal` loop.
2. **The janitor loop** (discovery, the heartbeat). Scheduled: audit the codebase → dedup → file work items into the PM spine. Its findings feed the engagement loop. This is the "automations" piece — the loop that *surfaces* the work.

Together: **janitor surfaces → engagement remediates → `.harness/` is the spine both read and write → human at the leverage points.** You design it once; you don't prompt the steps.

## Stay the engineer (the caveats = our existing invariants)

Loop engineering's honest warnings are the same guardrails we already bless — a smooth loop makes these *sharper*, not easier:
- **Verification is still on you** → human gates (Spec Lock, merge) + the adversarial checker. "Done" is a claim; the verifier makes it mean something.
- **Comprehension debt** (you stop understanding code the loop wrote) → read what the loop makes; the AI log + ADR keep it legible.
- **Cognitive surrender** (just take whatever it returns) → the human decides at leverage points. Designing the loop *with judgment* is the cure; doing it *to avoid thinking* is the trap. Same action, opposite result.
- **Token cost** → lanes + per-item budget; spend adversaries where a second opinion is worth paying for.

## The operator's job, restated

You write the **harness** (skills, gates, validations — PHILOSOPHY tenet 9) **and** you design the **loops** (the goals, the cadence, the stop conditions). You don't prompt the steps. **Build the loop. Stay the engineer.**

## References
- Addy Osmani — *Loop Engineering*, *Agent Harness Engineering*, *Factory Model*, *Long-running Agents*, *The Code Agent Orchestra*, *Adversarial Code Review*.
- steipete; bcherny (Claude Code).

> Tool primitives named in the source (`/loop`, `/goal`, Codex Automations, hooks, `isolation: worktree`) are Claude Code / Codex features — confirm exact availability against your installed versions before relying on them.
