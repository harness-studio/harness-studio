"""
test_skill.py — RED-step tests for the `hssd skill` command (cmd_skill / SKILL_CATALOG).

Each test maps exactly to one numbered acceptance criterion (AC1-AC24).
ALL tests are expected to FAIL before any implementation — cmd_skill does not exist yet.

Hermeticity contract (R5):
- Path.home() is monkeypatched to a tmp_path so ~/.hssd/skills.json is never touched.
- Git env vars (GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM, author/committer identity) are forced
  to hermetic values in every subprocess call that touches git.
- Local bare-ish repos are created via `git init + commit` then referenced as file:/// URLs
  (no network access).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

# Snapshot the real ~/.hssd/skills.json mtime BEFORE any test runs (module import time).
# AC24 compares against this to prove the file was never touched during the suite.
_real_skills_json_path = Path(os.path.expanduser("~")) / ".hssd" / "skills.json"
_real_skills_json_mtime_before: float | None = (
    _real_skills_json_path.stat().st_mtime if _real_skills_json_path.exists() else None
)

# ── The symbols under test (cmd_skill + SKILL_CATALOG do NOT exist yet — imports will fail
#    which makes the collection itself red, satisfying the TDD contract) ─────────────────────
from cli.hssd import main, PKG_ROOT, _mirror_if_absent, _mirror_force, cmd_sync  # noqa: F401

# Import the symbols that don't exist yet — these will raise ImportError, turning every
# test in the file red.  We defer with a try/except so we get a clean FAIL not an ERROR
# on the already-implemented symbols, but the individual tests that need cmd_skill / SKILL_CATALOG
# will fail explicitly.
try:
    from cli.hssd import cmd_skill  # type: ignore[attr-defined]
except ImportError:
    cmd_skill = None  # type: ignore[assignment]

try:
    from cli.hssd import SKILL_CATALOG  # type: ignore[attr-defined]
except ImportError:
    SKILL_CATALOG = None  # type: ignore[assignment]


# ── Hermetic git env ────────────────────────────────────────────────────────────────────────
_GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@test.com",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@test.com",
}


def _run(*cmd: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run a shell command with hermetic git env, check=True."""
    return subprocess.run(list(cmd), cwd=str(cwd), env=_GIT_ENV, check=True,
                          capture_output=True, text=True)


# ── Fixtures ────────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def fake_home(tmp_path: Path) -> Path:
    """A throw-away home directory. Monkeypatching Path.home to return this ensures
    ~/.hssd/skills.json is never created or read during the test suite."""
    home = tmp_path / "fake_home"
    home.mkdir()
    return home


@pytest.fixture(autouse=True)
def patch_home(monkeypatch: pytest.MonkeyPatch, fake_home: Path) -> None:
    """Auto-patched for every test: Path.home() -> fake_home.
    NOT patching on the module level (which would only affect the reference at import time)
    but on pathlib.Path.home so _user_catalog_path() calls pick it up."""
    monkeypatch.setattr(pathlib.Path, "home", staticmethod(lambda: fake_home))


@pytest.fixture()
def skill_repo(tmp_path: Path) -> Path:
    """
    A minimal git repo whose root contains SKILL.md.
    Returns the path; callers build `file:///` URLs from it.
    """
    repo = tmp_path / "hssd-skill-foo"
    repo.mkdir()
    (repo / "SKILL.md").write_text("# Test Skill\n", encoding="utf-8")
    _run("git", "init", "-b", "main", cwd=repo)
    _run("git", "add", ".", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)
    return repo


@pytest.fixture()
def nested_skill_repo(tmp_path: Path) -> Path:
    """
    A git repo that does NOT have SKILL.md at root — it lives in a subdirectory.
    Used by AC19 to verify that the command rejects repos without a root SKILL.md.
    """
    repo = tmp_path / "hssd-skill-nested"
    repo.mkdir()
    subdir = repo / "subdir"
    subdir.mkdir()
    (subdir / "SKILL.md").write_text("# Nested Skill\n", encoding="utf-8")
    (repo / "README.md").write_text("no SKILL.md here\n", encoding="utf-8")
    _run("git", "init", "-b", "main", cwd=repo)
    _run("git", "add", ".", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)
    return repo


