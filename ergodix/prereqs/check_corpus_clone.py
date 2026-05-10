"""
Cantilever prereq C2 (per ADR 0003): verify the corpus folder is a
git clone of the user's per-opus corpus repo.

ADR 0003 specced C2 as "Clone the corpus repo (``tapestry-of-the-mind``)."
The literal repo name was the original author's specific corpus; for
a generic-author tool, the corpus repo is per-author / per-opus and
its URL lives in the user's ``local_config.py`` (future
``CORPUS_REPO_URL`` field).

C2 lands as **verify-only in v1**, mirroring D1 / D2 / D4 / D5 / D6's
read-only pattern. The full clone action (read URL → ``git clone`` →
verify) defers to a future ``ergodix opus clone`` command. Reasons:

  - The ``CORPUS_REPO_URL`` field doesn't exist in
    ``local_config.example.py`` yet (its design lands with the future
    multi-opus story per ADR 0003's Note about per-opus configuration).
  - Cloning is mutative + network-required + can fail in many ways
    (auth, branch, partial clone interrupts); deserves explicit
    user opt-in via ``ergodix opus clone`` rather than firing
    automatically as part of every cantilever run.
  - B2 already validates that ``CORPUS_FOLDER`` resolves; C2 just
    tells the user whether what they have at that path is a clone
    they can git-pull from.

inspect() examines the corpus folder's git state via
``git -C <path> rev-parse``. Reports presence / absence; never
fails. apply() is a no-op.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ergodix.prereqs.types import ApplyResult, InspectResult
from ergodix.sync_transport import read_corpus_folder_from_local_config

OP_ID = "C2"
DESCRIPTION = "Verify corpus folder is a git clone of the per-opus corpus repo"


def _git_origin_url(path: Path) -> str | None:
    """Return the ``origin`` remote URL for the git repo at ``path``,
    or None if path isn't a git repo / has no origin / git fails."""
    try:
        result = subprocess.run(
            [  # noqa: S607 — git on PATH is intentional, same as other prereqs
                "git",
                "-C",
                str(path),
                "remote",
                "get-url",
                "origin",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    return url or None


def _is_git_repo(path: Path) -> bool:
    """True if ``path`` is inside a git working tree."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--git-dir"],  # noqa: S607
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return False
    return result.returncode == 0


def inspect() -> InspectResult:
    corpus = read_corpus_folder_from_local_config()

    if corpus is None:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                "CORPUS_FOLDER not configured in local_config.py; C2 only applies "
                "when a corpus path is set (B2 surfaces the missing-config case)"
            ),
            proposed_action=None,
            network_required=False,
        )

    if not corpus.exists():
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"CORPUS_FOLDER ({corpus}) doesn't exist on disk yet; C2 will run "
                "after `ergodix opus clone` (future) creates the clone, OR after "
                "the user manually populates the folder"
            ),
            proposed_action=None,
            network_required=False,
        )

    if not _is_git_repo(corpus):
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"corpus at {corpus} is not a git repo. If you intend to use git "
                "for editor collaboration (per ADR 0006), run `ergodix opus clone` "
                "(future) to set up the per-opus repo. Pure-local authors can "
                "ignore this — git collaboration is opt-in."
            ),
            proposed_action=None,
            network_required=False,
        )

    origin = _git_origin_url(corpus)
    if origin is None:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=(
                f"corpus at {corpus} is a git repo but has no `origin` remote. "
                "If you intend to push edits to a remote (per ADR 0006), run "
                "`git remote add origin <url>` from the corpus folder."
            ),
            proposed_action=None,
            network_required=False,
        )

    return InspectResult(
        op_id=OP_ID,
        status="ok",
        description=DESCRIPTION,
        current_state=f"corpus at {corpus} is a git clone of {origin}",
        proposed_action=None,
        network_required=False,
    )


def apply() -> ApplyResult:
    """No-op — C2 is verify-only in v1. The full clone flow defers
    to a future ``ergodix opus clone`` command, which lands when the
    multi-opus story (per ADR 0003's Note) ships and ``CORPUS_REPO_URL``
    becomes a real field in ``local_config.py``."""
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message=(
            "C2 is verify-only in v1; corpus clone runs via "
            "`ergodix opus clone` (future) once multi-opus support ships"
        ),
    )
