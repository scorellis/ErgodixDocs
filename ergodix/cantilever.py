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

import contextlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol

from ergodix.prereqs.types import ApplyResult, InspectResult
from ergodix.settings import BootstrapSettings, load_bootstrap_settings

# ─── Protocol that real prereqs and test fakes both satisfy ────────────────


PromptFn = Callable[[str, bool], "str | None"]
"""Callback the configure phase hands to interactive prereqs.

Args:
    prompt: text to display to the user (no trailing newline expected;
        the prompt_fn handles input/getpass which renders the prompt).
    hidden: if True, use ``getpass`` (credentials, tokens); if False,
        use plain ``input`` (git config, paths, free-form strings).

Returns the trimmed user answer, or None if the user pressed Enter
without typing anything (interpreted as "skip this prompt").
"""


class PrereqSpec(Protocol):
    """Anything cantilever can drive: an op_id plus the three lifecycle methods.

    Per ADR 0010 and ADR 0012, the lifecycle is:

    - ``inspect()`` (read-only) — what's the current state? Drives the plan.
    - ``apply()`` (mutative, no-op for needs-interactive ops) — make changes.
    - ``interactive_complete()`` (per ADR 0012) — when inspect returned
      ``needs-interactive``, the configure phase calls this with a prompt
      callback. The prereq runs its own prompt loop (one prereq may need
      multiple prompts, e.g., C3 wants user.name AND user.email) and
      reports back via an ApplyResult.

    Prereqs that never report ``needs-interactive`` may implement
    ``interactive_complete()`` as a no-op stub (e.g., return
    ``ApplyResult(status="skipped", message="not interactive")``).
    The ModulePrereq adapter handles modules that omit it entirely.
    """

    op_id: str

    def inspect(self) -> InspectResult: ...

    def apply(self) -> ApplyResult: ...

    def interactive_complete(self, prompt_fn: PromptFn) -> ApplyResult: ...


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
    "configure-failed",
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
    configure_results: list[ApplyResult] = field(default_factory=list)
    verify_results: list[VerifyResult] = field(default_factory=list)
    settings: BootstrapSettings | None = None
    """Settings snapshot loaded at pre-flight (per ADR 0012's F1 reframe).
    None only if cantilever exits before pre-flight (e.g. duplicate-op_id
    ValueError); otherwise always populated, with defaults when no
    ``settings/bootstrap.toml`` is present."""


# ─── Default consent function (replaced by tests) ──────────────────────────


def _default_consent_fn(plan: Plan) -> bool:
    """
    Real interactive consent. Tests inject their own. Implementation here
    is intentionally minimal until phase 2's plan-display UI is designed.

    The trailing ``print()`` is load-bearing: ``input()`` writes the prompt
    without a newline and, when stdin is piped (non-tty), no newline is
    appended on read either. Without the explicit ``print()``, the next
    ``output_fn`` call (apply progress) collides with the prompt line and
    the user never sees the consent question.
    """
    print(_render_plan(plan))
    answer = input("Apply these changes? [y/N]: ").strip().lower()
    print()
    return answer in {"y", "yes"}


def _render_plan(plan: Plan) -> str:
    """Plain-text plan rendering. Will get richer when phase 2 UI is built out."""
    lines = [f"\nPlan: {len(plan.items)} change(s) to apply"]
    if plan.has_admin_ops:
        lines.append("(Some steps require admin access; you'll be prompted once.)")
    interactive_count = sum(1 for it in plan.items if it.status == "needs-interactive")
    if interactive_count:
        lines.append(
            f"({interactive_count} step(s) marked [interactive] will prompt you for input "
            "after the install steps complete.)"
        )
    for i, item in enumerate(plan.items, 1):
        admin_marker = " [admin]" if item.needs_admin else ""
        interactive_marker = " [interactive]" if item.status == "needs-interactive" else ""
        eta = f" (~{item.estimated_seconds}s)" if item.estimated_seconds is not None else ""
        lines.append(
            f"  [{i}/{len(plan.items)}]{admin_marker}{interactive_marker}{eta} "
            f"{item.description}: {item.proposed_action}"
        )
    return "\n".join(lines)


