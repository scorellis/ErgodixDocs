"""
Cantilever prereq A6 (per ADR 0003): verify Python packages from
``pyproject.toml`` are installed.

Like A5, this is a verify-only stub — ``bootstrap.sh`` runs
``pip install ".[dev]"`` and the actual install is its responsibility.
A6 checks that the documented runtime dependencies are importable;
a partial install (some succeeded, some failed silently) would fail
the inspect with a clear "missing: X" message.

Checks the **runtime** dependency set from ``pyproject.toml`` —
``click``, ``keyring``, ``anthropic``, ``googleapiclient``,
``google_auth_httplib2``, ``google_auth_oauthlib``, ``docx``. The
``[dev]`` extras (pytest, ruff, mypy) are intentionally NOT checked:
a runtime install is functional without them.

apply() is a no-op (returns ``skipped``); the recovery path is
re-running ``./bootstrap.sh`` so the install runs end-to-end with
the right pip + venv state.
"""

from __future__ import annotations

import importlib
import importlib.util

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "A6"
DESCRIPTION = "Verify Python runtime packages from pyproject are installed"

# Maps the importable module name to a friendly label and the package
# spec used in pyproject (so the remediation message can name the
# pip-install argument).
_REQUIRED_PACKAGES: tuple[tuple[str, str], ...] = (
    ("click", "click"),
    ("keyring", "keyring"),
    ("anthropic", "anthropic"),
    ("googleapiclient", "google-api-python-client"),
    ("google_auth_httplib2", "google-auth-httplib2"),
    ("google_auth_oauthlib", "google-auth-oauthlib"),
    ("docx", "python-docx"),
)


def _module_present(name: str) -> bool:
    """True if importlib can locate ``name`` without raising. Uses
    find_spec rather than import_module so a package with side-effects
    on import doesn't get loaded just for a presence check."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def inspect() -> InspectResult:
    missing_imports = [
        pip_name for import_name, pip_name in _REQUIRED_PACKAGES if not _module_present(import_name)
    ]

    if missing_imports:
        return InspectResult(
            op_id=OP_ID,
            status="needs-install",
            description=DESCRIPTION,
            current_state=f"missing packages: {', '.join(missing_imports)}",
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
        current_state=f"all {len(_REQUIRED_PACKAGES)} runtime packages importable",
        proposed_action=None,
        network_required=False,
    )


def apply() -> ApplyResult:
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message="package install is bootstrap.sh's responsibility",
        remediation_hint="If packages are missing, re-run ./bootstrap.sh from the repo root.",
    )
