"""
Tests for ergodix.prereqs.check_mactex — the A4 prereq from ADR 0003.

A4 ensures XeLaTeX is installed (via MacTeX or BasicTeX) so the render
pipeline locked in Story 0.2 can actually produce PDFs. **First prereq
that consumes ``BootstrapSettings``** — reads ``mactex_install_size``
to decide between ``brew install --cask mactex`` (full, ~4GB),
``brew install --cask basictex`` (~100MB), or ``skip`` (user opted out).

Per ADR 0012 the default is ``"full"``; the value is hardcoded for v1
and moves to ``settings/bootstrap.toml`` when the settings infrastructure
matures further.

Tests use ``shutil.which`` and ``subprocess.run`` monkeypatching so
they never download or invoke MacTeX. Settings are injected by
monkeypatching ``ergodix.settings.load_bootstrap_settings``.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

import pytest

from ergodix.settings import BootstrapSettings

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_A4() -> None:
    from ergodix.prereqs import check_mactex

    assert check_mactex.OP_ID == "A4"


def test_description_mentions_xelatex_or_mactex() -> None:
    from ergodix.prereqs import check_mactex

    desc = check_mactex.DESCRIPTION.lower()
    assert "xelatex" in desc or "mactex" in desc or "tex" in desc


# ─── Helper: stub the settings loader ──────────────────────────────────────


def _stub_settings(monkeypatch: pytest.MonkeyPatch, *, install_size: str = "full") -> None:
    """Replace ergodix.prereqs.check_mactex's settings loader with a fake
    that returns a BootstrapSettings with the given install_size."""

    def fake_loader() -> BootstrapSettings:
        return BootstrapSettings(mactex_install_size=install_size)  # type: ignore[arg-type]

    # Patch at the import site (how the prereq module looks it up).
    from ergodix.prereqs import check_mactex

    monkeypatch.setattr(check_mactex, "load_bootstrap_settings", fake_loader)


# ─── inspect() ──────────────────────────────────────────────────────────────


def test_inspect_returns_ok_when_xelatex_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="full")
    monkeypatch.setattr(
        shutil, "which", lambda cmd: "/Library/TeX/texbin/xelatex" if cmd == "xelatex" else None
    )

    result = check_mactex.inspect()

    assert result.op_id == "A4"
    assert result.status == "ok"
    assert result.needs_action is False


def test_inspect_returns_needs_install_when_xelatex_absent_and_size_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="full")
    monkeypatch.setattr(shutil, "which", lambda _cmd: None)

    result = check_mactex.inspect()

    assert result.status == "needs-install"
    assert result.proposed_action is not None
    assert "mactex" in result.proposed_action.lower()
    assert result.needs_admin is True
    assert result.network_required is True
    # 4GB install — surface a real ETA.
    assert result.estimated_seconds is not None
    assert result.estimated_seconds >= 60


def test_inspect_returns_needs_install_with_basictex_when_size_basic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="basic")
    monkeypatch.setattr(shutil, "which", lambda _cmd: None)

    result = check_mactex.inspect()

    assert result.status == "needs-install"
    assert "basictex" in (result.proposed_action or "").lower()
    assert result.needs_admin is True
    assert result.network_required is True


def test_inspect_returns_ok_when_install_size_is_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User explicitly opted out via settings. Even if XeLaTeX is absent,
    the prereq reports ``ok`` — the user accepts that render won't work
    and prefers to skip the 4GB install."""
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="skip")
    monkeypatch.setattr(shutil, "which", lambda _cmd: None)

    result = check_mactex.inspect()

    assert result.status == "ok"
    assert result.needs_action is False


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


def test_apply_invokes_brew_install_cask_mactex_when_size_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="full")
    calls = _record_subprocess(monkeypatch, rc=0)

    check_mactex.apply()

    assert any(
        isinstance(cmd, list)
        and cmd[:2] == ["brew", "install"]
        and "--cask" in cmd
        and "mactex" in cmd
        for cmd, _ in calls
    ), f"expected `brew install --cask mactex`; got {calls!r}"


def test_apply_invokes_brew_install_cask_basictex_when_size_basic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="basic")
    calls = _record_subprocess(monkeypatch, rc=0)

    check_mactex.apply()

    assert any(
        isinstance(cmd, list)
        and cmd[:2] == ["brew", "install"]
        and "--cask" in cmd
        and "basictex" in cmd
        for cmd, _ in calls
    ), f"expected `brew install --cask basictex`; got {calls!r}"


def test_apply_is_a_no_op_when_size_is_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """``skip`` means don't install. inspect returns ok so apply
    shouldn't run; if it does (e.g., a future ordering bug), it must
    NOT invoke brew."""
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="skip")
    calls = _record_subprocess(monkeypatch, rc=0)

    result = check_mactex.apply()

    assert result.status == "skipped"
    # No brew calls; user opted out.
    assert not any(isinstance(cmd, list) and cmd[:2] == ["brew", "install"] for cmd, _ in calls)


def test_apply_sets_homebrew_no_auto_update_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="full")
    calls = _record_subprocess(monkeypatch, rc=0)

    check_mactex.apply()

    assert any(
        isinstance(kwargs.get("env"), dict) and kwargs["env"].get("HOMEBREW_NO_AUTO_UPDATE") == "1"
        for _, kwargs in calls
    )


def test_apply_returns_ok_on_zero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="full")
    _record_subprocess(monkeypatch, rc=0)

    result = check_mactex.apply()

    assert result.op_id == "A4"
    assert result.status == "ok"


def test_apply_returns_failed_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="full")
    _record_subprocess(monkeypatch, rc=1)

    result = check_mactex.apply()

    assert result.status == "failed"
    assert result.remediation_hint is not None
    assert (
        "mactex" in result.remediation_hint.lower()
        or "tug.org" in result.remediation_hint.lower()
        or "brew" in result.remediation_hint.lower()
    )


def test_apply_returns_failed_when_brew_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.prereqs import check_mactex

    _stub_settings(monkeypatch, install_size="full")

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess:
        raise FileNotFoundError("brew")

    monkeypatch.setattr(subprocess, "run", boom)

    result = check_mactex.apply()

    assert result.status == "failed"
    assert "brew" in result.message.lower()


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_mactex

    assert isinstance(check_mactex.OP_ID, str)
    assert callable(check_mactex.inspect)
    assert callable(check_mactex.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "A4" in op_ids, f"A4 not registered; have {sorted(op_ids)}"
