"""
Tests for ergodix.prereqs.check_vscode — the A7 prereq from ADR 0003.

A7 ensures Visual Studio Code is installed plus the small set of
extensions ergodic-text editing depends on (Markdown Preview Enhanced
for live render, LTeX for grammar/style on prose, CriticMarkup for
editor-style change marks).

Two-stage shape:
  - inspect() looks for `code` on PATH; if present, lists installed
    extensions and compares to REQUIRED_EXTENSIONS.
  - apply() installs VS Code via brew --cask if missing, then runs
    `code --install-extension <id>` for each missing extension.

Idempotent: a re-run with everything already installed returns ok
without spawning brew or `code`.

Tests stub shutil.which and subprocess.run so no real installs run.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

import pytest

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_A7() -> None:
    from ergodix.prereqs import check_vscode

    assert check_vscode.OP_ID == "A7"


def test_description_mentions_vscode_or_code() -> None:
    from ergodix.prereqs import check_vscode

    text = check_vscode.DESCRIPTION.lower()
    assert "vs code" in text or "visual studio code" in text or "code" in text


def test_required_extensions_are_nonempty_strings() -> None:
    """Pin the shape — a non-empty tuple of <publisher>.<name> IDs.
    Don't pin specific IDs so we can swap LTeX → ltex-plus etc. without
    test churn."""
    from ergodix.prereqs import check_vscode

    assert len(check_vscode.REQUIRED_EXTENSIONS) >= 1
    for ext in check_vscode.REQUIRED_EXTENSIONS:
        assert isinstance(ext, str)
        assert "." in ext, f"extension ID {ext!r} should be <publisher>.<name>"


# ─── inspect() ──────────────────────────────────────────────────────────────


def _mock_code_present(monkeypatch: pytest.MonkeyPatch, path: str = "/usr/local/bin/code") -> None:
    monkeypatch.setattr(shutil, "which", lambda cmd: path if cmd == "code" else None)


def _mock_code_absent(monkeypatch: pytest.MonkeyPatch, tmp_path: Any | None = None) -> None:
    """Make the resolver return None: hide `code` from PATH AND point the
    macOS app-bundle fallback at a path that doesn't exist."""
    from pathlib import Path

    from ergodix.prereqs import check_vscode

    monkeypatch.setattr(shutil, "which", lambda _cmd: None)
    monkeypatch.setattr(
        check_vscode, "_MAC_APP_BUNDLE_CODE", Path("/nonexistent-vscode-fallback/code")
    )


