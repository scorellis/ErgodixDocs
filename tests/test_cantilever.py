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

from collections.abc import Callable
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
    returning an ApplyResult, interactive_complete() (per ADR 0012) for
    needs-interactive ops.
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

    # Interactive-complete configuration (only relevant when inspect_status
    # is "needs-interactive"; ignored otherwise).
    interactive_complete_status: ApplyStatus = "ok"
    interactive_complete_message: str = "fake configured"
    # Each entry is a list of (prompt, hidden) tuples that the prereq
    # asked the prompt_fn for during a single interactive_complete call.
    interactive_prompts_to_request: list[tuple[str, bool]] = field(
        default_factory=lambda: [("Fake prompt: ", False)]
    )

    inspect_call_count: int = field(default=0, init=False)
    apply_call_count: int = field(default=0, init=False)
    # Records what was answered for each prompt in the order it was requested.
    interactive_complete_answers: list[str | None] = field(default_factory=list, init=False)
    interactive_complete_call_count: int = field(default=0, init=False)

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

    def interactive_complete(
        self,
        prompt_fn: Callable[[str, bool], str | None],
    ) -> ApplyResult:
        self.interactive_complete_call_count += 1
        for prompt, hidden in self.interactive_prompts_to_request:
            answer = prompt_fn(prompt, hidden)
            self.interactive_complete_answers.append(answer)
        return ApplyResult(
            op_id=self.op_id,
            status=self.interactive_complete_status,
            message=self.interactive_complete_message,
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


def _needs_interactive_prereq(
    op_id: str = "C3",
    prompts: list[tuple[str, bool]] | None = None,
) -> FakePrereq:
    """
    Helper for needs-interactive prereqs (per ADR 0012). Default prompts to
    a single non-hidden input.
    """
    return FakePrereq(
        op_id=op_id,
        inspect_status="needs-interactive",
        proposed_action=f"Configure {op_id}",
        interactive_prompts_to_request=prompts or [(f"Enter value for {op_id}: ", False)],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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
        verify_checks=[],
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


# ─── Phase 4: verify ───────────────────────────────────────────────────────


def test_verify_runs_after_successful_apply() -> None:
    from ergodix.cantilever import VerifyResult, run_cantilever

    p = _needs_install_prereq("A3")
    verify_called = False

    def fake_verify() -> VerifyResult:
        nonlocal verify_called
        verify_called = True
        return VerifyResult(name="t", passed=True, message="ok")

    run_cantilever(
        floaters={"writer": True},
        prereqs=[p],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        verify_checks=[fake_verify],
    )

    assert verify_called


def test_verify_runs_even_when_apply_aborted() -> None:
    """End-state verification matters most when apply went sideways."""
    from ergodix.cantilever import VerifyResult, run_cantilever

    p = _needs_install_prereq("A3")
    p.apply_status = "failed"

    verify_called = False

    def fake_verify() -> VerifyResult:
        nonlocal verify_called
        verify_called = True
        return VerifyResult(name="t", passed=True, message="ok")

    run_cantilever(
        floaters={"writer": True},
        prereqs=[p],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        verify_checks=[fake_verify],
    )

    assert verify_called


def test_verify_runs_when_no_changes_needed() -> None:
    """
    Per Copilot review 2026-05-05: verify should run on the no-changes-
    needed path too — that's the moment a too-permissive inspect would
    produce a false green. Verify is the cross-check.
    """
    from ergodix.cantilever import VerifyResult, run_cantilever

    verify_called = False

    def fake_verify() -> VerifyResult:
        nonlocal verify_called
        verify_called = True
        return VerifyResult(name="t", passed=True, message="ok")

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok_prereq("A1")],
        consent_fn=lambda _plan: pytest.fail("consent should not be requested"),
        is_online_fn=lambda: True,
        verify_checks=[fake_verify],
    )

    assert verify_called


def test_verify_failure_when_no_changes_needed_yields_verify_failed_outcome() -> None:
    from ergodix.cantilever import VerifyResult, run_cantilever

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok_prereq("A1")],
        consent_fn=lambda _plan: pytest.fail("consent should not be requested"),
        is_online_fn=lambda: True,
        verify_checks=[
            lambda: VerifyResult(name="t", passed=False, message="bad", remediation="x"),
        ],
    )

    assert result.outcome == "verify-failed"


def test_verify_skipped_in_dry_run() -> None:
    from ergodix.cantilever import run_cantilever

    def fake_verify():  # type: ignore[no-untyped-def]
        pytest.fail("verify should not run in dry-run mode")

    run_cantilever(
        floaters={"writer": True, "dry-run": True},
        prereqs=[_needs_install_prereq("A3")],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        verify_checks=[fake_verify],
    )


