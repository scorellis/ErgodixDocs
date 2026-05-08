# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning policy: while the tool is pre-1.0, **0.MINOR.PATCH** — minor bumps may include breaking changes; we will reach 1.0.0 when the migration script, render command, and at least one Sprint 1 story (e.g. plotline tracking) are working end-to-end on real Tapestry content.

## [Unreleased]

### Added (Story 0.11 phase 2 — in flight)
- **Spike 0009** — phase-2 design decisions resolved (six decisions: C3 git-config interactive, C6 credentials, A4 MacTeX default, D6 signing-key auth scope, F1 framing, sudo-cache assumption).
- **ADR 0012** — codifies the new five-phase orchestrator (inspect → plan + consent → apply → **configure** → verify), the new `InspectResult.status = "needs-interactive"` value, F1 reframed as orchestrator code (not a prereq module — drops the remaining-prereq count from 22 to 21), A4 MacTeX `full` hard-coded in v1, D6 signing-key scope refresh on demand.
- **Configure phase implementation** (`feature/phase-2-configure-phase`): cantilever now runs an interactive collection phase between apply and verify. New `PromptFn` callable type (`(prompt: str, hidden: bool) -> str | None`), new `_run_configure_phase` orchestrator, `_default_prompt_fn` using `input` / `getpass`. Configure phase iterates `inspect_results` filtered to `status == "needs-interactive"`; each prereq's `interactive_complete(prompt_fn)` runs its own prompt loop (one prereq may issue multiple prompts — e.g., C3 wants user.name AND user.email). `--ci` floater skips the entire configure phase. New `CantileverOutcome = "configure-failed"` value; outcome ladder updated. `CantileverResult.configure_results` field added. `_apply_consented` skips needs-interactive ops cleanly so their `apply()` is never called. `_render_plan` marks needs-interactive ops with `[interactive]` so the consent gate explicitly previews "you will be prompted later."
- **PrereqSpec protocol extended** with `interactive_complete(prompt_fn) -> ApplyResult`. `ModulePrereq` adapter forwards to the underlying module's `interactive_complete` if defined; if absent, returns a "prereq-module bug" `ApplyResult(status='failed', ...)` rather than `AttributeError`-ing mid-orchestration. Modules that never report `needs-interactive` don't need to define it.
- `ergodix/prereqs/check_git_config.py` — operation C3: ensures `git config --global user.name` and `user.email` are both set. **First prereq using the new configure phase end-to-end** (A1, C4, C5 are all non-interactive). Inspect returns `ok` when both values are set, `needs-interactive` when either is missing, `failed` if `git` itself isn't on PATH. Apply is a no-op (returns `skipped`) — the configure phase does the real work via `interactive_complete`, which prompts for whichever field is unset (skipping prompts the user already answered correctly), then shells `git config --global <key> <value>` for each non-blank answer. Skip semantics: blank answer leaves the field unset; partial completion is reported as `ok` for what got set; `verify` will surface remaining gaps on the next inspect.
- `ergodix/prereqs/check_gh_auth.py` — operation C1: ensures the user is authenticated to GitHub via the `gh` CLI. Inspect returns `ok` when `gh auth status` exits 0, `needs-install` when it exits non-zero (apply will run `gh auth login`), `failed` when `gh` isn't on PATH. Apply runs `gh auth login` as a subprocess that inherits the user's terminal (no `capture_output`, no `input` redirection) so `gh`'s browser-based device-code UI works exactly as it would standalone. `network_required=True` so the orchestrator's offline-rewrite path turns this into `deferred-offline` when `is_online_fn` reports False. Per ADR 0012, C1 unblocks C2 (clone corpus) and D6 (editor signing-key registration), and does NOT request `admin:public_key` upfront — D6 prompts for that scope refresh via the configure phase only when the editor floater activates.
- **F1 reframe** (per ADR 0012): F1 ("pre-run: detect connectivity + load settings") is now orchestrator code, not a prereq module. Drops the prereq count from 22 → 21 (and the registered total from 24 → 24 stays since C3 just landed; F1 was never registered).
  - **`ergodix/connectivity.py`** — real fall-through TCP probe replacing cantilever's `_default_is_online_fn` stub. Probes Cloudflare 1.1.1.1, Google 8.8.8.8, and api.github.com on port 443 with a 3-second per-endpoint timeout. Returns True on first reachable endpoint; False only when all fail. Includes a bare-IP endpoint so a broken DNS resolver doesn't get reported as offline. 8 unit tests covering happy path, all-fail, fall-through, timeout per endpoint, socket-timeout-as-offline, and ENDPOINTS list shape.
  - **`ergodix/settings.py`** — typed `BootstrapSettings` snapshot loader for `settings/bootstrap.toml`. Returns defaults when the file is missing (the project ships with no committed `settings/` directory); records human-readable warnings without aborting cantilever when the file is malformed or contains an unknown value for a documented field. First consumer field: `mactex_install_size: Literal["full","basic","skip"]` (default `"full"` per ADR 0012). 9 unit tests covering missing-file, missing-dir, explicit values, parametrized accepted values, unknown-value-falls-back-with-warning, malformed-TOML-graceful-failure, and dataclass shape.
  - **Cantilever pre-flight integration** — `run_cantilever()` now loads `BootstrapSettings` after the op_id-uniqueness check, surfaces any `settings.warnings` to the user via `output_fn` before the plan-display phase, and stores the snapshot on `CantileverResult.settings` so prereqs and tests can read it. 2 new cantilever tests cover the missing-file (defaults, no warnings) and malformed-TOML (defaults + warning surfaced) paths. The default `_default_is_online_fn` now delegates to `ergodix.connectivity.is_online`.