@pytest.fixture()
def no_skill_repo(tmp_path: Path) -> Path:
    """
    A git repo with only README.md at root (no SKILL.md anywhere).
    Used by AC19 to verify BLOCK on missing SKILL.md.
    """
    repo = tmp_path / "hssd-skill-noskilmd"
    repo.mkdir()
    (repo / "README.md").write_text("# No skill here\n", encoding="utf-8")
    _run("git", "init", "-b", "main", cwd=repo)
    _run("git", "add", ".", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)
    return repo


def _call_main(args: list[str]) -> tuple[int, str, str]:
    """Call main(), capturing stdout/stderr and the return/exit code.
    Catches SystemExit so argparse errors are captured as non-zero return codes."""
    out_buf, err_buf = StringIO(), StringIO()
    rc: int
    # Redirect stdout; stderr stays on sys.stderr but we also redirect it
    orig_stderr = sys.stderr
    try:
        sys.stderr = err_buf
        with redirect_stdout(out_buf):
            try:
                rc = main(args)
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
    finally:
        sys.stderr = orig_stderr
    return rc, out_buf.getvalue(), err_buf.getvalue()


def _skills_json(fake_home: Path) -> Path:
    return fake_home / ".hssd" / "skills.json"


def _write_skills_json(fake_home: Path, entries: list[dict]) -> None:
    p = _skills_json(fake_home)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _read_skills_json(fake_home: Path) -> list[dict]:
    p = _skills_json(fake_home)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def _file_url(path: Path) -> str:
    """Convert an absolute path to a file:/// URL suitable for git clone."""
    # On Windows Path.as_uri() produces file:///C:/... which git accepts.
    return path.as_uri()


# ── helpers that verify SKILL_CATALOG is populated (will fail if it's None) ────────────────

def _require_catalog() -> list[dict]:
    assert SKILL_CATALOG is not None, "SKILL_CATALOG is not defined in cli.hssd (not implemented yet)"
    assert len(SKILL_CATALOG) > 0, "SKILL_CATALOG is empty — no blessed skills registered"
    return SKILL_CATALOG


def _require_cmd_skill():
    assert cmd_skill is not None, "cmd_skill is not defined in cli.hssd (not implemented yet)"
    return cmd_skill


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC1: list exits 0; stdout contains every SKILL_CATALOG name + url, tagged "blessed"
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac1_list_exits0_shows_blessed_catalog():
    """skill list exits 0; every blessed entry (name + url) appears tagged 'blessed'."""
    _require_cmd_skill()
    catalog = _require_catalog()

    rc, out, _ = _call_main(["skill", "list"])

    assert rc == 0, f"skill list exited {rc}, expected 0"
    for entry in catalog:
        assert entry["name"] in out, f"blessed name {entry['name']!r} missing from output"
        assert entry["url"] in out, f"blessed url {entry['url']!r} missing from output"
    assert "blessed" in out, "'blessed' tag not found in output"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC2: with a valid ~/.hssd/skills.json, list also prints user entries tagged "user"
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac2_list_shows_user_entries(fake_home: Path):
    """When skills.json exists with user entries, list prints them tagged 'user'."""
    _require_cmd_skill()
    _write_skills_json(fake_home, [
        {"name": "my-custom-skill", "url": "https://example.com/my-skill", "tech": ["python"]}
    ])

    rc, out, _ = _call_main(["skill", "list"])

    assert rc == 0, f"skill list exited {rc}, expected 0"
    assert "my-custom-skill" in out, "user skill name missing from output"
    assert "https://example.com/my-skill" in out, "user skill url missing from output"
    assert "user" in out, "'user' tag missing from output"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC3: corrupt ~/.hssd/skills.json → list still exits 0, prints blessed rows, no traceback
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac3_list_handles_corrupt_skills_json(fake_home: Path):
    """Corrupt skills.json does not crash; blessed rows still appear."""
    _require_cmd_skill()
    catalog = _require_catalog()

    p = _skills_json(fake_home)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{this is not valid json!!!!}", encoding="utf-8")

    rc, out, err = _call_main(["skill", "list"])

    assert rc == 0, f"skill list exited {rc} with corrupt json, expected 0"
    # Blessed entries still visible
    for entry in catalog:
        assert entry["name"] in out, f"blessed name {entry['name']!r} missing despite corrupt user catalog"
    assert "Traceback" not in err, "traceback leaked on corrupt skills.json"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC4: add --name foo --from=<url> --tech a,b exits 0; skills.json has the right entry
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac4_add_writes_skills_json(fake_home: Path):
    """add with valid args exits 0 and persists correct entry in skills.json."""
    _require_cmd_skill()

    rc, _, _ = _call_main([
        "skill", "add",
        "--name", "foo",
        "--from", "https://example.com/foo-skill",
        "--tech", "a,b",
    ])

    assert rc == 0, f"skill add exited {rc}, expected 0"
    entries = _read_skills_json(fake_home)
    assert len(entries) == 1
    assert entries[0]["name"] == "foo"
    assert entries[0]["url"] == "https://example.com/foo-skill"
    assert entries[0]["tech"] == ["a", "b"]


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC5: add missing --name or --from exits non-zero (BLOCK); skills.json unchanged/uncreated
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac5_add_missing_name_blocks(fake_home: Path):
    """add without --name exits non-zero; skills.json is not created."""
    _require_cmd_skill()

    rc, _, _ = _call_main(["skill", "add", "--from", "https://example.com/skill"])
    assert rc != 0, "skill add without --name must exit non-zero"
    assert not _skills_json(fake_home).exists(), "skills.json must not be created on BLOCK"


