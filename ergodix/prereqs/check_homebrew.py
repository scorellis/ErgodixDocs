"""
Cantilever prereq A2 (per ADR 0003): install/verify Homebrew.

A2 is the first **Tier-2** prereq — network + admin. It unblocks the
rest of the A-tier (A3 Pandoc, A4 MacTeX, A7 VS Code) and B1 (Google
Drive Desktop), all of which install via ``brew``.

Inspect uses ``shutil.which`` to detect ``brew`` on PATH. If absent,
apply runs the official Homebrew install one-liner:

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

with ``NONINTERACTIVE=1`` set so the install script doesn't re-prompt
the user mid-run (per Spike 0008 / Story 0.11 task list, and ADR 0010's
single-consent contract). The Homebrew install script is itself
idempotent — re-running on an installed system is a fast no-op.

network_required=True so the orchestrator's offline-rewrite path turns
A2 into ``deferred-offline`` when ``is_online_fn`` reports False.
needs_admin=True; sudo is grouped at the apply phase per ADR 0010.

Failure surfacing: any non-zero exit or OSError reports ``failed``
with ``remediation_hint`` pointing at the brew.sh manual install page,
so the user can complete it without re-running cantilever.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "A2"
DESCRIPTION = "Install/verify Homebrew package manager"

_HOMEBREW_INSTALL_URL = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
_HOMEBREW_MANUAL_URL = "https://brew.sh"


def inspect() -> InspectResult:
    """Detect ``brew`` on PATH via ``shutil.which``."""
    brew_path = shutil.which("brew")

    if brew_path is not None:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"Homebrew at {brew_path}",
            proposed_action=None,
            network_required=True,
        )

    return InspectResult(
        op_id=OP_ID,
        status="needs-install",
        description=DESCRIPTION,
        current_state="brew not found on PATH",
        proposed_action="Install Homebrew via the official install.sh script",
        needs_admin=True,
        estimated_seconds=180,
        network_required=True,
    )


def apply() -> ApplyResult:
    """
    Run the documented Homebrew install one-liner with ``NONINTERACTIVE=1``.

    Failure modes:
    - ``OSError`` from subprocess.run (no /bin/bash, FS issue) → failed.
    - Non-zero exit code → failed (network drop mid-install, sudo
      cancelled, permission issue, etc.).

    All failures point at ``brew.sh``'s manual instructions in the
    ``remediation_hint`` so the user can complete it directly.
    """
    # Pass /bin/bash the substitution form as -c argument; bash itself
    # runs `curl` and evaluates its output. Avoids shell=True + the
    # whole-command-as-string shape (and the S602 lint trigger that
    # comes with it) while preserving the documented one-liner behavior.
    bash_command = f"$(curl -fsSL {_HOMEBREW_INSTALL_URL})"

    env = dict(os.environ)
    env["NONINTERACTIVE"] = "1"

    try:
        result = subprocess.run(
            ["/bin/bash", "-c", bash_command],
            check=False,
            env=env,
        )
    except OSError as exc:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"could not spawn Homebrew install subprocess: {exc}",
            remediation_hint=(
                f"Install Homebrew manually following the instructions at {_HOMEBREW_MANUAL_URL}, "
                "then re-run cantilever."
            ),
        )

    if result.returncode == 0:
        return ApplyResult(
            op_id=OP_ID,
            status="ok",
            message="Homebrew installed",
        )

    return ApplyResult(
        op_id=OP_ID,
        status="failed",
        message=f"Homebrew install script exited {result.returncode}",
        remediation_hint=(
            f"Run the install script manually from {_HOMEBREW_MANUAL_URL} "
            "(it's idempotent — safe to retry)."
        ),
    )
