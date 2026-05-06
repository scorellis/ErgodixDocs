"""
Cantilever — the four-phase installer orchestrator from ADR 0010.

Phases:
  1. INSPECT  — run every prereq's inspect() (read-only). Network-required
                ops return deferred-offline when offline.
  2. PLAN     — filter to needs-action items; offer the plan to the user
                via consent_fn. --dry-run shows the plan and exits.
                --ci skips consent and proceeds. Decline exits cleanly.
  3. APPLY    — call apply() for consented items. (Implemented in step 2b
                of Story 0.11; this file lands phases 1+2 first.)
  4. VERIFY   — smoke checks confirming the install works. (Step 2b.)

Phase 3 and Phase 4 are stubbed today: when consent is given, we walk
the plan and call apply() in order. Failure handling, sudo grouping,
progress display, and verify-phase smoke checks land in the next step.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from ergodix.prereqs.types import ApplyResult, InspectResult

# ─── Protocol that real prereqs and test fakes both satisfy ────────────────


class PrereqSpec(Protocol):
    """Anything cantilever can drive: an op_id plus inspect() and apply()."""

    op_id: str

    def inspect(self) -> InspectResult: ...

    def apply(self) -> ApplyResult: ...


# ─── Plan ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Plan:
    """The ordered list of ops the user is being asked to consent to."""

    items: list[InspectResult]

    @property
    def has_admin_ops(self) -> bool:
        return any(item.needs_admin for item in self.items)

    @property
    def total_estimated_seconds(self) -> int:
        """Treats unknown estimates as zero."""
        return sum(item.estimated_seconds or 0 for item in self.items)


# ─── Result ────────────────────────────────────────────────────────────────


CantileverOutcome = Literal[
    "no-changes-needed",
    "consent-declined",
    "dry-run",
    "applied",
    "applied-with-failures",
    "admin-denied",
]


@dataclass
class CantileverResult:
    """Final report from a cantilever run."""

    outcome: CantileverOutcome
    inspect_results: list[InspectResult]
    plan: Plan
    apply_results: list[ApplyResult] = field(default_factory=list)


# ─── Default consent function (replaced by tests) ──────────────────────────


def _default_consent_fn(plan: Plan) -> bool:
    """
    Real interactive consent. Tests inject their own. Implementation here
    is intentionally minimal until phase 2's plan-display UI is designed.
    """
    print(_render_plan(plan))
    answer = input("Apply these changes? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def _render_plan(plan: Plan) -> str:
    """Plain-text plan rendering. Will get richer when phase 2 UI is built out."""
    lines = [f"\nPlan: {len(plan.items)} change(s) to apply"]
    if plan.has_admin_ops:
        lines.append("(Some steps require admin access; you'll be prompted once.)")
    for i, item in enumerate(plan.items, 1):
        admin_marker = " [admin]" if item.needs_admin else ""
        eta = f" (~{item.estimated_seconds}s)" if item.estimated_seconds is not None else ""
        lines.append(
            f"  [{i}/{len(plan.items)}]{admin_marker}{eta} "
            f"{item.description}: {item.proposed_action}"
        )
    return "\n".join(lines)


# ─── Default connectivity probe ────────────────────────────────────────────


def _default_is_online_fn() -> bool:
    """
    Conservative network check. Tests inject their own. Real implementation
    will live in ergodix/connectivity.py per ADR 0003 / 0010 and probably
    do a quick TCP probe to a stable endpoint.
    """
    return True


def _default_request_admin_fn() -> bool:
    """
    Request admin (sudo) credentials once. After this returns True, any
    subsequent `sudo` call within the cache window (default 5 min on macOS)
    runs without prompting again. Tests inject their own.
    """
    import shutil
    import subprocess

    sudo_path = shutil.which("sudo")
    if sudo_path is None:
        return False
    try:
        result = subprocess.run([sudo_path, "-v"], check=False)
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


# ─── Phase implementations ─────────────────────────────────────────────────


def _inspect_all(prereqs: list[PrereqSpec], *, online: bool) -> list[InspectResult]:
    """
    Phase 1: run every prereq's inspect(). If the system is offline, any
    network-required op that came back as needing action is rewritten to
    deferred-offline (its action is genuinely not safe to attempt).
    """
    results: list[InspectResult] = []
    for prereq in prereqs:
        result = prereq.inspect()
        if not online and result.network_required and result.status != "ok":
            # Re-issue as deferred-offline. InspectResult is frozen, so build a new one.
            result = InspectResult(
                op_id=result.op_id,
                status="deferred-offline",
                description=result.description,
                current_state=result.current_state,
                proposed_action=result.proposed_action,
                needs_admin=result.needs_admin,
                estimated_seconds=result.estimated_seconds,
                network_required=result.network_required,
            )
        results.append(result)
    return results


def _build_plan(inspect_results: list[InspectResult]) -> Plan:
    """Phase 2 (build): filter to needs-action items; preserve input order."""
    return Plan(items=[ir for ir in inspect_results if ir.needs_action])


def _apply_consented(
    prereqs: list[PrereqSpec],
    plan: Plan,
    *,
    output_fn: Callable[[str], None],
) -> tuple[list[ApplyResult], bool]:
    """
    Phase 3 (apply): walk the plan in order, call apply() on each prereq.

    - Emits a `[k/total] description...` progress line per op.
    - Emits a check or cross marker line per op.
    - On the first failure, emits a remediation block (with the prereq's
      remediation_hint if present) and returns immediately. Subsequent
      ops are NOT invoked. This is the abort-fast contract from ADR 0003.

    Returns a tuple ``(results, completed_fully)``. ``completed_fully``
    is False when an apply failed (so the caller can set the appropriate
    outcome).
    """
    by_op_id = {p.op_id: p for p in prereqs}
    results: list[ApplyResult] = []
    total = len(plan.items)

    for index, item in enumerate(plan.items, start=1):
        prereq = by_op_id[item.op_id]
        output_fn(f"[{index}/{total}] {item.description}…")
        result = prereq.apply()
        results.append(result)

        if result.status == "failed":
            output_fn(f"  ✗ Failed at step {index} of {total}: {item.op_id} — {item.description}")
            output_fn(f"    Reason: {result.message}")
            if result.remediation_hint:
                output_fn(f"    Suggested fix: {result.remediation_hint}")
            output_fn(
                "    Re-run cantilever after addressing this; "
                "earlier steps that already succeeded will be skipped (idempotent)."
            )
            return results, False

        output_fn(f"  ✓ {result.message}")

    return results, True


# ─── Public entry point ────────────────────────────────────────────────────


def run_cantilever(
    *,
    floaters: dict[str, bool],
    prereqs: list[PrereqSpec],
    consent_fn: Callable[[Plan], bool] = _default_consent_fn,
    is_online_fn: Callable[[], bool] = _default_is_online_fn,
    output_fn: Callable[[str], None] = print,
    request_admin_fn: Callable[[], bool] = _default_request_admin_fn,
) -> CantileverResult:
    """
    Top-level entrypoint. Per ADR 0010.

    Args:
        floaters: dict of floater names → enabled. Recognized: 'dry-run', 'ci'.
        prereqs: ordered list of prereq specs to drive.
        consent_fn: receives the Plan; returns True for accept, False for decline.
        is_online_fn: returns True if network is available.
        output_fn: writes progress/remediation lines. Tests pass a list-appender;
            real use prints to stderr/stdout.
        request_admin_fn: prompts for admin (sudo) credentials once, returning
            True if granted. Called only when the plan contains an op marked
            ``needs_admin``.

    Returns:
        CantileverResult describing the outcome, the inspections, the plan,
        and any apply results.
    """
    # Phase 1: Inspect (read-only).
    online = is_online_fn()
    inspect_results = _inspect_all(prereqs, online=online)

    # Phase 2: Plan.
    plan = _build_plan(inspect_results)

    if not plan.items:
        return CantileverResult(
            outcome="no-changes-needed",
            inspect_results=inspect_results,
            plan=plan,
        )

    # Phase 2: Consent gate (or floater bypass).
    if floaters.get("dry-run"):
        # Dry-run: show plan, do not apply.
        output_fn(_render_plan(plan))
        return CantileverResult(
            outcome="dry-run",
            inspect_results=inspect_results,
            plan=plan,
        )

    if not floaters.get("ci"):
        # Interactive (or test-injected) consent.
        consented = consent_fn(plan)
        if not consented:
            return CantileverResult(
                outcome="consent-declined",
                inspect_results=inspect_results,
                plan=plan,
            )
    # else: --ci floater treats as accept.

    # Phase 3: Apply.
    # Sudo grouping: if any plan op needs admin, request credentials ONCE
    # before any apply runs. Subsequent sudo invocations within the cache
    # window won't re-prompt. If the user denies / sudo fails, we abort
    # without running any apply.
    if plan.has_admin_ops and not request_admin_fn():
        output_fn(
            "error: admin credentials required for one or more steps but "
            "were not granted. No changes have been made."
        )
        return CantileverResult(
            outcome="admin-denied",
            inspect_results=inspect_results,
            plan=plan,
        )

    apply_results, completed = _apply_consented(prereqs, plan, output_fn=output_fn)

    outcome: CantileverOutcome = "applied" if completed else "applied-with-failures"

    return CantileverResult(
        outcome=outcome,
        inspect_results=inspect_results,
        plan=plan,
        apply_results=apply_results,
    )