def test_ac5_add_missing_from_blocks(fake_home: Path):
    """add without --from exits non-zero; skills.json is not created."""
    _require_cmd_skill()

    rc, _, _ = _call_main(["skill", "add", "--name", "myskill"])
    assert rc != 0, "skill add without --from must exit non-zero"
    assert not _skills_json(fake_home).exists(), "skills.json must not be created on BLOCK"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC6: add with a url already in SKILL_CATALOG exits 0, prints "already known", no duplicate
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac6_add_blessed_url_prints_already_known(fake_home: Path):
    """Adding a URL that already appears in SKILL_CATALOG exits 0 with 'already known' message."""
    _require_cmd_skill()
    catalog = _require_catalog()

    blessed_url = catalog[0]["url"]
    rc, out, _ = _call_main([
        "skill", "add",
        "--name", "duplicate-attempt",
        "--from", blessed_url,
    ])

    assert rc == 0, f"Expected 0 (already known), got {rc}"
    assert "already known" in out.lower(), f"Expected 'already known' in output, got: {out!r}"

    # Must not append a duplicate to user catalog
    entries = _read_skills_json(fake_home)
    assert not any(e.get("url") == blessed_url for e in entries), \
        "Blessed URL must not be duplicated in user skills.json"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC7: add of the same user url twice → exactly one entry
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac7_add_same_url_twice_deduplicates(fake_home: Path):
    """Calling add twice with the same user URL yields exactly one entry."""
    _require_cmd_skill()

    url = "https://example.com/my-unique-skill"
    _call_main(["skill", "add", "--name", "myskill", "--from", url])
    rc, out, _ = _call_main(["skill", "add", "--name", "myskill-copy", "--from", url])

    assert rc == 0, f"Second add exited {rc}, expected 0"
    entries = _read_skills_json(fake_home)
    matching = [e for e in entries if e.get("url") == url]
    assert len(matching) == 1, f"Expected exactly 1 entry for {url!r}, got {len(matching)}"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC8: rm --name foo after add exits 0 and removes it (add→rm round-trips to empty)
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac8_rm_after_add_round_trips_to_empty(fake_home: Path):
    """add then rm --name leaves skills.json empty."""
    _require_cmd_skill()

    _call_main(["skill", "add", "--name", "temp", "--from", "https://example.com/temp"])
    assert len(_read_skills_json(fake_home)) == 1

    rc, _, _ = _call_main(["skill", "rm", "--name", "temp"])
    assert rc == 0, f"skill rm exited {rc}, expected 0"
    assert _read_skills_json(fake_home) == [], "Expected empty user catalog after rm"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC9: rm --name <blessed-name> exits 0, prints "not in your registry", blessed unchanged
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac9_rm_blessed_name_prints_not_in_registry(fake_home: Path):
    """Attempting to rm a blessed skill name exits 0 and says it's not in the user registry."""
    _require_cmd_skill()
    catalog = _require_catalog()

    blessed_name = catalog[0]["name"]
    rc, out, _ = _call_main(["skill", "rm", "--name", blessed_name])

    assert rc == 0, f"skill rm blessed exited {rc}, expected 0"
    assert "not in your registry" in out.lower(), \
        f"Expected 'not in your registry' in output, got: {out!r}"

    # The blessed catalog must still be intact
    rc2, out2, _ = _call_main(["skill", "list"])
    assert rc2 == 0
    assert blessed_name in out2, "Blessed skill disappeared from list after attempted rm"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC10: rm with neither --name nor --from exits non-zero (BLOCK)
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac10_rm_no_args_blocks():
    """skill rm without --name or --from exits non-zero."""
    _require_cmd_skill()

    rc, _, _ = _call_main(["skill", "rm"])
    assert rc != 0, "skill rm with no args must exit non-zero (BLOCK)"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC11: user entry whose name == blessed name is removable; blessed still shows in list
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac11_user_entry_same_name_as_blessed_is_removable(fake_home: Path):
    """A user entry whose name collides with a blessed name can be removed; the blessed remains."""
    _require_cmd_skill()
    catalog = _require_catalog()

    blessed_name = catalog[0]["name"]
    # Register a *user* entry under the same name (different URL)
    _write_skills_json(fake_home, [
        {"name": blessed_name, "url": "https://example.com/user-copy", "tech": []}
    ])

    rc, _, _ = _call_main(["skill", "rm", "--name", blessed_name])
    assert rc == 0

    # User entry gone
    entries = _read_skills_json(fake_home)
    assert not any(e.get("name") == blessed_name for e in entries), \
        "User entry with blessed name not removed"

    # Blessed entry still in list
    rc2, out2, _ = _call_main(["skill", "list"])
    assert rc2 == 0
    assert blessed_name in out2, "Blessed entry disappeared from list after removing user copy"
    assert "blessed" in out2, "'blessed' tag must still appear in list"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC12: import --from=file:///path exits 0; creates <project>/.claude/skills/<name>/SKILL.md