def test_verify_skipped_when_consent_declined() -> None:
    from ergodix.cantilever import run_cantilever

    def fake_verify():  # type: ignore[no-untyped-def]
        pytest.fail("verify should not run when consent declined")

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_needs_install_prereq("A3")],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
        verify_checks=[fake_verify],
    )


def test_verify_skipped_when_admin_denied() -> None:
    from ergodix.cantilever import run_cantilever

    def fake_verify():  # type: ignore[no-untyped-def]
        pytest.fail("verify should not run when admin was denied")

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_needs_install_prereq("A3", needs_admin=True)],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        request_admin_fn=lambda: False,
        verify_checks=[fake_verify],
    )


def test_verify_results_collected_in_cantilever_result() -> None:
    from ergodix.cantilever import VerifyResult, run_cantilever

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[_needs_install_prereq("A3")],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        verify_checks=[
            lambda: VerifyResult(name="c1", passed=True, message="ok"),
            lambda: VerifyResult(name="c2", passed=True, message="ok"),
        ],
    )

    assert [vr.name for vr in result.verify_results] == ["c1", "c2"]


def test_verify_failed_after_successful_apply_yields_verify_failed_outcome() -> None:
    from ergodix.cantilever import VerifyResult, run_cantilever

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[_needs_install_prereq("A3")],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        verify_checks=[
            lambda: VerifyResult(name="c1", passed=False, message="bad", remediation="fix it"),
        ],
    )

    assert result.outcome == "verify-failed"


def test_verify_does_not_override_applied_with_failures_outcome() -> None:
    """Apply failure dominates verify failure in the outcome ladder."""
    from ergodix.cantilever import VerifyResult, run_cantilever

    p = _needs_install_prereq("A3")
    p.apply_status = "failed"

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[p],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        verify_checks=[lambda: VerifyResult(name="c1", passed=False, message="bad")],
    )

    assert result.outcome == "applied-with-failures"


def test_verify_emits_pass_marker_for_passing_checks() -> None:
    from ergodix.cantilever import VerifyResult, run_cantilever

    captured: list[str] = []

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_needs_install_prereq("A3")],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        output_fn=captured.append,
        verify_checks=[lambda: VerifyResult(name="ergodix_imports", passed=True, message="ok")],
    )

    output = "\n".join(captured)
    assert "ergodix_imports" in output
    assert "✓" in output


# ─── Inspect-failed halts cantilever (Copilot 2026-05-05 finding #2) ──────


def test_inspect_failed_halts_cantilever_before_plan_building() -> None:
    """
    Per Copilot review 2026-05-05: a failed inspect must NOT silently fall
    through to no-changes-needed (because needs_action is False for status
    'failed') or get rewritten to deferred-offline. It is its own outcome.
    """
    from ergodix.cantilever import run_cantilever

    failing = FakePrereq(
        op_id="A2",
        inspect_status="failed",
        description="Pandoc availability",
        current_state="exec failed: command not found",
        proposed_action=None,
    )
    other = _needs_install_prereq("A3")

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[failing, other],
        consent_fn=lambda _plan: pytest.fail("consent must not run when inspect failed"),
        is_online_fn=lambda: True,
        verify_checks=[lambda: pytest.fail("verify must not run when inspect failed")],  # type: ignore[arg-type, return-value]
    )

    assert result.outcome == "inspect-failed"
    # No apply must have happened.
    assert other.apply_call_count == 0
    # The failing inspect result is in the result.
    assert any(r.status == "failed" for r in result.inspect_results)


def test_inspect_failed_status_not_rewritten_to_deferred_offline_when_offline() -> None:
    """
    Even offline, a 'failed' inspect must remain failed — not get rewritten
    to 'deferred-offline'. Only needs-install / needs-update get rewritten.
    """
    from ergodix.cantilever import run_cantilever

    failing = FakePrereq(
        op_id="A2",
        inspect_status="failed",
        description="Pandoc availability",
        current_state="probe error",
        network_required=True,
    )

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[failing],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: False,
        verify_checks=[],
    )

    by_id = {ir.op_id: ir for ir in result.inspect_results}
    assert by_id["A2"].status == "failed"
    assert result.outcome == "inspect-failed"


# ─── op_id uniqueness validation (Copilot finding #3) ─────────────────────


