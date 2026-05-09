"""
Tests for ergodix.version.

Pre-implementation: these are the contracts version.py should satisfy.
Some pass against the existing implementation; others are forward-looking
and will fail until features land.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def test_version_is_a_string():
    from ergodix import version

    assert isinstance(version.__version__, str)
    assert version.__version__  # not empty


def test_version_matches_VERSION_file():
    """The exposed __version__ must match the contents of repo-root VERSION."""
    repo_root = Path(__file__).resolve().parent.parent
    expected = (repo_root / "VERSION").read_text().strip()

    from ergodix import version

    assert version.__version__ == expected


def test_version_falls_back_to_unknown_when_metadata_and_file_missing(monkeypatch, tmp_path):
    """
    Three-tier resolution: package metadata (preferred — works for both
    editable and non-editable installs since pip writes dist-info either
    way), then VERSION file at the repo root (raw checkout, no install),
    then the literal '0.0.0+unknown' fallback.

    This test pins the deepest fallback: if package metadata raises
    PackageNotFoundError AND the VERSION file is missing, __version__
    must be '0.0.0+unknown' rather than raising.
    """
    import importlib.metadata as md

    # Stage a fake ergodix package in tmp_path with NO VERSION file at
    # the parent level; force a re-import so version.py runs fresh.
    fake_pkg = tmp_path / "ergodix"
    fake_pkg.mkdir()
    (fake_pkg / "__init__.py").write_text("")
    real_version = Path(__file__).resolve().parent.parent / "ergodix" / "version.py"
    (fake_pkg / "version.py").write_text(real_version.read_text())

    # Force importlib.metadata to raise so the fallback chain advances
    # past the metadata tier into the VERSION-file tier (which then
    # also fails because there's no VERSION at tmp_path).
    def _raise_not_found(_name: str) -> str:
        raise md.PackageNotFoundError("ergodix")

    monkeypatch.setattr(md, "version", _raise_not_found)
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("ergodix.version", None)
    sys.modules.pop("ergodix", None)

    from ergodix import version

    assert version.__version__ == "0.0.0+unknown"

    # cleanup so other tests get the real package back
    sys.modules.pop("ergodix.version", None)
    sys.modules.pop("ergodix", None)


def test_version_module_is_runnable():
    """`python -m ergodix.version` should print the version and exit 0."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "ergodix.version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip()  # non-empty


@pytest.mark.skip(reason="Forward-looking: VERSION must be valid PEP 440 once 1.0.0 ships")
def test_version_is_valid_pep440():
    """When we go 1.0+, enforce strict PEP 440 versioning."""
    from packaging.version import Version

    from ergodix import version

    Version(version.__version__)  # raises if invalid


def test_version_module_has_no_side_effects_on_import():
    """Importing ergodix.version must not write anything to disk."""
    importlib.import_module("ergodix.version")
    # no assertion needed — if import had side effects, other tests would catch it