#        with content equal to source
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac12_import_creates_skill_md(tmp_path: Path, skill_repo: Path):
    """import from a local file:// repo creates .claude/skills/<name>/SKILL.md."""
    _require_cmd_skill()

    project = tmp_path / "project"
    project.mkdir()
    url = _file_url(skill_repo)

    rc, out, err = _call_main(["skill", "import", "--from", url, "--into", str(project)])

    assert rc == 0, f"skill import exited {rc}; stderr={err!r}"
    installed = project / ".claude" / "skills" / "foo" / "SKILL.md"
    assert installed.exists(), f"SKILL.md not created at {installed}"
    assert installed.read_text(encoding="utf-8") == "# Test Skill\n", \
        "Installed SKILL.md content does not match source"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC13: after import, <project>/.claude/skills/<name>/.git does NOT exist
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac13_import_strips_git_dir(tmp_path: Path, skill_repo: Path):
    """After import, no .git directory is left inside the installed skill folder."""
    _require_cmd_skill()

    project = tmp_path / "project"
    project.mkdir()
    url = _file_url(skill_repo)

    rc, _, _ = _call_main(["skill", "import", "--from", url, "--into", str(project)])
    assert rc == 0

    git_dir = project / ".claude" / "skills" / "foo" / ".git"
    assert not git_dir.exists(), f".git directory must not be present after import: {git_dir}"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC14: name resolves from repo dir with hssd-skill- stripped;
#        --name bar overrides to skills/bar/
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac14_name_stripped_from_repo_dir(tmp_path: Path, skill_repo: Path):
    """Repo named 'hssd-skill-foo' installs to skills/foo/ (strip prefix)."""
    _require_cmd_skill()

    project = tmp_path / "project"
    project.mkdir()

    rc, _, _ = _call_main(["skill", "import", "--from", _file_url(skill_repo), "--into", str(project)])
    assert rc == 0
    assert (project / ".claude" / "skills" / "foo" / "SKILL.md").exists()


