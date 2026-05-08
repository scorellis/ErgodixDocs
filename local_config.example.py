"""
ErgodixDocs — per-machine local configuration template.

This file is the **template**. The cantilever orchestrator (operation C4)
copies it to local_config.py and chmods it 0o600 on first install; from
then on you edit local_config.py directly. local_config.py is gitignored
and is the only place that should hold absolute paths or machine-specific
overrides for this project.

API keys (Anthropic, Google OAuth client_id/secret) are NOT stored here.
They live in your OS keyring (Keychain on macOS, Secret Service on Linux,
Credential Manager on Windows) and are managed via:

    ergodix auth set-key anthropic_api_key
    ergodix auth status

A file fallback at ~/.config/ergodix/secrets.json is supported for headless
environments. See ergodix/auth.py for the full lookup order.

After bootstrap.sh + cantilever land local_config.py, **edit CORPUS_FOLDER
below** to point at your own corpus folder under My Drive. The placeholder
will not survive a real `ergodix migrate` or `ergodix render` run.
"""

from pathlib import Path

# ─── Google Drive paths ─────────────────────────────────────────────────────
#
# A future cantilever prereq (B2 in ADR 0003) auto-detects Drive mount mode
# and substitutes the right values here. Until B2 lands, the defaults below
# work for Mirror mode on macOS/Linux out of the box; Stream-mode users
# need to point these at the CloudStorage path manually.

# Root of the Drive mount.
#   Mirror mode: ~/My Drive
#   Stream mode: ~/Library/CloudStorage/GoogleDrive-<email>/
DRIVE_MOUNT_ROOT = Path.home() / "My Drive"

# The "My Drive" folder itself. In Mirror mode this equals DRIVE_MOUNT_ROOT.
MY_DRIVE = Path.home() / "My Drive"

# ─── Corpus folder — REQUIRED EDIT ──────────────────────────────────────────
#
# Source folder for this opus's corpus content. The placeholder below
# (angle brackets, ALL-CAPS) is intentionally not a real path so you'll
# notice you need to edit it. Replace ``<YOUR-CORPUS-FOLDER>`` with the
# actual folder name under My Drive that holds your manuscript content.
#
# Examples:
#   CORPUS_FOLDER = Path.home() / "My Drive" / "My Novel Series"
#   CORPUS_FOLDER = MY_DRIVE / "Working Drafts" / "Project Atlas"
#
# (Multi-opus support is Story 0.X — when it lands, this single value
# becomes a dict keyed by opus name and `ergodix opus add` populates it.)
CORPUS_FOLDER = Path.home() / "My Drive" / "<YOUR-CORPUS-FOLDER>"

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
