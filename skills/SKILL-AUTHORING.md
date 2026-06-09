# Harness Studio — Skill Authoring (the blessed format)

> A **skill** is packaged, opinionated knowledge a role pulls in when relevant. It answers "*the* way we do X" — never "some ways you could do X". This document defines the one format every Harness Studio skill follows. (This is convention-over-configuration applied to skills themselves.)

## What a skill is (and isn't)

- **Is:** the blessed conventions, patterns, and gotchas for a technology or a recurring task (e.g., `fastapi`, `react`, `write-adr`).
- **Is not:** a worker (that's a subagent), a sequence (that's a workflow), or a menu of options. A skill that says "you could do A or B" is a bug — pick one, document the other only if it's a sanctioned path.

## Two kinds of skills

- **Tech skills** (`python`, `fastapi`, `react`, `nextjs`): the app-construction conventions. The "how we build" layer.
- **Process skills** (`write-adr`, `capture-ai-log`, `stress-test-concurrency`): repeatable craft used across engagements.

## File layout

```
skills/
  <skill-name>/
    SKILL.md          # required — the skill itself
    examples/         # optional — reference snippets (the blessed shapes)
    scripts/          # optional — helper scripts the skill invokes
```

## Required structure of every `SKILL.md`

```markdown
---
name: <skill-name>
description: <one line that says exactly when to load this skill — the trigger>
---

## The blessed way
The single approach. State it as a decision, not options.

## Conventions
Concrete, enforceable rules (structure, naming, patterns). Numbered/listed.

## Gotchas & AI failure modes
What goes subtly wrong here — especially where an AI is overconfident or
declares "done" early in THIS technology. This is what the adversaries hunt.

## How "done" is proven (tests)
The evidence that work in this tech is actually correct. Maps to the gates.

## Out of scope
What this skill deliberately does NOT cover. Escape hatches are listed here
as sanctioned paths, or they don't exist.

## Examples
The blessed shapes (link to examples/ or inline).
```

## Authoring rules (non-negotiable, from PHILOSOPHY.md)

1. **One blessed way.** No "option A vs B" in the body. Decide.
2. **Escape hatches are explicit or absent.** If there's a sanctioned alternative, it lives under *Out of scope* as a documented path. Otherwise it doesn't exist.
3. **Gotchas are mandatory.** A skill without a failure-modes section is incomplete — that section is what makes the technology *harnessable* (the adversaries need to know what to attack).
4. **"Done" must be provable.** Every skill says how correctness is demonstrated in that tech, or it can't be gated.
5. **Do it well or leave it out.** A thin, half-true skill is worse than none — it gives false confidence.
6. **Extend by adding skills, not options.** New need → a new skill (or a new sanctioned path documented in an existing one). Never turn a skill into a configurable everything-doc.

## How skills compose with the team

- A subagent (role) loads the skills relevant to its task automatically (matched by the skill `description`).
- Example: `backend-dev` building an API loads `python` + `fastapi`; `frontend-dev` loads `react` + `nextjs`.
- The **Test Adversary** and **Independent Verifier** use each skill's *Gotchas* and *How "done" is proven* sections to know what to attack and what evidence to demand.

## Ratification

A tech skill encodes opinions about how to build. Those opinions are **proposed by the Architect and ratified by the human (Engagement Lead)** — the same Architect↔Adversary tension the framework uses everywhere. A skill is not "true" until ratified; until then it's a proposal (mark it `status: proposed` in a comment).
