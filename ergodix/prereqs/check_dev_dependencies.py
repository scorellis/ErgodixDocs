"""
Cantilever prereq D3 (per ADR 0003): verify Python ``[dev]`` packages
from ``pyproject.toml`` are installed.

Like A5 / A6 (Python venv + runtime packages), D3 is a verify-only
stub — ``bootstrap.sh`` runs ``pip install ".[dev]"`` and the actual
install is its responsibility. D3 confirms the dev tools (pytest,
ruff, mypy, pytest-cov) are importable so cantilever's plan-display
correctly shows their state.

The runtime packages from pyproject (click, keyring, etc.) are A6's
responsibility; D3 covers only the ``[dev]`` extras. A user with the
``--developer`` floater active needs both; a writer / editor / focus-
reader needs only A6's runtime set.

Currently persona-agnostic — D3 always inspects, regardless of
floater. A future persona-aware refinement (skip when ``--developer``
isn't active) is deferred until floater-aware prereq filtering lands
in the orchestrator.

apply() is a no-op (returns ``skipped``); the recovery path is
re-running ``./bootstrap.sh`` so the install runs end-to-end.
"""

from __future__ import annotations

import importlib.util

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "D3"
DESCRIPTION = "Verify Python [dev] dependencies (pytest, ruff, mypy) are installed"

# Maps importable module names to pip-package specs from pyproject's
# [project.optional-dependencies] dev table.
_DEV_PACKAGES: tuple[tuple[str, str], ...] = (
    ("pytest", "pytest"),
    ("pytest_cov", "pytest-cov"),
    ("ruff", "ruff"),
    ("mypy", "mypy"),
)


def _module_present(name: str) -> bool:
    """True if importlib can locate ``name`` without raising. Mirrors
    the helper in check_python_packages so behavior stays consistent
    across the A6 + D3 verify pair."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def inspect() -> InspectResult:
    missing_imports = [
        pip_name for import_name, pip_name in _DEV_PACKAGES if not _module_present(import_name)
    ]

    if missing_imports:
        return InspectResult(
            op_id=OP_ID,
            status="needs-install",
            description=DESCRIPTION,
            current_state=f"missing dev packages: {', '.join(missing_imports)}",
            proposed_action=(
                "Re-run ./bootstrap.sh, OR install manually: "
                f"pip install {' '.join(missing_imports)}"
            ),
            network_required=True,
        )

    return InspectResult(
        op_id=OP_ID,
        status="ok",
        description=DESCRIPTION,
        current_state=f"all {len(_DEV_PACKAGES)} dev packages importable",
        proposed_action=None,
        network_required=False,
    )


def apply() -> ApplyResult:
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message="dev-package install is bootstrap.sh's responsibility",
        remediation_hint=(
            "If [dev] packages are missing, re-run ./bootstrap.sh from the repo root."
        ),
    )
