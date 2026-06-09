# Frontend scaffold — Vite + React + TypeScript (lightweight tier)

A minimal, blessed starting shape for a dashboard SPA. Demonstrates the conventions, not a finished app.

## Why this tier
A simple, read-mostly dashboard that **polls** is well served by a Vite + React SPA — no SSR needed. For a real application, use the `frontend-nextjs` tier (Next.js, server-component-first) and justify it in the ADR.

## Run
**Requires Node 20+.**
```bash
npm install
npm run dev          # vite dev server
npm run typecheck    # tsc --noEmit (strict)
```

## Structure
```
src/
  main.tsx                 # entry
  App.tsx                  # dashboard (uses the polling hook)
  hooks/useCounters.ts     # blessed polling hook (typed, no stale closure, cleans up)
index.html
tsconfig.json              # strict
vite.config.ts
hssd.yaml                  # type: template (this repo is a template, not a managed project)
docs/ADR.md, docs/AI_LOG.md   # governance, day zero (from templates/)
.vscode/                   # existing extensions (ESLint, Prettier, Tailwind)
```

## Blessed UI (to wire on init)
Per `STANDARDS.md`, the blessed UI is **Tailwind + shadcn/ui**, server-component-first on the Next tier. This minimal skeleton uses plain markup so it runs with zero UI deps; `hssd vscode setup` / a follow-up wires Tailwind + shadcn + ESLint config.

## Governance from minute zero
`docs/ADR.md` and `docs/AI_LOG.md` exist before any code — filled as the process runs.
