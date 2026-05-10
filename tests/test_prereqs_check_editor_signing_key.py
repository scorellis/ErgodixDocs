"""
Tests for ergodix.prereqs.check_editor_signing_key — D6 verify-only
check from ADR 0003 + ADR 0006 + ADR 0012.

D6 is verify-only in v1: the full install flow (keygen + gh scope
refresh + register + git config) defers to a future ``ergodix
editor init`` command. inspect() always returns ``ok``; the
current_state describes what was found.

Tests stub ``Path.exists`` and ``subprocess.run`` so they're
deterministic regardless of dev-machine ssh / git state.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest


def test_op_id_is_D6() -> None:
    from ergodix.prereqs import check_editor_signing_key

    assert check_editor_signing_key.OP_ID == "D6"


def test_description_mentions_signing_or_editor() -> None:
    from ergodix.prereqs import check_editor_signing_key

    text = check_editor_signing_key.DESCRIPTION.lower()
    assert "sign" in text or "editor" in text


# ─── inspect() ────────────────────────────────────────────────────────────


def test_inspect_ok_deferred_when_signing_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No editor signing key on disk → status=ok with deferred state.
    D6 stays out of the way for non-editor users — the install flow
    fires explicitly via `ergodix editor init`, not from cantilever."""
    from ergodix.prereqs import check_editor_signing_key

    monkeypatch.setattr(Path, "exists", lambda _self: False)

    result = check_editor_signing_key.inspect()

    assert result.op_id == "D6"
    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "not yet" in state_lower or "editor init" in state_lower


def test_inspect_ok_when_key_exists_and_git_config_aligned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Key on disk + git is configured to sign with it → ok with happy
    current_state. The canonical "everything is set up" path."""
    from ergodix.prereqs import check_editor_signing_key

    expected_pubkey = Path.home() / ".ssh" / "id_ed25519_ergodix_editor.pub"

    monkeypatch.setattr(Path, "exists", lambda _self: True)

    config_values = {
        "gpg.format": "ssh",
        "user.signingkey": str(expected_pubkey),
        "commit.gpgsign": "true",
    }

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        # cmd is ["git", "config", "--global", "<key>"]
        if cmd[:3] == ["git", "config", "--global"] and len(cmd) >= 4:
            key = cmd[3]
            value = config_values.get(key, "")
            return subprocess.CompletedProcess(
                cmd, 0 if value else 1, stdout=value + "\n", stderr=""
            )
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_editor_signing_key.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "configured to sign" in state_lower or "signing key" in state_lower


def test_inspect_ok_with_warning_when_key_exists_but_git_config_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Key on disk but git has no signing config → ok status with
    current_state listing the missing config bits and the fix command.
    Pure informational — apply doesn't act."""
    from ergodix.prereqs import check_editor_signing_key

    monkeypatch.setattr(Path, "exists", lambda _self: True)

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        # All git config calls return "unset" (rc=1)
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_editor_signing_key.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "incomplete" in state_lower or "missing" in state_lower
    # The fix command must be visible
    assert "git config" in state_lower
    assert "gpg.format" in state_lower


def test_inspect_ok_with_warning_when_signingkey_points_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Key on disk but user.signingkey points at a different file → ok
    with warning. Surfaces a likely partial setup the user can fix."""
    from ergodix.prereqs import check_editor_signing_key

    monkeypatch.setattr(Path, "exists", lambda _self: True)

    config_values = {
        "gpg.format": "ssh",
        "user.signingkey": "/Users/me/.ssh/some_other_key.pub",  # wrong key
        "commit.gpgsign": "true",
    }

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        if cmd[:3] == ["git", "config", "--global"] and len(cmd) >= 4:
            key = cmd[3]
            value = config_values.get(key, "")
            return subprocess.CompletedProcess(
                cmd, 0 if value else 1, stdout=value + "\n", stderr=""
            )
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_editor_signing_key.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "incomplete" in state_lower or "missing" in state_lower


def test_inspect_handles_git_not_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive: if git itself isn't on PATH, D6 doesn't crash.
    Returns ok with current_state listing the config as missing
    (since we can't read it), pointing the user at the fix command."""
    from ergodix.prereqs import check_editor_signing_key

    monkeypatch.setattr(Path, "exists", lambda _self: True)

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", boom)

    result = check_editor_signing_key.inspect()

    assert result.status == "ok"


# ─── apply() — no-op ───────────────────────────────────────────────────────


def test_apply_is_skipped() -> None:
    from ergodix.prereqs import check_editor_signing_key

    result = check_editor_signing_key.apply()

    assert result.op_id == "D6"
    assert result.status == "skipped"
    assert "verify-only" in result.message.lower() or "editor init" in result.message.lower()


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_editor_signing_key

    assert isinstance(check_editor_signing_key.OP_ID, str)
    assert callable(check_editor_signing_key.inspect)
    assert callable(check_editor_signing_key.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "D6" in op_ids, f"D6 not registered; have {sorted(op_ids)}"
