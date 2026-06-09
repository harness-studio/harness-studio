# Scaffolds — blessed starting shapes

Each scaffold is a **known-good project skeleton** for a stack tier, applied by the CLI (`harness-sd new <scaffold>`, alias `hssd new`). Applying a scaffold drops:
- the blessed **project structure** (per the tech skills),
- the **`.vscode/` config** that wires *existing* extensions (Ruff, Python, ESLint, Tailwind…) — Harness Studio configures the IDE, it doesn't ship a plugin,
- the **day-zero governance**: `docs/ADR.md`, `docs/AI_LOG.md` (from `templates/`), `README.md`, the **pre-commit gate**, and the local `.harness/pm.sqlite` spine.

The human fills in app logic *under* the blessed shape; the scaffold guarantees the conventions and the governance exist from minute zero. That's what makes producing the graded deliverables (ADR, AI log) and passing the gates *easy*.

**Available**
- `backend-fastapi-sqlite/` — backend, lightweight tier.

**Planned**
- `frontend-vite-react-ts/` — frontend, lightweight tier.
- `backend-fastapi-postgres/` — backend, full tier.
- `frontend-nextjs/` — frontend, full tier.

Templates may also be brought from a **git URL** (see `STANDARDS.md` §3); a brought-in template is wrapped to conform to the governance files before use.
