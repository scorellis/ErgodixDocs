# Working Context

## Purpose

This file is the running project/context log for Copilot work in this repo.
Update it whenever a session changes direction, a window/session is lost, or a meaningful decision is made.

## Current State

- Date: 2026-05-02
- Workspace: ErgodixDocs
- Active reference files: README.md, Hierarchy.md, SprintLog.md, ai.summary.md, auth.py, install_dependencies.sh
- Repo shape: planning docs + install_dependencies.sh + auth.py + local_config.example.py + .gitignore
- Prior chat/session context was not recoverable in the current VS Code session
- Restored context from user summary captured below

## Resolved Items (2026-05-02 session)

- **Drive sync blocker is RESOLVED.** Google Drive for Desktop is running, signed in, and switched from Stream to **Mirror** mode.
- **Canonical paths:**
  - Drive mount root: `/Users/scorellis/My Drive/`
  - Tapestry source folder: `/Users/scorellis/My Drive/Tapestry of the Mind/`
  - There is also a legacy symlink at `~/Google Drive/My Drive` that points to `~/My Drive` — do not use the symlinked path; use the canonical `~/My Drive` directly.
- **Disk:** 7.3 TB volume, 2.3 TB free at start of mirror; full mirror sync is in progress in the background.
- **README** now has Origin / Goal / AI Boundaries / Install / Auth & Secrets sections.
- **Single-directory model adopted** (2026-05-02): one repo checkout, update via `git pull`, local secrets/state kept safe by `.gitignore` and file-mode controls.
- **Config format = Python module** (`local_config.py`), not JSON. Mirrors UpFlick's choice. Lets us use `pathlib.Path` and compute values.
- **Distribution intent reframed (2026-05-02):** ErgodixDocs is being built as a tool for *other authors* to use, not just a personal scorellis tool. Naming, paths, and docs use generic `ergodix` identifiers — no `scorellis-tools` references. "Local and frugal" is an explicit design principle.
- **Auth design = three-tier, POLP, OS-keyring-first:**
  - **Tier 1**: env var (`ANTHROPIC_API_KEY` etc.) — for CI/scripts.
  - **Tier 2**: OS keyring via `keyring` library, service name `ergodix` — primary live store. macOS Keychain / Linux Secret Service / Windows Credential Manager. Encrypted at rest by the OS.
  - **Tier 3**: `~/.config/ergodix/secrets.json` (mode 600) — fallback for headless environments. `auth.py` refuses to read if perms loosened.
  - **Per-project tokens**: `<repo_dir>/.ergodix_tokens.json` (mode 600) — OAuth refresh tokens scoped only to what ErgodixDocs needs.
  - Scopes in `auth.py`: `drive.readonly` + `documents.readonly` only. No write scopes — write back happens via the Mirror filesystem, not API.
  - CLI: `python auth.py {set-key|delete-key|status|migrate-to-keyring}` with hidden-input prompts.
- **Files in source repo now:**
  - `install_dependencies.sh` — bootstraps brew/Pandoc/Python/Drive, generates `local_config.py`, sets up central secrets dir.
  - `auth.py` — scope policy + central-secrets reader + stub Drive/Docs service builders.
  - `local_config.example.py` — Python config template.
  - `.gitignore` — excludes `local_config.py`, all `.ergodix_*` files, `.venv/`, `*.gdoc`/`.gsheet`/`.gslides`, build artifacts, creative folders.
