"""
ErgodixDocs — per-machine local configuration template.

Copy this file to local_config.py and fill in your real values. local_config.py
is gitignored and is the only place that should hold absolute paths or
machine-specific overrides for this project.

API keys (Anthropic, Google OAuth client_id/secret) are NOT stored here. They
live in your OS keyring (Keychain on macOS, Secret Service on Linux, Credential
Manager on Windows) and are managed via:

    python auth.py set-key anthropic_api_key
    python auth.py status

A file fallback at ~/.config/ergodix/secrets.json is supported for headless
environments. See auth.py for the full lookup order.

The installer (install_dependencies.sh) auto-generates this file with detected
Drive paths filled in. It will never overwrite an existing local_config.py.
"""

from pathlib import Path

# ─── Google Drive paths (auto-detected by install_dependencies.sh) ──────────

# Root of the Drive mount.
#   Mirror mode: ~/My Drive
#   Stream mode: ~/Library/CloudStorage/GoogleDrive-<email>/
DRIVE_MOUNT_ROOT = Path.home() / "My Drive"

# The "My Drive" folder itself. In Mirror mode this equals DRIVE_MOUNT_ROOT.
MY_DRIVE = Path.home() / "My Drive"

# Source folder for this opus's corpus content. Edit to point at your own
# corpus folder under My Drive. (Multi-opus support is Story 0.X — when it
# lands, this single value becomes a dict keyed by opus name.)
CORPUS_FOLDER = Path.home() / "My Drive" / "Tapestry of the Mind"

# "stream" or "mirror"
SYNC_MODE = "mirror"

# ─── Local paths ────────────────────────────────────────────────────────────

# This deployment directory.
DEPLOY_DIR = Path(__file__).resolve().parent

# Where converted Markdown lands. Defaults to a subfolder of the deploy dir.
BUILD_DIR = DEPLOY_DIR / "build"

# Where logs are written.
LOG_FILE = DEPLOY_DIR / "ergodix.log"

# ─── Per-project OAuth token store (Google Drive/Docs) ──────────────────────
#
# Holds refresh tokens for THIS project only, scoped to the Drive/Docs
# read-only scopes declared in auth.py. Never share across tools.

TOKEN_FILE = DEPLOY_DIR / ".ergodix_tokens.json"
