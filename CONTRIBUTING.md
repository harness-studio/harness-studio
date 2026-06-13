# Contributing to Harness Studio

Harness Studio is an open source project. Contributions are welcome — whether you're
fixing a bug, adding a command, writing a new agent card, or improving the docs.

All changes go through the framework's own governance loop (dogfood). This means
every non-trivial contribution follows P0→P4: intake → spec lock → red/green tests →
adversarial verification → merge.

---

## Versioning rules

**If something changed, it must be versioned.** No silent updates.

We follow [Semantic Versioning](https://semver.org/) with pre-release labels:

| Change | Version bump | Example |
|---|---|---|
| Breaking CLI interface change | **Major** `X.0.0` | rename/remove a command, change state machine transitions, breaking `.harness/` schema change |
| New command, new feature, new agent card, deprecation | **Minor** `0.X.0` | add `hssd intake`, add a new P4 adversary, deprecate `hssd overview` |
| Bug fix, doc fix, infographic update, non-breaking improvement | **Patch** `0.0.X` | fix a latent bug in `cmd_skill`, update the infographic, fix a test |

**Pre-1.0 (`0.x.y`):** minor versions carry significant new features and may include
breaking changes. Patch versions are fixes only. The `-alpha.N` / `-beta.N` suffix
signals the overall project maturity.

**The rule in practice:**
- Changed `cli/hssd.py` behavior → bump version in `pyproject.toml`
- Added or changed a command → minor bump minimum
- Changed the state machine → minor or major depending on backwards compatibility
- Fixed a bug only → patch bump
- Docs/presentation only → patch bump (optional — can batch with the next code change)

**How to bump:**
1. Edit `version` in `pyproject.toml`
2. The `__version__` in `cli/hssd.py` reads from `importlib.metadata` automatically
3. Update `CHANGELOG.md` under a new `## [X.Y.Z] — YYYY-MM-DD` header
4. After merging: `git tag -a vX.Y.Z -m "<summary>"` + `git push origin vX.Y.Z`

---

## Getting started

```bash
git clone https://github.com/harness-studio/harness-studio
cd harness-studio
uv sync                    # install + dev dependencies
uv run hssd --version      # verify
uv run pytest              # run the test suite
```

---

## Making a change

**Bug fix or small improvement:**
```bash
# 1. Write a failing test first (red)
# 2. Fix the bug (green)
# 3. Bump patch version in pyproject.toml
# 4. Update CHANGELOG.md
# 5. Open a PR
```

**New command or feature:**
```bash
# 1. Open an intake (describe what you're adding and why)
# 2. Get agreement on the spec before writing code
# 3. Write tests from the spec (red)
# 4. Implement (green)
# 5. Bump minor version in pyproject.toml
# 6. Update CHANGELOG.md
# 7. Open a PR
```

**Breaking change:**
- Open an issue first — breaking changes need discussion
- Major version bump
- Document the migration path in CHANGELOG.md

---

## Agent cards and skills

Agent cards live in `.claude/agents/` — one markdown file per role.
Skills live in `.claude/skills/<name>/SKILL.md`.

Adding a new agent card or skill:
- Follow the format in `skills/SKILL-AUTHORING.md`
- Test it by running the engagement loop with the new role
- Minor version bump if adding, patch if fixing an existing card

---

## Reporting issues

Open a GitHub issue with:
- What you expected
- What happened instead
- The command you ran and its output
- Your `hssd --version` output
- Your OS and Python version

The janitor also files issues automatically — if you see a janitor-filed issue,
it means the framework detected the problem in its own codebase.
