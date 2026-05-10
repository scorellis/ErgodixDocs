"""
Cantilever prereq D1 (per ADR 0003): verify the VS Code auto-sync
task is installed.

Per ADR 0003: "Install VS Code task for auto-sync (editor only)."
The actual auto-sync invokes ``ergodix sync-in`` / ``ergodix
sync-out`` (currently CLI stubs from ADR 0006's editor-collaboration
flow). The task lives in ``.vscode/tasks.json`` at the user's open
workspace (corpus folder for writer / editor; ergodix repo for
developer working on the tool itself).

D1 lands as **verify-only in v1**, mirroring D2 / D4 / D5 / D6's
read-only pattern. Reasons:

  - The ``ergodix sync-in`` / ``sync-out`` commands are currently
    stubs; installing tasks that invoke them would be inert — the
    user clicks "Run Task" and gets a "not yet implemented" message.
  - ``.vscode/tasks.json`` is per-workspace, persona-shaped, and
    potentially shared with other tasks the user has set up; a
    cantilever-driven mutation could clobber unrelated config.
  - The full install belongs to a future ``ergodix vscode init``
    command that's an explicit user opt-in.

inspect() looks for an ergodix-tagged task by recognizing the
``Ergodix:`` label prefix in the task definitions. Reports presence
/ absence; never fails. apply() is a no-op.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "D1"
DESCRIPTION = "Verify VS Code auto-sync task (editor / writer)"

# Tasks created by `ergodix vscode init` (future) carry this label
# prefix; D1 looks for it to recognize "our" tasks vs. unrelated
# user-installed tasks. Examples: "Ergodix: Sync In", "Ergodix:
# Render Chapter".
_TASK_LABEL_PREFIX = "Ergodix:"


def _read_tasks_json(path: Path) -> dict[str, Any] | None:
    """Read and parse ``tasks.json``. Returns the top-level dict, or
    None if the file is missing / unreadable / malformed. Defensive:
    a hand-edited tasks.json with a typo shouldn't crash D1."""
    if not path.exists():
        return None
    try:
        parsed: Any = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _has_ergodix_task(tasks_json: dict[str, Any]) -> bool:
    """Return True if the parsed tasks.json contains at least one
    task whose label starts with the ergodix prefix."""
    tasks = tasks_json.get("tasks", [])
    if not isinstance(tasks, list):
        return False
    for task in tasks:
        if not isinstance(task, dict):
            continue
        label = task.get("label")
        if isinstance(label, str) and label.startswith(_TASK_LABEL_PREFIX):
            return True
    return False


def inspect() -> InspectResult:
    tasks_path = Path.cwd() / ".vscode" / "tasks.json"

    if not tasks_path.exists():
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"VS Code tasks.json not present at {tasks_path}. When activating "
                "writer / editor mode and `ergodix sync-in/-out` ship, run "
                "`ergodix vscode init` (future) to install the auto-sync task."
            ),
            proposed_action=None,
            network_required=False,
        )

    tasks_json = _read_tasks_json(tasks_path)
    if tasks_json is None:
        # Exists but unreadable / malformed JSON. Don't claim ownership;
        # don't flag as failure — let the user fix their own broken file.
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"VS Code tasks.json at {tasks_path} is unreadable or malformed. "
                "Leaving it alone — D1 won't touch a file the user owns."
            ),
            proposed_action=None,
            network_required=False,
        )

    if _has_ergodix_task(tasks_json):
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"ergodix-managed VS Code tasks present at {tasks_path}",
            proposed_action=None,
            network_required=False,
        )

    return InspectResult(
        op_id=OP_ID,
        status="ok",
        description=DESCRIPTION,
        current_state=(
            f"VS Code tasks.json exists at {tasks_path} but contains no "
            f"ergodix-tagged tasks (no '{_TASK_LABEL_PREFIX}'-prefixed labels). "
            "Leaving it alone — the user's existing tasks are theirs."
        ),
        proposed_action=None,
        network_required=False,
    )


def apply() -> ApplyResult:
    """No-op — D1 is verify-only in v1. The full install flow defers
    to a future ``ergodix vscode init`` command, which lands when
    ``ergodix sync-in`` / ``sync-out`` become real."""
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message=(
            "D1 is verify-only in v1; tasks.json install runs via "
            "`ergodix vscode init` (future) once `ergodix sync-in/-out` are real"
        ),
    )