def test_duplicate_op_ids_raises_at_entry() -> None:
    """Two prereqs with the same op_id is a programmer error; fail loudly."""
    from ergodix.cantilever import run_cantilever

    a = _ok_prereq("A1")
    a_dup = _ok_prereq("A1")  # same op_id

    with pytest.raises(ValueError, match="duplicate"):
        run_cantilever(
            floaters={"writer": True},
            prereqs=[a, a_dup],
            consent_fn=lambda _plan: False,
            is_online_fn=lambda: True,
            verify_checks=[],
        )


# ─── Verify ergodix smoke uses venv path (Copilot finding #4) ──────────────


def test_default_ergodix_smoke_uses_interpreter_directory_path() -> None:
    """
    The default ergodix command smoke check must locate ergodix relative
    to sys.executable's directory (the venv's bin/Scripts), not via
    shutil.which() on ambient PATH. Otherwise the check is sensitive to
    how cantilever was invoked rather than to whether install succeeded.
    """
    import sys
    from pathlib import Path

    from ergodix.cantilever import _verify_ergodix_command

    result = _verify_ergodix_command()
    expected_dir = Path(sys.executable).parent
    # The check's message must reference the interpreter-derived path
    # whether it passed or failed — that's what we're really testing
    # (i.e. the path was derived from sys.executable, not from $PATH).
    assert str(expected_dir) in result.message


# ─── Local-config-sane verify check (Copilot finding #1, partial) ─────────


def test_verify_local_config_sane_passes_with_valid_file(tmp_path, monkeypatch) -> None:
    from ergodix.cantilever import _verify_local_config_sane

    monkeypatch.chdir(tmp_path)
    config = tmp_path / "local_config.py"
    config.write_text(
        "from pathlib import Path\nCORPUS_FOLDER = Path('/some/corpus')\n",
    )
    config.chmod(0o600)

    result = _verify_local_config_sane()
    assert result.passed
    assert "local_config" in result.name


def test_verify_local_config_sane_fails_when_missing(tmp_path, monkeypatch) -> None:
    from ergodix.cantilever import _verify_local_config_sane

    monkeypatch.chdir(tmp_path)  # no local_config.py exists here

    result = _verify_local_config_sane()
    assert not result.passed
    assert "not found" in result.message.lower() or "missing" in result.message.lower()


def test_verify_local_config_sane_fails_when_perms_loose(tmp_path, monkeypatch) -> None:
    from ergodix.cantilever import _verify_local_config_sane

    monkeypatch.chdir(tmp_path)
    config = tmp_path / "local_config.py"
    config.write_text(
        "from pathlib import Path\nCORPUS_FOLDER = Path('/some/corpus')\n",
    )
    config.chmod(0o644)  # too permissive

    result = _verify_local_config_sane()
    assert not result.passed
    assert "600" in result.message or "perm" in result.message.lower()


def test_verify_local_config_sane_fails_when_corpus_folder_empty(tmp_path, monkeypatch) -> None:
    from ergodix.cantilever import _verify_local_config_sane

    monkeypatch.chdir(tmp_path)
    config = tmp_path / "local_config.py"
    config.write_text("CORPUS_FOLDER = ''\n")
    config.chmod(0o600)

    result = _verify_local_config_sane()
    assert not result.passed
    assert "CORPUS_FOLDER" in result.message


# ─── Phase 4: Configure (per ADR 0012) ──────────────────────────────────────


def test_configure_phase_runs_after_apply_before_verify() -> None:
    """
    Per ADR 0012, the new five-phase orchestrator runs configure between
    apply and verify. Pin the order via call counters across two prereqs:
    one mutative (apply) and one interactive (configure).
    """
    from ergodix.cantilever import run_cantilever

    install = _needs_install_prereq("A3")
    configure = _needs_interactive_prereq("C3")

    run_cantilever(
        floaters={"writer": True},
        prereqs=[install, configure],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        prompt_fn=lambda _p, _h: "answer",
        verify_checks=[],
    )

    assert install.apply_call_count == 1
    assert configure.interactive_complete_call_count == 1
    # configure.apply() should NOT be called for needs-interactive ops
    # (apply() is a no-op stub for these per ADR 0012).
    assert configure.apply_call_count == 0


def test_configure_phase_skipped_when_no_needs_interactive_ops() -> None:
    """
    All ops are needs-install or ok → configure phase is silently skipped.
    No prompts emitted; no configure_results in the report.
    """
    from ergodix.cantilever import run_cantilever

    install = _needs_install_prereq("A3")

    prompt_calls: list[tuple[str, bool]] = []

    def recording_prompt(p: str, h: bool) -> str | None:
        prompt_calls.append((p, h))
        return "should-not-be-called"

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[install],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        prompt_fn=recording_prompt,
        verify_checks=[],
    )

    assert prompt_calls == []
    assert result.configure_results == []


