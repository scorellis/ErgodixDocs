"""
Tests for ergodix.prereqs.check_corpus_path — the B2 prereq from
ADR 0003, refined by ADR 0014.

B2 validates the user's CORPUS_FOLDER and dispatches on detected sync
transport. Unlike pre-ADR-0014 thinking, B2 does NOT install Google
Drive Desktop — that's B1. B2's job is purely:

  - Read CORPUS_FOLDER from local_config.py (via sync_transport helper).
  - If unset / file missing → ok ("deferred"). C4 hasn't run yet on
    a fresh install; halting here would prevent C4 from generating
    local_config.py at all. Verify phase catches the missing-config
    case via _verify_local_config_sane.
  - If set but path doesn't exist → failed ("corpus folder doesn't
    exist"). User-facing misconfiguration.
  - If drive-stream mode → failed ("switch to Mirror"). v1 doesn't
    support Stream mode.
  - drive-mirror or indy → ok with a current_state describing what
    was found.

Tests use tmp_path + monkeypatch.setenv("HOME") + monkeypatch.chdir
so cwd, $HOME, and the file system layout are all controlled.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_B2() -> None:
    from ergodix.prereqs import check_corpus_path

    assert check_corpus_path.OP_ID == "B2"


def test_description_mentions_corpus() -> None:
    from ergodix.prereqs import check_corpus_path

    text = check_corpus_path.DESCRIPTION.lower()
    assert "corpus" in text


# ─── inspect() — deferred cases (ok despite incomplete config) ─────────────


def test_inspect_ok_when_local_config_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No local_config.py at cwd → status="ok" with deferred state.
    On a fresh install, C4 hasn't generated local_config.py yet;
    halting B2 would prevent C4 from ever running. Verify phase is
    the loud failure surface for "you didn't configure anything."""
    from ergodix.prereqs import check_corpus_path

    monkeypatch.chdir(tmp_path)

    result = check_corpus_path.inspect()

    assert result.op_id == "B2"
    assert result.status == "ok"
    assert "defer" in result.current_state.lower() or "local_config" in result.current_state


def test_inspect_ok_when_corpus_folder_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """local_config.py exists but doesn't define CORPUS_FOLDER → ok deferred."""
    from ergodix.prereqs import check_corpus_path

    (tmp_path / "local_config.py").write_text("OTHER_FIELD = 'whatever'\n")
    monkeypatch.chdir(tmp_path)

    result = check_corpus_path.inspect()

    assert result.status == "ok"


# ─── inspect() — failure cases (real misconfigurations) ────────────────────


def test_inspect_failed_when_path_doesnt_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CORPUS_FOLDER set to a path that doesn't resolve on disk →
    status="failed" with remediation telling the user to either
    create the folder or update the path."""
    from ergodix.prereqs import check_corpus_path

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    nonexistent = tmp_path / "Documents" / "MyOpus"  # parent dir doesn't even exist
    (tmp_path / "local_config.py").write_text(
        f"from pathlib import Path\nCORPUS_FOLDER = Path('{nonexistent}')\n"
    )

    result = check_corpus_path.inspect()

    assert result.status == "failed"
    assert str(nonexistent) in result.current_state or "exist" in result.current_state.lower()


def test_inspect_failed_when_drive_stream_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CORPUS_FOLDER under ~/Library/CloudStorage/GoogleDrive-* →
    status="failed" with "switch to Mirror" remediation. v1 doesn't
    support Stream mode."""
    from ergodix.prereqs import check_corpus_path

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    stream_corpus = (
        tmp_path
        / "Library"
        / "CloudStorage"
        / "GoogleDrive-author@example.com"
        / "My Drive"
        / "MyOpus"
    )
    stream_corpus.mkdir(parents=True)  # path exists; only the mode is wrong
    (tmp_path / "local_config.py").write_text(
        f"from pathlib import Path\nCORPUS_FOLDER = Path('{stream_corpus}')\n"
    )

    result = check_corpus_path.inspect()

    assert result.status == "failed"
    # Either current_state or proposed_action must surface "Mirror" so
    # the user knows the fix.
    combined = (result.current_state + " " + (result.proposed_action or "")).lower()
    assert "mirror" in combined
    assert "stream" in combined


# ─── inspect() — happy paths (drive-mirror / indy) ─────────────────────────


def test_inspect_ok_under_drive_mirror_when_path_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CORPUS_FOLDER under ~/My Drive AND the path exists → ok with
    current_state naming the mode."""
    from ergodix.prereqs import check_corpus_path

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    corpus = tmp_path / "My Drive" / "MyOpus"
    corpus.mkdir(parents=True)
    (tmp_path / "local_config.py").write_text(
        f"from pathlib import Path\nCORPUS_FOLDER = Path('{corpus}')\n"
    )

    result = check_corpus_path.inspect()

    assert result.status == "ok"
    msg_lower = result.current_state.lower()
    assert "mirror" in msg_lower or "drive" in msg_lower
    assert str(corpus) in result.current_state


def test_inspect_ok_under_indy_when_path_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CORPUS_FOLDER on local disk (not under any Drive mount) AND
    the path exists → ok with current_state naming indy."""
    from ergodix.prereqs import check_corpus_path

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    corpus = tmp_path / "Documents" / "MyOpus"
    corpus.mkdir(parents=True)
    (tmp_path / "local_config.py").write_text(
        f"from pathlib import Path\nCORPUS_FOLDER = Path('{corpus}')\n"
    )

    result = check_corpus_path.inspect()

    assert result.status == "ok"
    assert "indy" in result.current_state.lower()
    assert str(corpus) in result.current_state


# ─── apply() — no-op for v1 ────────────────────────────────────────────────


def test_apply_is_noop_skipped() -> None:
    """B2's apply() is a no-op for v1. inspect either returns ok
    (no plan entry) or failed (cantilever halts before apply); the
    apply method exists only to satisfy the PrereqSpec protocol."""
    from ergodix.prereqs import check_corpus_path

    result = check_corpus_path.apply()

    assert result.op_id == "B2"
    assert result.status == "skipped"


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_corpus_path

    assert isinstance(check_corpus_path.OP_ID, str)
    assert callable(check_corpus_path.inspect)
    assert callable(check_corpus_path.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "B2" in op_ids, f"B2 not registered; have {sorted(op_ids)}"
