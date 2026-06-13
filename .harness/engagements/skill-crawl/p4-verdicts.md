# P4 Adversarial Verdicts — skill-crawl

Date: 2026-06-13. All adversaries ran independently (maker ≠ checker).

## independent-verifier → PASS
All 24 ACs met. Cross-checked implementation vs. tests (not just the green run):
- AC21 collision guard fires BEFORE any file write (confirmed)
- AC23 cmd_sync only force-overwrites names from _blessed_skill_names() (confirmed)
- AC14 uses str.removeprefix("hssd-skill-"), not regex (confirmed)
- AC17 _mirror_if_absent never overwrites — install-once pinned (confirmed)
- AC24 Path.home patch at pathlib.Path.home, called at runtime not import time (confirmed)

## regression-hunter → PASS
No regressions found:
- _load_user_catalog refactor: delegates to _load_catalog_file, identical behavior
- cmd_sync guard: d.name in blessed is always True for dirs in skills_root — no framework skill filtered
- cmd_work claim → _git_switch: safe improvement (handles "already exists" correctly)
- _log template import: `or args.template` was a latent AttributeError (never reached); removal is safe
- No other callers broken

## test-adversary → BLOCK (fixed in P3b loop)
Defects found and fixed:
1. AC6/AC1 VACUOUS: all 10 SKILL_CATALOG URLs were identical. Fixed: each entry now has a
   distinct URL (hssd-skill-<name> pattern).
2. AC15 WEAK ASSERTION: `"created 0" in out.lower() or "0" in out` — the `or "0" in out`
   branch was trivially true. Fixed: assertion is now `"created 0" in out.lower()` only.
3. AC24 DEAD SENTINEL: mtime comparison logic had a boolean short-circuit that always passed
   when ~/.hssd didn't exist. Fixed: now uses module-level snapshot of mtime before any test
   ran, with clear created/modified branching.

## completion-challenger → BLOCK (fixed in P3b loop)
Defects found and fixed:
1. `rm` None==None LATENT BUG: predicate `e.get("name") != args.name and e.get("url") !=
   args.from_git` — when args.from_git is None and an entry has no "url" key, None!=None is
   False, causing over-deletion. Fixed: predicate now explicitly guards on args.from_git.
2. `skill` missing from CLI docstring (hssd.py Surface line). Fixed.
3. `rm --from=<url>` untested. Fixed: added test_rm_by_url_removes_entry.
4. `add` without --tech untested. Fixed: added test_add_tech_omitted_yields_empty_list.
5. None-url latent bug: added test_rm_by_url_does_not_match_none_url_entries.

Advisory (not blocking, addressed separately):
- ADR.md and AI_LOG.md governance deliverables: built in docs/ per CLAUDE.md mandate.
- CLI.md skill section: to be added as part of this PR.

## Final state after P4 fixes
32/32 tests pass. All P4 BLOCKs resolved. Loop-until-dry: no adversary returned a new
BLOCK on the fixed implementation.
