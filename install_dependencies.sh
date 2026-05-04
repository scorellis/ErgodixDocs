#!/usr/bin/env bash
# ErgodixDocs — Prerequisite Installer
# Installs all tools needed to convert, render, and sync book content.
# Safe to re-run: checks before installing.

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; }
fail() { echo -e "${RED}  ✗ $1${NC}"; exit 1; }
step() { echo -e "\n${YELLOW}▶ $1${NC}"; }

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       ErgodixDocs Installer          ║"
echo "╚══════════════════════════════════════╝"

# ---------------------------------------------------------------------------
# 1. Homebrew
# ---------------------------------------------------------------------------
step "Checking platform"
if [[ "$(uname -s)" != "Darwin" ]]; then
    fail "This installer targets macOS (Darwin). Detected: $(uname -s)"
fi
ok "macOS detected ($(sw_vers -productVersion 2>/dev/null || echo 'unknown'))"

step "Checking Homebrew"
if ! command -v brew &>/dev/null; then
    warn "Homebrew not found — installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Ensure brew is on PATH for the remainder of this script (Apple Silicon vs Intel paths differ)
    if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    ok "Homebrew installed"
else
    ok "Homebrew already installed ($(brew --version | head -1))"
fi

# ---------------------------------------------------------------------------
# 2. Pandoc
# ---------------------------------------------------------------------------
step "Checking Pandoc"
if ! command -v pandoc &>/dev/null; then
    warn "Pandoc not found — installing..."
    brew install pandoc
    ok "Pandoc installed"
else
    ok "Pandoc already installed ($(pandoc --version | head -1))"
fi

# ---------------------------------------------------------------------------
# 3. MacTeX / XeLaTeX (for PDF rendering with custom fonts and LaTeX passthrough)
# ---------------------------------------------------------------------------
step "Checking XeLaTeX"
if ! command -v xelatex &>/dev/null; then
    warn "XeLaTeX not found."
    echo ""
    echo "  MacTeX is large (~4GB). You have two options:"
    echo "  (a) Full MacTeX — installs everything, recommended for ergodic typesetting"
    echo "      brew install --cask mactex"
    echo "  (b) BasicTeX — minimal install (~100MB), may need extra packages later"
    echo "      brew install --cask basictex"
    echo ""
    if [ -t 0 ]; then
        read -r -p "  Install (a) full MacTeX, (b) BasicTeX, or (s) skip? [a/b/s]: " choice
    else
        warn "Non-interactive shell — defaulting to skip"
        choice="s"
    fi
    case "$choice" in
        a|A) brew install --cask mactex;         ok "MacTeX installed" ;;
        b|B) brew install --cask basictex;       ok "BasicTeX installed" ;;
        s|S) warn "Skipped — PDF rendering will not work until XeLaTeX is installed" ;;
        *)   warn "Unrecognised choice — skipping" ;;
    esac
else
    ok "XeLaTeX already installed ($(xelatex --version | head -1))"
fi

# ---------------------------------------------------------------------------
# 4. Python 3
# ---------------------------------------------------------------------------
step "Checking Python 3"
if ! command -v python3 &>/dev/null; then
    warn "Python 3 not found — installing..."
    brew install python3
    ok "Python 3 installed"
else
    ok "Python 3 already installed ($(python3 --version))"
fi

# ---------------------------------------------------------------------------
# 5. Python virtual environment + packages
# ---------------------------------------------------------------------------
step "Setting up Python virtual environment"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
    ok "Virtual environment created at .venv"
else
    ok "Virtual environment already exists"
fi

# Activate and install packages
source "$VENV/bin/activate"

pip install --quiet --upgrade pip

PACKAGES=(
    "google-api-python-client"   # Google Drive API (deferred until Story 0.3)
    "google-auth-httplib2"       # Google auth transport
    "google-auth-oauthlib"       # Google OAuth flow
    "python-docx"                # .docx inspection/manipulation
    "click"                      # CLI interface (ergodix command)
    "anthropic"                  # Anthropic SDK for AI architectural analysis
    "keyring"                    # OS-native credential store (Keychain/Secret Service/Cred Mgr)
    # Dev / test dependencies (kept inline for v1; will move to requirements-dev.txt at Story 0.7).
    "pytest"                     # test runner — de-facto standard for Python testing
    "pytest-cov"                 # coverage reporting via `pytest --cov`
)

