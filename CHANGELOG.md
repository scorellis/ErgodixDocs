# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning is **PR-cadence-based**, not strict SemVer (see policy below).

Versioning policy (post-2026-05-10): **`1.MINOR.PATCH`**.
- **MAJOR** stays at `1` unless there's a project-wide pivot or rewrite.
- **MINOR** = the cumulative count of merged PRs that touched code (`ergodix/`, `tests/`, `pyproject.toml`, build scripts, deployment config). A "code PR" bump is `1.MINOR.0` — patch resets.
- **PATCH** = the count of doc-only merged PRs since the most recent code PR (anything under `adrs/`, `spikes/`, `docs/`, root `*.md`, `security/*.md`, etc.).

This intentionally departs from strict SemVer. Project progress is best read through merged increments rather than API stability — the API isn't stable yet, and won't be for a while. Earlier `0.1.0` policy (1.0 = migrate + render + Sprint 1 story end-to-end) is superseded; that milestone now corresponds to a tagged feature line, not a major version bump.

## [Unreleased]

(Nothing yet — next code PR will land as `1.65.0`, next docs PR as `1.64.1`.)

## [1.64.0] - 2026-05-10

**`ergodix index` chunk 1 — pure helpers in `ergodix/index.py`.** First implementation chunk of the ergodix-index arc (Spike 0015 §"Implementation chunks", ADR 0016). No FS orchestration yet; just the pure functions the orchestrator (chunk 2), drift comparison (chunk 3), and CLI wiring (chunk 4) will compose.

Exposed surface:

- `MAP_SCHEMA_VERSION = 1` — locked per ADR 0016 §1.
- `IndexEntry` / `Map` — frozen dataclasses for one file and the full map.
- `compute_sha256_of_file(path)` — lowercase hex SHA-256 over file bytes (streamed in 64 KiB chunks).
- `walk_corpus_for_index(corpus_root)` — yields indexable file paths per Spike 0015 §2: includes `.md`, `_preamble.tex`, any other `*.tex`; skips hidden files/dirs, `_archive/`, `_media/`, `__pycache__/`, `node_modules/`, `.ergodix-skip`-scoped trees, `.gdoc`/`.gsheet` placeholders.
- `build_map_entry(corpus_root, file_path)` — file → `IndexEntry` with POSIX-relative path, SHA-256, size, ISO-8601 UTC mtime.
- `serialize_map_toml(map_data)` — `Map` → TOML text in the schema fixed by ADR 0016 §1 (single `[meta]` block + one `[[files]]` array entry per file).
- `parse_map_toml(text)` — strict version refusal per ADR 0016 §1.

The walker duplicates the small `_walk` loop from `ergodix.migrate` per ADR 0016 §5 ("duplicate the small loop first, refactor only when chunks 2-4 show real coupling pressure"). The two walkers diverge in scope (migrate hands off to importer registry; index has a fixed extension allowlist) so factoring up-front would have been premature.

26 new tests covering: SHA-256 over known-content / lowercase-hex / empty file / binary file; walker yields `.md` / `_preamble.tex` / custom `.tex`; walker skips hidden / `_archive/` / `_media/` / `__pycache__` / `node_modules` / `.gdoc`+`.gsheet`; walker respects `.ergodix-skip` marker and descends into nested dirs; `build_map_entry` records all four fields correctly; serialize/parse round-trip; version-refusal on unknown / missing version. Full suite: 693 passed, 1 skipped (was 667). `ruff` + `format` + `mypy --strict` clean.

## [1.63.3] - 2026-05-10

**ADR 0016 — `ergodix index` + `_AI/ergodix.map` locked decisions.** Resolves the 9 open questions Spike 0015 left for ADR resolution. Decision highlights:

