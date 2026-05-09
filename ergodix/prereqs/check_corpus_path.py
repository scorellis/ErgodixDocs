"""
Cantilever prereq B2 (per ADR 0003, refined by ADR 0014):
validate the corpus folder and dispatch on detected sync transport.

B2's job, post-ADR-0014:
  - Read CORPUS_FOLDER from local_config.py (via the sync_transport
    helper).
  - If unset / file missing → ``ok`` with a deferred current_state.
    On a fresh install, C4 hasn't generated local_config.py yet; the
    ``_verify_local_config_sane`` smoke check is the loud surface for
    "you didn't configure anything." Halting B2 here would prevent
    C4 from ever applying, breaking the bootstrap flow.
  - If CORPUS_FOLDER is set but the path doesn't exist → ``failed``
    with remediation telling the user to create the folder or fix
    the path.
  - If the path is under Drive Stream's mount
    (``~/Library/CloudStorage/GoogleDrive-*/...``) → ``failed`` with
    "switch to Mirror" remediation. v1 doesn't support Stream mode
    per ADR 0014 §3.
  - Drive-mirror or indy mode with an existing path → ``ok`` with a
    current_state that names the mode (so the cantilever plan-display
    makes the detected transport visible to the user).

apply() is a no-op for v1: corpus folder creation is a precondition
the user handles (or a future ``ergodix opus init`` story handles).
The method exists only to satisfy the PrereqSpec protocol.

NOTE: this slightly refines the pseudocode in ADR 0014 §6, which had
all three "missing config" cases returning failed. The deferred-ok
treatment for the local_config.py-missing case is necessary so the
fresh-install bootstrap flow works (C4 must run before B2 can
validate). The verify phase still catches the missing-config case
loudly via _verify_local_config_sane, so users do see a clear
remediation on first install.
"""

from __future__ import annotations

from ergodix.prereqs.types import ApplyResult, InspectResult
from ergodix.sync_transport import (
    detect_sync_transport,
    read_corpus_folder_from_local_config,
)

OP_ID = "B2"
DESCRIPTION = "Validate corpus folder and detect sync transport mode"


def inspect() -> InspectResult:
    corpus_folder = read_corpus_folder_from_local_config()

    # Deferred case: local_config.py missing or CORPUS_FOLDER unset.
    # C4 will (or did) generate the file; verify catches the missing
    # field loudly. B2 stays out of the way so cantilever can proceed
    # to the apply phase that runs C4.
    if corpus_folder is None:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state="deferred — local_config.py not yet configured (C4 generates it)",
            proposed_action=None,
            network_required=False,
        )

    mode = detect_sync_transport(corpus_folder)

    # Drive Stream is rejected in v1. Surface the "switch to Mirror"
    # remediation regardless of whether the path actually exists.
    if mode == "drive-stream":
        return InspectResult(
            op_id=OP_ID,
            status="failed",
            description=DESCRIPTION,
            current_state=(
                f"CORPUS_FOLDER ({corpus_folder}) is under Drive Stream mount. "
                "v1 supports Mirror mode only."
            ),
            proposed_action=(
                "Open Drive for Desktop preferences → switch to Mirror mode → "
                "update CORPUS_FOLDER in local_config.py to the Mirror path → "
                "re-run cantilever."
            ),
            network_required=False,
        )

    # Real misconfiguration: CORPUS_FOLDER points at a path that
    # doesn't resolve. (The placeholder case `~/My Drive/<YOUR-CORPUS-FOLDER>`
    # also lands here — the path doesn't exist on disk, so B2 reports it.)
    if not corpus_folder.exists():
        return InspectResult(
            op_id=OP_ID,
            status="failed",
            description=DESCRIPTION,
            current_state=f"CORPUS_FOLDER points at {corpus_folder} but the path does not exist.",
            proposed_action=(
                f"Create the folder at {corpus_folder}, OR edit "
                "CORPUS_FOLDER in local_config.py to point at your existing "
                "corpus folder, then re-run cantilever."
            ),
            network_required=False,
        )

    # Happy paths: drive-mirror or indy with a real folder.
    if mode == "drive-mirror":
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"corpus at {corpus_folder} (Drive Mirror mount)",
            proposed_action=None,
            network_required=False,
        )

    # mode == "indy"
    return InspectResult(
        op_id=OP_ID,
        status="ok",
        description=DESCRIPTION,
        current_state=f"corpus at {corpus_folder}; indy mode (no Drive sync)",
        proposed_action=None,
        network_required=False,
    )


def apply() -> ApplyResult:
    """No-op for v1. inspect() either reports ok (no plan entry) or
    failed (cantilever halts before apply). This method exists only
    to satisfy the PrereqSpec protocol."""
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message="B2 has no apply phase in v1; inspect drives the outcome.",
    )