for pkg in "${PACKAGES[@]}"; do
    if pip install --quiet "$pkg"; then
        ok "Python: $pkg"
    else
        deactivate
        fail "Python: failed to install $pkg"
    fi
done

deactivate

# ---------------------------------------------------------------------------
# 6. Google Drive for Desktop (manual step)
# ---------------------------------------------------------------------------
step "Google Drive for Desktop"
if [ -d "/Applications/Google Drive.app" ]; then
    ok "Google Drive for Desktop already installed"
else
    warn "Google Drive for Desktop not found — installing via Homebrew cask"
    brew install --cask google-drive
    ok "Google Drive for Desktop installed"
fi

# Is the Drive process running?
if pgrep -f "Google Drive.app/Contents/MacOS/Google Drive" >/dev/null 2>&1; then
    ok "Google Drive process is running"
else
    warn "Google Drive is not running"
    echo "  → Launch Google Drive from /Applications and sign in"
    if [ -t 0 ]; then
        read -r -p "  Open Google Drive now? [y/N]: " open_drive
        if [[ "$open_drive" =~ ^[yY]$ ]]; then
            open -a "Google Drive"
            echo "  Waiting up to 60s for Drive to start and mount..."
            for _ in $(seq 1 30); do
                sleep 2
                if pgrep -f "Google Drive.app/Contents/MacOS/Google Drive" >/dev/null 2>&1; then
                    ok "Drive process detected"
                    break
                fi
            done
        fi
    fi
fi

# Detect mount paths. Mirror mode → ~/My Drive. Stream mode → ~/Library/CloudStorage/GoogleDrive-*.
DETECTED_MOUNT_ROOT=""
DETECTED_MY_DRIVE=""
DETECTED_SYNC_MODE=""

if [ -d "$HOME/My Drive" ] && [ ! -L "$HOME/My Drive" ]; then
    DETECTED_MY_DRIVE="$HOME/My Drive"
    DETECTED_MOUNT_ROOT="$HOME"
    DETECTED_SYNC_MODE="mirror"
    ok "Detected Mirror mode at $DETECTED_MY_DRIVE"
elif compgen -G "$HOME/Library/CloudStorage/GoogleDrive-*" >/dev/null; then
    CSTORAGE="$(ls -d "$HOME/Library/CloudStorage/GoogleDrive-"* 2>/dev/null | head -1)"
    if [ -d "$CSTORAGE/My Drive" ]; then
        DETECTED_MY_DRIVE="$CSTORAGE/My Drive"
        DETECTED_MOUNT_ROOT="$CSTORAGE"
        DETECTED_SYNC_MODE="stream"
        ok "Detected Stream mode at $DETECTED_MY_DRIVE"
    fi
else
    warn "No Drive mount detected yet"
    echo "  → Once Drive is running and signed in, re-run this script."
fi

# ---------------------------------------------------------------------------
# 7. local_config.py — per-machine configuration (gitignored)
# ---------------------------------------------------------------------------
step "Per-machine config (local_config.py)"

CONFIG_FILE="$SCRIPT_DIR/local_config.py"
CONFIG_EXAMPLE="$SCRIPT_DIR/local_config.example.py"

if [ ! -f "$CONFIG_EXAMPLE" ]; then
    warn "local_config.example.py not found — skipping config generation"
elif [ -f "$CONFIG_FILE" ]; then
    ok "Existing local_config.py found — leaving it alone (never overwritten)"
    echo "  → To regenerate, delete $CONFIG_FILE and re-run this script."
else
    # Try to auto-detect a corpus folder under My Drive. The default attempt is
    # "Tapestry of the Mind" (the original author's corpus name); other authors
    # can edit local_config.py after install. Multi-opus auto-detection is
    # Story 0.X — until then, single corpus folder per install.
    DETECTED_CORPUS=""
    if [ -n "$DETECTED_MY_DRIVE" ] && [ -d "$DETECTED_MY_DRIVE/Tapestry of the Mind" ]; then
        DETECTED_CORPUS="$DETECTED_MY_DRIVE/Tapestry of the Mind"
        ok "Detected corpus folder at $DETECTED_CORPUS"
    fi

    CONFIG_EXAMPLE_PATH="$CONFIG_EXAMPLE" \
    CONFIG_FILE_PATH="$CONFIG_FILE" \
    DETECTED_MOUNT_ROOT="$DETECTED_MOUNT_ROOT" \
    DETECTED_MY_DRIVE="$DETECTED_MY_DRIVE" \
    DETECTED_CORPUS="$DETECTED_CORPUS" \
    DETECTED_SYNC_MODE="$DETECTED_SYNC_MODE" \
    "$VENV/bin/python" - <<'PYEOF'
