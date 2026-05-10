"""
Cantilever prereq D2 (per ADR 0003): verify the git pre-commit hook
for prose linting is installed.

Per ADR 0003: "Configure git hooks for prose linting (writer /
writer+developer)." The actual prose linter is the future Phil-trained
linter from the SprintLog parking-lot story — a Skill that learns
from the editor's repeated corrections. The pre-commit hook this
prereq watches for would invoke that linter on changed chapter files.

D2 lands as **verify-only in v1**, mirroring D4 / D5 / D6's read-only
pattern. Reasons:

  - The Phil-trained linter doesn't exist yet (parking-lot, Sprint
    1+); installing a hook that invokes a missing tool would either
    fail-noisy on every commit or silently no-op — neither is
    useful.
  - Modifying ``.git/hooks/`` is mutative and persona-specific
    (writer / writer+developer per ADR 0003); deserves an explicit
    user opt-in via a future ``ergodix lint init`` command rather
    than firing on every cantilever run.

inspect() looks for an ergodix-managed pre-commit hook (identified
by a marker comment in the file). Reports presence / absence; never
fails. apply() is a no-op.

Detection of the git repo follows the same pattern as D4 — uses
``git rev-parse --git-dir`` to find the hooks directory, so this
works in worktrees / submodules / non-standard layouts.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "D2"
DESCRIPTION = "Verify prose-linter git pre-commit hook (writer / developer)"

# Marker string the future `ergodix lint init` writes into the hook
# script. D2 looks for this to recognize "our" hook vs. an unrelated
# user-installed one.
_HOOK_MARKER = "# ergodix-managed prose-lint hook"


def _git_dir() -> Path | None:
    """Return the resolved path to the git directory for cwd, or None
    if cwd is not inside a git working tree."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],  # noqa: S607 — git on PATH is intentional
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    git_dir = result.stdout.strip()
    if not git_dir:
        return None
    return (Path.cwd() / git_dir).resolve()


def inspect() -> InspectResult:
    git_dir = _git_dir()
    if git_dir is None:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"cwd ({Path.cwd()}) is not a git repo; D2 only applies when "
                "running from a git working tree (writer / developer modes)"
            ),
            proposed_action=None,
            network_required=False,
        )

    hook_path = git_dir / "hooks" / "pre-commit"
    if not hook_path.exists():
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"prose-linter pre-commit hook not installed at {hook_path}. "
                "When activating writer / writer+developer mode and the Phil-"
                "trained prose linter ships, run `ergodix lint init` (future) "
                "to install + configure the hook."
            ),
            proposed_action=None,
            network_required=False,
        )

    # Hook exists — check if it's ours by looking for the marker.
    try:
        contents = hook_path.read_text()
    except OSError:
        contents = ""

    if _HOOK_MARKER in contents:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"ergodix-managed prose-linter hook present at {hook_path}",
            proposed_action=None,
            network_required=False,
        )

    return InspectResult(
        op_id=OP_ID,
        status="ok",
        description=DESCRIPTION,
        current_state=(
            f"a pre-commit hook exists at {hook_path} but is NOT ergodix-managed "
            "(marker missing). Leaving it alone — D2 won't overwrite a hook the "
            "user installed for other purposes."
        ),
        proposed_action=None,
        network_required=False,
    )


def apply() -> ApplyResult:
    """No-op — D2 is verify-only in v1. The full install flow defers
    to a future ``ergodix lint init`` command, which lands when the
    Phil-trained prose linter ships."""
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message=(
            "D2 is verify-only in v1; hook install runs via "
            "`ergodix lint init` (future) once the Phil-trained linter ships"
        ),
    )