def test_configure_phase_calls_prereq_interactive_complete_with_prompt_fn() -> None:
    """
    The configure phase passes the prompt_fn to each needs-interactive
    prereq's interactive_complete() method so the prereq controls its own
    prompt loop (one prereq may need multiple prompts — e.g., C3 wants
    user.name AND user.email).
    """
    from ergodix.cantilever import run_cantilever

    multi_prompt = _needs_interactive_prereq(
        "C3",
        prompts=[
            ("Enter your git user.name: ", False),
            ("Enter your git user.email: ", False),
        ],
    )

    answer_iter = iter(["Stephen Corellis", "scorellis@example.com"])

    run_cantilever(
        floaters={"writer": True},
        prereqs=[multi_prompt],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        prompt_fn=lambda _p, _h: next(answer_iter),
        verify_checks=[],
    )

    assert multi_prompt.interactive_complete_call_count == 1
    assert multi_prompt.interactive_complete_answers == [
        "Stephen Corellis",
        "scorellis@example.com",
    ]


def test_configure_phase_skipped_when_ci_floater_set() -> None:
    """
    Per ADR 0012, --ci skips the configure phase entirely. CI environments
    must provide config via env vars (auth.py's tier-1 lookup; CI's git
    config setup), not via interactive prompts.
    """
    from ergodix.cantilever import run_cantilever

    configure = _needs_interactive_prereq("C3")

    prompt_calls: list[tuple[str, bool]] = []

    result = run_cantilever(
        floaters={"writer": True, "ci": True},
        prereqs=[configure],
        consent_fn=lambda _plan: True,  # ignored under --ci
        is_online_fn=lambda: True,
        prompt_fn=lambda p, h: prompt_calls.append((p, h)) or "should-not-be-called",
        verify_checks=[],
    )

    assert configure.interactive_complete_call_count == 0
    assert prompt_calls == []
    assert result.configure_results == []


def test_configure_phase_emits_results_per_prereq() -> None:
    """
    configure_results lists one ApplyResult per needs-interactive prereq
    that ran, in inspect-order, with the prereq's reported status.
    """
    from ergodix.cantilever import run_cantilever

    a = _needs_interactive_prereq("C3")
    b = _needs_interactive_prereq("C6")
    b.interactive_complete_status = "skipped"
    b.interactive_complete_message = "user skipped credential entry"

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[a, b],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        prompt_fn=lambda _p, _h: "answer",
        verify_checks=[],
    )

    assert len(result.configure_results) == 2
    assert [r.op_id for r in result.configure_results] == ["C3", "C6"]
    assert result.configure_results[0].status == "ok"
    assert result.configure_results[1].status == "skipped"


def test_needs_interactive_op_appears_in_plan_and_in_consent() -> None:
    """
    ADR 0012 requires that needs-interactive ops show up in the plan
    (so the user is informed at the consent gate that input will be
    requested later in the run).
    """
    from ergodix.cantilever import run_cantilever

    configure = _needs_interactive_prereq("C3")

    captured_plans: list[int] = []

    def consent(plan):
        captured_plans.append(len(plan.items))
        return False  # decline so we can assert without progressing

    run_cantilever(
        floaters={"writer": True},
        prereqs=[configure],
        consent_fn=consent,
        is_online_fn=lambda: True,
        prompt_fn=lambda _p, _h: "answer",
        verify_checks=[],
    )

    assert captured_plans == [1], "needs-interactive op must appear in the plan"


def test_configure_phase_on_no_changes_path_does_not_run() -> None:
    """
    When the plan is empty (no needs-* ops at all), there's nothing for
    configure to do either — it should be silently skipped on the
    no-changes-needed path.
    """
    from ergodix.cantilever import run_cantilever

    ok = _ok_prereq("A1")

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[ok],
        consent_fn=lambda _plan: pytest.fail("consent should not run"),
        is_online_fn=lambda: True,
        prompt_fn=lambda _p, _h: pytest.fail("prompt should not run"),
        verify_checks=[],
    )

    assert result.configure_results == []
    assert result.outcome == "no-changes-needed"