def _mock_list_extensions(
    monkeypatch: pytest.MonkeyPatch, installed: list[str], rc: int = 0
) -> list[list[str] | str]:
    """Stub subprocess.run so `code --list-extensions` reports `installed`.
    Returns the captured commands so tests can assert what was invoked."""
    calls: list[list[str] | str] = []

    def fake_run(cmd: list[str] | str, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        calls.append(cmd)
        if isinstance(cmd, list) and cmd[-1] == "--list-extensions":
            return subprocess.CompletedProcess(
                cmd, returncode=rc, stdout="\n".join(installed) + "\n", stderr=""
            )
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_inspect_returns_ok_when_code_and_all_extensions_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_vscode

    _mock_code_present(monkeypatch)
    _mock_list_extensions(monkeypatch, list(check_vscode.REQUIRED_EXTENSIONS))

    result = check_vscode.inspect()

    assert result.op_id == "A7"
    assert result.status == "ok"
    assert result.needs_action is False


def test_inspect_returns_needs_install_when_code_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_vscode

    _mock_code_absent(monkeypatch)

    result = check_vscode.inspect()

    assert result.status == "needs-install"
    assert result.needs_action is True
    assert result.network_required is True
    assert result.needs_admin is True  # cask writes to /Applications


def test_inspect_returns_needs_install_when_some_extensions_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Code is on PATH, but the required-extensions set is missing
    members. Inspect must surface this as needs-install with a proposed
    action that mentions extensions, not VS Code itself."""
    from ergodix.prereqs import check_vscode

    _mock_code_present(monkeypatch)
    # Pretend none of the required extensions are installed.
    _mock_list_extensions(monkeypatch, installed=[])

    result = check_vscode.inspect()

    assert result.status == "needs-install"
    proposed = (result.proposed_action or "").lower()
    assert "extension" in proposed


# ─── apply() ────────────────────────────────────────────────────────────────


def _record_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rc: int = 0,
    list_ext_output: str = "",
) -> list[tuple[list[str] | str, dict[str, Any]]]:
    """Generic subprocess.run stub. Returns the captured (cmd, kwargs) tuples.
    `code --list-extensions` always returns `list_ext_output`; everything
    else returns rc with empty stdout/stderr."""
    calls: list[tuple[list[str] | str, dict[str, Any]]] = []

    def fake_run(cmd: list[str] | str, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        calls.append((cmd, kwargs))
        if isinstance(cmd, list) and cmd[-1] == "--list-extensions":
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=list_ext_output, stderr="")
        return subprocess.CompletedProcess(cmd, returncode=rc, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_apply_invokes_brew_cask_when_code_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_vscode

    _mock_code_absent(monkeypatch)
    calls = _record_subprocess(monkeypatch, rc=0)

    check_vscode.apply()

    assert any(
        isinstance(cmd, list) and cmd[:4] == ["brew", "install", "--cask", "visual-studio-code"]
        for cmd, _ in calls
    ), f"expected `brew install --cask visual-studio-code`; got {calls!r}"


def test_apply_sets_homebrew_no_auto_update_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Per Spike 0008 / Story 0.11: brew calls in cantilever set
    HOMEBREW_NO_AUTO_UPDATE=1 so brew doesn't auto-update mid-install."""
    from ergodix.prereqs import check_vscode

    _mock_code_absent(monkeypatch)
    calls = _record_subprocess(monkeypatch, rc=0)

    check_vscode.apply()

    has_no_auto_update = any(
        isinstance(kwargs.get("env"), dict)
        and isinstance(cmd, list)
        and cmd[:1] == ["brew"]
        and kwargs["env"].get("HOMEBREW_NO_AUTO_UPDATE") == "1"
        for cmd, kwargs in calls
    )
    assert has_no_auto_update, f"expected HOMEBREW_NO_AUTO_UPDATE=1 set on brew call; got {calls!r}"


def test_apply_installs_each_missing_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    """When `code` is present but extensions are missing, apply runs
    `code --install-extension <id>` once per missing extension."""
    from ergodix.prereqs import check_vscode

    _mock_code_present(monkeypatch)
    calls = _record_subprocess(monkeypatch, rc=0, list_ext_output="")  # nothing installed

    check_vscode.apply()

    install_invocations = [
        cmd
        for cmd, _ in calls
        if isinstance(cmd, list) and len(cmd) >= 3 and cmd[1] == "--install-extension"
    ]
    assert len(install_invocations) == len(check_vscode.REQUIRED_EXTENSIONS), (
        f"expected one --install-extension call per required extension; got {install_invocations!r}"
    )
    installed_args = {cmd[-1] for cmd in install_invocations}
    assert installed_args == set(check_vscode.REQUIRED_EXTENSIONS)


def test_apply_skips_extensions_already_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Idempotency: re-runs that find `code` on PATH and every required
    extension already listed must NOT call `code --install-extension`."""
    from ergodix.prereqs import check_vscode

    _mock_code_present(monkeypatch)
    list_output = "\n".join(check_vscode.REQUIRED_EXTENSIONS) + "\n"
    calls = _record_subprocess(monkeypatch, rc=0, list_ext_output=list_output)

    result = check_vscode.apply()

    install_invocations = [
        cmd
        for cmd, _ in calls
        if isinstance(cmd, list) and len(cmd) >= 3 and cmd[1] == "--install-extension"
    ]
    assert install_invocations == [], (
        f"expected NO --install-extension calls when all are present; got {install_invocations!r}"
    )
    assert result.status == "ok"


def test_apply_returns_failed_when_brew_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A7 lists A2 (Homebrew) as a dependency. If brew is gone, apply
    must return a failed result rather than crashing."""
    from ergodix.prereqs import check_vscode

    _mock_code_absent(monkeypatch)

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess:
        raise FileNotFoundError("brew")

    monkeypatch.setattr(subprocess, "run", boom)

    result = check_vscode.apply()

    assert result.status == "failed"
    assert "brew" in result.message.lower()


def test_apply_returns_failed_on_brew_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_vscode

    _mock_code_absent(monkeypatch)
    _record_subprocess(monkeypatch, rc=1)

    result = check_vscode.apply()

    assert result.status == "failed"
    assert result.remediation_hint is not None
    assert "visual-studio-code" in result.remediation_hint or "VS Code" in result.remediation_hint


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_vscode

    assert isinstance(check_vscode.OP_ID, str)
    assert callable(check_vscode.inspect)
    assert callable(check_vscode.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "A7" in op_ids, f"A7 not registered; have {sorted(op_ids)}"
