"""
Tests for ergodix.prereqs.check_platform — the A1 prereq from ADR 0003.

This is the simplest of the 25 prereqs: detect the host platform and
report whether it's one we support (macOS / Linux / Windows) or not.

Doubles as the canonical reference implementation of the inspect/apply
contract from ADR 0010 — every later prereq follows this shape.

Per CLAUDE.md TDD norm: tests landed before implementation.
"""

from __future__ import annotations

import pytest

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_A1() -> None:
    from ergodix.prereqs import check_platform

    assert check_platform.OP_ID == "A1"


def test_description_mentions_platform_detection() -> None:
    from ergodix.prereqs import check_platform

    assert "platform" in check_platform.DESCRIPTION.lower()


# ─── inspect() — supported platforms ────────────────────────────────────────


@pytest.mark.parametrize("system_name", ["Darwin", "Linux", "Windows"])
def test_inspect_returns_ok_on_supported_systems(monkeypatch, system_name) -> None:
    import platform

    from ergodix.prereqs import check_platform

    monkeypatch.setattr(platform, "system", lambda: system_name)
    monkeypatch.setattr(platform, "release", lambda: "X.Y.Z")
    if system_name == "Darwin":
        monkeypatch.setattr(platform, "mac_ver", lambda: ("14.5", ("", "", ""), ""))

    result = check_platform.inspect()

    assert result.op_id == "A1"
    assert result.status == "ok"
    assert result.proposed_action is None
    assert result.needs_admin is False
    assert result.network_required is False
    assert result.needs_action is False  # no plan entry needed


def test_inspect_macos_current_state_uses_friendly_macos_label(monkeypatch) -> None:
    import platform

    from ergodix.prereqs import check_platform

    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("14.5", ("", "", ""), ""))

    result = check_platform.inspect()
    # Should say "macOS 14.5", not "Darwin ..."
    assert "macOS" in result.current_state
    assert "14.5" in result.current_state
    assert "Darwin" not in result.current_state


def test_inspect_linux_current_state_uses_release(monkeypatch) -> None:
    import platform

    from ergodix.prereqs import check_platform

    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "release", lambda: "6.5.0")

    result = check_platform.inspect()
    assert "Linux" in result.current_state
    assert "6.5.0" in result.current_state


def test_inspect_windows_current_state_uses_release(monkeypatch) -> None:
    import platform

    from ergodix.prereqs import check_platform

    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "release", lambda: "11")

    result = check_platform.inspect()
    assert "Windows" in result.current_state
    assert "11" in result.current_state


# ─── inspect() — unsupported platform ───────────────────────────────────────


@pytest.mark.parametrize("system_name", ["FreeBSD", "OpenBSD", "SunOS", "Haiku", "AIX", ""])
def test_inspect_returns_failed_on_unsupported_system(monkeypatch, system_name) -> None:
    """
    A non-supported platform must surface as status='failed' so cantilever's
    inspect-failed handling halts before apply runs.
    """
    import platform

    from ergodix.prereqs import check_platform

    monkeypatch.setattr(platform, "system", lambda: system_name)
    monkeypatch.setattr(platform, "release", lambda: "0.0")

    result = check_platform.inspect()

    assert result.op_id == "A1"
    assert result.status == "failed"
    # current_state should still describe what we found, even if unsupported.
    if system_name:
        assert system_name in result.current_state or "unsupported" in result.current_state.lower()


# ─── apply() — no-op for this op ────────────────────────────────────────────


def test_apply_is_a_no_op_with_skipped_status() -> None:
    """
    Platform detection has no apply step. apply() exists to satisfy the
    PrereqSpec protocol; it should never be reached in the happy path
    (inspect returns 'ok' so needs_action is False; cantilever skips apply).
    If it IS called, it must not raise — return skipped.
    """
    from ergodix.prereqs import check_platform

    result = check_platform.apply()

    assert result.op_id == "A1"
    assert result.status == "skipped"
    assert result.message  # non-empty


# ─── Integration: prereq satisfies the cantilever PrereqSpec protocol ───────


def test_module_satisfies_prereq_spec_protocol() -> None:
    """check_platform must be usable as a PrereqSpec — op_id + inspect + apply."""
    from ergodix.prereqs import check_platform

    assert isinstance(check_platform.OP_ID, str)
    assert callable(check_platform.inspect)
    assert callable(check_platform.apply)


def test_runs_through_cantilever_without_special_handling(monkeypatch) -> None:
    """
    Smoke test: check_platform plugged into run_cantilever() with the
    PrereqSpec protocol works end-to-end on a supported platform.
    """
    import platform

    from ergodix.cantilever import run_cantilever
    from ergodix.prereqs import check_platform

    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("14.5", ("", "", ""), ""))

    # Adapter that wraps the module as a PrereqSpec object.
    class ModulePrereq:
        op_id = check_platform.OP_ID

        def inspect(self):
            return check_platform.inspect()

        def apply(self):
            return check_platform.apply()

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[ModulePrereq()],
        consent_fn=lambda _plan: pytest.fail("consent should not run; status is ok"),
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    assert result.outcome == "no-changes-needed"
