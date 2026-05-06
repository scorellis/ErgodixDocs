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
from pathlib import Path
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
    "verify-failed",
    "inspect-failed",
]


@dataclass(frozen=True)
class VerifyResult:
    """Output of a single phase-4 verify check. Read-only."""

    name: str
    """Stable identifier of the check (e.g. 'ergodix_imports')."""

    passed: bool
    """True iff the check determined the system is in the expected state."""

    message: str
    """Human-readable summary, displayed regardless of passed."""

    remediation: str | None = None
    """Actionable advice when passed is False."""


@dataclass
class CantileverResult:
    """Final report from a cantilever run."""

    outcome: CantileverOutcome
    inspect_results: list[InspectResult]
    plan: Plan
    apply_results: list[ApplyResult] = field(default_factory=list)
    verify_results: list[VerifyResult] = field(default_factory=list)


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


def _verify_import_package() -> VerifyResult:
    """Smoke check: `python -c "import ergodix"` exits 0."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c", "import ergodix"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return VerifyResult(
            name="ergodix_imports",
            passed=True,
            message="`import ergodix` succeeds",
        )
    stderr = result.stderr.strip()
    last_line = stderr.splitlines()[-1] if stderr else "unknown error"
    return VerifyResult(
        name="ergodix_imports",
        passed=False,
        message=f"`import ergodix` failed: {last_line}",
        remediation="Activate your venv and run: pip install -e .",
    )


def _verify_ergodix_command() -> VerifyResult:
    """
    Smoke check: `ergodix --version` exits 0.

    Locates the script via ``sys.executable``'s directory rather than via
    ``shutil.which`` on ambient PATH. PATH-based lookup is sensitive to
    *how* cantilever was invoked rather than to whether the install
    actually succeeded; deriving from the interpreter directory matches
    where ``pip install -e .`` puts the console-script.
    """
    import platform
    import subprocess
    import sys

    interpreter_dir = Path(sys.executable).parent
    suffix = ".exe" if platform.system() == "Windows" else ""
    ergodix_path = interpreter_dir / f"ergodix{suffix}"

    if not ergodix_path.exists():
        return VerifyResult(
            name="ergodix_on_path",
            passed=False,
            message=f"`ergodix` script not found at {ergodix_path}",
            remediation="Activate the venv and run: pip install -e .",
        )
    try:
        result = subprocess.run(
            [str(ergodix_path), "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return VerifyResult(
            name="ergodix_on_path",
            passed=False,
            message=f"failed to run `{ergodix_path} --version`: {exc}",
            remediation="Re-run cantilever to repair the install.",
        )
    if result.returncode == 0:
        return VerifyResult(
            name="ergodix_on_path",
            passed=True,
            message=f"`{ergodix_path} --version` returns: {result.stdout.strip()}",
        )
    return VerifyResult(
        name="ergodix_on_path",
        passed=False,
        message=f"`{ergodix_path} --version` exited {result.returncode}",
        remediation="Re-run cantilever to repair the install.",
    )


def _verify_local_config_sane() -> VerifyResult:
    """
    Smoke check (per ADR 0010): ``local_config.py`` exists in the current
    directory, has mode 600, and defines a non-empty ``CORPUS_FOLDER``.

    Resolves the file from the current working directory because cantilever
    is documented to run from the repo root. Tests use ``monkeypatch.chdir``
    to point this at fixture content.
    """
    import importlib.util

    config_path = Path.cwd() / "local_config.py"

    if not config_path.exists():
        return VerifyResult(
            name="local_config_sane",
            passed=False,
            message=f"local_config.py not found at {config_path}",
            remediation="Re-run cantilever; the config-bootstrap step generates it.",
        )

    mode = config_path.stat().st_mode & 0o777
    if mode != 0o600:
        return VerifyResult(
            name="local_config_sane",
            passed=False,
            message=f"local_config.py has perms {oct(mode)}, expected 0o600",
            remediation=f"chmod 600 {config_path}",
        )

    try:
        spec = importlib.util.spec_from_file_location("_local_config_check", config_path)
        if spec is None or spec.loader is None:  # pragma: no cover — defensive
            return VerifyResult(
                name="local_config_sane",
                passed=False,
                message=f"could not load {config_path} as a module",
                remediation="Inspect the file for syntax errors.",
            )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:
        return VerifyResult(
            name="local_config_sane",
            passed=False,
            message=f"loading local_config.py raised: {exc}",
            remediation="Inspect the file for syntax errors and re-run cantilever.",
        )

    corpus = getattr(module, "CORPUS_FOLDER", None)
    if not corpus or not str(corpus).strip():
        return VerifyResult(
            name="local_config_sane",
            passed=False,
            message="CORPUS_FOLDER in local_config.py is missing or empty",
            remediation="Edit local_config.py and set CORPUS_FOLDER to your corpus path.",
        )

    return VerifyResult(
        name="local_config_sane",
        passed=True,
        message=f"local_config.py at {config_path} has mode 600 and CORPUS_FOLDER={corpus}",
    )


_DEFAULT_VERIFY_CHECKS: list[Callable[[], VerifyResult]] = [
    _verify_import_package,
    _verify_ergodix_command,
    _verify_local_config_sane,
]


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
    network-required op that *would have wanted to act* (needs-install or
    needs-update) is rewritten to deferred-offline. A 'failed' inspect is
    NEVER rewritten — it surfaces as-is so cantilever can halt with an
    inspect-failed outcome.
    """
    rewritable = {"needs-install", "needs-update"}
    results: list[InspectResult] = []
    for prereq in prereqs:
        result = prereq.inspect()
        if not online and result.network_required and result.status in rewritable:
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