1. **Schema** declares `version = 1`; readers refuse unknown versions (matches migrate manifest posture).
2. **No `kind` field per file** — path + extension carry kind information.
3. **`mtime` is advisory only**; SHA-256 is authoritative for drift detection.
4. **Map is tracked in git, not gitignored** — merge conflicts auto-recover by re-running `ergodix index`; audit value outweighs friction.
5. **Walker factoring deferred to chunk-1 impl** — duplicate the small loop first, refactor to `corpus_walker.py` only when chunks 2–4 show real coupling pressure.
6. **`--check` exits 1 on drift** (mirrors migrate's exit-code convention).
7. **First-consumer interface**: downstream tools (Continuity-Engine, Plot-Planner, MCP server) read via a `read_map(path) -> Map` helper, never raw TOML. Helper survives schema evolution.
8. **Sliced editor repos regenerate locally** — the map is tooling metadata, not corpus content; carrying it would force a filter-to-slice step. Editors run `ergodix index` against their slice after sync-in.
9. **`_AI/` namespace is project-wide canonical** for AI-emitted artifacts — codifies the implicit convention growing across Continuity-Engine, Plot-Planner, Skill-factory-seal parking-lot stories.

Spike 0015's status updated from "Open" → "Resolved." The active story ([stories/active/ergodix-index.md](stories/active/ergodix-index.md)) now points at ADR 0016 directly. Six-chunk implementation arc is unblocked.

## [1.63.2] - 2026-05-10

**Bulk-extract remaining parking-lot stories from `stories/SprintLog.md` monolith.** Completes the per-file-story migration started in PR #89. Fifteen new files under `stories/parking-lot/` — one per pending story called out in the README's "still in the monolith" section, plus a sixteenth (`scale-concerns.md`) that bundles Stories 0.Z1–0.Z5 under one umbrella since they're all "deferred — activate per real signal" sub-issues of the same architectural concern:

- Spike: `criticmarkup-dual-mode-review`
- Sprint 1+: `continuity-engine`, `phil-trained-prose-linter`
- Sprint 2+: `plot-planner`, `devils-toolbox`, `form-analyzer-ergodite`, `skill-factory-seal-protection`, `mcp-server-ai-user-persona`
- Way-later (post-distribution): `ip-strategy`, `licensing-monetization`, `sell-my-book`, `in-app-ai-editor`
- Scale / multi-tenancy: `multi-opus-support`, `scale-concerns`, `publishing-house-enterprise-scale`

Each file uses the per-file convention from PR #89 (status + origin + ASVRAT or lighter shape per ADR 0011, with cross-references resolved to per-file siblings where they previously pointed into the monolith). `stories/README.md` is restructured to group entries by activation horizon (infra / Sprint 1+ / Sprint 2+ / way-later / scale) instead of the previous flat "pending migration" list — easier to read the parking-lot at a glance. The monolith `stories/SprintLog.md` remains untouched (geological layer; no longer the canonical source for any active or parking-lot story).

## [1.63.1] - 2026-05-10

**`diagrams/ergodix-system-flow.md` — first system-flow diagram (Copilot-generated).** Mermaid flowchart mapping the current end-to-end functional architecture: CLI dispatcher → Cantilever orchestrator (inspect → plan/consent → configure → apply → verify) → prereqs/settings cascade; Auth & Secrets (env → keyring → file fallback, OAuth token store); Import & Index (migrate orchestrator → importer registry → run manifest → `_archive` originals; `ergodix index` → `_AI/ergodix.map`); Render pipeline (Pandoc/XeLaTeX + preamble cascade); Collaboration & Sync (publish/ingest, sync-in poller, slice registry). Four cross-cutting decision boundaries surfaced as named gates: AI Action Boundary (ADR 0013), Idempotency Required (ADRs 0003/0010/0015), Connectivity Auto-detect (ADRs 0003/0004/0014), Least-Privilege Scopes (ADR 0015). Companion node-reference table cross-links every node to its ADR(s) + story origin. Coverage notes list three focused follow-up diagrams the next session can request (cantilever phase detail / migrate internals / collaboration topology).

## [1.63.0] - 2026-05-10

**`scripts/integration-smoke.sh` hardening — Review 0015.3 findings #1 + #2.** Closes both findings the third external review (`reviews/0015.3.external-review.md`) raised against PR #85's smoke script.

- **Finding #1 (Medium): version-mismatch false-negative.** The smoke compared `ergodix --version` against `$SOURCE_DIR/VERSION` (the workspace), but the installed package's version is what setuptools read from `$DEPLOY_DIR/VERSION` at install time. After rsync, the two paths usually agree, but any drift (concurrent edit, partial rsync, stale deploy) produced a false-negative version mismatch even when the installed package and its source-of-record were in fact consistent. Smoke now reads `$DEPLOY_DIR/VERSION` — the load-bearing copy.
- **Finding #2 (Low): blocking on cantilever's interactive consent gate.** The smoke documents itself as CI-ready, but on environments where inspect succeeded and a non-empty plan was built (i.e., not the placeholder-`local_config.py` halt path), `bash bootstrap.sh` blocked at the consent prompt — the reviewer hit this and had to manually answer `n`. Smoke now invokes `bash bootstrap.sh --dry-run cantilever`, forwarding the top-level `--dry-run` floater through to cantilever. Result: inspect runs, plan is printed, exits cleanly with outcome `dry-run` (no consent prompt, no system mutations). The `inspect-failed` exit-1 path on placeholder-config deploys is preserved (still working-as-designed).

Self-smoke against `/Users/scorellis/Documents/Scorellient/Applications/ErgodixDocs/` PASSes with the new flags. CI workflow (`.github/workflows/integration.yml`) inherits the fix unchanged — it invokes the same script.

## [1.62.2] - 2026-05-10

**Establish `stories/` per-file convention; move SprintLog.md into it as a geological layer.** Migrates the project's story-tracking from a single ~700-line `SprintLog.md` at the repo root to a per-file convention mirroring `adrs/` and `spikes/`. Layout: `stories/active/<slug>.md` for in-flight stories, `stories/parking-lot/<slug>.md` for deferred ones, `stories/README.md` as the index. The monolithic `SprintLog.md` moves to `stories/SprintLog.md` as a frozen historical record — no longer edited going forward. First two per-file stories landed here: `stories/active/ergodix-index.md` (the Sprint 1 starter activated alongside Spike 0015) and `stories/parking-lot/uv-migration.md` (the follow-up that was previously hiding only in ADR 0009's "Note — pragmatic v1" section). All cross-references in `spikes/`, `adrs/`, `security/`, `CLAUDE.md`, `README.md`, and `WorkingContext.md` updated to `../stories/SprintLog.md` (or `stories/SprintLog.md` from root). The remaining ~14 parking-lot stories still live in the monolith pending extraction in a follow-up PR; the index README documents which ones are pending.

