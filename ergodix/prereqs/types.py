"""
Dataclasses describing the contract between cantilever and individual prereq
modules. Per ADR 0010.

Two types:

    InspectResult — the read-only output of a prereq's inspect() function.
                    Frozen. Cantilever uses it to build the plan.

    ApplyResult   — the report of a prereq's apply() function. Mutable, so
                    a long-running apply step can update its message as it
                    progresses. Cantilever logs it in the run-record.

Status vocabularies are intentionally narrow:

    InspectResult.status ∈ {ok, needs-install, needs-update,
                            needs-interactive, deferred-offline, failed}
    ApplyResult.status   ∈ {ok, skipped, failed}

The ``needs-interactive`` status (added by ADR 0012) signals that an op
needs user input that ADR 0010's pre-apply consent gate cannot collect
in advance — the new five-phase orchestrator's *configure* phase
(between apply and verify) handles these ops. The op's ``apply()`` is a
no-op (returns ``skipped`` with a "awaiting configure phase" message);
the op's ``interactive_complete()`` method (per the PrereqSpec protocol
extension) is called by the configure phase with the user's input.

The literals are enforced by mypy (strict) at compile time. Runtime
validation is deliberately not added — the cost outweighs the benefit
for internal types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

InspectStatus = Literal[
    "ok",
    "needs-install",
    "needs-update",
    "needs-interactive",
    "deferred-offline",
    "failed",
]

ApplyStatus = Literal[
    "ok",
    "skipped",
    "failed",
]


@dataclass(frozen=True)
class InspectResult:
    """Output of a prereq's inspect() function. Read-only by contract."""

    op_id: str
    """Stable identifier from ADR 0003's operation menu, e.g. 'A1', 'C6'."""

    status: InspectStatus
    """Current state classification. Drives whether apply() will be called."""

    description: str
    """What this op is responsible for. Surfaced in the plan view."""

    current_state: str
    """Human-readable summary of what's there now. e.g. 'Pandoc 3.9.0 installed'."""

    proposed_action: str | None
    """What apply() would do, in human-readable form. None if no change is needed."""

    needs_admin: bool = False
    """Whether apply() requires sudo or another admin escalation."""

    estimated_seconds: int | None = None
    """Optional estimate, surfaced in the plan view to set expectations."""

    network_required: bool = False
    """Whether apply() needs network. If offline, op is deferred."""

    @property
    def needs_action(self) -> bool:
        """
        True iff the op should appear in the plan (and therefore in the
        consent gate's display).

        Maps the six-valued status into a binary: needs-install,
        needs-update, and needs-interactive all mean the plan should
        include this op; ok, deferred-offline, and failed mean it should
        not (the first because nothing to do, the latter two because the
        op is currently un-applyable).

        Note: ``needs-interactive`` ops appear in the plan but their
        ``apply()`` is a no-op — actual work happens in the configure
        phase (per ADR 0012) via ``interactive_complete()``.
        """
        return self.status in {"needs-install", "needs-update", "needs-interactive"}


@dataclass
class ApplyResult:
    """Report of a prereq's apply() function. Mutable so progress can be tracked."""

    op_id: str
    """Stable identifier matching the InspectResult that triggered this apply."""

    status: ApplyStatus
    """Final classification of the apply attempt."""

    message: str
    """Human-readable summary. May be updated during execution."""

    remediation_hint: str | None = None
    """If status is 'failed', actionable advice for the user."""