def test_ac14_name_override_with_name_arg(tmp_path: Path, skill_repo: Path):
    """--name bar overrides auto-resolved name; installs to skills/bar/."""
    _require_cmd_skill()

    project = tmp_path / "project"
    project.mkdir()

    rc, _, _ = _call_main([
        "skill", "import",
        "--from", _file_url(skill_repo),
        "--name", "bar",
        "--into", str(project),
    ])
    assert rc == 0
    assert (project / ".claude" / "skills" / "bar" / "SKILL.md").exists(), \
        "Expected skill installed under skills/bar/ when --name bar is given"
    # The auto-named path must NOT exist
    assert not (project / ".claude" / "skills" / "foo" / "SKILL.md").exists(), \
        "auto-named skills/foo/ must not exist when --name bar overrides it"


def test_ac14_plain_name_no_prefix_stripping(tmp_path: Path, tmp_path_factory):
    """Repo named 'myskill' (no hssd-skill- prefix) installs to skills/myskill/."""
    _require_cmd_skill()

    repo_root = tmp_path_factory.mktemp("repos")
    repo = repo_root / "myskill"
    repo.mkdir()
    (repo / "SKILL.md").write_text("# My Skill\n", encoding="utf-8")
    _run("git", "init", "-b", "main", cwd=repo)
    _run("git", "add", ".", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)

    project = tmp_path / "project"
    project.mkdir()

    rc, _, _ = _call_main([
        "skill", "import",
        "--from", _file_url(repo),
        "--into", str(project),
    ])
    assert rc == 0
    assert (project / ".claude" / "skills" / "myskill" / "SKILL.md").exists()


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC15: re-running the same import is idempotent: exits 0, reports "created 0", no changes
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac15_import_idempotent(tmp_path: Path, skill_repo: Path):
    """Running import twice exits 0 and reports 'created 0' on the second run."""
    _require_cmd_skill()

    project = tmp_path / "project"
    project.mkdir()
    url = _file_url(skill_repo)

    _call_main(["skill", "import", "--from", url, "--into", str(project)])
    installed = project / ".claude" / "skills" / "foo" / "SKILL.md"
    mtime_before = installed.stat().st_mtime

    rc, out, _ = _call_main(["skill", "import", "--from", url, "--into", str(project)])
    assert rc == 0, f"Second import exited {rc}, expected 0"
    assert "created 0" in out.lower(), \
        f"Expected 'created 0' in second import output, got: {out!r}"

    # File must not have been modified
    mtime_after = installed.stat().st_mtime
    assert mtime_before == mtime_after, \
        "SKILL.md modification time changed on idempotent re-import"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC16: import where SKILL.md already exists keeps the existing file; only new files added
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac16_import_keeps_existing_skill_md(tmp_path: Path, skill_repo: Path):
    """Existing SKILL.md is not overwritten; only new files from the repo are added."""
    _require_cmd_skill()

    project = tmp_path / "project"
    project.mkdir()
    url = _file_url(skill_repo)

    # Pre-create a customized SKILL.md
    skills_dir = project / ".claude" / "skills" / "foo"
    skills_dir.mkdir(parents=True)
    custom_content = "# My Custom Skill — do not overwrite\n"
    (skills_dir / "SKILL.md").write_text(custom_content, encoding="utf-8")

    rc, _, _ = _call_main(["skill", "import", "--from", url, "--into", str(project)])
    assert rc == 0

    actual = (skills_dir / "SKILL.md").read_text(encoding="utf-8")
    assert actual == custom_content, \
        f"SKILL.md was overwritten; expected {custom_content!r}, got {actual!r}"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC17: re-import of a repo whose SKILL.md changed keeps OLD content (install-once pinned)
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac17_reimport_after_upstream_change_keeps_old(tmp_path: Path, tmp_path_factory):
    """After upstream SKILL.md changes, re-import keeps the old installed content (pinned)."""
    _require_cmd_skill()

    # Build the initial repo
    repo_root = tmp_path_factory.mktemp("repos17")
    repo = repo_root / "hssd-skill-pinned"
    repo.mkdir()
    (repo / "SKILL.md").write_text("# Version 1\n", encoding="utf-8")
    _run("git", "init", "-b", "main", cwd=repo)
    _run("git", "add", ".", cwd=repo)
    _run("git", "commit", "-m", "v1", cwd=repo)

    project = tmp_path / "project"
    project.mkdir()
    url = _file_url(repo)

    # First import
    rc, _, _ = _call_main(["skill", "import", "--from", url, "--into", str(project)])
    assert rc == 0
    installed = project / ".claude" / "skills" / "pinned" / "SKILL.md"
    assert "Version 1" in installed.read_text(encoding="utf-8")

    # Mutate the upstream repo
    (repo / "SKILL.md").write_text("# Version 2 — upstream changed\n", encoding="utf-8")
    _run("git", "add", ".", cwd=repo)
    _run("git", "commit", "-m", "v2", cwd=repo)

    # Re-import: old content must survive (install-once pinning)
    rc2, out2, _ = _call_main(["skill", "import", "--from", url, "--into", str(project)])
    assert rc2 == 0
    content_after = installed.read_text(encoding="utf-8")
    assert "Version 1" in content_after, \
        "Re-import overwrote pinned SKILL.md — expected old content to be kept"
    assert "Version 2" not in content_after, \
        "Upstream v2 bled into the installed skill — install-once semantics violated"
    # The output should mention 'skipped'
    assert "skipped" in out2.lower(), f"Expected 'skipped' in re-import output, got: {out2!r}"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC18: import missing --from exits non-zero (BLOCK)
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac18_import_missing_from_blocks(tmp_path: Path):
    """skill import without --from exits non-zero."""
    _require_cmd_skill()

    project = tmp_path / "project"
    project.mkdir()

    rc, _, err = _call_main(["skill", "import", "--into", str(project)])
    assert rc != 0, "skill import without --from must exit non-zero (BLOCK)"
    assert "BLOCK" in err or "block" in err.lower() or "from" in err.lower(), \
        f"Expected a BLOCK/error message about --from, got: {err!r}"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC19: import --from=<repo-without-SKILL.md-at-root> exits non-zero; installs nothing
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac19_import_nested_skill_md_blocks(tmp_path: Path, nested_skill_repo: Path):
    """Repo with SKILL.md only in a subdirectory (not root) → BLOCK; nothing installed."""
    _require_cmd_skill()

    project = tmp_path / "project"
    project.mkdir()
    url = _file_url(nested_skill_repo)

    rc, _, _ = _call_main(["skill", "import", "--from", url, "--into", str(project)])
    assert rc != 0, "import of nested-only SKILL.md must exit non-zero (BLOCK)"

    skills_dir = project / ".claude" / "skills"
    assert not skills_dir.exists() or not any(skills_dir.iterdir()), \
        "Nothing must be installed when SKILL.md is not at root"


