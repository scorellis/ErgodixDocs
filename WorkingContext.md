# Working Context

## Purpose

This file is the running project/context log for Copilot work in this repo.
Update it whenever a session changes direction, a window/session is lost, or a meaningful decision is made.

## Current State

- Date: 2026-05-02
- Workspace: ErgodixDocs
- Active reference files: README.md, Hierarchy.md, stories/SprintLog.md, ai.summary.md, auth.py, install_dependencies.sh
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
- **Canonical chapter format LOCKED:** Pandoc Markdown with raw LaTeX passthrough, file extension `.md`, mandatory YAML frontmatter declaring `format: pandoc-markdown` plus the active `pandoc-extensions` list. See stories/SprintLog.md Story 0.2 "Format Decisions" for the full feature inventory.
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

## 2026-05-07 (mid-morning checkpoint)

### What changed
- **Story 0.11 phase 1 complete and reviewed clean.** Branch `feature/installer-redesign` is 17 commits ahead of `main` and Copilot-recommended for PR + merge.
- Today's commits: ADR 0011 (ASVRAT), C4 prereq (`check_local_config`), C5 prereq (`check_credential_store`), inspect-failed UX message, consent-prompt newline fix, `local_config.example.py` genericized (Tapestry leak removed → `<YOUR-CORPUS-FOLDER>` placeholder), permissions overhaul (broad allowlist + targeted deny + bash-log hook).
- Tests: 158 passing, 1 skipped, 80% coverage. ruff + mypy strict clean. Three real-machine self-smokes at the test deploy directory all green.
- Two working norms hardened into memory: (a) self-smoke as the Installer persona instead of delegating, (b) every "OK to push?" ask pairs with a brief reason.

### What was decided
- Phase-1-vs-phase-2 split: ship cantilever foundation + first 3 prereqs as a single PR rather than waiting for all 25 prereqs to land. Smaller PRs, validated pattern, easier review.
- Permission floor: `git push *` stays in the prompt zone (CLAUDE.md "always ask before pushing"); destructive variants (force-push, hard-reset, branch -D, sudo, system installs, raw-disk ops) explicitly denied.
- Bash audit log: every command Claude runs lands in `ai.bashcommands.log` (gitignored, project root) with UTC timestamps. Local backtrack only, never reaches origin.

### What remains next
- **Open the PR** for `feature/installer-redesign` against `main` (17 commits, Copilot-clean).
- **Phase 2 first wave** (next 3 prereqs, per Plan-subagent output 2026-05-07): C1 (`gh auth login`), C2 (clone corpus repo), A2 (install/verify Homebrew). Full Plan output in [SprintLog Story 0.11](stories/SprintLog.md).
- **Design decisions to resolve before phase 2:** C3/C6 interactive-in-apply pattern, A4 MacTeX-vs-BasicTeX default, D6 signing-key auth scope, F1 prereq-vs-orchestrator framing, `needs_admin` escalation semantics in `ApplyResult`. These are captured in SprintLog.

## Immediate Next Step

**Mid-session as of 2026-05-07 ~08:30. Story 0.11 phase 1 ready for PR.**

State now:
- **Story 0.8 (architecture)** — DONE. ADRs 0001–0011 + Spikes 0001–0008 merged to main.
- **Story 0.10 (TDD scaffolding)** — partial work merged via prior PR; remaining ~40 test stubs paused pending Story 0.11 phase 2.
- **Story 0.11 phase 1 (cantilever foundation + first 3 prereqs + UX + permissions)** — DONE on `feature/installer-redesign`, 17 commits pushed, Copilot review clean (zero blockers).
  - Cantilever orchestrator (4 phases: inspect → plan + consent → apply → verify) with sudo grouping, abort-fast, op_id-uniqueness validation, inspect-failed first-class outcome, verify-on-no-changes path.
  - Three prereqs landed: A1 (platform), C4 (local_config bootstrap), C5 (credential-store dir).
  - Bootstrap.sh replaces install_dependencies.sh: minimal Python-detect / venv-create / pip-install / hand-off-to-cantilever.
  - UX: consent-prompt newline visible, inspect-failed surfaces what failed, `local_config.example.py` genericized (no more "Tapestry of the Mind" leak).
  - Permissions: broad allowlist + targeted deny + bash-log hook.
- **Tests: 158 passing, 1 skipped, 80% coverage. ruff + mypy strict clean.**

Story 0.11 phase 2 remaining (per Plan subagent 2026-05-07):
- Recommended next 3 in order: **C1** (`gh auth login`), **C2** (clone corpus repo), **A2** (install/verify Homebrew). Full plan + design-decision list in [SprintLog Story 0.11](stories/SprintLog.md).
- 19 more prereqs after that — see SprintLog for tier grouping and dependencies.

Next-session opening move: open the PR for `feature/installer-redesign` against `main`. After merge, start phase 2 from a fresh branch off main, opening with the design-decisions resolution (C3/C6 interactivity, A4 MacTeX default, D6 auth scope, F1 framing, `needs_admin` escalation) — likely a short spike or ADR — before any new prereq code.

## 2026-05-08 (late-session continuation)

### What changed
- **Six PRs merged** in this session: #22 (A4 MacTeX), #23 (license switch to PolyForm Strict 1.0.0 + parking-lot stories), #24 (bootstrap editable_mode=compat — superseded), #25 (bootstrap non-editable install + version.py three-tier fix), #26 (`examples/showcase/` render-pipeline fixture with sidebar/footnotes/rotation/spiral/vector figure), #27 (verify rejects `<…>` placeholder in local_config.py).
- **Two PRs awaiting merge** at session end: #28 (A7 check_vscode) and #29 (F2 run-record). Both branched off main, both green (296 tests pass, ruff + mypy clean), both independently mergeable.
- Story 0.11 prereq coverage rose from ~33% to ~46% (after #28 merges): 11 of 24 prereq ops registered.
- ADR 0011 / ADR 0012 / Spike 0009 already on main from prior session.

### What was decided
- **License = PolyForm Strict 1.0.0**, not open-source. Source-available so the architecture can be referenced; commercial use requires a separate written license from scorellis@gmail.com. Repo stays public.
- **F2 lives in orchestrator code**, not as a prereq module — same reframe as F1. There's no install-vs-not state; it's a post-run side-effect. Wired via a `_finalize()` closure inside `run_cantilever`.
- **Showcase fixture pattern** — when the user asks for a smoke artifact, ship it into the repo as a permanent regression-lock rather than leaving it in an ephemeral test deploy. `examples/showcase/showcase.md` is the first instance.
- **Verify-phase placeholder detection is structural** — regex `<[^/<>]+>` catches any future `<YOUR-X>` placeholder without test churn.

### What remains next
- Merge PRs #28 + #29.
- Next mechanical wins: E2 (persona-tailored "you're done" message, ~20 min), A5/A6 (Python venv + packages verify-only stubs, ~30 min each), B2 (Drive mount detection — closes the local_config placeholder loop at install rather than verify level, ~60 min).
- Bigger arc: `ergodix migrate --from gdocs` is Story 0.2's other big task. Multi-session, needs design first (Docs API → Pandoc-Markdown mapping, hierarchy detection, idempotency model). Highest user-visible value.

### User context noted
- User confirmed their relationship to the ergodic-text genre: invented his approach independently over ~a decade, parallel to (not descended from) Aarseth or Danielewski. Future framing should not position him as a follower of either. Saved as user memory.