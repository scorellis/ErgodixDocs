"""
Cantilever prereq C5 (per ADR 0003): create ``~/.config/ergodix/`` with
mode 0o700.

Mutative, no network, no admin. The directory is the file-fallback tier
of auth.py's three-tier credential lookup (env var → OS keyring → file).
The 0o700 invariant is load-bearing: a transient world-readable
``secrets.json`` inside a 0o755 directory would still be exposed via
directory traversal.

ADR 0003 wording is "Create ~/.config/ergodix/ and secrets.json
template." In practice ``secrets.json`` is auto-created by ``auth.py``
when the user saves a key via the file fallback; C5's job is the
directory + mode invariant. The file is auth.py's concern.

Path resolution lazy via ``Path.home()`` inside the inspect/apply
functions per CLAUDE.md (no module-level home-baking).
"""

from __future__ import annotations

from pathlib import Path

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "C5"
DESCRIPTION = "Create ~/.config/ergodix/ credential-store directory (mode 0o700)"

_EXPECTED_MODE = 0o700


def _central_dir() -> Path:
    """Resolve ~/.config/ergodix at call time. Mirrors auth.py's helper."""
    return Path.home() / ".config" / "ergodix"


def inspect() -> InspectResult:
    """
    Three terminal states:

    - dir exists with mode 0o700 → ``ok``
    - dir exists but mode is wider than 0o700 → ``needs-update`` (chmod fix)
    - dir does not exist → ``needs-install`` (mkdir + chmod)
    """
    central = _central_dir()

    if not central.exists():
        return InspectResult(
            op_id=OP_ID,
            status="needs-install",
            description=DESCRIPTION,
            current_state=f"{central} does not exist",
            proposed_action=f"Create {central} with mode 0o700",
            estimated_seconds=1,
        )

    if not central.is_dir():
        return InspectResult(
            op_id=OP_ID,
            status="failed",
            description=DESCRIPTION,
            current_state=f"{central} exists but is not a directory",
            proposed_action=None,
        )

    mode = central.stat().st_mode & 0o777
    if mode == _EXPECTED_MODE:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"{central} exists with mode 0o700",
            proposed_action=None,
        )

    return InspectResult(
        op_id=OP_ID,
        status="needs-update",
        description=DESCRIPTION,
        current_state=f"{central} exists but has mode {oct(mode)}",
        proposed_action=f"chmod {central} to 0o700",
        estimated_seconds=1,
    )


def apply() -> ApplyResult:
    """
    Create ``~/.config/ergodix/`` if absent (with parents) and ensure
    mode 0o700. Idempotent — returns ``skipped`` if the dir already
    exists at the right mode.
    """
    central = _central_dir()

    try:
        if not central.exists():
            central.mkdir(parents=True, exist_ok=True)
            central.chmod(_EXPECTED_MODE)
            return ApplyResult(
                op_id=OP_ID,
                status="ok",
                message=f"created {central} (mode 0o700)",
            )

        if not central.is_dir():
            return ApplyResult(
                op_id=OP_ID,
                status="failed",
                message=f"{central} exists but is not a directory",
                remediation_hint=(
                    f"Inspect {central} manually; rename or remove if it's not "
                    "the credential-store directory."
                ),
            )

        mode = central.stat().st_mode & 0o777
        if mode == _EXPECTED_MODE:
            return ApplyResult(
                op_id=OP_ID,
                status="skipped",
                message=f"{central} already at mode 0o700",
            )

        central.chmod(_EXPECTED_MODE)
        return ApplyResult(
            op_id=OP_ID,
            status="ok",
            message=f"tightened {central} from {oct(mode)} to 0o700",
        )
    except OSError as exc:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"could not create or chmod {central}: {exc}",
            remediation_hint=(
                f"Check that {central.parent} is writable; "
                "ensure the filesystem isn't read-only or out of space."
            ),
        )
