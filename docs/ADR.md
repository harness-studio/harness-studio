# ADR — <engagement title>

> Architecture Decision Record (1 page). Assemble from Phases 0 and 2 — don't write from scratch at the end. Keep it lean: decision → reason → trade-off.

## 1. The 2-3 most important decisions (and why)
> From Phase 2 (Architect proposed ↔ Architecture Adversary challenged). Include the highest domain-risk ones (concurrency/isolation, persistence, transport).

- **Decision A:** <what was decided>
  - Why: <reason>
  - Alternative considered: <option> — rejected because <trade-off>
- **Decision B:** ...
- **Decision C:** ...

## 2. What was unclear in the spec, and what we assumed
> Straight from the Definition Skeptic's list (Phase 0). Shows the ambiguities were identified and consciously assumed.

- Unclear: <point> → Assumed: <assumption> (why: <reason>)
- ...

## 3. What would change at significant scale
> Define "significant" with a number. Say what breaks first and what replaces it.

- "Significant" = <e.g., from X to Y>.
- What breaks first: <bottleneck> → change: <new approach>

## 4. What we deliberately left out (and why)
> From Phase 0's out-of-scope + budget right-sizing decisions.

- <item> — because <reason (time / marginal value / controlled risk)>
