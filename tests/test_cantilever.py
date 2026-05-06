"""
Tests for ergodix.cantilever — the four-phase installer orchestrator from
ADR 0010.

This file pins phases 1 (inspect) and 2 (plan + consent gate). Phases 3
(apply) and 4 (verify) are landed in a follow-up step.

The orchestrator takes a list of prereqs (each satisfying a small
PrereqSpec protocol — op_id + inspect() + apply()), a consent callable,
and a connectivity probe. Tests use fake prereqs and inject the consent
+ connectivity functions to exercise edge cases without touching the
real OS.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from ergodix.prereqs.types import (
    ApplyResult,
    ApplyStatus,
    InspectResult,
    InspectStatus,
)

# ─── Fake prereq fixtures ──────────────────────────────────────────────────


@dataclass
class FakePrereq:
    """
    Test-only prereq. Satisfies the PrereqSpec protocol the orchestrator
    expects: an op_id, inspect() returning an InspectResult, apply()
    returning an ApplyResult.
    """

    op_id: str
    inspect_status: InspectStatus = "ok"
    description: str = "Fake op"
    current_state: str = "fake state"
    proposed_action: str | None = None
    needs_admin: bool = False
    estimated_seconds: int | None = None
    network_required: bool = False
    apply_status: ApplyStatus = "ok"
    apply_message: str = "fake applied"

    inspect_call_count: int = field(default=0, init=False)
    apply_call_count: int = field(default=0, init=False)

    def inspect(self) -> InspectResult:
        self.inspect_call_count += 1
        return InspectResult(
            op_id=self.op_id,
            status=self.inspect_status,
            description=self.description,
            current_state=self.current_state,
            proposed_action=self.proposed_action,
            needs_admin=self.needs_admin,
            estimated_seconds=self.estimated_seconds,
            network_required=self.network_required,
        )

    def apply(self) -> ApplyResult:
        self.apply_call_count += 1
        return ApplyResult(
            op_id=self.op_id,
            status=self.apply_status,
            message=self.apply_message,
        )


def _ok_prereq(op_id: str = "A1") -> FakePrereq:
    return FakePrereq(op_id=op_id, inspect_status="ok")


def _needs_install_prereq(op_id: str = "A3", needs_admin: bool = False) -> FakePrereq:
    return FakePrereq(
        op_id=op_id,
        inspect_status="needs-install",
        proposed_action=f"Install {op_id}",
        needs_admin=needs_admin,
    )


# ─── Phase 1: inspect ──────────────────────────────────────────────────────


def test_inspect_phase_calls_every_prereq() -> None:
    from ergodix.cantilever import run_cantilever

    prereqs = [_ok_prereq("A1"), _ok_prereq("A2"), _ok_prereq("A3")]

    run_cantilever(
        floaters={"writer": True},
        prereqs=prereqs,
        consent_fn=lambda _plan: False,  # no-op since plan is empty
        is_online_fn=lambda: True,
    )

    for p in prereqs:
        assert p.inspect_call_count == 1


def test_inspect_phase_returns_results_for_every_prereq_in_result() -> None:
    from ergodix.cantilever import run_cantilever

    prereqs = [_ok_prereq("A1"), _needs_install_prereq("A3")]

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=prereqs,
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
    )

    assert {ir.op_id for ir in result.inspect_results} == {"A1", "A3"}


def test_inspect_phase_marks_network_required_ops_deferred_when_offline() -> None:
    from ergodix.cantilever import run_cantilever

    network_op = FakePrereq(
        op_id="A2",
        inspect_status="needs-install",
        network_required=True,
        proposed_action="brew install pandoc",
    )
    local_op = FakePrereq(op_id="A1", inspect_status="ok")

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[network_op, local_op],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: False,
    )

    by_id = {ir.op_id: ir for ir in result.inspect_results}
    assert by_id["A2"].status == "deferred-offline"
    assert by_id["A1"].status == "ok"  # not network-dependent


def test_inspect_phase_runs_network_ops_normally_when_online() -> None:
    from ergodix.cantilever import run_cantilever

    network_op = FakePrereq(
        op_id="A2",
        inspect_status="needs-install",
        network_required=True,
        proposed_action="brew install pandoc",
    )

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[network_op],
        consent_fn=lambda _plan: True,  # accept
        is_online_fn=lambda: True,
    )

    by_id = {ir.op_id: ir for ir in result.inspect_results}
    assert by_id["A2"].status == "needs-install"


# ─── Phase 2: plan building ────────────────────────────────────────────────


def test_plan_filters_to_needs_action_items_only() -> None:
    from ergodix.cantilever import run_cantilever

    prereqs = [
        _ok_prereq("A1"),
        _needs_install_prereq("A3"),
        _ok_prereq("A5"),
        _needs_install_prereq("A7"),
    ]

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=prereqs,
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
    )

    assert {item.op_id for item in result.plan.items} == {"A3", "A7"}


def test_plan_is_empty_when_all_ops_are_ok() -> None:
    from ergodix.cantilever import run_cantilever

    prereqs = [_ok_prereq("A1"), _ok_prereq("A2"), _ok_prereq("A3")]

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=prereqs,
        consent_fn=lambda _plan: pytest.fail("consent should not be requested for empty plan"),
        is_online_fn=lambda: True,
    )

    assert result.plan.items == []
    assert result.outcome == "no-changes-needed"


def test_plan_has_admin_ops_property() -> None:
    from ergodix.cantilever import run_cantilever

    prereqs = [
        _needs_install_prereq("A3", needs_admin=False),
        _needs_install_prereq("A4", needs_admin=True),
    ]

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=prereqs,
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
    )

    assert result.plan.has_admin_ops is True


def test_plan_total_estimated_seconds() -> None:
    from ergodix.cantilever import run_cantilever

    a = FakePrereq(
        op_id="A3",
        inspect_status="needs-install",
        proposed_action="x",
        estimated_seconds=30,
    )
    b = FakePrereq(
        op_id="A4",
        inspect_status="needs-install",
        proposed_action="y",
        estimated_seconds=600,
    )
    c = FakePrereq(
        op_id="A5",
        inspect_status="needs-install",
        proposed_action="z",
        # estimated_seconds=None
    )

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[a, b, c],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
    )

    # Treats None as 0, sums the rest.
    assert result.plan.total_estimated_seconds == 630


# ─── Phase 2: consent gate ─────────────────────────────────────────────────


def test_consent_callable_receives_the_built_plan() -> None:
    from ergodix.cantilever import Plan, run_cantilever

    received: list[Plan] = []

    def capturing_consent(plan: Plan) -> bool:
        received.append(plan)
        return False

    prereqs = [_needs_install_prereq("A3"), _needs_install_prereq("A7")]

    run_cantilever(
        floaters={"writer": True},
        prereqs=prereqs,
        consent_fn=capturing_consent,
        is_online_fn=lambda: True,
    )

    assert len(received) == 1
    assert {item.op_id for item in received[0].items} == {"A3", "A7"}


def test_consent_decline_returns_declined_outcome() -> None:
    from ergodix.cantilever import run_cantilever

    prereqs = [_needs_install_prereq("A3")]

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=prereqs,
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
    )

    assert result.outcome == "consent-declined"
    # No apply happened.
    assert prereqs[0].apply_call_count == 0


def test_consent_accept_proceeds_to_apply() -> None:
    """
    Accepting should call apply() at least for ops that needed action.
    Phase 3 details are exercised in their own tests; this one just
    confirms the gate doesn't block.
    """
    from ergodix.cantilever import run_cantilever

    p = _needs_install_prereq("A3")

    run_cantilever(
        floaters={"writer": True},
        prereqs=[p],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
    )

    assert p.apply_call_count == 1


# ─── Floater: --dry-run ────────────────────────────────────────────────────


def test_dry_run_floater_shows_plan_and_exits_without_consent_or_apply() -> None:
    from ergodix.cantilever import run_cantilever

    prereqs = [_needs_install_prereq("A3")]

    result = run_cantilever(
        floaters={"writer": True, "dry-run": True},
        prereqs=prereqs,
        consent_fn=lambda _plan: pytest.fail("consent should not be called under --dry-run"),
        is_online_fn=lambda: True,
    )

    assert result.outcome == "dry-run"
    assert prereqs[0].apply_call_count == 0


# ─── Floater: --ci ─────────────────────────────────────────────────────────


def test_ci_floater_bypasses_consent_treats_as_accept() -> None:
    from ergodix.cantilever import run_cantilever

    p = _needs_install_prereq("A3")

    result = run_cantilever(
        floaters={"writer": True, "ci": True},
        prereqs=[p],
        consent_fn=lambda _plan: pytest.fail("consent should not be called under --ci"),
        is_online_fn=lambda: True,
    )

    # Apply was invoked despite no consent prompt.
    assert p.apply_call_count == 1
    # Outcome is success (consent was implicitly given).
    assert result.outcome in {"applied", "applied-with-failures"}


# ─── Phase 3: apply ────────────────────────────────────────────────────────


def test_apply_runs_each_consented_op_in_plan_order() -> None:
    from ergodix.cantilever import run_cantilever

    a = _needs_install_prereq("A3")
    b = _needs_install_prereq("A5")
    c = _needs_install_prereq("A7")

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[a, b, c],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
    )

    # Each apply called once, in plan order.
    assert a.apply_call_count == 1
    assert b.apply_call_count == 1
    assert c.apply_call_count == 1
    assert [r.op_id for r in result.apply_results] == ["A3", "A5", "A7"]


def test_apply_emits_progress_lines_per_op() -> None:
    from ergodix.cantilever import run_cantilever

    captured: list[str] = []
    a = _needs_install_prereq("A3")
    b = _needs_install_prereq("A5")

    run_cantilever(
        floaters={"writer": True},
        prereqs=[a, b],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        output_fn=captured.append,
    )

    output = "\n".join(captured)
    # Each step in the plan should produce a [k/total] line during apply.
    assert "[1/2]" in output
    assert "[2/2]" in output


def test_apply_aborts_fast_on_first_failure() -> None:
    """If apply() returns failed, the remaining ops are not invoked."""
    from ergodix.cantilever import run_cantilever

    a = _needs_install_prereq("A3")
    a.apply_status = "failed"
    a.apply_message = "brew install failed"

    b = _needs_install_prereq("A5")  # should never be applied
    c = _needs_install_prereq("A7")  # should never be applied

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[a, b, c],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
    )

    assert a.apply_call_count == 1
    assert b.apply_call_count == 0
    assert c.apply_call_count == 0
    assert result.outcome == "applied-with-failures"
    assert len(result.apply_results) == 1


def test_apply_outcome_applied_when_all_succeeded() -> None:
    from ergodix.cantilever import run_cantilever

    a = _needs_install_prereq("A3")
    b = _needs_install_prereq("A5")

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[a, b],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
    )

    assert result.outcome == "applied"


def test_apply_emits_remediation_hint_on_failure() -> None:
    from ergodix.cantilever import run_cantilever
    from ergodix.prereqs.types import ApplyResult

    captured: list[str] = []

    class FailingPrereq:
        op_id = "A4"

        def inspect(self) -> InspectResult:
            return InspectResult(
                op_id="A4",
                status="needs-install",
                description="Install XeLaTeX",
                current_state="not found",
                proposed_action="brew install --cask mactex",
            )

        def apply(self) -> ApplyResult:
            return ApplyResult(
                op_id="A4",
                status="failed",
                message="brew install --cask mactex returned exit 1",
                remediation_hint="Free up at least 4 GB of disk space.",
            )

    run_cantilever(
        floaters={"writer": True},
        prereqs=[FailingPrereq()],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        output_fn=captured.append,
    )

    output = "\n".join(captured)
    assert "Free up at least 4 GB of disk space" in output


# ─── Sudo grouping ─────────────────────────────────────────────────────────


def test_admin_credentials_requested_once_when_plan_has_admin_ops() -> None:
    from ergodix.cantilever import run_cantilever

    a = _needs_install_prereq("A3", needs_admin=True)
    b = _needs_install_prereq("A4", needs_admin=True)
    c = _needs_install_prereq("A5", needs_admin=False)

    request_count = 0

    def fake_request_admin() -> bool:
        nonlocal request_count
        request_count += 1
        return True

    run_cantilever(
        floaters={"writer": True},
        prereqs=[a, b, c],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        request_admin_fn=fake_request_admin,
    )

    # Even though TWO ops need admin, the request happens just once.
    assert request_count == 1


def test_admin_credentials_not_requested_when_no_admin_ops() -> None:
    from ergodix.cantilever import run_cantilever

    a = _needs_install_prereq("A3", needs_admin=False)
    b = _needs_install_prereq("A5", needs_admin=False)

    def fake_request_admin() -> bool:
        pytest.fail("admin should not be requested when no plan op needs it")

    run_cantilever(
        floaters={"writer": True},
        prereqs=[a, b],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        request_admin_fn=fake_request_admin,
    )


def test_admin_denied_outcome_when_credentials_not_granted() -> None:
    from ergodix.cantilever import run_cantilever

    a = _needs_install_prereq("A4", needs_admin=True)

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[a],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        request_admin_fn=lambda: False,  # user declined / sudo failed
    )

    assert result.outcome == "admin-denied"
    assert a.apply_call_count == 0  # no apply ran
    assert result.apply_results == []