def test_ac19_import_no_skill_md_blocks(tmp_path: Path, no_skill_repo: Path):
    """Repo with no SKILL.md at all → BLOCK; nothing installed."""
    _require_cmd_skill()

    project = tmp_path / "project"
    project.mkdir()
    url = _file_url(no_skill_repo)

    rc, _, _ = _call_main(["skill", "import", "--from", url, "--into", str(project)])
    assert rc != 0, "import of repo with no SKILL.md must exit non-zero (BLOCK)"

    skills_dir = project / ".claude" / "skills"
    assert not skills_dir.exists() or not any(skills_dir.iterdir()), \
        "Nothing must be installed when repo has no SKILL.md"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC20: --into <dir> directs install to that dir, not cwd
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac20_into_directs_install(tmp_path: Path, skill_repo: Path):
    """--into <dir> installs into that directory's .claude/skills/, not cwd."""
    _require_cmd_skill()

    project = tmp_path / "target_project"
    project.mkdir()
    other = tmp_path / "other_dir"
    other.mkdir()

    # Run from a different cwd by starting the process from `other`; the CLI's cwd will be
    # wherever the test process is, but --into forces the correct install target.
    rc, _, _ = _call_main(["skill", "import", "--from", _file_url(skill_repo), "--into", str(project)])
    assert rc == 0

    # Must appear under the specified --into dir
    assert (project / ".claude" / "skills" / "foo" / "SKILL.md").exists(), \
        "Skill not installed into the --into directory"

    # Must NOT appear under the other dir
    other_skills = other / ".claude" / "skills"
    assert not other_skills.exists() or not any(other_skills.rglob("SKILL.md")), \
        "Skill was spuriously installed into the wrong directory"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC21: import whose resolved name collides with a blessed framework skill name → BLOCK;
