"""
Tests for ergodix.prereqs.check_pandoc — the A3 prereq from ADR 0003.

A3 ensures Pandoc is installed. Pandoc + XeLaTeX is the canonical
render path per Story 0.2 — without it, ``ergodix render`` can't
produce PDFs.

A3 depends on A2 (Homebrew) — apply runs ``brew install pandoc``.
The orchestrator's ordering of prereqs in the registry is responsible
for ensuring A2 lands before A3 in the same run.

Tests use ``shutil.which`` and ``subprocess.run`` monkeypatching so
the suite never actually invokes brew.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

import pytest

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_A3() -> None:
    from ergodix.prereqs import check_pandoc

    assert check_pandoc.OP_ID == "A3"


def test_description_mentions_pandoc() -> None:
    from ergodix.prereqs import check_pandoc

    assert "pandoc" in check_pandoc.DESCRIPTION.lower()


# ─── inspect() ──────────────────────────────────────────────────────────────


def test_inspect_returns_ok_when_pandoc_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_pandoc

    monkeypatch.setattr(
        shutil, "which", lambda cmd: "/opt/homebrew/bin/pandoc" if cmd == "pandoc" else None
    )

    result = check_pandoc.inspect()

    assert result.op_id == "A3"
    assert result.status == "ok"
    assert result.needs_action is False


def test_inspect_returns_needs_install_when_pandoc_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_pandoc

    monkeypatch.setattr(shutil, "which", lambda _cmd: None)

    result = check_pandoc.inspect()

    assert result.status == "needs-install"
    assert result.needs_action is True
    assert result.network_required is True
    assert result.needs_admin is False  # brew install runs in user-space (no sudo)


# ─── apply() — runs `brew install pandoc` ──────────────────────────────────


def _record_subprocess(
    monkeypatch: pytest.MonkeyPatch, *, rc: int
) -> list[tuple[list[str] | str, dict[str, Any]]]:
    calls: list[tuple[list[str] | str, dict[str, Any]]] = []

    def fake_run(cmd: list[str] | str, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, returncode=rc, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_apply_invokes_brew_install_pandoc(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_pandoc

    calls = _record_subprocess(monkeypatch, rc=0)

    check_pandoc.apply()

    assert any(
        isinstance(cmd, list) and cmd[:3] == ["brew", "install", "pandoc"] for cmd, _ in calls
    ), f"expected `brew install pandoc`; got {calls!r}"


def test_apply_sets_homebrew_no_auto_update_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Per Spike 0008 / Story 0.11 task list: brew calls in cantilever
    must set HOMEBREW_NO_AUTO_UPDATE=1 so Homebrew doesn't surprise
    the user with a multi-minute self-update mid-install.
    """
    from ergodix.prereqs import check_pandoc

    calls = _record_subprocess(monkeypatch, rc=0)

    check_pandoc.apply()

    has_no_auto_update = any(
        isinstance(kwargs.get("env"), dict) and kwargs["env"].get("HOMEBREW_NO_AUTO_UPDATE") == "1"
        for _, kwargs in calls
    )
    assert has_no_auto_update, f"expected HOMEBREW_NO_AUTO_UPDATE=1 set on brew call; got {calls!r}"


def test_apply_returns_ok_on_zero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_pandoc

    _record_subprocess(monkeypatch, rc=0)

    result = check_pandoc.apply()

    assert result.op_id == "A3"
    assert result.status == "ok"


def test_apply_returns_failed_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_pandoc

    _record_subprocess(monkeypatch, rc=1)

    result = check_pandoc.apply()

    assert result.status == "failed"
    assert result.remediation_hint is not None
    assert "brew install pandoc" in result.remediation_hint


def test_apply_returns_failed_when_brew_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A3 lists A2 (Homebrew) as a dependency, but if A2 hasn't run yet
    or brew was uninstalled mid-run, A3.apply() must surface a clear
    failed result rather than crashing."""
    from ergodix.prereqs import check_pandoc

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess:
        raise FileNotFoundError("brew")

    monkeypatch.setattr(subprocess, "run", boom)

    result = check_pandoc.apply()

    assert result.status == "failed"
    assert "brew" in result.message.lower()


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_pandoc

    assert isinstance(check_pandoc.OP_ID, str)
    assert callable(check_pandoc.inspect)
    assert callable(check_pandoc.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "A3" in op_ids, f"A3 not registered; have {sorted(op_ids)}"