def test_configure_failure_does_not_block_verify() -> None:
    """
    A configure prereq returning status='failed' is recorded but doesn't
    prevent verify from running — the user still needs to see the full
    end-state picture, same contract as apply-failed (per ADR 0010's
    "Verify always runs" Note from 2026-05-06 finding #5).
    """
    from ergodix.cantilever import VerifyResult, run_cantilever

    configure = _needs_interactive_prereq("C3")
    configure.interactive_complete_status = "failed"
    configure.interactive_complete_message = "could not run git config"

    verify_calls = []

    def verify_check() -> VerifyResult:
        verify_calls.append(1)
        return VerifyResult(name="x", passed=True, message="ok")

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[configure],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        prompt_fn=lambda _p, _h: "answer",
        verify_checks=[verify_check],
    )

    assert verify_calls == [1]
    assert result.configure_results[0].status == "failed"


# ─── Pre-flight: settings loading + warnings (per ADR 0012 / F1 reframe) ──


def test_run_cantilever_loads_settings_at_preflight_with_defaults_when_no_file(
    tmp_path,
    monkeypatch,
) -> None:
    """
    Pre-flight loads settings/bootstrap.toml; when no settings/ directory
    exists, defaults are used and the run completes normally. The loaded
    settings end up on the CantileverResult for downstream visibility.
    """
    from ergodix.cantilever import run_cantilever

    monkeypatch.chdir(tmp_path)

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok_prereq("A1")],
        consent_fn=lambda _plan: pytest.fail("consent should not run"),
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    assert result.settings is not None
    # Documented default per ADR 0012.
    assert result.settings.mactex_install_size == "full"
    # No warnings on the no-file path.
    assert result.settings.warnings == []


def test_run_cantilever_surfaces_settings_warnings_to_user(
    tmp_path,
    monkeypatch,
) -> None:
    """
    Malformed bootstrap.toml → defaults take over (no abort) AND warnings
    are emitted via output_fn before the plan-display phase, so the user
    sees their config typo without losing the run.
    """
    from ergodix.cantilever import run_cantilever

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "bootstrap.toml").write_text("not = valid TOML at all [")
    monkeypatch.chdir(tmp_path)

    captured: list[str] = []

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok_prereq("A1")],
        consent_fn=lambda _plan: pytest.fail("consent should not run"),
        is_online_fn=lambda: True,
        output_fn=captured.append,
        verify_checks=[],
    )

    output = "\n".join(captured)
    assert "settings" in output.lower() or "warning" in output.lower()
    assert result.settings.warnings
    # Run still completes; settings just default.
    assert result.settings.mactex_install_size == "full"


# ─── Default consent function — interactive UX ────────────────────────────


def test_default_consent_fn_terminates_with_newline_so_apply_starts_clean(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    Regression for the 2026-05-07 self-smoke finding: consent prompt and
    apply progress visually collided. ``input()`` does not append a newline
    when stdin is piped (no interactive Enter to echo), so the next
    ``output_fn`` call landed on the same line as the prompt — making the
    consent question and answer effectively invisible to the user.

    Invariant: after ``_default_consent_fn`` returns, anything subsequently
    written to stdout starts on a fresh line. Operationally that means the
    captured output ends with ``\\n``.
    """
    from ergodix.cantilever import Plan, _default_consent_fn
    from ergodix.prereqs.types import InspectResult

    # Mirror real input() behavior: it writes the prompt to stdout (with no
    # trailing newline) before reading. A bare ``lambda _: "y"`` would skip
    # that write and hide the bug.
    def fake_input(prompt: str) -> str:
        import sys

        sys.stdout.write(prompt)
        return "y"

    monkeypatch.setattr("builtins.input", fake_input)
    plan = Plan(
        items=[
            InspectResult(
                op_id="X1",
                status="needs-install",
                description="fake op",
                current_state="absent",
                proposed_action="install fake op",
            )
        ]
    )

    accepted = _default_consent_fn(plan)
    captured = capsys.readouterr().out

    assert accepted is True
    assert captured.endswith("\n"), (
        "consent prompt did not terminate with a newline; subsequent "
        "output will collide with the prompt line. "
        f"trailing chars: {captured[-60:]!r}"
    )


def test_verify_emits_fail_marker_and_remediation() -> None:
    from ergodix.cantilever import VerifyResult, run_cantilever

    captured: list[str] = []

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_needs_install_prereq("A3")],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        output_fn=captured.append,
        verify_checks=[
            lambda: VerifyResult(
                name="ergodix_imports",
                passed=False,
                message="couldn't import",
                remediation="run pip install -e .",
            ),
        ],
    )

    output = "\n".join(captured)
    assert "✗" in output
    assert "ergodix_imports" in output
    assert "run pip install -e ." in output
