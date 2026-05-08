"""
Cantilever prereq A4 (per ADR 0003): install/verify XeLaTeX (MacTeX or
BasicTeX).

A4 is the last installer prereq required for the Story 0.2 render
pipeline (Pandoc → XeLaTeX → PDF). Without XeLaTeX, ``ergodix render``
surfaces a "no PDF engine" error.

**First prereq that consumes BootstrapSettings.** Reads
``mactex_install_size`` from ``settings/bootstrap.toml`` to decide:

- ``"full"``  — ``brew install --cask mactex``    (~4GB; default per ADR 0012)
- ``"basic"`` — ``brew install --cask basictex``  (~100MB)
- ``"skip"``  — no-op; user opts out of the render pipeline entirely

Detection: ``shutil.which("xelatex")`` works for both MacTeX and
BasicTeX-with-xetex. The cantilever doesn't differentiate between them
post-install; both provide the binary `ergodix render` invokes.

Network: required. Admin: required (`--cask` writes to /Applications
or /Library/TeX). Sudo grouped at the apply phase per ADR 0010.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from ergodix.prereqs.types import ApplyResult, InspectResult
from ergodix.settings import load_bootstrap_settings

OP_ID = "A4"
DESCRIPTION = "Install/verify XeLaTeX (MacTeX or BasicTeX) for the render pipeline"


def _cask_for_size(install_size: str) -> str | None:
    """Return the brew cask for a given install_size, or None for skip."""
    if install_size == "full":
        return "mactex"
    if install_size == "basic":
        return "basictex"
    return None


def inspect() -> InspectResult:
    install_size = load_bootstrap_settings().mactex_install_size

    # User opted out — return ok regardless of whether xelatex is present.
    if install_size == "skip":
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state="user opted out via mactex_install_size='skip'",
            proposed_action=None,
        )

    xelatex_path = shutil.which("xelatex")
    if xelatex_path is not None:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"xelatex at {xelatex_path}",
            proposed_action=None,
            network_required=True,
        )

    cask = _cask_for_size(install_size)
    # Defensive: if a future settings value sneaks past validation, treat
    # it as the documented default.
    if cask is None:
        cask = "mactex"

    # MacTeX is ~4GB; BasicTeX is ~100MB. Surface a real ETA so the
    # plan-display sets the user's expectations correctly.
    estimated = 600 if cask == "mactex" else 90

    return InspectResult(
        op_id=OP_ID,
        status="needs-install",
        description=DESCRIPTION,
        current_state=f"xelatex not found on PATH; will install {cask}",
        proposed_action=f"brew install --cask {cask}",
        needs_admin=True,
        estimated_seconds=estimated,
        network_required=True,
    )


def apply() -> ApplyResult:
    install_size = load_bootstrap_settings().mactex_install_size

    if install_size == "skip":
        return ApplyResult(
            op_id=OP_ID,
            status="skipped",
            message="user opted out via mactex_install_size='skip'; no install attempted",
        )

    cask = _cask_for_size(install_size) or "mactex"

    env = dict(os.environ)
    env["HOMEBREW_NO_AUTO_UPDATE"] = "1"

    try:
        result = subprocess.run(
            ["brew", "install", "--cask", cask],  # noqa: S607
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
                f"or install manually: `brew install --cask {cask}`."
            ),
        )
    except OSError as exc:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"could not spawn brew install: {exc}",
            remediation_hint=f"Try `brew install --cask {cask}` manually.",
        )

    if result.returncode == 0:
        return ApplyResult(
            op_id=OP_ID,
            status="ok",
            message=f"{cask} installed; xelatex is now available for `ergodix render`",
        )

    return ApplyResult(
        op_id=OP_ID,
        status="failed",
        message=f"brew install --cask {cask} exited {result.returncode}",
        remediation_hint=(
            f"Run `brew install --cask {cask}` manually, "
            "or download MacTeX directly from https://tug.org/mactex/."
        ),
    )
