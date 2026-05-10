"""
Cantilever prereq D4 (per ADR 0003): verify local branch tracking.

ADR 0003 specced D4 as "Set up `develop` branch tracking + branch
protection notice (developer floater)." That spec predates the
2026-05-03 trunk-based branching decision (CLAUDE.md "Branching and
PRs"; ``develop`` was deleted, only ``main`` plus feature branches).

D4 is reframed for the trunk-based model: when the user is running
cantilever from inside a git repo (canonical case: developer working
on ErgodixDocs itself), check whether the local ``main`` branch
tracks ``origin/main``. The check is **strictly informational** —
``apply()`` is a no-op. Setting an upstream automatically would touch
git config in ways the user might not expect; the right outcome is
to surface the state and let the user run the suggested
``git branch --set-upstream-to`` themselves.

When cwd isn't a git repo at all (writer / editor / focus-reader
running ergodix from their corpus folder, not the ergodix-source
clone), D4 reports ``ok`` with a current_state that names the
condition. The prereq is persona-agnostic — it just describes what
it sees and stays out of the way for users who don't care.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "D4"
DESCRIPTION = "Verify local 'main' branch tracking (developer mode)"


def _is_git_repo() -> bool:
    """True if cwd is inside a git working tree. Uses ``git rev-parse``
    rather than checking for ``.git`` because submodules and worktrees
    have non-standard layouts."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],  # noqa: S607 — git on PATH is intentional
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return False
    return result.returncode == 0


def _git_main_upstream() -> str | None:
    """Return the upstream tracking-branch name for local ``main``,
    or None if main has no upstream / git fails / main doesn't exist."""
    try:
        result = subprocess.run(
            [  # noqa: S607 — git on PATH is intentional, same as check_git_config
                "git",
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "main@{upstream}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    upstream = result.stdout.strip()
    return upstream or None


def inspect() -> InspectResult:
    if not _is_git_repo():
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"cwd ({Path.cwd()}) is not a git repo; D4 only applies when "
                "running from the ergodix-source clone in developer mode"
            ),
            proposed_action=None,
            network_required=False,
        )

    upstream = _git_main_upstream()

    if upstream is None:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                "local 'main' has no upstream tracking. To fix, run: "
                "git branch --set-upstream-to=origin/main main"
            ),
            proposed_action=None,
            network_required=False,
        )

    if upstream == "origin/main":
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"local 'main' tracks {upstream}",
            proposed_action=None,
            network_required=False,
        )

    return InspectResult(
        op_id=OP_ID,
        status="ok",
        description=DESCRIPTION,
        current_state=(
            f"local 'main' tracks {upstream}, not origin/main. "
            "If this isn't intentional, run: "
            "git branch --set-upstream-to=origin/main main"
        ),
        proposed_action=None,
        network_required=False,
    )


def apply() -> ApplyResult:
    """No-op — D4 is strictly informational. Setting an upstream
    automatically would touch git config without explicit user
    consent. The remediation is in inspect's current_state."""
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message="D4 is read-only; any remediation runs manually via git",
    )