# ─── Default prompt function (configure phase, per ADR 0012) ───────────────


def _default_prompt_fn(prompt: str, hidden: bool) -> str | None:
    """
    Real interactive prompt for the configure phase. Tests inject their own.

    Uses ``getpass`` for hidden input (credentials, tokens) and plain
    ``input`` otherwise (git config, paths). A blank answer (just Enter)
    is interpreted as "skip this prompt" and returns None — the prereq
    can decide what to do with a None answer (skip the entire op vs.
    prompt again with rephrased text vs. fall back to a default).

    The trailing ``print()`` mirrors the consent-fn fix from 2026-05-07:
    when stdin is piped, neither input() nor getpass() emits a newline
    after the response, so subsequent output_fn calls would collide.
    """
    if hidden:
        from getpass import getpass

        raw = getpass(prompt)
    else:
        raw = input(prompt)
    print()
    answer = raw.strip()
    return answer or None


# ─── Default connectivity probe ────────────────────────────────────────────


def _default_is_online_fn() -> bool:
    """
    Default connectivity probe — delegates to ``ergodix.connectivity.is_online``,
    a fall-through TCP probe against well-known endpoints (per ADR 0012's
    F1 reframe). Tests inject their own callable to avoid touching the
    real network.
    """
    from ergodix.connectivity import is_online

    return is_online()


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

    # The example template ships with `<YOUR-CORPUS-FOLDER>` baked into the
    # path so installs land in a syntactically-valid but obviously-unedited
    # state. A literal `<…>` segment anywhere in the path is the marker.
    if re.search(r"<[^/<>]+>", str(corpus)):
        return VerifyResult(
            name="local_config_sane",
            passed=False,
            message=(
                f"CORPUS_FOLDER still contains a placeholder segment "
                f"(found in: {corpus}). The file hasn't been edited yet."
            ),
            remediation=(
                f"Edit {config_path} and replace the <…> placeholder with "
                f"your real corpus folder path."
            ),
        )

    return VerifyResult(
        name="local_config_sane",
        passed=True,
        message=f"local_config.py at {config_path} has mode 600 and CORPUS_FOLDER={corpus}",
    )


