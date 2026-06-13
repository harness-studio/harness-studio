# Locked-spec candidate — `hssd skill` (Crawl slice)

> Dogfood engagement. P0–P2 ran as the governed loop: architect (maker) proposed, architecture-adversary (independent checker) attacked. This is the synthesized spec for the **Spec Lock** human gate. No code is written until the human approves.

## Story
As a Harness Studio user, I can discover, import, and register **skills** the same way I do templates — so a skill (`<name>/SKILL.md` directory) becomes an importable unit, not a framework-bundled, hardcoded one. Mirrors `hssd template`: `list / import / add / rm`, a blessed in-code catalog + a user catalog at `~/.hssd/skills.json`, non-destructive install into `.claude/skills/<name>/`.

## Design decisions (architect + adversary resolutions folded in)

1. **Command surface:** `hssd skill list | import --from=<git> [--into <dir>] | add --name <n> --from=<git> [--tech a,b] | rm --name <n>`. New `skill` subparser mirroring the `template` one.
2. **Data:** in-code `SKILL_CATALOG` (blessed) + user catalog `~/.hssd/skills.json`. Refactor `_load_user_catalog()` → `_load_catalog_file(path)` (shared tolerant parse); add `_skill_user_catalog_path()`, `_load_skill_user_catalog()`, `_full_skill_catalog()`. Reuse `_mirror_if_absent` verbatim.
3. **import:** require `--from`; `git clone --depth 1` into tmp; strip `.git`; resolve `<name>` = `--name` else repo dir name with `hssd-skill-` prefix stripped, via `_slug()`; require `SKILL.md` **at incoming root** (nested → BLOCK); install via `_mirror_if_absent` into `<project>/.claude/skills/<name>/`; surface `(created N, kept M)`; clean tmp.
4. **list/add/rm:** mirror `cmd_template` exactly against the skill catalog/path (same predicates + message strings). `add` dedups by url against the full catalog; `rm` mutates only the user catalog (blessed not removable; a user entry shadowing a blessed name is still removable).

### Resolutions from the adversary (★ = the catch that justified the review)

- **★ R1 — collision with the framework's own skills.** `_wire_claude` already mirrors `PKG_ROOT/skills/*` → `.claude/skills/<name>` on `new`/`init`, and `cmd_sync` **force-overwrites** them. So an imported skill sharing a blessed name would be half-merged now and clobbered by a future `hssd sync`. → **BLOCK import when the resolved name collides with a `PKG_ROOT/skills/<dir>` blessed name** (clear message), AND **constrain `cmd_sync` to only overwrite known framework-shipped skill names** so it can never silently destroy an imported skill.
- **R2 — empty-slug guard.** A repo named `hssd-skill-` (or non-latin) slugs to empty → would write `SKILL.md` at the skills root. → **BLOCK if the resolved name is empty.**
- **R3 — install-once semantics pinned.** Create-if-absent means re-importing a repo whose `SKILL.md` changed keeps the OLD content (skipped). → keep non-destructive behavior, but the message says so, and an AC pins it. (An `--update` path is out of scope / Walk.)
- **R4 — `--into` must be an existing directory** → BLOCK otherwise (tighter than template's loose behavior; the right call for one-blessed-way).
- **R5 — test hermeticity.** Monkeypatch `Path.home` to a tmp dir; clone from a **local** git fixture (`file://`, no network); clear `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM` in the fixture; assert the real `~/.hssd` is untouched after the suite.

## Acceptance criteria (objective, testable → become `tests/`)

**list**
1. `skill list` exits 0; stdout contains every `SKILL_CATALOG` name + url, tagged `blessed`.
2. With a valid `~/.hssd/skills.json` (home monkeypatched), `list` also prints those entries tagged `user`.
3. With a **corrupt** `~/.hssd/skills.json`, `list` still exits 0 and prints blessed rows (no traceback).

**add**
4. `add --name foo --from=<url> --tech a,b` exits 0; `skills.json` then has `{"name":"foo","url":<url>,"tech":["a","b"]}`.
5. `add` missing `--name` or `--from` exits non-zero with `BLOCK`; `skills.json` unchanged/uncreated.
6. `add` with a url already in `SKILL_CATALOG` exits 0, prints `already known`, no duplicate appended.
7. `add` of the same user url twice → exactly one entry.

**rm**
8. `rm --name foo` after add exits 0 and removes it (add→rm round-trips to empty).
9. `rm --name <blessed-name>` exits 0, prints "not in your registry", blessed listing unchanged.
10. `rm` with neither `--name` nor `--from` exits non-zero with `BLOCK`.
11. A user entry whose name equals a blessed name is removable from the user catalog; the blessed one still shows in `list`.

**import**
12. `import --from=<local-skill-repo>` exits 0; creates `<project>/.claude/skills/<name>/SKILL.md` equal to source.
13. After import, `<project>/.claude/skills/<name>/.git` does NOT exist.
14. Name resolves from repo dir with `hssd-skill-` stripped (`hssd-skill-foo` → `skills/foo/`); `--name bar` overrides to `skills/bar/`.
15. Re-running the same import is idempotent: exits 0, reports `created 0`, no existing file modified.
16. Import where `.claude/skills/<name>/SKILL.md` already exists keeps the existing file; only new files added.
17. Re-import of a repo whose `SKILL.md` **changed** keeps the OLD content (reports skipped) — install-once pinned.
18. `import` missing `--from` exits non-zero with `BLOCK`.
19. `import --from=<repo-without-SKILL.md-at-root>` (incl. nested `subdir/SKILL.md`) exits non-zero with `BLOCK`; installs nothing under `.claude/skills/`.
20. `--into <dir>` directs install to that dir, not cwd.
21. **★ `import` whose resolved name collides with a blessed framework skill name (e.g. `python`, `harness-studio`) exits non-zero with `BLOCK`; installs nothing.**
22. `import` resolving to an empty name (repo `hssd-skill-`) exits non-zero with `BLOCK`.
23. After `cmd_sync`, a previously imported NON-framework skill under `.claude/skills/` is left intact (sync only overwrites framework-shipped names).
24. The real `~/.hssd/skills.json` is never created/modified by the suite (home-monkeypatch sentinel).

## Test approach
- New `tests/` dir; `pytest` added to `pyproject.toml` dev deps; runnable via `uv run pytest`.
- Local git fixture: build a temp skill dir, `git init` + commit, clone via `file://` path — no network.
- `Path.home` monkeypatched to a tmp dir; `GIT_CONFIG_GLOBAL`/`SYSTEM` cleared for hermetic clones.

## Out of scope (Walk/Run)
`skill.yaml` manifest; `.harness/skills.json` routing; data-driven role→skill routing; running `check.cmd` in `engage`; Bash whitelist from `check.needs`; extracting blessed skills to real `hssd-skill-*` repos.

---
**Verdict of P0–P2:** architecture-adversary returned **PASS** with advisories (all folded above). Awaiting human **Spec Lock**.
