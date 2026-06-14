---
name: makefile
description: Load when setting up or reviewing any project — Makefile as the universal command interface. Standard targets that delegate to the stack runner (uv, npm, etc.), so the developer always types `make <target>` regardless of the underlying technology.
---
<!-- status: BLESSED — ratified. The universal interface rule: one project, one set of commands. -->

## The blessed way

Every project exposes the same interface regardless of stack. `make test` runs the tests whether the project uses `uv run pytest`, `npm test`, or anything else. The Makefile is the contract between the developer and the project; the stack runner is an implementation detail.

**Why Makefile over stack-native scripts:** npm scripts, uv scripts, and shell aliases are stack-specific and inconsistent across projects. A developer switching between a Python service and a TypeScript frontend shouldn't need to remember two different command sets. `make dev` always starts the dev server. `make test` always runs the tests. `make lint` always lints.

## Blessed standard targets

Every project must implement these targets (using `.PHONY` to avoid conflicts with files of the same name):

| Target | What it does |
|---|---|
| `make install` | Install all dependencies (fresh clone or after lock file change) |
| `make dev` | Start the development server (hot reload, debug mode) |
| `make test` | Run the full test suite |
| `make lint` | Run the linter (check only, no writes) |
| `make format` | Format the code (writes in place) |
| `make build` | Build for production (compile, bundle, optimize) |
| `make migrate` | Run pending database migrations |
| `make clean` | Remove build artifacts, caches, generated files |

Optional but encouraged:
| Target | What it does |
|---|---|
| `make prod` | Start the production server (used in containers/CI) |
| `make check` | Run lint + test in one shot (CI shorthand) |
| `make docs` | Generate or serve API docs |

## Canonical Python (uv) Makefile

```makefile
.PHONY: install dev test lint format migrate clean check

install:
	uv sync

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest --tb=short -q

lint:
	uv run ruff check .

format:
	uv run ruff format .

migrate:
	uv run alembic upgrade head

clean:
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache dist build

check: lint test
```

## Canonical TypeScript / Node Makefile

```makefile
.PHONY: install dev test lint format build clean check

install:
	npm install

dev:
	npm run dev

test:
	npm test

lint:
	npx @biomejs/biome check .

format:
	npx @biomejs/biome format --write .

build:
	npm run build

clean:
	rm -rf node_modules dist .next .turbo

check: lint test
```

## Rules

1. **All targets are `.PHONY`** unless they produce a real file artifact — prevents `make` from skipping a target because a file of the same name exists.
2. **Targets call the stack runner, not tools directly** — `uv run pytest`, not `pytest`; `npx biome`, not `biome`. This ensures the project's environment is always used.
3. **`make check` = lint + test** — the canonical CI gate; runs both in sequence so CI always uses the same commands a developer would.
4. **No environment-specific targets in the Makefile** — `make dev` and `make prod` are the only environment variants. Environment variables are passed externally (`ENV=production make prod`), not baked into separate targets.
5. **The Makefile lives at the project root** — always `./Makefile`, never in a subdirectory.
6. **Document non-obvious targets** — a comment above each non-trivial target explaining what it runs and why.

## Anti-patterns to DETECT (and the fix to PROPOSE)

- **Stack-native scripts only** (e.g. only `npm run test`, no Makefile) → propose adding a Makefile with the standard targets
- **Missing `.PHONY`** → propose adding it; a `test` or `clean` file will silently prevent the target from running
- **Hardcoded tool invocation** (`pytest` instead of `uv run pytest`) → propose using the stack runner
- **Environment baked in** (`make dev-local`, `make dev-staging`) → propose using env vars externally
- **Makefile in a subdirectory** → propose moving to the project root

## Review checklist

- [ ] Makefile exists at the project root
- [ ] All standard targets are present: `install`, `dev`, `test`, `lint`, `format`, `build`, `clean`
- [ ] All targets are marked `.PHONY`
- [ ] Targets call the stack runner (`uv run`, `npx`), not tools directly
- [ ] `make check` runs lint + test (the CI gate)
- [ ] No environment-specific targets; environment is passed via env vars
