---
name: typescript
description: Load for any TypeScript/React frontend work — dashboards and web UIs, project setup, components, data fetching, styling.
---
<!-- status: BLESSED — ratified. -->

## The blessed way

**TypeScript (strict) + React**, **npm** for deps, **shadcn/ui + Tailwind** for UI. For full applications: **Next.js, server-component-first**. For a simple dashboard (read-mostly, polling), the sanctioned lighter path is **Vite + React + TS (SPA)** — chosen by the Architect and justified in the ADR. No `any`. Typed API boundaries.

## Conventions

1. **Deps: `npm`.** `package.json` is the source of truth.
2. **TypeScript strict.** `strict: true` in tsconfig; **no `any`** (use `unknown` + narrowing). API responses are typed.
3. **App framework (pick one, per Architect):**
   - **Next.js** — blessed for real apps; **server-component-first** (client components only where interactivity needs them).
   - **Vite + React SPA** — sanctioned light path for simple dashboards; documented in the ADR when chosen.
4. **UI: shadcn/ui + Tailwind.** Don't hand-roll components that shadcn provides; don't introduce a second styling system.
5. **Components:** function components + hooks; typed props; small and single-purpose (atomic). Early returns for loading/empty/error states.
6. **Data fetching in a dedicated layer** (hooks/services), not inline in components; always render loading + error states.
7. **Lint + format: Biome** (blessed default for new projects) or ESLint + Prettier (keep if already in the project — no forced migration). See "Lint gate" section.

## Gotchas & AI failure modes

- **`any` everywhere.** AI reaches for `any` to silence the compiler — defeats the point. Type the data.
- **Everything client-side in Next.** AI ignores server components and makes the whole tree `"use client"`. Server-component-first is the rule.
- **Hand-rolled UI** instead of shadcn — inconsistent, more code, more bugs.
- **Missing loading/error/empty states** — AI renders only the happy path; a live dashboard must handle "no data yet", "fetch failed", "stale".
- **Stale-closure bugs in polling.** A `setInterval` capturing stale state/props is a classic AI miss; use refs or the functional updater, and clean up the interval.
- **Untyped fetch responses** — `res.json()` as `any` propagates untyped data through the app.
- **Bare global `JSX.Element`** — removed in `@types/react` v19. Annotate components with `ReactElement` (`import type { ReactElement } from "react"`) or `React.JSX.Element`, never the bare global `JSX.Element`. (Caught live by `tsc` on the scaffold.)

## Lint gate — mandatory before declaring done

Lint is a **hard gate**: P3b is not done until the linter passes clean.

**Biome (blessed for new TypeScript projects):**
```bash
npx @biomejs/biome check .          # lint + format check — zero errors required
npx @biomejs/biome check --apply .  # auto-fix safe issues
```

**ESLint (keep if already in the project):**
```bash
npx eslint . --ext .ts,.tsx         # zero errors required
npx eslint . --ext .ts,.tsx --fix   # auto-fix safe issues
```

**Biome vs ESLint — the decision:**
- **Biome**: single binary, replaces ESLint + Prettier, zero config to start, ~100× faster. Blessed for new projects from 2024 onward.
- **ESLint**: larger plugin ecosystem, required for projects with custom rules or legacy configs. Keep it if the project already uses it.
- **The rule**: new project → Biome. Existing project with ESLint → keep ESLint, don't migrate mid-engagement.

**`tsc` is always required** regardless of which linter is used:
```bash
npx tsc --noEmit   # strict type check — zero errors required
```

Run in order: `tsc --noEmit` → linter → tests. Type errors and lint errors caught by tools cost zero tokens.

## How "done" is proven

- `npx tsc --noEmit` → zero errors (strict)
- `npx @biomejs/biome check .` (or `npx eslint .`) → zero errors
- UI acceptance criteria are **demonstrable** — screenshot or description covers: success state, loading state, error state, empty state
- For logic-heavy pieces: unit test (Vitest / React Testing Library)
- Evidence = command output attached. No "should pass".

## Out of scope (sanctioned paths or absent)

- **State libraries (Redux/MobX/etc.):** not default. React state/hooks first; a library only if the Architect justifies it in the ADR.
- **CSS systems other than Tailwind:** not blessed.
- **The polling-vs-websockets decision:** owned by the Architect per engagement (justified in the ADR), not hard-coded here. For modest update rates, polling is usually the simpler, defensible default.

## Examples

Typed polling hook (the blessed shape — no stale closure, cleans up):
```typescript
function useCounters(intervalMs = 2000): Record<string, number> | null {
  const [counts, setCounts] = useState<Record<string, number> | null>(null);
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      const res = await fetch("/counters");
      const data = (await res.json()) as Record<string, number>;
      if (alive) setCounts(data);
    };
    void tick();
    const id = setInterval(tick, intervalMs);
    return () => { alive = false; clearInterval(id); };
  }, [intervalMs]);
  return counts;
}
```