## [1.62.1] - 2026-05-10

**Spike 0015 — `ergodix index` + `_AI/ergodix.map` design.** Activates the parking-lot story as the first Sprint 1 implementation arc. Captures the design surface: TOML schema (versioned, per-file SHA-256 + size + advisory mtime, `[meta]` block matching migrate's manifest shape), location at `<corpus>/_AI/ergodix.map`, scope (walks `.md` + `_preamble.tex` + custom `.tex`; skips hidden / `_archive/` / scratch / `.ergodix-skip` dirs — same rules as migrate's walker), CLI surface (`ergodix index [--check] [--corpus <path>] [--quiet]` with exit-code conventions matching migrate), re-run semantics (regenerate-from-scratch; per-file hash caching deferred until corpus size warrants it), and the lean: **tracked, not gitignored**, with conflicts auto-recovered by re-running. 9 open questions enumerated for ADR 0016. 6 implementation chunks proposed for the smaller-units cadence. Cross-refs to ADR 0015 (manifest shape parallel) + Continuity-Engine + Plot-Planner parking-lot stories (downstream consumers) + Spike 0013 (ergodite registry — every ergodite reads the map first).

## [1.62.0] - 2026-05-10

**`.github/workflows/integration.yml` — GitHub Actions integration smoke.** Invokes `scripts/integration-smoke.sh` on every PR and every push to main, in parallel with `.github/workflows/ci.yml`. The two are complementary: `ci.yml` catches unit-test / lint / type-check regressions; this one catches install + console-script registration + migrate-against-fixture regressions that the unit tests don't reach. Ubuntu runner with Python 3.13. Uses `$RUNNER_TEMP/ergodix-smoke-deploy` (workflow-local) via the `ERGODIX_SMOKE_DEPLOY` env var override so parallel runs from different PRs don't collide. Closes the second half of the "shift CI/CD to GitHub" arc the user flagged after PR #85 — the local-runnable smoke and the GitHub-hosted smoke are now the **same script**.

## [1.61.0] - 2026-05-10

**`.github/workflows/ci.yml` — pragmatic v1 of ADR 0009 CI.** Adds the first GitHub Actions workflow that runs `ruff check` + `ruff format --check` + `mypy --strict` + `pytest` on every push to main and every PR against main. Single cell: Ubuntu + Python 3.13, using `pip install -e ".[dev]"`. Catches the unit-test / lint / type-check regression layer on every PR — the integration smoke (PR #85) already covers the install + CLI + migrate-against-fixture layer locally. ADR 0009 gains a "Note — pragmatic v1 (2026-05-10)" section explaining the deviation from the locked design (full uv + 9-cell macOS/Ubuntu/Windows × 3.11/3.12/3.13 matrix; `test-latest` informational tripwire). The uv-migration follow-up arc swaps `pip` for `uv sync`, generates `uv.lock`, expands the matrix, and lifts the Note. Until then, this PR closes the "no CI on GitHub" gap — the project no longer relies solely on me running tests locally before each PR.

## [1.60.0] - 2026-05-10

**`scripts/integration-smoke.sh` — local-first deployment-pipeline smoke test.** Closes the gap between "we shipped chunks 1-7+6b of migrate over the last 22 PRs" and "we've actually verified the install path still works against the new code." The script syncs source to a fresh deploy directory (default `/tmp/ergodix-smoke-deploy`, override via `ERGODIX_SMOKE_DEPLOY`), runs `bootstrap.sh`, verifies the `ergodix` console-script registers and `--version` matches the source's `VERSION` file, exercises `ergodix status` and `ergodix migrate --from docx --check --corpus examples/migrate-fixture`, and asserts expected `migrated=1, skipped=2` counts. Re-runnable; `python3 -m venv --clear` rebuilds any bit-rotted previous venv without needing `rm -rf` (matters in restricted sandboxes). Accepts bootstrap exit code 0 or 1 (the latter is cantilever's halt-on-unresolvable-inspect or consent-declined paths, both working-as-designed). Designed for parity with future CI: the same script will be invoked from `.github/workflows/integration.yml` when CI/CD shifts off-machine — no rewrite needed. README.md gains a §Integration smoke test section; CLAUDE.md gains a working-norm bullet directing future install-touching PRs through the smoke before reporting "done." Self-tested in this PR: full PASS against `/tmp/ergodix-smoke-deploy` from a fresh checkout.

