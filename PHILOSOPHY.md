# Harness Studio — Design Philosophy

> The soul of the framework. Every other document serves this one. If a future decision conflicts with these tenets, the tenets win.

## The core belief

In a world where AI can generate *anything*, control comes from **deliberately reducing what's possible**. An opinionated system isn't a weaker tool — it's a governable one. This is [Ashby's Law of Requisite Variety](https://en.wikipedia.org/wiki/Variety_(cybernetics)#Law_of_requisite_variety) applied to AI engineering: a regulator can only control what it has a model of, and you can only build a model of a system whose variety you've narrowed. **Opinion is variety reduction. Variety reduction is what makes AI output controllable and the harness gates meaningful.**

So: we choose constraint on purpose. If that makes the framework limited, good — we extend it deliberately, never dilute it.

## The tenets

1. **Opinionated over flexible.** There is one blessed way to do each thing. The framework owns the *how*; you bring the *what*. We are not trying to be amazing at everything — we are trying to do what we propose, with control.

2. **Convention over configuration.** Defaults are decisions, not placeholders. Few knobs. The less there is to choose, the less there is to get wrong — for a human or an AI.

3. **Constraint is the feature.** Narrowing the space of "how" is the whole point. A system that can do anything can be governed by no one. Committing to conventions is a variety-reduction move that makes a comprehensive harness achievable.

4. **One paved path. No menus.** We don't offer alternatives for how to do something. Either there is *the* way, or the capability isn't here yet. "It depends" is not an answer the framework gives.

5. **Escape hatches are explicit or they don't exist.** An alternative is *documented as a sanctioned path* or it does not exist. No silent side-doors, no undocumented flexibility, no "you're on your own off-road." If you can do it, it's described. If it's not described, you can't.

6. **Do it well or don't do it.** A capability is first-class and excellent, or it is out of scope. No half-supported features, no "kind of works" corners. The quality bar is binary.

7. **Extend by adding opinions, not by adding configuration.** When you hit a limit, the fix is a *new blessed module or path*, decided and documented — never turning an existing piece into a configurable everything-machine. The framework grows by accumulating good opinions, not options.

8. **The way of doing is owned by the framework.** This is not control for its own sake — it's what makes AI output predictable and verification possible. The gates can check the work because the work has a known shape.

9. **Fix the harness, not the code.** When something is wrong, the fix is a new validation, linter, gate, or skill — so the framework gets it right *next time* — never just a one-off patch. The operator's primary work is **writing harness** (skills, gates, validations), not final code. Patching the same class of error forever is exactly the failure mode this framework exists to escape; every correction must harden the system.

10. **No unexplained acronyms or jargon.** Clarity is owned by the writer, the same way correctness is owned by the maker. Every abbreviation is either spelled out on first use or defined in the [glossary](GLOSSARY.md) — a reader never has to already know the vocabulary to follow the work. Short texts (slides, role cards, a one-line label) expand the term inline; long or repetitive documents carry a glossary and link to it. "The reader will figure it out" is not an acceptable default; an undefined acronym is a defect, like an untested guarantee.

## What this is NOT

- Not a Swiss-army knife. Breadth is a non-goal.
- Not a meta-framework of options. We don't ship "10 ways to do X."
- Not infinitely flexible. Flexibility that isn't a documented path is a bug.

## What this means in practice

- **Installation is one command, one way.** No setup decisions to make.
- **A new need is met by proposing a new convention** — through the framework's own adversarial process (Architect proposes ↔ Adversary challenges) — not by exposing a config flag.
- **"Limited but extensible" is the design, not a compromise.** Limited keeps it governable; extensible (by adding opinions) keeps it growing.
- **This applies to both layers:** how work is done (the team/process) *and* how applications are built (the conventions/scaffolds). The framework determines the way of doing in both.

## The reflexive point

This philosophy is harness engineering applied to the framework's own design. We constrain Harness Studio for the same reason Harness Studio constrains AI: a narrow, well-defined system is one you can trust, verify, and govern. We eat our own cooking.
