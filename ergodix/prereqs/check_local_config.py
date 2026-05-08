"""
Cantilever prereq C4 (per ADR 0003): bootstrap ``local_config.py`` from
``local_config.example.py`` at the repo root.

Mutative, no network. **Preserves** an existing ``local_config.py`` — never
overwrites the user's machine-specific paths or hand-edits.

Future enhancement: a sibling B2 prereq detects Drive mount mode + corpus
folder and patches the generated ``local_config.py`` accordingly. C4 v1
just copies the template verbatim and locks the file at mode 0o600; the
user (or B2) substitutes paths after.

Path resolution uses ``Path.cwd()`` per CLAUDE.md (no module-level
``Path.home()`` baking) and matches cantilever's verify-phase behavior,
which also probes ``Path.cwd() / "local_config.py"``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "C4"
DESCRIPTION = "Bootstrap local_config.py from local_config.example.py"

_EXAMPLE_FILENAME = "local_config.example.py"
_CONFIG_FILENAME = "local_config.py"
_EXPECTED_MODE = 0o600


def _paths() -> tuple[Path, Path]:
    """Resolve example + target paths from the current working directory."""
    cwd = Path.cwd()
    return cwd / _EXAMPLE_FILENAME, cwd / _CONFIG_FILENAME


def inspect() -> InspectResult:
    """
    Three terminal states:

    - ``local_config.py`` exists → ``ok`` (preserve, nothing to plan)
    - only the example exists → ``needs-install`` (plan an apply)
    - neither exists → ``failed`` (broken repo state; halt cantilever)
    """
    example, config = _paths()

    if config.exists():
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"{_CONFIG_FILENAME} present at {config}",
            proposed_action=None,
        )

    if example.exists():
        return InspectResult(
            op_id=OP_ID,
            status="needs-install",
            description=DESCRIPTION,
            current_state=f"{_CONFIG_FILENAME} not present; template available",
            proposed_action=(
                f"Copy {_EXAMPLE_FILENAME} → {_CONFIG_FILENAME} and chmod {oct(_EXPECTED_MODE)}"
            ),
            estimated_seconds=1,
        )

    return InspectResult(
        op_id=OP_ID,
        status="failed",
        description=DESCRIPTION,
        current_state=(f"neither {_CONFIG_FILENAME} nor {_EXAMPLE_FILENAME} found in {Path.cwd()}"),
        proposed_action=None,
    )


def apply() -> ApplyResult:
    """
    Copy ``local_config.example.py`` → ``local_config.py`` (preserving an
    existing target) and chmod the result to 0o600.

    Returns ``skipped`` if local_config.py already exists, ``failed`` if
    the example template is missing, ``ok`` on a clean copy.
    """
    example, config = _paths()

    if config.exists():
        return ApplyResult(
            op_id=OP_ID,
            status="skipped",
            message=f"{_CONFIG_FILENAME} already exists; preserved",
        )

    if not example.exists():
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"{_EXAMPLE_FILENAME} not found in {Path.cwd()}",
            remediation_hint=(
                f"Re-clone ErgodixDocs or restore {_EXAMPLE_FILENAME} from git: "
                f"`git checkout -- {_EXAMPLE_FILENAME}`"
            ),
        )

    try:
        shutil.copyfile(example, config)
        config.chmod(_EXPECTED_MODE)
    except OSError as exc:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"could not write {_CONFIG_FILENAME}: {exc}",
            remediation_hint=f"Check write permissions on {Path.cwd()}",
        )

    return ApplyResult(
        op_id=OP_ID,
        status="ok",
        message=f"wrote {_CONFIG_FILENAME} (mode {oct(_EXPECTED_MODE)})",
    )
