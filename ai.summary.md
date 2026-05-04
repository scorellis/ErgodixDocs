# AI Session Summary

## 2026-05-03 (end-of-day)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. It uses AI as architectural co-author and continuity engine.
- AI's role is **Architectural Analysis only** — never edits prose chapters; tracks plotlines, flags plot holes, builds summaries/storyboards, supports worldbuilding.

**Architecture phase (Story 0.8) is DONE as of 2026-05-03.** ADRs 0001–0008 and spikes 0001–0006 merged to main. Don't revisit unless explicitly asked.

**Locked architectural decisions (read these in `adrs/` to fully load context):**

- **ADR 0001** — Click subcommand groups, plugin registries (later collapsed by 0005).
- **ADR 0002** — Two-repo topology: public `ErgodixDocs` (tooling) + private corpus repo (per opus). Editor sections later partly superseded by 0006.
- **ADR 0003** — Cantilever bootstrap orchestrator with 22 operations. Idempotent. Abort-fast with detailed remediation. Connectivity auto-detected. Settings paths simplified by 0005.
- **ADR 0004** — Continuous polling job (every 5 min, persona-aware, no-op when offline). LaunchAgent on macOS for v1.
- **ADR 0005** — All roles as floaters in single registry. `--writer`, `--editor`, `--developer`, `--publisher`, `--focus-reader`, plus behavior floaters (`--dry-run`, `--verbose`, `--ci`). focus-reader is mutex with the others via declarative `exclusive_with`. Multi-corpus container named **opus** (plural **opera**).
- **ADR 0006** — Editor collaboration via sliced git repos with baseline-tracked resync. Master + per-editor slice repos. `ergodix publish` / `ergodix ingest`. Signed commits required.
- **ADR 0007** — `bootstrap.sh` (macOS/Linux) + `bootstrap.ps1` (Windows). Each prereq op is an importable Python module exposing `def check() -> CheckResult`. `pyproject.toml` console-script entry registers `ergodix` on PATH.
- **ADR 0008** — `ergodix sync` rename: `sync-out` (editor save) + `sync-in` (poller fetch). `local_config.py` (per-machine, gitignored) vs `settings/*.toml` (per-repo, committed) ownership rule. Auto-fix iterative bound (one retry, no recursion). ruff + mypy adopted.

**Format decisions (Story 0.2, locked):**

- Pandoc Markdown + raw LaTeX passthrough.
- `.md` extension with mandatory YAML frontmatter (`format: pandoc-markdown`, `pandoc-extensions: [...]`).
- One `.md` file per Chapter (smallest creative unit).
- LaTeX preamble cascade: optional `_preamble.tex` at every folder level (Epoch / Compendium / Book / Section); render walks up the tree, concatenates most-general-first.
- Three scopes for font/style changes: inline (`{\fontfamily{...}\selectfont ...}`), per-chapter (frontmatter `extra-preamble:`), per-folder (`_preamble.tex`).
- Render pipeline: Pandoc → XeLaTeX → PDF.

**Branch model:** trunk-based. Only `main` plus feature branches. `develop` was deleted 2026-05-03; we'll reintroduce when there are outside contributors. PR-then-merge via the GitHub web UI (gh CLI is broken on user's machine due to corporate integration; will be addressed Monday).

**Distribution / pacing:**

- Tool naming is generic ("ergodix"); the corpus name "tapestry" should not bleed into the tool surface.
- Author intends ~1 year of private development in `--writer --developer` floater combination before inviting other authors. Story 0.7 (intuitive installers, app-store packaging) covers eventual non-technical onboarding; not urgent.

**Where work paused (2026-05-03 evening):**

- On branch `feature/test-scaffolding`. **Story 0.10 (TDD scaffolding) is in flight.**
- One commit landed locally on this branch (not yet pushed): `pyproject.toml` + `ergodix/` package skeleton with `auth.py` and `version.py` moved in + `tests/` with conftest + test_version + test_auth.
- **22 tests pass, 1 skipped** (PEP 440 strict-version test gated until 1.0).
- **Bug found and fixed during TDD red phase**: `auth.py` was resolving `Path.home()` at import time, baking module-level constants. Tests that monkeypatch HOME got stale values. Fixed via `_LazyPath` descriptor that evaluates `Path.home()` on attribute access.
- `.venv` was recreated with Python 3.13.12 (system Python 3.9.6 was too old for `>=3.11`).
- `.gitignore` extended for `*.egg-info`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `htmlcov`.

**Story 0.10 remaining work:**

- Stub failing tests for every planned module (~40 test files): cli, cantilever, 22 prereqs, 8 floaters, 2 importers, publish, ingest, connectivity, runrecord.
- Confirm all stubbed tests are RED for the right reasons.
- Begin GREEN phase: minimal implementations, smallest module first.

**Open architectural concern**: ADR 0009 (CI workflow design) — lint, typecheck, test, coverage, multi-platform matrix, what blocks merge. Story 0.10's CI task waits on this. Decide whether to write ADR 0009 first or stub more tests first when work resumes.

**Tomorrow's first move:**

1. Push `feature/test-scaffolding` (1 commit) to remote for review.
2. Decide: stub more tests vs. draft ADR 0009 (CI design).
3. Continue Story 0.10 work toward GREEN phase.

Please start by asking the user whether they want to (a) keep stubbing failing tests for the unimplemented modules, or (b) draft ADR 0009 first, before resuming work. Then proceed accordingly.
