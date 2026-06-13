# Harness Studio — Project Identity

## What is Project Identity

Every project governed by Harness Studio has an identity document: `project.md`. This document answers the question "what is this project?" — not what it does today, but what it is trying to become and why.

Project identity is the anchor for everything else. Intakes are validated against it (is this work aligned with what the project is for?). Architecture decisions reference it (does this stack choice serve the project's goals?). The janitor uses it (is this detected debt worth fixing given where the project is going?).

Without a clear project identity, a project can be technically correct but strategically incoherent — features get built that serve no objective, architecture gets chosen for the wrong reasons, and "done" has no meaning because there is no definition of success.

---

## What `project.md` Contains

A well-written `project.md` has five sections:

### 1. Vision
One or two sentences. What does this project exist to do, at the highest level? This should be stable — it should not change every quarter.

```
Example:
Harness Studio is an open-source framework that brings governed, adversarial
delivery discipline to AI-assisted software development — making rigorous
delivery accessible to any team, at any scale.
```

### 2. Objectives
Three to five concrete goals the project is working toward. Each objective should be:
- Specific enough to evaluate (you can tell when it's achieved)
- Meaningful at the project level (not a task, not a feature)
- Aligned with the vision

```
Example objectives:
1. Developers can adopt Harness Studio into an existing project in under 10 minutes.
2. Every intake — regardless of source or form — follows the same governance cycle.
3. Parallel iterations can be activated and orchestrated without manual coordination overhead.
4. The framework is self-documented: every concept has a canonical reference document.
```

### 3. Non-Goals
What this project explicitly does not do. Non-goals are as important as goals — they prevent scope creep and help the team say no to work that feels relevant but isn't.

```
Example non-goals:
- Harness Studio does not replace CI/CD pipelines or deployment infrastructure.
- Harness Studio does not track time, OKRs, or stakeholder communication.
- Harness Studio is not opinionated about which language or framework you use.
```

### 4. Principles
The rules the project follows when making decisions. Principles resolve conflicts — when two options both seem valid, the principle tells you which to choose.

```
Example principles:
- Evidence over assertion: done means test output, a diff, or a verdict — never a claim.
- Maker ≠ checker: the agent that builds never certifies its own work.
- Simple scales: the parallel model is implicit in how many IDs you pass, not in flags.
- Documentation is the product: a tool no one understands is a tool no one uses.
```

### 5. North Star
Where the project is going at its furthest horizon. Not a roadmap item — a direction. Used to evaluate long-horizon decisions: does this choice move us toward the north star or away from it?

```
Example:
A developer — or a fleet of AI agents — should be able to take any feature
request from raw idea to merged, verified code with complete confidence that
nothing was skipped, nothing was self-certified, and every decision is traceable.
```

---

## Two Paths to Project Identity

### Path 1: New Project

The project does not exist yet. The developer starts with a blank slate.

```
hssd init
```

After initialization, the framework prompts for a project brief. A product analyst subagent takes the brief and drafts `project.md`. The developer reviews, corrects, and iterates. When the document is accurate:

```
hssd project approve
```

The project moves from `initialized` to `identified`.

### Path 2: Existing Project (Adopt)

The codebase already exists. The developer is adding governance to something that has been running without it.

```
hssd adopt
```

After adoption, an exploration agent reads the repository: source files, existing documentation, commit history, package manifests, README files. It infers what the project is trying to do, what technologies are in use, and what constraints already exist.

The exploration agent drafts `project.md` based on what it finds. This draft may be incomplete or partially wrong — the project's real objectives may not be fully expressed in the code. The developer's job is to correct it.

Common corrections on the adopt path:
- The code reveals what was built, but the objectives behind it were different from what the agent inferred.
- The project started as one thing and evolved into another — the current code reflects the evolution, not the original intent.
- Some objectives are implicit in the team's knowledge but not in the codebase.

The developer corrects the draft until it accurately represents the project. Then:

```
hssd project approve
```

---

## Project Identity is Stable

`project.md` changes rarely. It is not a sprint planning document or a feature backlog. It describes what the project fundamentally is.

Edits to `project.md` require human acknowledgment — they are not casual changes. When the vision, objectives, or principles change, that is a significant event: it means the project is evolving at a strategic level, and all current and future work should be evaluated against the new identity.

Signs that `project.md` needs updating:
- Intakes are consistently being marked out-of-scope by the definition skeptic, but the team believes they should be in-scope.
- The architecture decisions in the ADR no longer serve the objectives.
- The north star has shifted because of new information (market, technology, user research).

Signs that `project.md` does NOT need updating:
- A new feature request arrives (this is an intake, not an identity change).
- A technology choice turns out to be wrong (this is an architecture revision, not an identity change).
- Sprint goals change (this is iteration planning, not identity).

---

## Project Identity vs. the ADR

These two documents are often confused. They are different in scope and lifecycle:

| | `project.md` | `docs/ADR.md` |
|---|---|---|
| **Answers** | What is this project for? | How is this project built? |
| **Scope** | Strategic — vision, goals, principles | Technical — stack, data model, decisions |
| **Changes when** | Strategic direction shifts | Architecture pivots |
| **Written by** | Product analyst + human | Architect + human |
| **Validated by** | Definition skeptic (intake alignment) | Architecture adversary |
| **Locked by** | `hssd project approve` | `hssd architecture approve` |

Both are stable. Both require human approval to change. But they govern different layers: `project.md` governs what is worth building; the ADR governs how it gets built.

---

## Using Project Identity in Practice

**During intake grooming:**
The definition skeptic checks every concern in the intake against `project.md`. A concern that does not serve any of the listed objectives is flagged as out of scope. The human can override — but the flag forces an explicit decision rather than silent scope creep.

**During architecture review:**
The architect references `project.md` when justifying decisions. "We chose PostgreSQL because the project requires ACID guarantees for financial data" is a decision grounded in project identity. "We chose PostgreSQL because it's popular" is not.

**During janitor scans:**
The janitor checks detected debt against project objectives before filing an intake. Technical debt that would cost significant engineering effort but serves no current objective may be deferred. Debt that blocks an objective is always filed.

**During sprint retrospective:**
The team asks: did what we built this sprint actually advance the project toward its objectives? If not — was that because the intake was wrong, or because the objectives need to be updated?