- **Note added to ADR 0003** — F1 removed from prereq-module count (now 24); B2's "Tapestry path" wording flagged as pre-pivot leftover.
- **Note added to ADR 0006** — editor signing-key flow uses scope-refresh-on-demand via the configure phase, not upfront max-scope grant on C1.
- **Note added to ADR 0010** — four-phase model partially superseded by ADR 0012's five-phase model; sudo-cache assumption documented.

### Added
- Architecture design phase complete: ADRs 0001–0008 and Spikes 0001–0006 covering CLI framework, registries, repo topology, editor collaboration via sliced repos, cantilever orchestrator, polling job, role/floater model, opus naming, bootstrap layout, and post-audit cleanup decisions. Merged to main via PR #2.
- `docs/comments-explained.md` — educational doc on CriticMarkup, HTML comments, raw LaTeX comments, and Pandoc spans/divs.
- `docs/gcp-setup.md` — canonical SOP for the one-time GCP project setup (cherry-picked onto main via PR #3 after the architecture-spike merge).
- `adrs/`, `spikes/` folders with READMEs documenting conventions and numbering.
- `pyproject.toml` (Story 0.10) — Python >=3.11, console-script entry, pytest/ruff/mypy config per ADR 0008.
- `ergodix/` package skeleton (Story 0.10) — `auth.py` and `version.py` moved from repo root.
- `tests/` directory with `conftest.py` + first failing test files for `version` and `auth`. 22 passing, 1 skipped (PEP 440 strict-version test gated until 1.0).
- ADR 0009 — CI workflow + dependency-pin policy (locked vs. latest two-job CI; uv as lockfile tool; reactive capping pre-Story-0.7).
- ADR 0010 — installer pre-flight scan + single consent gate + atomic execute + verify. Splits the prereq contract into `inspect()` and `apply()`, replacing ADR 0007's `check() -> CheckResult` + `auto_fix` callable.
- ADR 0011 — ASVRAT story format required for persona-driven sprint stories; infrastructure stories may keep SVRAT. Forward-only convention (no retroactive migration).
- Story 0.11 cantilever orchestrator (`ergodix/cantilever.py`): four-phase execution per ADR 0010 — inspect → plan + consent → apply (with grouped sudo + abort-fast remediation) → verify (smoke checks: package import, ergodix-script-on-PATH, local_config sanity).
- `ergodix/prereqs/types.py` — `InspectResult` and `ApplyResult` dataclasses per ADR 0010.
- `ergodix/prereqs/check_platform.py` — first real prereq (operation A1), validating the inspect/apply contract against running code.
- `ergodix/prereqs/check_local_config.py` — operation C4: bootstraps `local_config.py` from `local_config.example.py` at the repo root, preserving an existing file (never overwrites). Sets mode 0o600. First mutative prereq with real behavior; closes the smoke-test verify gap surfaced on 2026-05-07.
- `ergodix/prereqs/check_credential_store.py` — operation C5: ensures `~/.config/ergodix/` exists with mode 0o700 (the file-fallback tier of auth.py's three-tier credential lookup). Three inspect outcomes: `ok` (dir present at 0o700), `needs-update` (dir present but mode wider — apply chmods to 0o700), `needs-install` (dir absent — apply mkdir + chmod). Idempotent. Per ADR 0003, the matching `secrets.json` template is auth.py's concern (auto-created when the user saves a credential via the file fallback); C5's job is the directory + mode invariant only.
- `ergodix cantilever` CLI subcommand wired to `run_cantilever()`.

### Changed
- `auth.py` central paths now resolve `Path.home()` lazily via a `_LazyPath` descriptor (bug found during TDD: tests that monkeypatched HOME got stale paths because module-level constants resolved at import time).
- Branch model simplified to trunk-based on 2026-05-03 — `develop` deleted; only `main` plus feature branches.
- **`install_dependencies.sh` replaced by `bootstrap.sh`** (per ADR 0007 + ADR 0010). The new script does only: locate a Python ≥3.11 interpreter, create `.venv`, `pip install -e ".[dev]"`, hand off to `ergodix cantilever`. Everything the old monolith did inline (Pandoc / MacTeX / Drive / VS Code extensions / `local_config.py` generation) moves into the cantilever orchestrator's inspect/plan/apply/verify phases. The `ergodix` console-script is now on PATH after first run.
- Cantilever's inspect-failed branch now emits a user-facing message (which prereqs failed and their `current_state`) before halting. Previously silent — a `verify-failed` -style outcome with no surfacing of *what* failed. Surfaced during 2026-05-07 self-smoke at the test deploy directory.
- Cantilever's default consent function now appends a newline after the user's response so the next apply-progress line starts on a fresh line. Previously, when stdin was piped (non-tty), the consent prompt and apply progress collided on a single line and the user couldn't tell consent had been requested. Surfaced during 2026-05-07 self-smoke ("I never saw the consent prompt").
- `local_config.example.py` no longer hardcodes the original author's corpus name. The `CORPUS_FOLDER` default is now an obvious placeholder (`<YOUR-CORPUS-FOLDER>`, angle-bracketed) with a clear "REQUIRED EDIT" comment block. Pre-pivot leftover from before [ADR 0005](adrs/0005-roles-as-floaters-and-opus-naming.md) reframed the project as "tool for any author" — install_dependencies.sh's auto-detect path was scorellis-specific, and C4's verbatim-copy in the new world meant every fresh install landed with the original author's corpus name pre-populated. Auto-substitution of detected paths is deferred to operation B2.
- `tests/test_cli.py::test_cantilever_no_args_invokes_orchestrator` removed and replaced by two focused, host-state-controlled tests (`test_cantilever_inspect_failed_exits_1`, `test_cantilever_consent_declined_exits_0`). The old test asserted `exit_code in (0, 1)` — too permissive to catch a real wiring regression.

### Removed
- Stale `feature/gcp-setup-playbook` branch (content was cherry-picked to a fresh branch off post-architecture main; original branch had become unmergeable).
- `install_dependencies.sh` — superseded by `bootstrap.sh` + cantilever (see Changed above).

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
