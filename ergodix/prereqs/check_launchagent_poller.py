"""
Cantilever prereq D5 (per ADR 0003 + ADR 0004): verify the
continuous-polling LaunchAgent is installed.

Per [ADR 0004](../../adrs/0004-continuous-repo-polling.md), ErgodixDocs
installs a macOS LaunchAgent at
``~/Library/LaunchAgents/com.ergodix.poller.plist`` that runs every
~5 minutes and invokes ``ergodix sync-in --background``. The poller
no-ops when offline (per ADR 0003's connectivity model) and is
persona-aware in its actual sync behavior.

D5 is **verify-only in v1**, mirroring D4 / D6's read-only pattern:
the actual install (write the plist, ``launchctl bootstrap`` it)
defers to a future ``ergodix poller init`` command. Reasons:

  - The poller invokes ``ergodix sync-in --background`` which is
    currently a stub — installing the LaunchAgent now would schedule
    a 5-minute beat that does nothing useful.
  - ``launchctl bootstrap`` is mutative and platform-specific; it
    deserves an explicit user opt-in step rather than firing as part
    of every cantilever run.
  - Persona-aware behavior (writer vs. editor vs. focus-reader cadence
    differences from the ADR) needs the floater context that prereqs
    can't currently see.

inspect() reports presence/absence; apply() is a no-op. When the
poller-install command lands, this module's apply() can be promoted
to actually run ``launchctl bootstrap``.

Note: macOS-only in v1. Linux (systemd timer) and Windows (Task
Scheduler) are deferred per ADR 0004's "v1?" column.
"""

from __future__ import annotations

from pathlib import Path

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "D5"
DESCRIPTION = "Verify continuous-polling LaunchAgent (macOS)"

# Canonical install path for the poller plist on macOS.
_PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "com.ergodix.poller.plist"


def inspect() -> InspectResult:
    if not _PLIST_PATH.exists():
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"polling LaunchAgent not installed at {_PLIST_PATH}. "
                "When activating continuous-sync workflow (post-`ergodix sync-in`), "
                "run `ergodix poller init` (future) to install + load the LaunchAgent."
            ),
            proposed_action=None,
            network_required=False,
        )

    return InspectResult(
        op_id=OP_ID,
        status="ok",
        description=DESCRIPTION,
        current_state=f"polling LaunchAgent installed at {_PLIST_PATH}",
        proposed_action=None,
        network_required=False,
    )


def apply() -> ApplyResult:
    """No-op — D5 is verify-only in v1. The full install flow
    (write plist + ``launchctl bootstrap``) defers to a future
    ``ergodix poller init`` command."""
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message=(
            "D5 is verify-only in v1; LaunchAgent install runs via "
            "`ergodix poller init` (future) once `ergodix sync-in` is real"
        ),
    )