## [1.59.1] - 2026-05-10

**`ai.summary.md` refresh — end-of-day 2026-05-10 checkpoint.** Replaces the 2026-05-09 (Story 0.11 closure) snapshot with the current state. Captures: migrate arc feature-complete (chunks 1-7 + 6b), OAuth security review backlog at 0 open findings, ~22 PRs merged today, two external reviews completed (0015 + 0015.2), versioning and reviews conventions established, branch-stacking discipline established, three remembered gotchas (GitHub stacked-PR base auto-retarget unreliable; force-push sandbox-blocked; zsh `interactivecomments` OFF means no `#` lines in paste blocks). v1.0.0 milestone (per the original CLAUDE.md bar: migrate + render + Sprint 1 story end-to-end) is ~85% — migrate ✅, render ✅, Sprint 1 story is the next major arc (likely starting move: `ergodix index` + `_AI/ergodix.map`).

## [1.59.0] - 2026-05-10

**Review 0015.2 follow-ups — test coverage.** Adds the missing test coverage called out in the second external review. 13 new tests:

- **#75 docx None-style guard:** `test_render_paragraph_handles_none_style` — pins the defensive null guard in `_render_paragraph` against pathological docs where `paragraph.style` is None.
- **#chunk-6 docx .bin fallback:** `test_suffix_for_image_part_falls_back_to_bin` — covers `partname=None`, extensionless partname, and the typical `.png` case.
- **#chunk-6b gdocs `_guess_image_extension`:** 6 new tests exercising magic-byte priority over URI suffix, URI fallback for jpeg/png/webp, query-string stripping, `.bin` fallback for Docs-style `lh3.googleusercontent.com` URLs (which carry no recognizable extension), and direct recognition of JPEG/GIF87/GIF89/WebP magic bytes.
- **#oauth-backlog partial-field corruption:** `test_credentials_from_dict_partial_field_corruption_token_uri_only_missing` (two of three required fields present, one missing — error names the specific field) + `test_credentials_from_dict_happy_path_all_required_present` (all fields present → no exception).
- **#77 direct heuristic-bucket tests:** 4 new tests exercising `_emit_token_exchange_diagnostic` directly: invalid_grant bucket, phrase-anchored "already used" (catches "already used" but NOT a bare "used" embedded in unrelated text — the false-positive case finding #77 flagged), rate-limit bucket (4 trigger phrases tested), and the generic-bucket fallback that preserves the raw error text.
- **#76 `.gsheet` skip-reason:** the existing `test_e2e_gdocs_run_against_fixture` now also asserts `reasons["Notes.gsheet"] == "out-of-scope file type"` and `"failed" not in statuses.values()` — pins the "unknown extension → skip with reason" contract so a future regression that classifies as `failed` surfaces as a fixture-test failure.

Full suite: 667 passed, 1 skipped (was 654). ruff + format + `mypy --strict` clean.

## [1.58.0] - 2026-05-10

**Review 0015.2 follow-ups — code improvements.** Addresses the low/medium findings from the second external review (`reviews/0015.2.external-review.md`):

