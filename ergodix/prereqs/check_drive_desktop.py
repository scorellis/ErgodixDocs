"""
Cantilever prereq B1 (per ADR 0003): install/verify Google Drive for
Desktop.

The migrate / sync flows depend on Drive's local Mirror mount so
chapter files round-trip without API calls (per ADR 0006). B1 ensures
the Drive app is installed; B2 (separate prereq) detects which mount
mode (Mirror vs Stream) is active and surfaces the path. Sign-in
itself is a manual step the cantilever cannot automate — ADR 0010's
plan-display surfaces the requirement, the user signs in via the
menu-bar app, then re-runs cantilever.

Detection: `/Applications/Google Drive.app` is the canonical macOS
install location. We don't probe the running process here — Drive may
be installed but not running (the user hasn't launched it yet); B1's
job is "is the app on disk," not "is it running."

Apply: `brew install --cask google-drive`. `--cask` writes to
`/Applications`, so this needs sudo (admin grouped at the apply phase
per ADR 0010). `HOMEBREW_NO_AUTO_UPDATE=1` per Spike 0008 / Story 0.11.

Depends on A2 (Homebrew). Failure surfaces a remediation hint pointing
at the manual `brew install --cask google-drive` command (or the
direct download URL if brew isn't available).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "B1"
DESCRIPTION = "Install/verify Google Drive for Desktop"

_APP_PATH = Path("/Applications/Google Drive.app")


def inspect() -> InspectResult:
    if _APP_PATH.is_dir():
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"Google Drive.app at {_APP_PATH}",
            proposed_action=None,
            network_required=True,
        )

    return InspectResult(
        op_id=OP_ID,
        status="needs-install",
        description=DESCRIPTION,
        current_state="Google Drive.app not found in /Applications",
        proposed_action="brew install --cask google-drive",
        needs_admin=True,
        estimated_seconds=120,
        network_required=True,
    )


def apply() -> ApplyResult:
    env = dict(os.environ)
    env["HOMEBREW_NO_AUTO_UPDATE"] = "1"

    try:
        result = subprocess.run(
            ["brew", "install", "--cask", "google-drive"],  # noqa: S607
            check=False,
            env=env,
        )
    except FileNotFoundError:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message="brew not found at apply time (A2 must run first)",
            remediation_hint=(
                "Re-run cantilever after A2 (Install/verify Homebrew) succeeds, "
                "or download Drive directly from https://www.google.com/drive/download/."
            ),
        )
    except OSError as exc:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"could not spawn brew install: {exc}",
            remediation_hint="Try `brew install --cask google-drive` manually.",
        )

    if result.returncode == 0:
        return ApplyResult(
            op_id=OP_ID,
            status="ok",
            message="Google Drive for Desktop installed (sign in via the menu-bar app)",
        )

    return ApplyResult(
        op_id=OP_ID,
        status="failed",
        message=f"brew install --cask google-drive exited {result.returncode}",
        remediation_hint=(
            "Run `brew install --cask google-drive` manually, "
            "or download from https://www.google.com/drive/download/."
        ),
    )
