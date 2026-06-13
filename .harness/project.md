# Harness Studio

## Vision

Software delivery governed by AI — where rigor multiplies speed instead of fighting it.

Harness Studio is an open-source framework that turns AI agents into a disciplined delivery team: structured intake, adversarial verification at every step, and evidence-based "done." It scales from a solo developer with a single AI assistant all the way to parallel fleets of agents working independent iterations simultaneously and converging on a shared codebase.

## The Problem

AI-assisted development today is largely unstructured: a developer describes what they want, an agent writes code, and "done" is whatever the agent claims. This works for small tasks. It breaks down for real projects — ambiguous requirements ship as bugs, nobody checks the checker, and there's no paper trail when something goes wrong.

Teams have always solved this with process: intake, architecture review, testable acceptance criteria, independent QA, merge gates. But those processes were designed for humans and don't compose naturally with AI agents.

Harness Studio brings that discipline to AI-native delivery, without making it slow.

## Objectives

1. **Structured intake at any scale** — every piece of work enters through a grooming cycle (product analyst + skeptic), an architecture review (inherit the ADR or extend it), and a split into verifiable stories. Whether the input is a hand-written feature request, a structured spec from another tool, an imported library, or a janitor-discovered debt item — the same intake cycle applies.

2. **Governance that doesn't block** — maker ≠ checker is a standing rule, not an end task. The author never certifies their own work. Adversarial agents (security, completeness, test integrity, regression) attack every story before merge. Evidence (test output, diffs, verdicts) is the only proof of done.

3. **Parallel delivery** — iterations are first-class entities. A single intake can produce 20 stories; those stories can be assigned to 20 parallel iterations, each running its own full P0→P4 loop in an isolated worktree. The caller — Claude Code, the CLI, or a CI orchestrator — manages the fleet.

4. **Adopt, don't replace** — existing projects can be adopted into Harness Studio. The framework reads the codebase, infers objectives, validates the existing stack against the ADR, and opens for intakes. No greenfield-only assumption.

5. **Teach, not just run** — every concept is documented, every decision is explained. The framework is a learning artifact as much as a delivery tool. A developer new to governed AI delivery should be able to read the docs and understand why each step exists.

## The Delivery Cycle

```
PROJECT (stable)
  project.md   — vision, objectives, non-goals
  ADR          — stack, architecture decisions (locked, human-approved)

     │ (at any point, n times)
     ▼

INTAKE (recurring)
  Forms: hand-written · structured · unstructured · operational (libs, skills)
  Steps: grooming → architecture lite → split → stories in backlog

     │
     ▼

ITERATION PLANNING
  Pick which stories → which iteration
  Plan now, activate when ready — sequence or in parallel

     │  hssd iteration activate <id> [<id2> <id3> ...]
     ▼

ITERATION (per active process)
  Per story: P0 intake → P1 AC → P2 arch → [Spec Lock]
             → P3 red/green → P4 adversarial dry → [Merge]

  Janitor runs continuously: discovers drift, debt, latent bugs → new intakes

     └── converge → main → next intake
```

## Non-Goals

- **Not a CI/CD platform.** Harness Studio governs the delivery loop; it doesn't replace pipelines, container registries, or deployment infrastructure.
- **Not a project management replacement.** It doesn't track OKRs, roadmaps, stakeholder communication, or time-box sprints. It tracks work items and their governance state.
- **Not a vibe-coding tool.** There is no "just make it work" mode. Every story goes through intake, spec lock, and adversarial verification before merge.
- **Not opinionated about your stack.** The framework works with any language or framework — skills encode the conventions, the governance loop is stack-agnostic.
- **Not a closed tool.** Skills, agent cards, and workflows are plain markdown and YAML files. The community can publish, share, and import them.

## North Star

A developer — or a fleet of AI agents — should be able to take any feature request from raw idea to merged, verified code with complete confidence that nothing was skipped, nothing was self-certified, and every decision is traceable. And a new contributor to that project should be able to understand exactly what was built and why by reading the evidence trail.

## Principles

- **Evidence over assertion.** "Done" means test output, a diff, or a screenshot — never a claim.
- **Maker ≠ checker.** The agent that builds never certifies its own work.
- **Governance is standing, not an end task.** Every intake, every story, every merge — the loop is always on.
- **Documentation is the product.** A tool without clear docs is a tool no one uses.
- **Simple scales.** `hssd iteration activate id1 id2 id3` starts 3 parallel processes. No flags, no modes.