- **VERSION sync** (housekeeping): main was at 1.56.0 with a `[1.57.0]` CHANGELOG entry — PR #81's VERSION bump didn't propagate through merge. This PR catches up to the [1.57.0] state and bumps to 1.58.0 for its own content.
- **#74 (Low): silent author-config failure.** `_read_author_from_local_config` in `ergodix/cli.py` now emits a `UserWarning` on broken `local_config.py` instead of silently swallowing exceptions. Mirrors the pattern from `oauth.py::_token_file_path`. Users no longer migrate with empty author silently when their config is broken.
- **#74 (Low): counts_str ordering.** `migrate_cmd` now emits `failed` first when non-zero (e.g. `migrate run 2026-...: failed=2, migrated=10, skipped=3`) so failures are at the front of the line, not buried alphabetically.
- **#77 (Low): heuristic phrase-anchoring.** `_emit_token_exchange_diagnostic` no longer matches the bare words `"used"` / `"redeemed"` (which can appear in unrelated DNS-layer errors like "address already used"). Now anchored to phrases: `"already used"`, `"already redeemed"`, `"code has been"`. Reduces false-positive misclassification of generic errors as bad-OAuth-code errors.
- **#oauth-backlog (Low): module constant for stale-token threshold.** Extracted `_REFRESH_TOKEN_STALE_DAYS = 90` as a module-level constant with a comment referencing Google's ~6-month invalidation policy. If the policy or lead time ever changes, it's a one-line edit instead of finding the magic number inside a function. Also documents the Python ≥3.11 dependency for `datetime.fromisoformat()`'s `Z` suffix support.
- **#chunk-6 (Medium): `_media/` mkdir mode intentionality.** Added an in-code comment to both `docx.py::_extract_images` and `gdocs.py::_extract_inline_images` documenting that `_media/` directories are intentionally created at umask default (not 0o700 like OAuth dirs). Rationale: chapter images are readable artifacts the author may share / view in Preview, not credentials.

No behavior changes that affect tests; existing 654 tests pass unchanged. ruff + format + `mypy --strict` clean.

## [1.57.0] - 2026-05-10

**OAuth review backlog cleanup — findings #3 and #7.** Closes the last two non-security items from the original OAuth security review (`reviews/0015.external-review.md`). After this PR, all 7 findings from that review are addressed.

- **#7 (Low): Credentials deserialization validation.** `_credentials_from_dict` now validates the load-bearing fields (`token_uri`, `client_id`, `client_secret`) up-front and raises `ValueError` listing all missing fields at once. Empty-string is treated as missing. A corrupted token file now fails immediately with a clear message instead of producing a `Credentials` object that fails cryptically (`NoneType has no attribute …`) on the next refresh. 4 new tests covering individual missing fields, empty-string-as-missing, and "lists all missing at once."

- **#3 (Low): Refresh-token age tracking + staleness warning.** New optional `refresh_token_issued_at` field in the saved tokens dict (ISO-8601 UTC). `acquire_oauth_credentials` stamps this on initial auth; `load_or_acquire_credentials` preserves it across access-token refreshes (only re-acquire-from-scratch resets it). On load, if the refresh token is older than 90 days, an inform-don't-block warning fires via `output_fn` ("Google may invalidate refresh tokens after ~6 months of non-use"). Backwards-compatible: token files written before this PR have no `refresh_token_issued_at`; they're silently treated as unknown-age (no warning, no re-auth). 4 new tests covering: timestamp recorded on acquire, stale-token warning, fresh-token silence, missing-timestamp silence, refresh preserves the timestamp.

OAuth review status: **0 open findings**. Prior PRs closed #1, #2, #4, #5, #6.

8 new tests total. Full suite: 654 passed, 1 skipped. ruff + format + `mypy --strict` clean.

## [1.56.0] - 2026-05-10

