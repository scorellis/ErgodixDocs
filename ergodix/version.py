"""
ErgodixDocs version.

Single source of truth: the ``VERSION`` file at the repo root. Setuptools
reads it at install time (per ``[tool.setuptools.dynamic]`` in
pyproject.toml) and stamps the value into the installed package
metadata. We read that metadata at runtime via
``importlib.metadata.version`` — works for both editable and
non-editable installs.

Fallback: if the package isn't installed (e.g., running from a raw
checkout without ever running ``pip install``), read the VERSION file
directly from the repo root.

Future tooling that needs to stamp output (PDF metadata, AI-generated
docs, CLI ``--version``) imports ``__version__`` from here.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path

try:
    __version__ = _pkg_version("ergodix")
except PackageNotFoundError:
    # Not installed — fall back to reading VERSION at the repo root
    # (parent of this package directory).
    _VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"
    try:
        __version__ = _VERSION_FILE.read_text().strip()
    except FileNotFoundError:
        __version__ = "0.0.0+unknown"


if __name__ == "__main__":
    print(__version__)