- **Removed:** `update.sh` (single-directory decision) and earlier rsync/deploy/config JSON experiments.
- **Canonical chapter format LOCKED:** Pandoc Markdown with raw LaTeX passthrough, file extension `.md`, mandatory YAML frontmatter declaring `format: pandoc-markdown` plus the active `pandoc-extensions` list. See SprintLog.md Story 0.2 "Format Decisions" for the full feature inventory.
- **Authoring direction reversed:** VS Code (not Google Docs) is the primary editor going forward. After one-time migration, chapters live as `.md` files in the private corpus repo (`tapestry-of-the-mind`), edited in VS Code by author and editor, version-controlled via git per [ADR 0006](adrs/0006-editor-collaboration-sliced-repos.md). No Drive/Docs API at runtime for content. CriticMarkup remains as optional annotation; editor's primary review is direct prose edits via signed git commits in their slice repo.
- **Pre-release timeline (2026-05-03):** the author intends ~1 year of private development in `--writer --developer` floater combination before inviting other authors. This pacing informs Story 0.7 (distribution prep) — no urgency to ship installers, app-store packaging, etc. until the tool has stabilized through real daily use.

## Known Content

- README.md contains Origin, Goal, AI Boundaries, Install, and Auth & Secrets guidance
- Hierarchy.md describes a proposed documentation/story hierarchy for the EPOCH "Tapestry of the Mind"

## Latest Session Notes

- User reopened or changed VS Code window context and prior chat state appears to have been lost
- User wants ongoing work context documented in-repo so it survives session changes
- This file was created to serve that purpose
- Previous discussion centered on a Google Docs <-> repo synchronization workflow
- Target content format is Pandoc Markdown with raw LaTeX passthrough
- Intended workflow includes bidirectional sync between repo files and Google Drive / Google Docs
- Comments should be preserved or otherwise represented in the sync model
- Creative materials should live in an untracked folder; only tooling should be pushed to GitHub
- Sprint planning should live in Markdown and use SVRAT story structure: So that, Value, Risk, Assumptions, Tasks
- Earlier blocker: Google Drive on macOS needed reinstall or OS update attention before local sync could work
- Current blocker: Google Drive has been reinstalled but is still not syncing after restart

## Open Questions

- ~~Where is the local Google Drive mount point or mirror folder on this Mac after reinstall?~~ **Resolved:** `/Users/scorellis/My Drive/` (Mirror mode).
- ~~Is Google Drive failing to start, signed in but idle, or showing a specific sync error?~~ **Resolved:** running, signed in, Mirror sync in progress.
- ~~Which files belong in the tracked tooling area versus the untracked creative-materials area?~~ **Partially resolved:** boundary captured in `.gitignore` and the README "Install" section. Tracked = tooling + planning. Untracked = `config.json`, `.venv/`, `*.gdoc`/`*.gsheet`/`*.gslides`, and any creative folder.
- ~~Should we use a two-directory deploy model?~~ **Resolved:** no. Single-directory workflow adopted; `update.sh` removed.
- How should comments map during sync: preserve as sidecar metadata, inline annotations, or a tool-specific representation? *(Sprint 0 Story 0.3)*
- What's the expected end-state behavior when a chapter is edited in two places between syncs? *(Sprint 0 Story 0.2 / 0.3 boundary)*

## Next Update Rule

When work resumes, append a short dated note covering:

- what changed
- what decision was made
- what remains next

## Reconstructed Direction

- Build tooling that reads Google Docs content from a synced Google Drive location
- Convert source material into repo-friendly Pandoc Markdown with raw LaTeX passthrough where needed
- Support bidirectional sync so edits in the repo can be pushed back to Google Docs and remote changes can be pulled in
- Design a strategy for comments instead of discarding review context
- Keep creative/source materials out of GitHub by storing them in an untracked local folder or otherwise ignored path
- Track implementation work using a Markdown sprint log with SVRAT stories

## Immediate Next Step

- Wait for Mirror first-sync to complete in the background.
- Initial commit + push of the source repo to GitHub.
- Keep setup and daily workflow in a single checkout; run `./install_dependencies.sh` in repo root as needed.
- Then enter planning mode for **Sprint 0 Story 0.2 — Define canonical repo format** (Pandoc Markdown + raw LaTeX, decide which Google Docs features must round-trip, how to represent unsupported constructs, file naming/folder conventions inside `Tapestry of the Mind`).