**Migrate chunk 6b — gdocs inline image extraction.** Closes the gdocs half of ADR 0015 §3 image handling that was deferred from chunk 6 (#78). When `media_dir` is set, `gdocs.extract` walks the document body for `inlineObjectElement` references, resolves them against `document.inlineObjects.<id>.inlineObjectProperties.embeddedObject.imageProperties.contentUri`, fetches bytes via an authenticated HTTP session, saves to `media_dir / "img-NNN.<ext>"` with extension inferred from magic bytes (PNG / JPEG / GIF / WebP) falling back to URI-suffix scan, and appends `![](filename)` references to the rendered Markdown. New `image_fetcher: Callable[[str], bytes | None]` parameter lets tests inject a stub; production builds the default lazily from `oauth.load_or_acquire_credentials` + `google.auth.transport.requests.AuthorizedSession`. **Lazy fetcher construction** — only built when an image-bearing inline element is encountered, so docs without images never trigger OAuth or pull google-auth even with `media_dir` set. Failed fetches (network / auth errors → fetcher returns None) are silently dropped without crashing extract; body content still renders. 4 new tests. Full suite: 645 passed, 1 skipped. ruff + format + `mypy --strict` clean.

## [1.55.0] - 2026-05-10

**Migrate chunk 6 — embedded image extraction (docx; gdocs deferred).** First slice of ADR 0015 §3 image handling. The `docx` importer now extracts every embedded image part to `<corpus>/<chapter parent>/_media/<chapter slug>/img-NNN.<ext>` (zero-padded sequential numbering, extension preserved from the original part) and appends `![](filename)` references to the rendered Markdown body. The orchestrator computes `media_dir = corpus_root / target_rel.parent / "_media" / target_rel.stem` per chapter and passes it to `importer.extract`; `--check` (dry-run) skips the dir entirely. The `gdocs` importer accepts `media_dir` for orchestrator-call-shape parity but doesn't yet fetch image bytes — the Docs API inline-image flow needs a Drive API auth path + contentUri fetch that's its own follow-up. Inline images in `.gdoc` sources are silently skipped in v1; the body content (paragraphs, headings, formatting, lists) extracts unchanged. Image references appear as a trailing block at the end of the markdown rather than positioned inline (python-docx's public API doesn't surface inline image positions cleanly without walking OOXML; v1 ships bytes + complete reference list, polish pass repositions). 3 new tests covering: image bytes written to media_dir, no media_dir = no extraction (dry-run safe), multiple distinct images get sequential filenames. Full suite: 641 passed, 1 skipped. ruff + format + `mypy --strict` clean.

## [1.54.0] - 2026-05-10

**OAuth review follow-up — finding #4 (rate-limit / token-exchange messaging).** `acquire_oauth_credentials` now wraps `flow.fetch_token(code=code)` in a try/except that classifies common failure modes via heuristics on the error message and emits a friendlier explanation through `output_fn` before re-raising. Three buckets: (1) `invalid_grant` / expired / re-used codes → "codes expire ~10 minutes after issue and can only be used once; run again with a fresh code"; (2) 429 / rate-limited / quota / "too many" → "Google rate-limited the OAuth exchange; wait ~60 seconds and run again"; (3) anything else → generic "re-run; check your network and OAuth client credentials." The exception is preserved (re-raised after the diagnostic) so technical info isn't lost. Closes the third item from the original PR Review 1 pre-migrate checklist (#1, #2, #5, #6 shipped in PR #72; #3 token-age and #7 deserialization-validation remain as deferred non-security UX polish). 3 new tests covering the three buckets. Full suite: 638 passed, 1 skipped. ruff + format + `mypy --strict` clean.

## [1.53.0] - 2026-05-10

**Migrate chunk 7 — `examples/migrate-fixture/`.** Adds a checked-in canned corpus that exercises every layer of migrate (walker, gdocs/docx importers, orchestrator, frontmatter, manifest, archive) against real on-disk inputs without needing Drive or network. Mirrors the role `examples/showcase/` plays for render. Layout: `Book 1/Chapter 1.gdoc` (JSON placeholder; tests inject a mocked `docs_service`), `Book 1/Chapter 2.docx` (real binary built by `tests/build_migrate_docx_fixture.py`, exercising headings + bold/italic + bulleted lists), `Notes.gsheet` (verifies out-of-scope skip path). The `.docx` builder lives under `tests/` (not inside the fixture corpus) so the migrate walker doesn't pick the `.py` script up as an out-of-scope file. 5 hermetic e2e tests in `tests/test_migrate_fixture.py`: fixture-shape contract, full gdocs run, full docx run, `--check` dry-run leaves the tree untouched, re-run idempotency on an unchanged source. Catches regressions in any single layer as a fixture-test failure rather than as a unit-test scoped to one module. Full suite: 635 passed, 1 skipped. ruff + format + `mypy --strict` clean.

## [1.52.1] - 2026-05-10

**Spike 0014 + parking-lot story — `form-analyzer` ergodite.** Captures the design surface for a single ergodite that grades a chapter's *form* on three axes: readability/grade-level (publicly-defined formulas — Flesch-Kincaid, Gunning Fog, SMOG, Coleman-Liau, ARI, Dale-Chall via `textstat`-style portfolio + consensus + band classification), rhetorical eloquence (per-paragraph density of detected figures: anaphora, epistrophe, polysyndeton, asyndeton, tricolon, alliteration, anastrophe — first concrete consumer of the Devil's Toolbox rhetoric primitives), and Fibonacci/golden-mean structural arc (per the author's writing prompt, blocked on `docs/fibonacci-writing-prompt.md` capture). Single ergodite with toggleable sub-checks rather than three separate ergodites. Companion parking-lot story added to SprintLog.md with ASVRAT body + tasks. Activation gated on Spike 0013's ergodite registry shipping (ADR-X1).

(Bonus: corrected two `../spikes/...` → `spikes/...` cross-ref paths in SprintLog.md while editing — `SprintLog.md` lives at the repo root, so the leading `..` was a stale lift-and-shift bug.)

## [1.52.0] - 2026-05-10

**Migrate chunk 5 — `.docx` importer.** New `ergodix/importers/docx.py` extracts Word / Scrivener `.docx` files to Pandoc-Markdown via the `python-docx` runtime dep that's already in `pyproject.toml` (no new deps). Coverage matches the gdocs importer: paragraphs (Normal), headings (Heading 1-6, Title, Subtitle), bold + italic + bold-italic combined, bulleted lists ("List Bullet" style). Tables / images / footnotes silently skipped — chunk 6 (image extraction) and a future polish pass cover them. Registered in `ergodix/importers/__init__.py`'s explicit registry alongside `gdocs`. Empty paragraphs (the trailing one python-docx adds automatically, plus user-inserted empties) are dropped so re-render Markdown doesn't accumulate blank-line gaps. The orchestrator's `docs_service` kwarg is accepted-and-ignored via `**_kwargs` so non-OAuth importers slot into the registry without per-importer signature plumbing. 15 new tests building real `.docx` files via `python-docx` in tmp_path then asserting on rendered Markdown. Full suite: 631 passed, 1 skipped. ruff + format + `mypy --strict` clean.

## [1.51.0] - 2026-05-10

**Migrate chunk 4 — CLI wiring.** Replaces the `migrate` stub in `ergodix/cli.py` with the real command per ADR 0015 §6: `ergodix migrate --from <importer> [--check] [--force] [--corpus <path>] [--limit N]`. Resolves `corpus_root` from `--corpus` override or `local_config.CORPUS_FOLDER`; resolves `author` from `local_config.AUTHOR` → `git config user.name` → empty string. For the gdocs importer, calls `auth.get_docs_service()` (which triggers the OAuth dance on first use); ignored kwarg for non-gdocs importers. `--check` and `--force` mutually exclusive. Prints a one-line summary `migrate run <id>: migrated=N, skipped=N, ...` plus the manifest path; exits 1 if any files have status="failed", else 0. The `migrate` row in `test_cli.py`'s "stubs exit with not-yet-implemented" parametrize list is removed; the new `test_migrate_*` tests pin the real surface. 10 new tests covering `--from` required, `--check`/`--force` mutex, arg-resolution wiring, `--corpus` override, `--check`/`--force`/`--limit` plumbing, AUTHOR fallback to `git config`, error when corpus unconfigured, summary output, exit-1 on failures.

## [1.50.0] - 2026-05-10

**OAuth security review — follow-up fixes (PR Review 1, findings #1, #2, #5, #6).** Closes the four pre-migrate-checklist items from the external review of chunks 1a/1b/1c. Specifically:

- **#1 (Medium): RefreshError messaging.** `load_or_acquire_credentials` now surfaces the underlying `RefreshError` via `output_fn` before clearing tokens and re-acquiring, so the user sees *why* re-auth is happening instead of a silent silent re-prompt.
- **#2 (Low): Client-ID consistency check.** New helper `_client_id_matches_config` runs before any refresh attempt: if the token's `client_id` doesn't match the current `google_oauth_client_id` from the credential store (i.e. the user rotated their OAuth client), tokens are cleared immediately with a clear message rather than burning a refresh attempt that's guaranteed to fail. Skipped gracefully when the credential isn't set yet (lets downstream flow handle it).
- **#5 (Low): Parent-dir mode safety net in `save_oauth_tokens`.** Mirrors the load-side check: parent dir is created at mode 0o700 when missing, and `_check_parent_dir_mode` is invoked after to reject any pre-existing parent at loose perms (the file's 0o600 invariant is meaningless when the parent is 0o755).
- **#6 (Low): Broken local_config.py warning.** `_token_file_path` no longer silently swallows import errors — broken `local_config.py` now emits a `UserWarning` so the user sees their `TOKEN_FILE` override is being ignored.

The three remaining findings (#3 token-age check, #4 OAuth rate-limit handling, #7 lenient deserialization validation) are non-security UX/robustness improvements deferred to a future polish pass.

**Reviews convention follow-through.** With the four security findings closed, the OAuth review is now safe to publish: `reviews/0015.external-review.md` is removed from `.gitignore` (line dropped, since #71 added it) and committed alongside the fixes.

7 new tests covering all four fixes (RefreshError messaging path, client_id mismatch path, client_id-skip path when config unset, save with loose parent, warn on broken local_config, no-warn on clean local_config). Full suite: 594 passed, 1 skipped. ruff + format + `mypy --strict` clean.

## [1.49.1] - 2026-05-10

**Spike 0013 amendment — ergodites naming + integrity sub-section.** Per a Message 1 addendum from the author, the analysis-plugin concept is now named **ergodites** (etymology: "ergodic" + "-ite", framed as a little "ego" that carries out a task; avoids the Claude Code / Agent SDK "skill" collision). Locks what was an open naming question. Section C is reorganized into C.1 (pattern + module contract — now `ergodix/ergodites/`) and a new **C.2 Ergodite integrity** sub-section capturing the author's tamper-resistance instinct (salted hash dictionary per release). C.2 enumerates two approaches (hash manifest only vs. signed manifest + signed ergodites) with the lean: start hash-manifest, promote to signed alongside the §D certificate flow. Custom / user-authored ergodites discussed as a parking-lot question. Open-questions list updated: ADR-X1 drops "naming" and gains four integrity questions. Section H (ADR 0013 boundary check) updated to note ergodite integrity is also tooling-side, not corpus mutation.

Incorporates two findings from the Copilot review of this PR (see [reviews/copilot-pr-reviews.md](reviews/copilot-pr-reviews.md) §"PR Review 2"): C.2 gains an explicit *Threat-model honesty* paragraph clarifying that Approach 1 is tamper-evident under a trusted distribution channel and **does not** resist a local attacker with write access to both ergodites and manifest — adversarial resistance starts at Approach 2. Open-questions numbering renumbered monotonically (1-8 ADR-X1, 9-13 ADR-X2, 14-18 ADR-X3, 19-20 cross-cutting) so cross-references in future ADRs aren't ambiguous.

**Reviews convention.** Adds a `reviews/` folder with ADR-scoped filenames (`NNNN.external-review.md`, optionally `NNNN.X.external-review.md` when multiple PRs map to the same ADR). Reviewer-agnostic — Copilot, ChatGPT, human peers all land in the same scheme. CLAUDE.md gains the rule; README.md gains a §Reviews pointer. First review committed: `reviews/0013.external-review.md` (this PR's review). The OAuth security review (`reviews/0015.external-review.md`) is `.gitignore`d for now: it enumerates 7 low/medium findings against `ergodix/oauth.py` / `ergodix/auth.py`, and publishing it before the queued follow-ups merge would hand attackers a code-path roadmap. Will commit alongside the follow-up PR that closes the findings.

## [1.49.0] - 2026-05-10

**Migrate chunk 3c — `migrate_run()` orchestrator.** Stitches the chunk 3a walker + chunk 3b manifest/archive + chunk 2 importer registry into the full migrate run. Public surface: `migrate_run(corpus_root, importer_name, *, docs_service, author, force, check, limit, now_fn, output_fn) -> MigrateResult`. Composes: load latest manifest for re-run idempotency, walk corpus, classify each file, phase 1 (extract markdown via importer), phase 2 (write target + archive source), record manifest. Re-run semantics per ADR 0015 §5: `--force` re-migrates regardless of prior state, prior-hash match → skipped ("unchanged since last run"), prior-hash mismatch → drift-detected (no re-migrate), no prior → migrated. `--check` is a clean dry-run with no filesystem writes. `--limit` caps eligible-file processing. Phase 1 errors record `status="failed"` and continue; the source stays at its original location for re-run. Existing `.md` files in the corpus are silently passed over (not added to the manifest as skipped) so re-run manifests don't accumulate noise — proper "touch frontmatter, leave content" handling per ADR 0015 §2 lands later. 13 new tests covering happy paths (single + nested), `--check`, out-of-scope, `--limit`, phase 1 failure, unchanged re-run, drift detection, `--force` re-migrate, empty corpus, unknown importer, `.ergodix-skip` end-to-end.

## [1.48.0] - 2026-05-10

**Migrate chunk 3b — manifest TOML I/O + archive mover.** Adds the chunk 3b surface to `ergodix/migrate.py`: `Manifest` / `ManifestEntry` dataclasses (frozen, schema version 1) capturing the per-run record locked by ADR 0015 §4, plus `format_run_id`, `manifest_path_for_run`, `archive_path_for`, `write_manifest` (atomic tmp+rename), `read_manifest` (round-trip via stdlib `tomllib`), `find_latest_manifest`, and `move_to_archive` (refuses to overwrite, portable POSIX/Windows behavior). TOML serializer is hand-written rather than pulling in `tomli-w` — small controlled schema, dependency footprint stays minimal. 26 new tests (round-trip, escape handling, empty-files, schema-version rejection, atomic write, archive collision). Chunk 3c is next: `migrate_run()` orchestrator stitching helpers + walker + manifest + archive together with re-run idempotency, two-phase atomicity, and partial-failure recovery.

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
