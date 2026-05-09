"""
Cantilever prereq A5 (per ADR 0003): verify Python virtual environment.

The actual venv creation is ``bootstrap.sh``'s responsibility — by the
time cantilever runs, ``.venv`` either exists (bootstrap was run) or
cantilever wouldn't be importable. This prereq is a verify-only stub
that confirms the active interpreter is running inside a venv.

Detection: ``sys.prefix != sys.base_prefix`` is Python's standard
"am I in a venv" signal — cleaner than poking at ``.venv/`` paths,
which differ across deploy modes (local repo vs. installed package).

apply() is a no-op (returns ``skipped``). Cantilever can't recover
from "Python venv is broken" because cantilever itself is Python in
that venv. The remediation_hint points the user back at
``./bootstrap.sh``.
"""

from __future__ import annotations

import sys

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "A5"
DESCRIPTION = "Verify Python virtual environment is active"


def inspect() -> InspectResult:
    if sys.prefix == sys.base_prefix:
        return InspectResult(
            op_id=OP_ID,
            status="needs-install",
            description=DESCRIPTION,
            current_state=(
                f"interpreter at {sys.executable} is not running in a virtual environment"
            ),
            proposed_action="Run ./bootstrap.sh to create and activate .venv",
            network_required=False,
        )

    py = sys.version_info
    return InspectResult(
        op_id=OP_ID,
        status="ok",
        description=DESCRIPTION,
        current_state=f"venv active at {sys.prefix} (Python {py.major}.{py.minor}.{py.micro})",
        proposed_action=None,
        network_required=False,
    )


def apply() -> ApplyResult:
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message="venv setup is bootstrap.sh's responsibility",
        remediation_hint=(
            "If the venv is broken or missing, re-run ./bootstrap.sh from the repo root."
        ),
    )