#        installs nothing (test with "python" and "harness-studio")
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac21_import_collides_with_blessed_python_blocks(tmp_path: Path, tmp_path_factory):
    """Repo whose resolved name is 'python' (a blessed framework skill) → BLOCK."""
    _require_cmd_skill()

    repo_root = tmp_path_factory.mktemp("repos21a")
    repo = repo_root / "hssd-skill-python"
    repo.mkdir()
    (repo / "SKILL.md").write_text("# Fake Python Skill\n", encoding="utf-8")
    _run("git", "init", "-b", "main", cwd=repo)
    _run("git", "add", ".", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)

    project = tmp_path / "project_python"
    project.mkdir()

    rc, _, err = _call_main([
        "skill", "import",
        "--from", _file_url(repo),
        "--into", str(project),
    ])
    assert rc != 0, "import whose resolved name is 'python' (blessed) must BLOCK"

    skills_dir = project / ".claude" / "skills"
    assert not skills_dir.exists() or not any(skills_dir.iterdir()), \
        "Nothing must be installed on blessed-name collision (python)"


def test_ac21_import_collides_with_blessed_harness_studio_blocks(tmp_path: Path, tmp_path_factory):
    """Repo whose resolved name is 'harness-studio' (a blessed framework skill) → BLOCK."""
    _require_cmd_skill()

    repo_root = tmp_path_factory.mktemp("repos21b")
    repo = repo_root / "hssd-skill-harness-studio"
    repo.mkdir()
    (repo / "SKILL.md").write_text("# Fake Harness Studio Skill\n", encoding="utf-8")
    _run("git", "init", "-b", "main", cwd=repo)
    _run("git", "add", ".", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)

    project = tmp_path / "project_hs"
    project.mkdir()

    rc, _, err = _call_main([
        "skill", "import",
        "--from", _file_url(repo),
        "--into", str(project),
    ])
    assert rc != 0, "import whose resolved name is 'harness-studio' (blessed) must BLOCK"

    skills_dir = project / ".claude" / "skills"
    assert not skills_dir.exists() or not any(skills_dir.iterdir()), \
        "Nothing must be installed on blessed-name collision (harness-studio)"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC22: import resolving to an empty name (repo "hssd-skill-") → BLOCK
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac22_import_empty_name_after_prefix_strip_blocks(tmp_path: Path, tmp_path_factory):
    """Repo named exactly 'hssd-skill-' yields empty name after stripping prefix → BLOCK."""
    _require_cmd_skill()

    repo_root = tmp_path_factory.mktemp("repos22")
    # Directory name is "hssd-skill-" — after stripping "hssd-skill-" the name is ""
    repo = repo_root / "hssd-skill-"
    repo.mkdir()
    (repo / "SKILL.md").write_text("# Empty Name Skill\n", encoding="utf-8")
    _run("git", "init", "-b", "main", cwd=repo)
    _run("git", "add", ".", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)

    project = tmp_path / "project22"
    project.mkdir()

    rc, _, err = _call_main([
        "skill", "import",
        "--from", _file_url(repo),
        "--into", str(project),
    ])
    assert rc != 0, "import resolving to empty name must exit non-zero (BLOCK)"

    skills_dir = project / ".claude" / "skills"
    assert not skills_dir.exists() or not any(skills_dir.iterdir()), \
        "Nothing must be installed when resolved name is empty"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC23: after cmd_sync, a previously imported NON-framework skill is left intact
#        (sync only overwrites framework-shipped names)
#
#        NOTE: cmd_sync currently overwrites ALL skills, so this test WILL fail red
#        until the constrained behavior is implemented — that is the point.
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac23_sync_preserves_user_imported_skill(tmp_path: Path, skill_repo: Path, monkeypatch):
    """cmd_sync must NOT overwrite a user-imported skill that has no matching framework name."""
    _require_cmd_skill()

    project = tmp_path / "project23"
    project.mkdir()

    # Import the user skill first
    url = _file_url(skill_repo)
    rc, _, _ = _call_main(["skill", "import", "--from", url, "--into", str(project)])
    assert rc == 0
    installed = project / ".claude" / "skills" / "foo" / "SKILL.md"
    assert installed.exists()
    original_content = installed.read_text(encoding="utf-8")

    # Run cmd_sync (the constrained implementation should leave user skills alone)
    # We monkeypatch cwd to the project directory so cmd_sync operates on it
    monkeypatch.chdir(project)
    import argparse
    sync_args = argparse.Namespace()
    result = cmd_sync(sync_args)
    assert result == 0, f"cmd_sync returned {result}, expected 0"

    # The user-imported skill must be intact
    assert installed.exists(), "User-imported SKILL.md was deleted by sync"
    content_after = installed.read_text(encoding="utf-8")
    assert content_after == original_content, \
        f"User-imported SKILL.md was overwritten by sync. Before: {original_content!r}, " \
        f"after: {content_after!r}"