def _run_verify_phase(
    checks: list[Callable[[], VerifyResult]],
    *,
    output_fn: Callable[[str], None],
) -> list[VerifyResult]:
    """
    Phase 4: run each verify check, collect results, emit a summary.

    Always runs every check (no abort-fast) — the user wants to see the
    full end-state, not just the first thing that's wrong.
    """
    results: list[VerifyResult] = []
    output_fn("\nVerification:")
    for check in checks:
        result = check()
        results.append(result)
        marker = "✓" if result.passed else "✗"
        output_fn(f"  {marker} {result.name}: {result.message}")
        if not result.passed and result.remediation:
            output_fn(f"    Suggested fix: {result.remediation}")
    return results


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
    verify_checks: list[Callable[[], VerifyResult]] | None = None,
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
        verify_checks: list of phase-4 verify functions. Defaults to the
            built-in checks (``_verify_import_package`` and
            ``_verify_ergodix_command``). Tests inject explicit lists.

    Returns:
        CantileverResult describing the outcome, the inspections, the plan,
        and any apply / verify results.
    """
    checks = verify_checks if verify_checks is not None else _DEFAULT_VERIFY_CHECKS

    # Pre-flight: op_ids must be unique (Copilot review 2026-05-05 finding #3).
    seen: set[str] = set()
    duplicates: list[str] = []
    for prereq in prereqs:
        if prereq.op_id in seen:
            duplicates.append(prereq.op_id)
        seen.add(prereq.op_id)
    if duplicates:
        raise ValueError(
            f"prereq list contains duplicate op_id(s): {sorted(set(duplicates))}. "
            "Each prereq must have a unique op_id."
        )

    # Phase 1: Inspect (read-only).
    online = is_online_fn()
    inspect_results = _inspect_all(prereqs, online=online)

    # Phase 1.5: if any inspect failed, halt before plan/consent/apply.
    # Per Copilot review 2026-05-05 finding #2: a 'failed' inspect must not
    # silently fall through to no-changes-needed (because needs_action is
    # False) or be rewritten to deferred-offline.
    if any(ir.status == "failed" for ir in inspect_results):
        return CantileverResult(
            outcome="inspect-failed",
            inspect_results=inspect_results,
            plan=Plan(items=[]),
        )

    # Phase 2: Plan.
    plan = _build_plan(inspect_results)

    if not plan.items:
        # Per Copilot review 2026-05-05 finding #5: still run verify on the
        # no-changes path. If inspect was too permissive, verify is the
        # cross-check that catches a false green.
        verify_results = _run_verify_phase(checks, output_fn=output_fn)
        outcome: CantileverOutcome = (
            "verify-failed" if any(not vr.passed for vr in verify_results) else "no-changes-needed"
        )
        return CantileverResult(
            outcome=outcome,
            inspect_results=inspect_results,
            plan=plan,
            verify_results=verify_results,
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

    # Phase 4: Verify. Always runs after apply (whether apply succeeded or
    # aborted) — the user needs the end-state picture either way.
    verify_results = _run_verify_phase(checks, output_fn=output_fn)

    # Outcome ladder:
    #   apply failed at all → "applied-with-failures" (apply failure dominates)
    #   apply succeeded, any verify failed → "verify-failed"
    #   both apply and verify clean → "applied"
    if not completed:
        outcome = "applied-with-failures"
    elif any(not vr.passed for vr in verify_results):
        outcome = "verify-failed"
    else:
        outcome = "applied"

    return CantileverResult(
        outcome=outcome,
        inspect_results=inspect_results,
        plan=plan,
        apply_results=apply_results,
        verify_results=verify_results,
    )
