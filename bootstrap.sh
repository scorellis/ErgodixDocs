#!/usr/bin/env bash
# bootstrap.sh — minimal entry point for ErgodixDocs (per ADR 0007 + ADR 0010).
#
# This script does only what cantilever cannot do for itself:
#   1. Find a Python >= 3.11 interpreter.
#   2. Create .venv at the repo root if absent.
#   3. pip install -e ".[dev]"  (registers the `ergodix` console-script).
#   4. Hand off to `ergodix cantilever`.
#
# Everything else (Pandoc, MacTeX, Google Drive, VS Code extensions,
# local_config.py, credential-store layout) is the cantilever orchestrator's
# job — its four-phase model (inspect → plan + consent → apply → verify)
# is the single decision surface the user interacts with.
#
# Re-runnable. If .venv already exists and the package is already installed,
# this is fast: pip is a no-op, and cantilever's inspect phase reports
# everything as already-satisfied.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$REPO_ROOT/.venv"

# ── 1. Find Python >= 3.11 ────────────────────────────────────────────────
PYTHON=""
for candidate in python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

# Fallback: the unversioned `python3` symlink may itself be >=3.11.
if [ -z "$PYTHON" ] && command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
        PYTHON="python3"
    fi
fi

if [ -z "$PYTHON" ]; then
    echo "error: ErgodixDocs requires Python >= 3.11; none was found on PATH." >&2
    case "$(uname -s)" in
        Darwin)
            echo "  On macOS:  brew install python@3.13" >&2
            ;;
        Linux)
            echo "  On Debian/Ubuntu:  sudo apt install python3.13 python3.13-venv" >&2
            echo "  Or use pyenv:      https://github.com/pyenv/pyenv" >&2
            ;;
        *)
            echo "  Install Python 3.11+ from https://www.python.org/downloads/" >&2
            ;;
    esac
    exit 1
fi

echo "Using $PYTHON ($("$PYTHON" --version 2>&1))"

# ── 2. Create venv if absent ──────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment at $VENV"
    "$PYTHON" -m venv "$VENV"
fi

# ── 3. Install ergodix with dev extras (NON-editable) ────────────────────
# shellcheck source=/dev/null
source "$VENV/bin/activate"
pip install --quiet --upgrade pip
echo "Installing ergodix package (with dev extras)…"
# Non-editable install. Both editable modes (strict + compat) regress
# on Python 3.13 + recent setuptools — the .pth-based path / finder
# loader silently fails at Python startup, breaking `import ergodix`
# from any cwd that doesn't already contain ./ergodix/. Diagnosed
# during the 2026-05-08 / 2026-05-09 self-smokes (PRs #22, #24, #25).
# Non-editable copies the package into site-packages — bulletproof.
# Developers who want editable mode for in-repo iteration can run
# `pip install -e .` manually after bootstrap, accepting the cwd-
# dependent import behavior on Python 3.13.
pip install --quiet ".[dev]"

# ── 4. Hand off to cantilever ─────────────────────────────────────────────
# No-arg invocation: run cantilever with default floaters. Forward any args
# the user passed (e.g. `./bootstrap.sh --dry-run` or `./bootstrap.sh --ci`)
# straight through to the ergodix CLI.
if [ $# -eq 0 ]; then
    exec ergodix cantilever
else
    exec ergodix "$@"
fi