# ══════════════════════════════════════════════════════════════════════════════════════════
# AC24: the real ~/.hssd/skills.json is NEVER created/modified by the suite
#        (the home monkeypatch sentinel — verified at end of suite)
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_ac24_real_home_skills_json_untouched(fake_home: Path, monkeypatch: pytest.MonkeyPatch):
    """The REAL ~/.hssd/skills.json must not be created or modified by any test in this suite.

    This test acts as a sentinel: it verifies the monkeypatch contract holds by asserting
    Path.home() returns our fake_home (not the real home directory) and that the real
    ~/.hssd/skills.json file does not exist or is unchanged.
    """
    _require_cmd_skill()

    # Verify the monkeypatch is in effect
    patched_home = Path.home()
    assert patched_home == fake_home, \
        f"Path.home() patch not active: got {patched_home}, expected {fake_home}"

    # Verify Path.home() now routes through fake_home (not real home).
    skills_path_via_patched = Path.home() / ".hssd" / "skills.json"
    assert str(skills_path_via_patched).startswith(str(fake_home)), \
        f"skills.json path {skills_path_via_patched} does not resolve through fake_home"

    # Run a harmless list to exercise the code path
    rc, _, _ = _call_main(["skill", "list"])
    assert rc == 0

    # Compare real file against the module-level snapshot taken before any test ran.
    if _real_skills_json_mtime_before is not None:
        assert _real_skills_json_path.stat().st_mtime == _real_skills_json_mtime_before, \
            "Real ~/.hssd/skills.json was modified during the test suite — monkeypatch leaked"
    else:
        assert not _real_skills_json_path.exists(), \
            "Real ~/.hssd/skills.json was CREATED during the test suite — monkeypatch leaked"


# ══════════════════════════════════════════════════════════════════════════════════════════
# Extra coverage: add without --tech (empty tech list) + rm by --from=<url>
# (gaps identified by the completion-challenger / test-adversary in P4)
# ══════════════════════════════════════════════════════════════════════════════════════════

def test_add_tech_omitted_yields_empty_list(fake_home: Path):
    """skill add without --tech stores an empty tech list, not None or an error."""
    _require_cmd_skill()

    rc, _, _ = _call_main(["skill", "add", "--name", "bare", "--from", "https://example.com/bare"])
    assert rc == 0, f"skill add without --tech exited {rc}, expected 0"
    entries = _read_skills_json(fake_home)
    assert len(entries) == 1
    assert entries[0]["tech"] == [], f"Expected tech=[], got {entries[0].get('tech')!r}"


def test_rm_by_url_removes_entry(fake_home: Path):
    """skill rm --from=<url> removes the matching entry (remove by URL, not name)."""
    _require_cmd_skill()

    url = "https://example.com/rm-by-url-skill"
    _call_main(["skill", "add", "--name", "url-skill", "--from", url])
    assert len(_read_skills_json(fake_home)) == 1

    rc, _, _ = _call_main(["skill", "rm", "--from", url])
    assert rc == 0, f"skill rm --from exited {rc}, expected 0"
    assert _read_skills_json(fake_home) == [], "Entry not removed when rm uses --from=<url>"


def test_rm_by_url_does_not_match_none_url_entries(fake_home: Path):
    """rm --name only never removes entries whose 'url' key is missing (None!=None guard)."""
    _require_cmd_skill()

    # Write a malformed entry (missing url key) directly
    p = _skills_json(fake_home)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([{"name": "good-entry", "url": "https://example.com/good"},
                              {"name": "no-url-entry"}], indent=2), encoding="utf-8")

    rc, _, _ = _call_main(["skill", "rm", "--name", "good-entry"])
    assert rc == 0
    remaining = _read_skills_json(fake_home)
    assert len(remaining) == 1, "rm by name accidentally removed the entry missing a 'url' key"
    assert remaining[0]["name"] == "no-url-entry"
