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
step "Checking Homebrew"
if ! command -v brew &>/dev/null; then
    warn "Homebrew not found — installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
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
    read -r -p "  Install (a) full MacTeX, (b) BasicTeX, or (s) skip? [a/b/s]: " choice
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
    "google-api-python-client"   # Google Drive API
    "google-auth-httplib2"       # Google auth transport
    "google-auth-oauthlib"       # Google OAuth flow
    "python-docx"                # .docx inspection/manipulation
    "toml"                       # ergodix.toml config parsing
    "click"                      # CLI interface (ergodix command)
)

for pkg in "${PACKAGES[@]}"; do
    pip install --quiet "$pkg"
    ok "Python: $pkg"
done

deactivate

# ---------------------------------------------------------------------------
# 6. Google Drive for Desktop (manual step)
# ---------------------------------------------------------------------------
step "Google Drive for Desktop"
if [ -d "/Applications/Google Drive.app" ]; then
    ok "Google Drive for Desktop already installed"
else
    warn "Google Drive for Desktop not found"
    echo "  → Download and install from: https://www.google.com/drive/download/"
    echo "  → After install: sign in, enable 'Mirror files' for your book folder"
    echo "  → This gives the BuildArchive converter direct local file access"
fi

# ---------------------------------------------------------------------------
# 7. VS Code extensions (optional but recommended)
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
echo "║  1. Install Google Drive for Desktop (if skipped)   ║"
echo "║  2. Run: source .venv/bin/activate                  ║"
echo "║  3. We will build the BuildArchive converter next   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
