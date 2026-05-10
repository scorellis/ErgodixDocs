#!/usr/bin/env bash
# scripts/integration-smoke.sh
#
# End-to-end smoke test for the deployment pipeline.
#
# What it verifies:
#   1. bootstrap.sh runs cleanly against a fresh deploy directory.
#   2. The `ergodix` console-script is registered in the venv.
#   3. `ergodix --version` matches the deploy directory's VERSION file
#      (what setuptools read at install time).
#   4. `ergodix migrate --from docx --check` against the in-repo
#      fixture reports `migrated=1, skipped=2` (Chapter 2.docx
#      migrated; Chapter 1.gdoc + Notes.gsheet skipped as out-of-scope
#      for the docx run).
#   5. `ergodix status` exits 0.
#
# Cantilever is invoked with `--dry-run` so the smoke runs unattended:
# inspect + plan only, no consent prompt, no system changes.
#
# What it does NOT test (these need real infrastructure beyond a
# script can sandbox):
#   - The OAuth dance (requires a real Google account + browser).
#   - Real Drive / Docs API calls (uses canned mocks in the unit tests).
#   - `cantilever` apply phase (requires sudo + brew + interactive
#     consent gate).
#
# Designed to be runnable both:
#   - LOCALLY: `scripts/integration-smoke.sh` from the repo root.
#   - FROM CI (future): the same script invoked from a GitHub Actions
#     workflow with no changes. The deploy directory is configurable
#     via the `ERGODIX_SMOKE_DEPLOY` env var so CI can use a workflow-
#     local temp dir.
#
# Re-runnable. Each run starts from a clean venv (cleared via
# `python3 -m venv --clear`) so a previously-bit-rotted venv from a
# stale run doesn't poison the result.

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

DEPLOY_DIR="${ERGODIX_SMOKE_DEPLOY:-/tmp/ergodix-smoke-deploy}"
SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

log() {
    echo "[smoke] $*"
}

fail() {
    echo "[smoke] FAIL: $*" >&2
    exit 1
}

# ── 1. Prepare deploy directory ──────────────────────────────────────────────

log "preparing deploy at $DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

# Clear any previous venv so a bit-rotted .venv from a stale run doesn't
# poison the result. Per the 2026-05-10 self-smoke: a venv that sits
# unused for several days while pip/setuptools change underneath can
# leave the installed `click` / `pip._internal` in a broken state. The
# `--clear` rebuilds the venv from scratch without rm-ing the dir
# (avoiding sandboxes that block recursive deletes).
if [ -d "$DEPLOY_DIR/.venv" ]; then
    log "clearing existing .venv"
    python3 -m venv --clear "$DEPLOY_DIR/.venv"
fi

# ── 2. Sync source to deploy ─────────────────────────────────────────────────

log "syncing source to $DEPLOY_DIR"
rsync -a \
    --exclude='.venv' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='.ruff_cache' \
    --exclude='*.egg-info' \
    --exclude='.coverage' \
    --exclude='.coverage.*' \
    --exclude='build/' \
    --exclude='dist/' \
    "$SOURCE_DIR/" "$DEPLOY_DIR/"

cd "$DEPLOY_DIR"

# ── 3. Run bootstrap ─────────────────────────────────────────────────────────

# bootstrap.sh hands off to `ergodix cantilever`. We pass `--dry-run` so
# cantilever runs inspect → plan and exits cleanly without prompting for
# consent or applying any system changes. Per Review 0015.3 finding #2:
# without --dry-run, on environments where inspect succeeds and a non-
# empty plan is built, cantilever blocks at the interactive consent gate,
# making the smoke unsuitable for unattended (CI / review-bot) runs.
#
# Exit-code policy:
#   - 0 (success): --dry-run outcome, or no-changes-needed.
#   - 1: inspect-failed (e.g., placeholder local_config.py on a fresh
#        deploy) — this is working-as-designed behavior, not a smoke
#        failure. We accept it.
#   - >1: real bug in bootstrap.sh / cantilever itself.
log "running bootstrap.sh --dry-run cantilever"
set +e
bash bootstrap.sh --dry-run cantilever
BOOT_EXIT=$?
set -e
if [ "$BOOT_EXIT" -gt 1 ]; then
    fail "bootstrap.sh exited $BOOT_EXIT"
fi

# ── 4. Verify console-script registration ────────────────────────────────────

ERGODIX="$DEPLOY_DIR/.venv/bin/ergodix"
if [ ! -x "$ERGODIX" ]; then
    fail "ergodix console-script not registered at $ERGODIX"
fi
log "ergodix CLI installed at $ERGODIX"

# ── 5. Verify --version matches VERSION file ─────────────────────────────────

# Per Review 0015.3 finding #1: compare against $DEPLOY_DIR/VERSION (what
# setuptools actually read at install time), NOT $SOURCE_DIR/VERSION.
# The two should be identical after rsync, but if they ever diverge (e.g.,
# concurrent edit, rsync hiccup), the deploy copy is the load-bearing one
# because it's what got stamped into the installed package metadata.
EXPECTED_VERSION="$(tr -d '[:space:]' < "$DEPLOY_DIR/VERSION")"
ACTUAL_VERSION="$("$ERGODIX" --version | awk '{print $NF}')"
if [ "$ACTUAL_VERSION" != "$EXPECTED_VERSION" ]; then
    fail "version mismatch — deploy VERSION says $EXPECTED_VERSION, ergodix --version says $ACTUAL_VERSION"
fi
log "version $ACTUAL_VERSION matches deploy VERSION file"

# ── 6. ergodix status returns 0 ──────────────────────────────────────────────

log "running ergodix status"
"$ERGODIX" status > /dev/null
log "ergodix status exit 0"

# ── 7. migrate --check end-to-end against the fixture ────────────────────────

log "running migrate --from docx --check against examples/migrate-fixture"
SUMMARY="$("$ERGODIX" migrate --from docx --check \
    --corpus "$DEPLOY_DIR/examples/migrate-fixture" 2>&1 | tail -1)"
log "summary: $SUMMARY"

# Expected counts: 1 docx migrated; 2 skipped (gdoc + gsheet, both
# out-of-scope for the docx importer).
echo "$SUMMARY" | grep -q "migrated=1" \
    || fail "expected migrated=1 in summary"
echo "$SUMMARY" | grep -q "skipped=2" \
    || fail "expected skipped=2 in summary"

# ── PASS ─────────────────────────────────────────────────────────────────────

echo ""
log "PASS — version $ACTUAL_VERSION, bootstrap + CLI + migrate verified"
