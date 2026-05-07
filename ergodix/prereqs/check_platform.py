"""
Cantilever prereq A1 (per ADR 0003): detect the host platform.

Read-only and trivial — the simplest of the 25 ops. Doubles as the
canonical reference shape for inspect/apply per ADR 0010:

    OP_ID — module-level constant matching ADR 0003's op-table id
    inspect() -> InspectResult — read-only system probe
    apply() -> ApplyResult     — mutative action when needed (no-op here)

A1 reports an `ok` status on macOS / Linux / Windows. Any other system
surfaces as `failed`, which halts cantilever before the plan/consent/apply
phases run (per ADR 0010's inspect-failed handling).
"""

from __future__ import annotations

import platform

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "A1"
DESCRIPTION = "Detect platform (macOS / Linux / Windows)"

_SUPPORTED_SYSTEMS = frozenset({"Darwin", "Linux", "Windows"})


def _human_state() -> str:
    """Render a human-readable platform string. macOS uses the marketing name."""
    system = platform.system()
    if system == "Darwin":
        mac_version = platform.mac_ver()[0]
        return f"macOS {mac_version}".rstrip() if mac_version else "macOS"
    if system == "Linux":
        return f"Linux {platform.release()}".rstrip()
    if system == "Windows":
        return f"Windows {platform.release()}".rstrip()
    return system or "unknown"


def inspect() -> InspectResult:
    """Detect the host platform. Always read-only."""
    system = platform.system()
    state = _human_state()

    if system in _SUPPORTED_SYSTEMS:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"{state} detected",
            proposed_action=None,
        )

    # Anything else (FreeBSD, OpenBSD, exotic kernel, empty string) is
    # unsupported. Surface as failed so cantilever halts before plan-building.
    return InspectResult(
        op_id=OP_ID,
        status="failed",
        description=DESCRIPTION,
        current_state=f"{state} (unsupported)",
        proposed_action=None,
    )


def apply() -> ApplyResult:
    """
    No-op. Platform detection has no apply step — when inspect returns 'ok',
    cantilever doesn't include this op in the plan, so apply isn't called.
    Defined to satisfy the PrereqSpec protocol; reached only if a future
    refactor mistakenly schedules it, in which case we return skipped
    rather than raising.
    """
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message="platform detection has no apply step",
    )
