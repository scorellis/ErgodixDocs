# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning is **PR-cadence-based**, not strict SemVer (see policy below).

Versioning policy (post-2026-05-10): **`1.MINOR.PATCH`**.
- **MAJOR** stays at `1` unless there's a project-wide pivot or rewrite.
- **MINOR** = the cumulative count of merged PRs that touched code (`ergodix/`, `tests/`, `pyproject.toml`, build scripts, deployment config). A "code PR" bump is `1.MINOR.0` — patch resets.
- **PATCH** = the count of doc-only merged PRs since the most recent code PR (anything under `adrs/`, `spikes/`, `docs/`, root `*.md`, `security/*.md`, etc.).

This intentionally departs from strict SemVer. Project progress is best read through merged increments rather than API stability — the API isn't stable yet, and won't be for a while. Earlier `0.1.0` policy (1.0 = migrate + render + Sprint 1 story end-to-end) is superseded; that milestone now corresponds to a tagged feature line, not a major version bump.

## [Unreleased]

(Nothing yet — next code PR will land as `1.48.0`, next docs PR as `1.47.1`.)

## [1.47.0] - 2026-05-10

**Migrate chunk 3a — pure helpers + corpus walker.** First slice of `ergodix/migrate.py` per ADR 0015 §3 / §4. Public surface: `slugify_filename`, `build_target_path`, `compute_sha256`, `build_frontmatter`, `walk_corpus` + `WalkEntry`. All side-effect-free except `walk_corpus`'s read-only filesystem traversal. Walker skips hidden dirs, `_archive/`, scratch (`__pycache__`, `node_modules`), and any folder containing a `.ergodix-skip` marker. Each yielded entry carries the registered importer name (or `None` for unclaimed extensions). 32 new tests. Chunk 3b adds the manifest TOML schema + archive mover; chunk 3c stitches the orchestrator together with re-run idempotency and two-phase atomicity.

**VERSION catch-up.** Per the new PR-cadence policy, PRs #65, #66, and #67 didn't include their own bumps — VERSION was set to 1.45.0 by #67 reflecting the state through PR #64, but by the time #67 merged the other two had already landed. Strict accounting from the 1.45.0 baseline: #65 (code) → 1.46.0, #66 (docs) → 1.46.1, #67 (docs, the release-bump PR itself only touched VERSION + CHANGELOG) → 1.46.2, this PR (code) → **1.47.0**. Going forward, each PR includes its own bump in the same commit so drift doesn't recur.

## [1.45.0] - 2026-05-10

**Versioning scheme reset.** Per the new PR-cadence policy above, this release rolls everything merged since `0.1.0` (PRs #2 through #64) into a single line. The contents below are the accumulated `[Unreleased]` content from the prior policy — preserved verbatim so the PR-by-PR detail isn't lost.

Future releases will be cut per-PR: each merged code PR bumps MINOR by 1; each merged docs PR bumps PATCH by 1; PATCH resets on every code-PR bump.

### Added (2026-05-08 late session)
- **PR #28 — A7 prereq (check_vscode)**: install/verify VS Code + 3 ergodic-text editing extensions (markdown-preview-enhanced, ltex, criticmarkup). Cookie-cutter on the check_pandoc/check_mactex pattern. Two-stage: cask install if `code` missing, then `code --install-extension` for any missing IDs. Resolver tries `shutil.which("code")` first, then falls back to `/Applications/Visual Studio Code.app/.../bin/code` so a fresh cask install in the same shell can still install extensions without a PATH refresh. Idempotent: re-runs with everything present make zero install calls. 14 new tests.
- **PR #29 — F2 run-record (orchestrator code, not a prereq)**: per ADR 0003 §164. Each cantilever invocation now appends one JSONL line to `~/.config/ergodix/cantilever.log` containing `{ts, floaters, operations, exit, duration_seconds, outcome}`. Like F1, F2 lives in `cantilever.py` (no install-vs-not state). Wired via a `_finalize()` closure that wraps every existing return path. Two-layer fail-safe: `_write_run_record` swallows `OSError` / `ValueError` / `TypeError`, and `_finalize` wraps the call in `contextlib.suppress(Exception)` — even a bug past the inner except can't crash cantilever. Parent dir created lazily so the very first run on a fresh machine still gets a record. 14 new tests.
- **PR #26 — `examples/showcase/`**: render-pipeline regression-lock fixture. `showcase.md` is a Pandoc-Markdown chapter exercising footnotes, a tcolorbox sidebar, `\rotatebox` upside-down text, `\reflectbox` mirror text, a TikZ spiral, and a TikZ vector figure of the opus → chapter hierarchy. `_preamble.tex` pulls graphicx + tikz + tcolorbox. Renders to a 58KB PDF via both `pandoc --pdf-engine=xelatex` directly and `ergodix render`. `*.pdf` added to `.gitignore` — render artifacts stay out of git.
- **PR #27 — verify rejects `<…>` placeholder in local_config.py**: closes a UX loose end. A freshly-installed `local_config.py` ships with `<YOUR-CORPUS-FOLDER>` baked into the path; the verify check previously accepted it (CORPUS_FOLDER was non-empty), giving every first install a misleading green checkmark. Now `_verify_local_config_sane` looks for any `<…>` segment in `str(CORPUS_FOLDER)` and fails with a clear "still contains a placeholder segment" message. Detection is structural (regex `<[^/<>]+>`) so future placeholders are caught without further code changes.

### Changed (2026-05-08 late session)
- **PR #25 — bootstrap.sh now uses non-editable install** (`pip install ".[dev]"`, no `-e`). Both editable modes (strict + compat) regress on Python 3.13 + recent setuptools — the `.pth`-based path / finder loader silently fails at Python startup, breaking `import ergodix` from any cwd that doesn't contain `./ergodix/`. Diagnosed during the 2026-05-08 / 2026-05-09 self-smokes. Non-editable copies the package into site-packages — bulletproof. Devs who want editable mode for in-repo iteration can run `pip install -e .` manually after bootstrap, accepting the cwd-dependent behavior.
- **PR #25 — `ergodix/version.py` three-tier resolution**: primary source is `importlib.metadata.version("ergodix")` (works for both editable and non-editable installs since pip writes dist-info either way), VERSION file is the second-tier fallback (raw checkout, no install), `0.0.0+unknown` is the deepest fallback. Fixes the `0.0.0+unknown` regression seen in non-editable installs (the wheel doesn't bundle the VERSION file, so the earlier filesystem-only fallback couldn't find it).
- **PR #23 — License switched to PolyForm Strict 1.0.0** (source-available, commercial use requires separate written license from copyright holder). README NOTICE block + LICENSE file + pyproject classifier updated. Repo is public; non-commercial use OK; commercial inquiries to scorellis@gmail.com.

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
