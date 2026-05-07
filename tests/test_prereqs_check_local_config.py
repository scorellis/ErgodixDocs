"""
Tests for ergodix.prereqs.check_local_config — the C4 prereq from ADR 0003.

C4 bootstraps ``local_config.py`` from ``local_config.example.py`` at the
repo root. ADR 0003 requires it to **preserve an existing** local_config.py
(never overwrite — that file holds the user's machine-specific paths and
recreating it from the template would clobber their edits).

C4 is the first *mutative* prereq with real behavior. A1 was read-only with
a no-op apply; this one exercises the full inspect → plan → apply → verify
loop and is what turns the smoke-test verify phase fully green after the
end-to-end install.

Per CLAUDE.md TDD norm: tests landed before implementation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# A minimal local_config.example.py we reuse across the file. Real layout
# (see local_config.example.py at repo root) is more elaborate; the prereq
# only cares that the example file exists and is readable.
_EXAMPLE_CONTENT = '''"""
ErgodixDocs — per-machine local configuration template.
"""

from pathlib import Path

DRIVE_MOUNT_ROOT = Path.home() / "My Drive"
MY_DRIVE = Path.home() / "My Drive"
CORPUS_FOLDER = Path.home() / "My Drive" / "Tapestry of the Mind"
SYNC_MODE = "mirror"
'''


def _seed_example(tmp_path: Path) -> Path:
    """Drop a local_config.example.py into tmp_path. Return its path."""
    example = tmp_path / "local_config.example.py"
    example.write_text(_EXAMPLE_CONTENT)
    return example


# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_C4() -> None:
    from ergodix.prereqs import check_local_config

    assert check_local_config.OP_ID == "C4"


def test_description_mentions_local_config() -> None:
    from ergodix.prereqs import check_local_config

    assert "local_config" in check_local_config.DESCRIPTION.lower()


# ─── inspect() — three states ───────────────────────────────────────────────


def test_inspect_returns_ok_when_local_config_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If local_config.py is already present, no action needed (preserve)."""
    from ergodix.prereqs import check_local_config

    _seed_example(tmp_path)
    (tmp_path / "local_config.py").write_text("# user's existing config\n")
    monkeypatch.chdir(tmp_path)

    result = check_local_config.inspect()

    assert result.op_id == "C4"
    assert result.status == "ok"
    assert result.proposed_action is None
    assert result.needs_action is False  # plan does NOT include it
    assert result.needs_admin is False
    assert result.network_required is False


def test_inspect_returns_needs_install_when_only_example_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fresh checkout: example file exists, local_config.py does not → plan."""
    from ergodix.prereqs import check_local_config

    _seed_example(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = check_local_config.inspect()

    assert result.op_id == "C4"
    assert result.status == "needs-install"
    assert result.proposed_action is not None
    assert "local_config.py" in result.proposed_action
    assert result.needs_action is True
    assert result.needs_admin is False
    assert result.network_required is False


def test_inspect_returns_failed_when_example_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    No template AND no actual config means we can't bootstrap from anything.
    This is a broken repo state — surface as 'failed' so cantilever halts
    via the inspect-failed path before any apply runs.
    """
    from ergodix.prereqs import check_local_config

    monkeypatch.chdir(tmp_path)  # empty dir, neither file present

    result = check_local_config.inspect()

    assert result.op_id == "C4"
    assert result.status == "failed"
    assert result.needs_action is False  # failed inspects never plan apply


def test_inspect_does_not_create_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """inspect() is read-only: must not write local_config.py as a side effect."""
    from ergodix.prereqs import check_local_config

    _seed_example(tmp_path)
    monkeypatch.chdir(tmp_path)

    check_local_config.inspect()

    assert not (tmp_path / "local_config.py").exists()


# ─── apply() — happy path ───────────────────────────────────────────────────


def test_apply_creates_local_config_from_example(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.prereqs import check_local_config

    _seed_example(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = check_local_config.apply()

    config = tmp_path / "local_config.py"
    assert result.op_id == "C4"
    assert result.status == "ok"
    assert config.exists()
    # Content should derive from the example. Exact byte-equality isn't
    # required (a future revision might do path substitution), but a key
    # marker from the template should survive.
    assert "CORPUS_FOLDER" in config.read_text()


def test_apply_sets_mode_600(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Per the file-mode invariants documented in README + auth.py: any file
    that may hold path/secret-adjacent data lands at 0o600. local_config.py
    paths are not credentials but they're machine-specific and the
    invariant is a project-wide rule.
    """
    from ergodix.prereqs import check_local_config

    _seed_example(tmp_path)
    monkeypatch.chdir(tmp_path)

    check_local_config.apply()

    mode = (tmp_path / "local_config.py").stat().st_mode & 0o777
    assert mode == 0o600


# ─── apply() — preserve-existing invariant ──────────────────────────────────


def test_apply_does_not_overwrite_existing_local_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    ADR 0003 op C4 specifies "preserve if present". apply() must never
    clobber a local_config.py the user already has — it holds their
    machine paths and possibly hand-edits.
    """
    from ergodix.prereqs import check_local_config

    _seed_example(tmp_path)
    sentinel = "# DO NOT OVERWRITE — user's hand-edited paths\nCUSTOM = 'mine'\n"
    config = tmp_path / "local_config.py"
    config.write_text(sentinel)
    monkeypatch.chdir(tmp_path)

    result = check_local_config.apply()

    assert result.status == "skipped"
    assert config.read_text() == sentinel


# ─── apply() — failure modes ────────────────────────────────────────────────


def test_apply_returns_failed_when_example_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    apply() is normally only called when inspect() returned needs-install,
    which already requires the example file. But if a future ordering bug
    schedules apply() in a broken-repo state, it must fail gracefully with
    actionable remediation rather than raising or silently writing nothing.
    """
    from ergodix.prereqs import check_local_config

    monkeypatch.chdir(tmp_path)  # no example, no local_config

    result = check_local_config.apply()

    assert result.op_id == "C4"
    assert result.status == "failed"
    assert result.message  # non-empty
    assert result.remediation_hint is not None


# ─── PrereqSpec protocol + cantilever integration ──────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_local_config

    assert isinstance(check_local_config.OP_ID, str)
    assert callable(check_local_config.inspect)
    assert callable(check_local_config.apply)


def test_end_to_end_through_cantilever_creates_local_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Full inspect → plan → apply loop via run_cantilever().

    Fresh dir with only the example file. With consent granted, cantilever
    should plan + apply C4, leaving local_config.py at mode 0o600. Verify
    is left out of this test (verify_checks=[]) — that's covered by the
    cantilever-side tests.
    """
    from ergodix.cantilever import run_cantilever
    from ergodix.prereqs import check_local_config

    _seed_example(tmp_path)
    monkeypatch.chdir(tmp_path)

    class ModulePrereq:
        op_id = check_local_config.OP_ID

        def inspect(self):
            return check_local_config.inspect()

        def apply(self):
            return check_local_config.apply()

    consent_calls: list[int] = []

    def consent(plan):
        consent_calls.append(len(plan.items))
        return True

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[ModulePrereq()],
        consent_fn=consent,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    assert consent_calls == [1], "consent should be asked once with one planned op"
    assert result.outcome == "applied"
    assert (tmp_path / "local_config.py").exists()
    mode = (tmp_path / "local_config.py").stat().st_mode & 0o777
    assert mode == 0o600


def test_registered_in_prereqs_registry() -> None:
    """check_local_config must be in the registry so cantilever picks it up."""
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "C4" in op_ids, f"C4 not registered; have {sorted(op_ids)}"