from pathlib import Path
import os

example = Path(os.environ["CONFIG_EXAMPLE_PATH"]).read_text()
mount = os.environ.get("DETECTED_MOUNT_ROOT", "")
mydrive = os.environ.get("DETECTED_MY_DRIVE", "")
corpus = os.environ.get("DETECTED_CORPUS", "")
sync_mode = os.environ.get("DETECTED_SYNC_MODE", "") or "mirror"

# Replace the example's path expressions with detected absolute paths.
def line(name, value):
    if value:
        return f'{name} = Path({value!r})'
    return None

replacements = {
    'DRIVE_MOUNT_ROOT = Path.home() / "My Drive"': line("DRIVE_MOUNT_ROOT", mount),
    'MY_DRIVE = Path.home() / "My Drive"':         line("MY_DRIVE", mydrive),
    'CORPUS_FOLDER = Path.home() / "My Drive" / "Tapestry of the Mind"':
        line("CORPUS_FOLDER", corpus),
    'SYNC_MODE = "mirror"': f'SYNC_MODE = {sync_mode!r}',
}
out = example
for old, new in replacements.items():
    if new:
        out = out.replace(old, new)
Path(os.environ["CONFIG_FILE_PATH"]).write_text(out)
PYEOF

    chmod 600 "$CONFIG_FILE"
    ok "Wrote $CONFIG_FILE (mode 600)"
    if [ -z "$DETECTED_CORPUS" ]; then
        warn "Corpus folder not detected — edit local_config.py and set CORPUS_FOLDER manually"
    fi
fi

# ---------------------------------------------------------------------------
# 8. Credential store — primary: OS keyring; fallback: ~/.config/ergodix/
# ---------------------------------------------------------------------------
step "Credential store"

CENTRAL_DIR="$HOME/.config/ergodix"
mkdir -p "$CENTRAL_DIR"
chmod 700 "$CENTRAL_DIR"
ok "Fallback dir ready: $CENTRAL_DIR (mode 700)"
ok "Primary credential store: OS keyring (macOS Keychain on this machine)"
echo ""
echo "  To store API keys (interactive, hidden input):"
echo "    python auth.py set-key anthropic_api_key"
echo "    python auth.py set-key google_oauth_client_id"
echo "    python auth.py set-key google_oauth_client_secret"
echo ""
echo "  To check what's stored (without printing values):"
echo "    python auth.py status"
echo ""
echo "  Lookup order at runtime:  env var → OS keyring → ~/.config/ergodix/secrets.json"

# ---------------------------------------------------------------------------
# 9. VS Code extensions (optional but recommended)
# ---------------------------------------------------------------------------
step "VS Code extensions (recommended for writing)"
if command -v code &>/dev/null; then
    echo "  Installing writing extensions..."
    code --install-extension shd101wyy.markdown-preview-enhanced  2>/dev/null && ok "Markdown Preview Enhanced" || warn "Could not install Markdown Preview Enhanced"
    code --install-extension valentjn.vscode-ltex                 2>/dev/null && ok "LTeX (grammar/spellcheck)"  || warn "Could not install LTeX"
else
    warn "VS Code CLI ('code') not in PATH — skipping extension install"
    echo "  Manually install: Markdown Preview Enhanced, LTeX"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║              Installation Complete                   ║"
echo "║                                                      ║"
echo "║  Next steps:                                         ║"
echo "║  1. Launch Google Drive and sign in (if not done)   ║"
echo "║  2. Verify local_config.py paths are correct        ║"
echo "║  3. Store API keys in keyring (when needed):        ║"
echo "║     python auth.py set-key anthropic_api_key        ║"
echo "║  4. Run: source .venv/bin/activate                  ║"
echo "║  5. We will build ergodix migrate/render next       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
