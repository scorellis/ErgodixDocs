"""
Tests for ergodix.prereqs.check_drive_desktop — the B1 prereq from ADR 0003.

B1 ensures Google Drive for Desktop is installed. The migrate / sync
flows depend on Drive's local Mirror mount being present so chapter
files round-trip without API calls (per ADR 0006).

Inspect detects via `/Applications/Google Drive.app` (macOS install
location). Apply runs `brew install --cask google-drive`, which needs
admin (sudo) because `--cask` writes to `/Applications`.

Tests use ``pathlib.Path.is_dir`` and ``subprocess.run`` monkeypatching
so the suite never actually invokes brew or touches the filesystem.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_B1() -> None:
    from ergodix.prereqs import check_drive_desktop

    assert check_drive_desktop.OP_ID == "B1"


def test_description_mentions_drive() -> None:
    from ergodix.prereqs import check_drive_desktop

    assert "drive" in check_drive_desktop.DESCRIPTION.lower()


# ─── inspect() ──────────────────────────────────────────────────────────────


def test_inspect_returns_ok_when_drive_app_installed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_drive_desktop

    def fake_is_dir(self: Path) -> bool:
        return str(self) == "/Applications/Google Drive.app"

    monkeypatch.setattr(Path, "is_dir", fake_is_dir)
    # No local_config.py in tmp_path → detect_current_sync_transport()
    # returns drive-mirror (safe default) → existing B1 inspect logic runs.
    monkeypatch.chdir(tmp_path)

    result = check_drive_desktop.inspect()

    assert result.op_id == "B1"
    assert result.status == "ok"
    assert result.needs_action is False
    assert result.network_required is True


def test_inspect_returns_needs_install_when_drive_app_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_drive_desktop

    monkeypatch.setattr(Path, "is_dir", lambda _self: False)
    monkeypatch.chdir(tmp_path)

    result = check_drive_desktop.inspect()

    assert result.status == "needs-install"


# ─── ADR 0014 — B1 conditional on detected sync transport ────────────────
#
# Per ADR 0014 §5: B1 short-circuits to status="ok" under indy mode —
# the user doesn't sync via Drive, so installing Drive Desktop would be
# gratuitous bloat. Detection happens at the top of inspect().


def test_inspect_returns_ok_under_indy_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When local_config.py points CORPUS_FOLDER at a path outside any
    Drive mount, B1 reports ok regardless of whether Google Drive.app
    is on disk. The current_state must mention 'indy' so plan-display
    output makes the short-circuit visible to the user."""
    from ergodix.prereqs import check_drive_desktop

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "local_config.py"
    config.write_text(
        f"from pathlib import Path\nCORPUS_FOLDER = Path('{tmp_path / 'Documents' / 'MyOpus'}')\n"
    )
    # Drive.app explicitly absent — should not matter under indy.
    monkeypatch.setattr(Path, "is_dir", lambda _self: False)

    result = check_drive_desktop.inspect()

    assert result.status == "ok"
    assert result.needs_action is False
    assert "indy" in result.current_state.lower()


def test_inspect_under_indy_mode_short_circuits_even_when_drive_app_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even if the user happens to have Google Drive.app installed,
    indy mode means B1 doesn't care — same 'ok / indy' short-circuit.
    The original Drive-app detection only matters when sync mode is
    drive-mirror."""
    from ergodix.prereqs import check_drive_desktop

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "local_config.py"
    config.write_text(
        f"from pathlib import Path\nCORPUS_FOLDER = Path('{tmp_path / 'Documents' / 'MyOpus'}')\n"
    )
    monkeypatch.setattr(Path, "is_dir", lambda self: str(self) == "/Applications/Google Drive.app")

    result = check_drive_desktop.inspect()

    assert result.status == "ok"
    assert "indy" in result.current_state.lower()


def test_inspect_keeps_existing_behavior_under_drive_mirror_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When CORPUS_FOLDER is under My Drive, B1 falls through to its
    original needs-install / ok logic based on Drive.app presence.
    Pins that the conditional doesn't break the canonical case."""
    from ergodix.prereqs import check_drive_desktop

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "local_config.py"
    config.write_text(
        f"from pathlib import Path\nCORPUS_FOLDER = Path('{tmp_path / 'My Drive' / 'MyOpus'}')\n"
    )
    monkeypatch.setattr(Path, "is_dir", lambda _self: False)

    result = check_drive_desktop.inspect()

    assert result.status == "needs-install"  # original behavior preserved
    assert result.needs_action is True
    assert result.needs_admin is True  # --cask writes to /Applications
    assert result.network_required is True


# ─── apply() ────────────────────────────────────────────────────────────────


def _record_subprocess(
    monkeypatch: pytest.MonkeyPatch, *, rc: int
) -> list[tuple[list[str] | str, dict[str, Any]]]:
    calls: list[tuple[list[str] | str, dict[str, Any]]] = []

    def fake_run(cmd: list[str] | str, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, returncode=rc, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_apply_invokes_brew_install_cask_google_drive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_drive_desktop

    calls = _record_subprocess(monkeypatch, rc=0)

    check_drive_desktop.apply()

    assert any(
        isinstance(cmd, list)
        and cmd[:2] == ["brew", "install"]
        and "--cask" in cmd
        and "google-drive" in cmd
        for cmd, _ in calls
    ), f"expected `brew install --cask google-drive`; got {calls!r}"


def test_apply_sets_homebrew_no_auto_update_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_drive_desktop

    calls = _record_subprocess(monkeypatch, rc=0)

    check_drive_desktop.apply()

    has_no_auto_update = any(
        isinstance(kwargs.get("env"), dict) and kwargs["env"].get("HOMEBREW_NO_AUTO_UPDATE") == "1"
        for _, kwargs in calls
    )
    assert has_no_auto_update


def test_apply_returns_ok_on_zero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_drive_desktop

    _record_subprocess(monkeypatch, rc=0)

    result = check_drive_desktop.apply()

    assert result.op_id == "B1"
    assert result.status == "ok"


def test_apply_returns_failed_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_drive_desktop

    _record_subprocess(monkeypatch, rc=1)

    result = check_drive_desktop.apply()

    assert result.status == "failed"
    assert result.remediation_hint is not None
    assert "google-drive" in result.remediation_hint or "Drive" in result.remediation_hint


def test_apply_returns_failed_when_brew_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_drive_desktop

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess:
        raise FileNotFoundError("brew")

    monkeypatch.setattr(subprocess, "run", boom)

    result = check_drive_desktop.apply()

    assert result.status == "failed"
    assert "brew" in result.message.lower()


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_drive_desktop

    assert isinstance(check_drive_desktop.OP_ID, str)
    assert callable(check_drive_desktop.inspect)
    assert callable(check_drive_desktop.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "B1" in op_ids, f"B1 not registered; have {sorted(op_ids)}"
