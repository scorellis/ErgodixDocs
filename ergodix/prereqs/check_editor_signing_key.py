"""
Cantilever prereq D6 (per ADR 0003 + ADR 0006 + ADR 0012's Note):
verify the editor's SSH signing key + git signing config.

ADR 0006 / ADR 0012 spec D6 as a multi-step install: generate
ed25519 key, refresh ``gh`` scope to ``admin:public_key``, register
the key as a signing key with GitHub, configure local git to sign
commits. Cantilever's prereq protocol doesn't have access to floater
state, so D6 can't persona-gate itself ("only run when --editor is
active"). To avoid surfacing a noisy "needs-interactive" prompt for
every non-editor user, D6 lands as a **verify-only check** in v1
(mirroring D4's read-only pattern):

  - Signing key absent → ``ok`` with deferred current_state
    ("editor signing key not yet configured; run `ergodix editor
    init` when activating the editor floater").
  - Signing key present + git is configured to sign with it → ``ok``.
  - Signing key present but git config is incomplete → ``ok`` with a
    warning current_state listing the missing git config bits.

The full install flow (keygen + gh scope refresh + register +
git config) defers to a future ``ergodix editor init`` command. That
command is the user's explicit handle for opting into editor-mode
setup; D6 stays informational so non-editor users see no prompts.

apply() is a no-op (returns ``skipped``). Mutating ssh / gh / git
config without explicit user action would violate the AI permitted-
actions boundary (ADR 0013) on a prereq that may not even apply to
this user.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "D6"
DESCRIPTION = "Verify editor signing key + git signing config (editor floater)"

# Canonical paths for the editor signing key. The "_ergodix_editor" suffix
# keeps it distinct from any existing SSH keys the user has for other
# purposes (per ADR 0006: per-project keys, not reuse).
_EDITOR_KEY_PATH = Path.home() / ".ssh" / "id_ed25519_ergodix_editor"
_EDITOR_PUBKEY_PATH = Path.home() / ".ssh" / "id_ed25519_ergodix_editor.pub"


def _git_config_value(key: str) -> str | None:
    """Read a global git config value. Returns None if unset / git fails /
    git not on PATH (defensive: D6 must not crash for non-developer users)."""
    try:
        result = subprocess.run(
            ["git", "config", "--global", key],  # noqa: S607 — git on PATH is intentional
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def inspect() -> InspectResult:
    if not _EDITOR_KEY_PATH.exists():
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"editor signing key not yet configured at {_EDITOR_KEY_PATH}. "
                "When activating editor-floater workflow, run `ergodix editor init` "
                "(future) to generate the key, register it with GitHub, and configure "
                "git to sign commits."
            ),
            proposed_action=None,
            network_required=False,
        )

    # Key exists — validate git is configured to sign with it.
    gpg_format = _git_config_value("gpg.format")
    signing_key = _git_config_value("user.signingkey")
    sign_commits = _git_config_value("commit.gpgsign")

    missing_config: list[str] = []
    if gpg_format != "ssh":
        missing_config.append(f"gpg.format=ssh (currently {gpg_format!r})")
    if signing_key != str(_EDITOR_PUBKEY_PATH):
        missing_config.append(f"user.signingkey={_EDITOR_PUBKEY_PATH} (currently {signing_key!r})")
    if sign_commits != "true":
        missing_config.append(f"commit.gpgsign=true (currently {sign_commits!r})")

    if not missing_config:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"editor signing key at {_EDITOR_KEY_PATH}; git is configured to sign "
                "commits with it"
            ),
            proposed_action=None,
            network_required=False,
        )

    return InspectResult(
        op_id=OP_ID,
        status="ok",
        description=DESCRIPTION,
        current_state=(
            f"editor signing key at {_EDITOR_KEY_PATH} but git config is incomplete: "
            f"{'; '.join(missing_config)}. To fix, run: "
            f"git config --global gpg.format ssh; "
            f"git config --global user.signingkey {_EDITOR_PUBKEY_PATH}; "
            f"git config --global commit.gpgsign true"
        ),
        proposed_action=None,
        network_required=False,
    )


def apply() -> ApplyResult:
    """No-op — D6 is verify-only in v1 per the module docstring. The
    full install flow defers to a future ``ergodix editor init``
    command."""
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message=(
            "D6 is verify-only in v1; editor-key install runs via `ergodix editor init` (future)"
        ),
    )
