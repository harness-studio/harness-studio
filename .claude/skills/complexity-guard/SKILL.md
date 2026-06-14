---
name: complexity-guard
description: Load when designing, building, or reviewing any feature — guards against overengineering, unnecessary abstraction, and speculative generalization. The "do you actually need this?" filter.
---
<!-- status: BLESSED — mandatory gate for all design and implementation phases. -->

## The blessed way

Build the minimum that satisfies the acceptance criteria. Every line of code is a liability: it must be understood, tested, and maintained. Complexity must be justified by a specific, current requirement — not by anticipated future needs or by pattern familiarity.

The single test for any design element: **"Which acceptance criterion requires this?"** If there is no answer, the element should not exist.

## Conventions (the blessed rules)

1. **YAGNI — You Ain't Gonna Need It.** Do not build for hypothetical future requirements. If the AC doesn't require it, don't build it. Features, config options, extension points, and abstractions that aren't needed now are technical debt from day one.

2. **Simplest solution first.** When two implementations satisfy the AC, choose the simpler one. A function is simpler than a class. A class is simpler than a framework. Direct code is simpler than an indirection layer. A 10-line solution is simpler than a 100-line "flexible" one.

3. **Three instances before abstraction (Rule of Three).** Don't abstract on the first or second instance of a pattern. Abstract on the third — and only when the abstraction is clearly simpler than the repetition. Two similar functions is fine. A premature `BaseStrategy` is not.

4. **Complexity ceiling.**
   - Function body > 50 lines → consider splitting; require justification
   - File > 300 lines → consider splitting; require justification
   - Nesting depth > 3 levels (if/for/try) → refactor to early returns or extracted functions
   - These are flags, not hard limits — the justification is the deliverable

5. **No speculative config.** Don't add configuration options for things that don't vary today. A constant is better than a config key nobody sets. A hard-coded value is better than an env var that never changes. Add config when the variation is a current requirement.

6. **No backwards-compatibility shims for internal code.** If you control all callers, change them. Shims that exist "in case someone uses the old interface" are dead weight when you own the codebase.

7. **Dependencies have a cost.** Every added dependency must be justified: what does it provide that the stdlib or existing deps don't? A library that adds 50 transitive dependencies to avoid writing 20 lines of code is usually not worth it.

8. **No feature flags for unreleased features in a single-team codebase.** Feature flags are for gradual rollout across multiple deployments. In a single-team repo with no multi-environment rollout, a feature flag is just an if-statement with a config leak — ship the feature or don't.

## Anti-patterns to DETECT (and the fix to PROPOSE)

- **Factory of factories** (or any pattern-on-pattern without a concrete requirement) → propose the direct implementation
- **Base class for one subclass** → propose a single class or function
- **Strategy pattern where a function argument suffices** → propose a function with a `strategy` parameter or simple branching
- **Config for a constant** → propose hardcoding the value until variation is a real requirement
- **Abstraction over one caller** → propose inlining the abstraction and revisiting when a second caller appears
- **"We might need to swap this out later"** without an actual plan to swap → propose building for the current requirement
- **Generic framework for a specific need** → propose the specific solution; generalize when the second specific need arrives
- **Dependency for trivial functionality** → propose writing the 10 lines instead of importing a library

## Review checklist

- [ ] Every design element (class, interface, config key, abstraction layer) maps to a specific AC
- [ ] No function body exceeds 50 lines without documented justification
- [ ] No file exceeds 300 lines without documented justification
- [ ] No abstraction has fewer than three concrete instances (or a concrete plan for the second)
- [ ] No config option exists for a value that doesn't vary today
- [ ] No backwards-compatibility shim exists for internal code where callers can be changed
- [ ] Every added dependency is justified against the stdlib + existing deps
- [ ] No feature flag exists for a feature with no multi-environment rollout plan
