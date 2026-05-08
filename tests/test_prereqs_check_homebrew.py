"""
Tests for ergodix.prereqs.check_homebrew — the A2 prereq from ADR 0003.

A2 ensures Homebrew is installed. It's the **first Tier-2 prereq** —
network + admin — and unblocks A3 (Pandoc), A4 (MacTeX), A7 (VS Code),
B1 (Google Drive Desktop). Without A2, none of those install paths
work on a fresh macOS / Linux machine.

Inspect uses ``shutil.which`` to detect ``brew`` on PATH. Apply runs
the official Homebrew install script via the documented one-liner.
The install script itself prompts for sudo and is idempotent — running
it on an already-installed system does nothing harmful.

Tests use ``shutil.which`` and ``subprocess.run`` monkeypatching so the
suite never actually downloads or executes the Homebrew install script.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

import pytest

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_A2() -> None:
    from ergodix.prereqs import check_homebrew

    assert check_homebrew.OP_ID == "A2"


def test_description_mentions_homebrew() -> None:
    from ergodix.prereqs import check_homebrew

    desc = check_homebrew.DESCRIPTION.lower()
    assert "homebrew" in desc or "brew" in desc


# ─── inspect() — two states (no failed path on missing PATH; OS may differ) ─


def test_inspect_returns_ok_when_brew_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_homebrew

    monkeypatch.setattr(
        shutil, "which", lambda cmd: "/opt/homebrew/bin/brew" if cmd == "brew" else None
    )

    result = check_homebrew.inspect()

    assert result.op_id == "A2"
    assert result.status == "ok"
    assert result.needs_action is False
    assert result.network_required is True


def test_inspect_returns_needs_install_when_brew_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_homebrew

    monkeypatch.setattr(shutil, "which", lambda _cmd: None)

    result = check_homebrew.inspect()

    assert result.status == "needs-install"
    assert result.proposed_action is not None
    assert "homebrew" in result.proposed_action.lower() or "brew" in result.proposed_action.lower()
    assert result.needs_action is True
    assert result.needs_admin is True
    assert result.network_required is True
    # Multi-minute install — give the user a real ETA in the plan display.
    assert result.estimated_seconds is not None
    assert result.estimated_seconds >= 60


# ─── apply() — runs the official Homebrew install script ───────────────────


def _record_subprocess(
    monkeypatch: pytest.MonkeyPatch, *, rc: int
) -> list[tuple[list[str] | str, dict[str, Any]]]:
    """Stub subprocess.run; return (cmd, kwargs) tuples."""
    calls: list[tuple[list[str] | str, dict[str, Any]]] = []

    def fake_run(cmd: list[str] | str, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, returncode=rc, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_apply_invokes_official_homebrew_install_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The Homebrew install one-liner is the documented official path:

        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    Pin the URL + the bash invocation so future refactors don't switch
    to a third-party mirror or alter the documented happy path.
    """
    from ergodix.prereqs import check_homebrew

    calls = _record_subprocess(monkeypatch, rc=0)

    check_homebrew.apply()

    assert calls, "apply() did not invoke any subprocess"
    full_cmd_strs = [" ".join(cmd) if isinstance(cmd, list) else cmd for cmd, _ in calls]
    joined = " ".join(full_cmd_strs)
    assert "raw.githubusercontent.com/Homebrew/install" in joined
    assert "install.sh" in joined


def test_apply_sets_noninteractive_env_for_homebrew_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Per Spike 0008 / Story 0.11 task list: brew install must be
    non-interactive (NONINTERACTIVE=1) so the install script doesn't
    re-prompt the user mid-run. Sudo grouping per ADR 0010 means the
    user already authorized once at the consent gate.
    """
    from ergodix.prereqs import check_homebrew

    calls = _record_subprocess(monkeypatch, rc=0)

    check_homebrew.apply()

    # Find a call whose kwargs include env with NONINTERACTIVE=1.
    has_noninteractive = any(
        isinstance(kwargs.get("env"), dict) and kwargs["env"].get("NONINTERACTIVE") == "1"
        for _, kwargs in calls
    )
    assert has_noninteractive, (
        f"expected a subprocess call with env NONINTERACTIVE=1 set; calls={calls!r}"
    )


def test_apply_returns_ok_on_zero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_homebrew

    _record_subprocess(monkeypatch, rc=0)

    result = check_homebrew.apply()

    assert result.op_id == "A2"
    assert result.status == "ok"


def test_apply_returns_failed_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_homebrew

    _record_subprocess(monkeypatch, rc=2)

    result = check_homebrew.apply()

    assert result.status == "failed"
    assert result.message
    assert result.remediation_hint is not None
    # Surface the URL in the remediation so the user can run it manually.
    assert "brew.sh" in result.remediation_hint or "homebrew" in result.remediation_hint.lower()


def test_apply_returns_failed_when_subprocess_raises_oserror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If subprocess.run itself can't spawn (no /bin/bash, FS issue, etc.),
    don't crash — report failed."""
    from ergodix.prereqs import check_homebrew

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess:
        raise OSError("simulated spawn failure")

    monkeypatch.setattr(subprocess, "run", boom)

    result = check_homebrew.apply()

    assert result.status == "failed"
    assert result.remediation_hint is not None


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_homebrew

    assert isinstance(check_homebrew.OP_ID, str)
    assert callable(check_homebrew.inspect)
    assert callable(check_homebrew.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "A2" in op_ids, f"A2 not registered; have {sorted(op_ids)}"
