"""
Tests for ergodix.prereqs.types — InspectResult and ApplyResult dataclasses.

These pin the contract from ADR 0010:
- InspectResult is frozen (read-only inspection).
- ApplyResult is mutable (apply may update message as it progresses).
- Both have stable required and optional fields with documented defaults.

Per CLAUDE.md TDD norm: these tests landed before the implementation.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

# ─── InspectResult ──────────────────────────────────────────────────────────


def test_inspect_result_can_be_constructed_with_required_fields_only() -> None:
    from ergodix.prereqs.types import InspectResult

    result = InspectResult(
        op_id="A1",
        status="ok",
        description="Detect platform",
        current_state="macOS 14.5 detected",
        proposed_action=None,
    )
    assert result.op_id == "A1"
    assert result.status == "ok"
    assert result.description == "Detect platform"
    assert result.current_state == "macOS 14.5 detected"
    assert result.proposed_action is None


def test_inspect_result_optional_fields_have_documented_defaults() -> None:
    from ergodix.prereqs.types import InspectResult

    result = InspectResult(
        op_id="A1",
        status="ok",
        description="Detect platform",
        current_state="macOS 14.5",
        proposed_action=None,
    )
    # Per ADR 0010
    assert result.needs_admin is False
    assert result.estimated_seconds is None
    assert result.network_required is False


def test_inspect_result_accepts_all_fields() -> None:
    from ergodix.prereqs.types import InspectResult

    result = InspectResult(
        op_id="A4",
        status="needs-install",
        description="Install XeLaTeX",
        current_state="XeLaTeX not found",
        proposed_action="brew install --cask mactex",
        needs_admin=True,
        estimated_seconds=600,
        network_required=True,
    )
    assert result.needs_admin is True
    assert result.estimated_seconds == 600
    assert result.network_required is True


def test_inspect_result_is_frozen() -> None:
    """InspectResult must be immutable. Inspect is read-only by contract."""
    from ergodix.prereqs.types import InspectResult

    result = InspectResult(
        op_id="A1",
        status="ok",
        description="Detect platform",
        current_state="macOS 14.5",
        proposed_action=None,
    )
    with pytest.raises(FrozenInstanceError):
        result.status = "needs-update"  # type: ignore[misc]


def test_inspect_result_equality_is_value_based() -> None:
    from ergodix.prereqs.types import InspectResult

    a = InspectResult(
        op_id="A1",
        status="ok",
        description="Detect platform",
        current_state="macOS 14.5",
        proposed_action=None,
    )
    b = InspectResult(
        op_id="A1",
        status="ok",
        description="Detect platform",
        current_state="macOS 14.5",
        proposed_action=None,
    )
    c = InspectResult(
        op_id="A1",
        status="failed",  # different
        description="Detect platform",
        current_state="macOS 14.5",
        proposed_action=None,
    )
    assert a == b
    assert a != c


@pytest.mark.parametrize(
    "status",
    ["ok", "needs-install", "needs-update", "deferred-offline", "failed"],
)
def test_inspect_result_accepts_documented_status_values(status: str) -> None:
    from ergodix.prereqs.types import InspectResult

    result = InspectResult(
        op_id="A1",
        status=status,  # type: ignore[arg-type]
        description="Detect platform",
        current_state="x",
        proposed_action=None,
    )
    assert result.status == status


def test_inspect_result_needs_action_when_status_indicates_change() -> None:
    """
    Convenience check: cantilever needs to know whether an op should be
    included in the plan. needs-install and needs-update mean yes; ok,
    deferred-offline, and failed mean no plan entry.
    """
    from ergodix.prereqs.types import InspectResult

    needs_change = InspectResult(
        op_id="A4",
        status="needs-install",
        description="Install XeLaTeX",
        current_state="not found",
        proposed_action="brew install --cask mactex",
    )
    no_change = InspectResult(
        op_id="A1",
        status="ok",
        description="Detect platform",
        current_state="macOS 14.5",
        proposed_action=None,
    )
    assert needs_change.needs_action is True
    assert no_change.needs_action is False


# ─── ApplyResult ────────────────────────────────────────────────────────────


def test_apply_result_can_be_constructed_with_required_fields_only() -> None:
    from ergodix.prereqs.types import ApplyResult

    result = ApplyResult(
        op_id="A2",
        status="ok",
        message="Homebrew already installed (no action needed)",
    )
    assert result.op_id == "A2"
    assert result.status == "ok"
    assert result.message == "Homebrew already installed (no action needed)"


def test_apply_result_default_remediation_hint_is_none() -> None:
    from ergodix.prereqs.types import ApplyResult

    result = ApplyResult(op_id="A2", status="ok", message="ok")
    assert result.remediation_hint is None


def test_apply_result_accepts_remediation_hint() -> None:
    from ergodix.prereqs.types import ApplyResult

    result = ApplyResult(
        op_id="A4",
        status="failed",
        message="brew install --cask mactex returned exit 1",
        remediation_hint=(
            "Free up at least 4 GB of disk space, or re-run with --basictex-instead."
        ),
    )
    assert "Free up" in (result.remediation_hint or "")


def test_apply_result_is_mutable() -> None:
    """
    ApplyResult must be mutable. apply() may update its own message as
    a long-running step progresses (e.g. download progress).
    """
    from ergodix.prereqs.types import ApplyResult

    result = ApplyResult(op_id="A3", status="ok", message="starting...")
    result.message = "downloading..."
    result.message = "installed"
    assert result.message == "installed"


@pytest.mark.parametrize("status", ["ok", "skipped", "failed"])
def test_apply_result_accepts_documented_status_values(status: str) -> None:
    from ergodix.prereqs.types import ApplyResult

    result = ApplyResult(op_id="A2", status=status, message="x")  # type: ignore[arg-type]
    assert result.status == status


def test_apply_result_equality_is_value_based() -> None:
    from ergodix.prereqs.types import ApplyResult

    a = ApplyResult(op_id="A2", status="ok", message="installed")
    b = ApplyResult(op_id="A2", status="ok", message="installed")
    c = ApplyResult(op_id="A2", status="failed", message="installed")
    assert a == b
    assert a != c