def _verify_ergodix_status() -> VerifyResult:
    """E1 smoke check (per ADR 0003): ``ergodix status`` exits 0.

    The full read-only health command is the canonical "is the install
    working end-to-end?" smoke. If status fails, something more
    fundamental is broken — and the user already saw the output of
    `ergodix --version` (the simpler smoke above), so this is the
    next-tier confirmation.

    Resolves the script via ``sys.executable``'s directory (matching
    the pattern in ``_verify_ergodix_command``) so this works
    regardless of ambient PATH. Captures output but only the exit code
    drives pass / fail; status's own output is for users, not for the
    verify check.
    """
    import platform
    import subprocess
    import sys

    interpreter_dir = Path(sys.executable).parent
    suffix = ".exe" if platform.system() == "Windows" else ""
    ergodix_path = interpreter_dir / f"ergodix{suffix}"

    if not ergodix_path.exists():
        # _verify_ergodix_command will already have reported this; E1
        # surfaces it again here so the verify table is complete and
        # the user sees a unified picture.
        return VerifyResult(
            name="ergodix_status_clean",
            passed=False,
            message=f"`ergodix` script not found at {ergodix_path}; cannot run status",
            remediation="Activate the venv and run: pip install -e .",
        )

    try:
        result = subprocess.run(
            [str(ergodix_path), "status"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return VerifyResult(
            name="ergodix_status_clean",
            passed=False,
            message=f"failed to run `{ergodix_path} status`: {exc}",
            remediation="Re-run cantilever to repair the install.",
        )

    if result.returncode == 0:
        return VerifyResult(
            name="ergodix_status_clean",
            passed=True,
            message="`ergodix status` exits 0 (full read-only health check passed)",
        )

    stderr = result.stderr.strip()
    last_line = stderr.splitlines()[-1] if stderr else f"exit {result.returncode}"
    return VerifyResult(
        name="ergodix_status_clean",
        passed=False,
        message=f"`ergodix status` exited {result.returncode}: {last_line}",
        remediation=(
            "Run `ergodix status` directly to see the full output and fix the underlying issue."
        ),
    )


_DEFAULT_VERIFY_CHECKS: list[Callable[[], VerifyResult]] = [
    _verify_import_package,
    _verify_ergodix_command,
    _verify_local_config_sane,
    _verify_ergodix_status,
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
    Phase 3 (apply): walk the plan in order, call apply() on each prereq
    EXCEPT needs-interactive ops (those are handled by the configure
    phase per ADR 0012 — apply() is a no-op for them and we skip the call
    entirely so non-implementing prereqs don't see a spurious invocation).

    - Emits a `[k/total] description...` progress line per applied op.
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
    # Apply-eligible items: anything except needs-interactive (those go
    # through the configure phase). Indexes shown to the user reflect the
    # apply-eligible count, not the full plan length.
    apply_items = [it for it in plan.items if it.status != "needs-interactive"]
    total = len(apply_items)

    for index, item in enumerate(apply_items, start=1):
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


def _run_configure_phase(
    prereqs: list[PrereqSpec],
    inspect_results: list[InspectResult],
    *,
    prompt_fn: PromptFn,
    output_fn: Callable[[str], None],
) -> list[ApplyResult]:
    """
    Phase 4 (configure, per ADR 0012): collect interactive user input for
    needs-interactive ops via the injected ``prompt_fn``. Each prereq's
    ``interactive_complete()`` runs its own prompt loop (one prereq may
    request multiple prompts — e.g., C3 asks for both user.name and
    user.email).

    Always runs every needs-interactive op (no abort-fast) — the user
    needs to see and skip-or-fill each one independently. A failed
    interactive_complete is recorded but doesn't block subsequent ones,
    matching the "verify always runs" contract from ADR 0010.

    Returns the list of ApplyResults from each interactive_complete call,
    in inspect-result order. Empty list if no needs-interactive ops.
    """
    interactive_items = [ir for ir in inspect_results if ir.status == "needs-interactive"]
    if not interactive_items:
        return []

    by_op_id = {p.op_id: p for p in prereqs}
    results: list[ApplyResult] = []

    output_fn("\nConfiguration:")
    for item in interactive_items:
        prereq = by_op_id[item.op_id]
        result = prereq.interactive_complete(prompt_fn)
        results.append(result)
        if result.status == "ok":
            marker = "✓"
        elif result.status == "skipped":
            marker = "⊝"
        else:
            marker = "✗"
        output_fn(f"  {marker} {item.op_id}: {result.message}")
        if result.status == "failed" and result.remediation_hint:
            output_fn(f"    Suggested fix: {result.remediation_hint}")

    return results


# ─── F2: post-run record (per ADR 0003 §164) ────────────────────────────────


_SUCCESS_OUTCOMES: frozenset[CantileverOutcome] = frozenset(
    {"applied", "no-changes-needed", "dry-run"}
)


def _default_log_path() -> Path:
    """Resolve the F2 log path lazily (per CLAUDE.md: no Path.home() at
    module level). Tests monkeypatch this to redirect into tmp_path."""
    return Path.home() / ".config" / "ergodix" / "cantilever.log"


def _operation_records(result: CantileverResult) -> list[dict[str, str]]:
    """Per-op {id, status} list — final status (configure > apply > inspect),
    preserving the cantilever execution order from inspect_results."""
    final: dict[str, str] = {ir.op_id: ir.status for ir in result.inspect_results}
    for ar in result.apply_results:
        final[ar.op_id] = ar.status
    for cr in result.configure_results:
        final[cr.op_id] = cr.status
    seen: set[str] = set()
    ordered: list[dict[str, str]] = []
    for ir in result.inspect_results:
        if ir.op_id not in seen:
            ordered.append({"id": ir.op_id, "status": final[ir.op_id]})
            seen.add(ir.op_id)
    return ordered


def _build_run_record(
    result: CantileverResult,
    *,
    started_ts: datetime,
    duration_seconds: float,
    floaters: dict[str, bool],
) -> dict[str, object]:
    """Pure transform — produce the JSON-serializable F2 record. Pure so
    tests can verify shape without filesystem side-effects (and because
    the actual write path is fail-safe, which would otherwise hide bugs
    in the record builder)."""
    return {
        "ts": started_ts.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "floaters": sorted(k for k, v in floaters.items() if v),
        "operations": _operation_records(result),
        "exit": 0 if result.outcome in _SUCCESS_OUTCOMES else 1,
        "duration_seconds": round(duration_seconds),
        "outcome": result.outcome,
    }


def _write_run_record(
    result: CantileverResult,
    *,
    started_ts: datetime,
    duration_seconds: float,
    floaters: dict[str, bool],
) -> None:
    """Append one JSONL line to the F2 log. Fail-safe: any error is
    swallowed so cantilever's caller never sees an F2 problem. The price
    of losing a single record is worth not breaking a real install run.
    """
    try:
        record = _build_run_record(
            result,
            started_ts=started_ts,
            duration_seconds=duration_seconds,
            floaters=floaters,
        )
        log_path = _default_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, separators=(",", ":")) + "\n")
    except (OSError, ValueError, TypeError):
        # Loud-not-fatal: swallow F2 errors so cantilever's outcome is
        # never tainted by audit-log infrastructure. (We could output_fn
        # a warning here in a future iteration.)
        return


# ─── Public entry point ────────────────────────────────────────────────────


def run_cantilever(
    *,
    floaters: dict[str, bool],
    prereqs: list[PrereqSpec],
    consent_fn: Callable[[Plan], bool] = _default_consent_fn,
    is_online_fn: Callable[[], bool] = _default_is_online_fn,
    output_fn: Callable[[str], None] = print,
    request_admin_fn: Callable[[], bool] = _default_request_admin_fn,
    prompt_fn: PromptFn = _default_prompt_fn,
    verify_checks: list[Callable[[], VerifyResult]] | None = None,
) -> CantileverResult:
    """
    Top-level entrypoint. Per ADR 0010 (four-phase model) + ADR 0012
    (extends to five phases: inspect → plan + consent → apply → configure
    → verify).

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
        prompt_fn: callback the configure phase hands to interactive prereqs.
            Signature ``(prompt: str, hidden: bool) -> str | None``. Default
            uses ``input``/``getpass``. ``--ci`` floater skips the entire
            configure phase, so the prompt_fn is never called in CI mode.
        verify_checks: list of phase-4 verify functions. Defaults to the
            built-in checks (``_verify_import_package`` and
            ``_verify_ergodix_command``). Tests inject explicit lists.

    Returns:
        CantileverResult describing the outcome, the inspections, the plan,
        and any apply / configure / verify results.
    """
    checks = verify_checks if verify_checks is not None else _DEFAULT_VERIFY_CHECKS

    # F2 (per ADR 0003 §164): every return path runs through _finalize, which
    # appends a JSONL record to ~/.config/ergodix/cantilever.log. F2 is
    # fail-safe — _write_run_record swallows its own errors.
    started_at = time.monotonic()
    started_ts = datetime.now(UTC)

    def _finalize(result: CantileverResult) -> CantileverResult:
        # Belt-and-suspenders: _write_run_record already swallows its own
        # OSError/ValueError/TypeError, but defense-in-depth means even a
        # bug past its except clause can't crash cantilever's outcome.
        with contextlib.suppress(Exception):
            _write_run_record(
                result,
                started_ts=started_ts,
                duration_seconds=time.monotonic() - started_at,
                floaters=floaters,
            )
        return result

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

    # Pre-flight: load settings (per ADR 0012's F1 reframe). Defaults apply
    # when settings/bootstrap.toml is missing; warnings surface to the user
    # before plan-display so config typos don't silently propagate. A
    # malformed settings file does NOT abort cantilever — defaults take over.
    settings = load_bootstrap_settings()
    if settings.warnings:
        output_fn("\nSettings warnings:")
        for w in settings.warnings:
            output_fn(f"  ⚠ {w}")

    # Phase 1: Inspect (read-only).
    online = is_online_fn()
    inspect_results = _inspect_all(prereqs, online=online)

    # Phase 1.5: if any inspect failed, halt before plan/consent/apply.
    # Per Copilot review 2026-05-05 finding #2: a 'failed' inspect must not
    # silently fall through to no-changes-needed (because needs_action is
    # False) or be rewritten to deferred-offline.
    if any(ir.status == "failed" for ir in inspect_results):
        output_fn("\nInspect phase found unresolvable issues:")
        for ir in inspect_results:
            if ir.status == "failed":
                output_fn(f"  ✗ {ir.op_id} — {ir.description}: {ir.current_state}")
        output_fn("Cantilever halted before any changes were made.")
        return _finalize(
            CantileverResult(
                outcome="inspect-failed",
                inspect_results=inspect_results,
                plan=Plan(items=[]),
                settings=settings,
            )
        )

    # Phase 2: Plan.
    plan = _build_plan(inspect_results)

    # Dry-run wins over both empty-plan and consent paths. Even when the
    # plan is empty, the user asked for "show me what cantilever would do
    # without committing"; we honor that by emitting the (possibly empty)
    # plan and exiting cleanly without running verify.
    if floaters.get("dry-run"):
        output_fn(_render_plan(plan))
        return _finalize(
            CantileverResult(
                outcome="dry-run",
                inspect_results=inspect_results,
                plan=plan,
                settings=settings,
            )
        )

    if not plan.items:
        # Per Copilot review 2026-05-05 finding #5: still run verify on the
        # no-changes path. If inspect was too permissive, verify is the
        # cross-check that catches a false green.
        verify_results = _run_verify_phase(checks, output_fn=output_fn)
        outcome: CantileverOutcome = (
            "verify-failed" if any(not vr.passed for vr in verify_results) else "no-changes-needed"
        )
        return _finalize(
            CantileverResult(
                outcome=outcome,
                inspect_results=inspect_results,
                plan=plan,
                verify_results=verify_results,
                settings=settings,
            )
        )

    if not floaters.get("ci"):
        # Interactive (or test-injected) consent.
        consented = consent_fn(plan)
        if not consented:
            return _finalize(
                CantileverResult(
                    outcome="consent-declined",
                    inspect_results=inspect_results,
                    plan=plan,
                    settings=settings,
                )
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
        return _finalize(
            CantileverResult(
                outcome="admin-denied",
                inspect_results=inspect_results,
                plan=plan,
                settings=settings,
            )
        )

    apply_results, completed = _apply_consented(prereqs, plan, output_fn=output_fn)

    # Phase 4: Configure (per ADR 0012). Runs after apply, before verify.
    # Skipped under --ci (CI must provide interactive values via env). Also
    # skipped (silently) when no needs-interactive ops are in the plan.
    configure_results: list[ApplyResult] = []
    if not floaters.get("ci"):
        configure_results = _run_configure_phase(
            prereqs,
            inspect_results,
            prompt_fn=prompt_fn,
            output_fn=output_fn,
        )

    # Phase 5: Verify. Always runs (whether apply or configure succeeded
    # or not) — the user needs the end-state picture either way.
    verify_results = _run_verify_phase(checks, output_fn=output_fn)

    # Outcome ladder (ADR 0012 extends ADR 0010's):
    #   apply failed at all                       → "applied-with-failures"
    #   apply ok, any configure failed            → "configure-failed"
    #   apply ok, configure ok, any verify failed → "verify-failed"
    #   apply ok, configure ok, verify ok         → "applied"
    if not completed:
        outcome = "applied-with-failures"
    elif any(cr.status == "failed" for cr in configure_results):
        outcome = "configure-failed"
    elif any(not vr.passed for vr in verify_results):
        outcome = "verify-failed"
    else:
        outcome = "applied"

    return _finalize(
        CantileverResult(
            outcome=outcome,
            inspect_results=inspect_results,
            plan=plan,
            apply_results=apply_results,
            configure_results=configure_results,
            verify_results=verify_results,
            settings=settings,
        )
    )
