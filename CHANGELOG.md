# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning policy: while the tool is pre-1.0, **0.MINOR.PATCH** — minor bumps may include breaking changes; we will reach 1.0.0 when the migration script, render command, and at least one Sprint 1 story (e.g. plotline tracking) are working end-to-end on real Tapestry content.

## [Unreleased]

### Added
- Architecture design phase complete: ADRs 0001–0008 and Spikes 0001–0006 covering CLI framework, registries, repo topology, editor collaboration via sliced repos, cantilever orchestrator, polling job, role/floater model, opus naming, bootstrap layout, and post-audit cleanup decisions. Merged to main via PR #2.
- `docs/comments-explained.md` — educational doc on CriticMarkup, HTML comments, raw LaTeX comments, and Pandoc spans/divs.
- `docs/gcp-setup.md` — canonical SOP for the one-time GCP project setup (cherry-picked onto main via PR #3 after the architecture-spike merge).
- `adrs/`, `spikes/` folders with READMEs documenting conventions and numbering.
- `pyproject.toml` (Story 0.10) — Python >=3.11, console-script entry, pytest/ruff/mypy config per ADR 0008.
- `ergodix/` package skeleton (Story 0.10) — `auth.py` and `version.py` moved from repo root.
- `tests/` directory with `conftest.py` + first failing test files for `version` and `auth`. 22 passing, 1 skipped (PEP 440 strict-version test gated until 1.0).

### Changed
- `auth.py` central paths now resolve `Path.home()` lazily via a `_LazyPath` descriptor (bug found during TDD: tests that monkeypatched HOME got stale paths because module-level constants resolved at import time).
- Branch model simplified to trunk-based on 2026-05-03 — `develop` deleted; only `main` plus feature branches.

### Removed
- Stale `feature/gcp-setup-playbook` branch (content was cherry-picked to a fresh branch off post-architecture main; original branch had become unmergeable).

## [0.1.0] - 2026-05-02

Initial Sprint 0 infrastructure release. The tool does not yet read or write Tapestry content; this release establishes the foundation that Story 0.2 implementation work will sit on.

### Added
- Project scaffolding: `README.md` with Origin / Goal / AI Boundaries / Install / Auth & Secrets sections, `Hierarchy.md` capturing the EPOCH → Compendium → Book → Section → Chapter narrative model.
- Sprint planning in `SprintLog.md` using SVRAT story structure (So that, Value, Risk, Assumptions, Tasks). Sprint 0 stories 0.1, 0.4, 0.5 marked DONE; 0.2, 0.3, 0.6 in flight; Sprint 1 stories 1.1–1.5 as placeholders.
- Running session log in `WorkingContext.md` with resolved-items, open-questions, and immediate-next-step sections.
- AI session resume prompt in `ai.summary.md`.
- `install_dependencies.sh` — macOS bootstrap installer covering Homebrew, Pandoc, MacTeX/BasicTeX (optional), Python 3, Python virtual environment with `google-api-python-client`, `google-auth-*`, `python-docx`, `click`, `anthropic`, `keyring`. Installs Google Drive for Desktop via `brew install --cask google-drive` if missing. Auto-detects Drive Stream vs. Mirror mode and the `Tapestry of the Mind` folder. Generates `local_config.py` from `local_config.example.py` with detected paths injected via env-var-passed Python (no shell injection vector).
- `auth.py` — three-tier credential lookup (env var → OS keyring → `~/.config/ergodix/secrets.json` fallback), least-privilege scope policy (`drive.readonly`, `documents.readonly`), CLI subcommands `set-key`, `delete-key`, `status`, `migrate-to-keyring [--delete-file]`. Hidden-input prompts. Permission-mode invariant enforced on the fallback file.
- `local_config.example.py` — Python module template for per-machine paths.
- `.gitignore` — excludes `local_config.py`, `.ergodix_*` runtime files, `.venv/`, build artifacts, Google Drive placeholder files (`*.gdoc`/`*.gsheet`/`*.gslides`), creative-material folder conventions.
- `VERSION` and `CHANGELOG.md` — versioning and change-tracking infrastructure (matches UpFlick convention).

### Decisions locked
- **Sync transport**: filesystem via Drive Mirror, not Drive/Docs API at runtime. API used only during the one-time `ergodix migrate` step.
- **Canonical chapter format**: Pandoc Markdown with raw LaTeX passthrough, file extension `.md`, mandatory YAML frontmatter declaring `format: pandoc-markdown` and the active `pandoc-extensions` list.
- **Render pipeline**: Pandoc → XeLaTeX → PDF.
- **Editorial review surface**: CriticMarkup in-file (`{++add++} {--del--} {>>comment<<} {==highlight==}{>>comment<<}`).
- **Primary editor**: VS Code, not Google Docs. After one-time migration, native `.gdoc` files are archived.
- **Repository model**: single-directory; updates via `git pull`. Local secrets and runtime state survive via `.gitignore`. (Earlier two-directory deploy model considered and rejected as overhead for non-developer authors.)
- **Credential storage**: OS keyring (macOS Keychain / Linux Secret Service / Windows Credential Manager) is the primary store under service name `ergodix`; plaintext file is fallback only.
- **Distribution intent**: tool for any author, not just one user. Naming uses generic `ergodix` identifiers throughout.

### Security
- API keys live in the OS keyring by default — encrypted at rest by the OS, never plaintext on disk during normal use.
- Fallback `secrets.json` mode-checked at every read; loose permissions raise rather than silently load.
- `~/.config/ergodix/` directory is mode 700; `local_config.py` is mode 600 when generated by the installer.
- Google API scopes restricted to `drive.readonly` + `documents.readonly`. No write scopes requested. Filesystem write-back via Drive Mirror covers the bidirectional flow without API write privileges.
- Per-project OAuth refresh tokens (when added in Story 0.3) live at `<repo>/.ergodix_tokens.json` (gitignored, mode 600), never reused across tools.

### Removed
- Earlier rsync-based `deploy.sh` and `config.example.json` experiments.
- Earlier `update.sh` (UpFlick-style git-reset-with-protected-files); replaced by plain `git pull` once the single-directory decision was made.
- All `scorellis-tools` naming references in favor of generic `ergodix` identifiers.

### Notes
- Tool is pre-functional: `ergodix migrate` and `ergodix render` are not yet implemented. `auth.get_drive_service()` and `auth.get_docs_service()` are intentional `NotImplementedError` stubs pending Story 0.2 / 0.3 work.
