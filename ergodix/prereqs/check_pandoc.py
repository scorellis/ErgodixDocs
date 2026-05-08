"""
Cantilever prereq A3 (per ADR 0003): install/verify Pandoc.

Pandoc + XeLaTeX is the canonical render path per Story 0.2 — without
it, ``ergodix render`` cannot produce PDFs. A3 depends on A2 (Homebrew)
because apply runs ``brew install pandoc``; the registry orders A2
before A3 so A2 lands first within a single cantilever run.

network_required=True. needs_admin=False (brew install runs in
user-space; sudo is only needed for `brew install --cask` to write
to /Applications, which doesn't apply to Pandoc).

Per Spike 0008 / Story 0.11 task list, brew calls in cantilever set
``HOMEBREW_NO_AUTO_UPDATE=1`` so Homebrew doesn't surprise the user
with a multi-minute self-update mid-install — the user's consent at
the plan gate was for "install Pandoc," not "also update Homebrew."
"""

from __future__ import annotations

import os
import shutil
import subprocess

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "A3"
DESCRIPTION = "Install/verify Pandoc (canonical render-pipeline tool)"


def inspect() -> InspectResult:
    pandoc_path = shutil.which("pandoc")

    if pandoc_path is not None:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"Pandoc at {pandoc_path}",
            proposed_action=None,
            network_required=True,
        )

    return InspectResult(
        op_id=OP_ID,
        status="needs-install",
        description=DESCRIPTION,
        current_state="pandoc not found on PATH",
        proposed_action="brew install pandoc",
        estimated_seconds=30,
        network_required=True,
    )


def apply() -> ApplyResult:
    env = dict(os.environ)
    env["HOMEBREW_NO_AUTO_UPDATE"] = "1"

    try:
        result = subprocess.run(
            ["brew", "install", "pandoc"],  # noqa: S607 — brew is a developer tool, PATH lookup intentional
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
                "or install Pandoc manually: `brew install pandoc`."
            ),
        )
    except OSError as exc:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"could not spawn brew install: {exc}",
            remediation_hint="Try `brew install pandoc` manually.",
        )

    if result.returncode == 0:
        return ApplyResult(
            op_id=OP_ID,
            status="ok",
            message="Pandoc installed",
        )

    return ApplyResult(
        op_id=OP_ID,
        status="failed",
        message=f"brew install pandoc exited {result.returncode}",
        remediation_hint=(
            "Run `brew install pandoc` manually and re-run cantilever once it succeeds."
        ),
    )
