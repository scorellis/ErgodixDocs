"""
ErgodixDocs version.

Single source of truth: the VERSION file at the repo root. Read once at import.
Future tooling that needs to stamp output (PDF metadata, AI-generated docs,
CLI --version) imports __version__ from here.
"""

from __future__ import annotations

from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parent / "VERSION"

try:
    __version__ = _VERSION_FILE.read_text().strip()
except FileNotFoundError:
    __version__ = "0.0.0+unknown"


if __name__ == "__main__":
    print(__version__)
