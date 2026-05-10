# Spike 0012: `ergodix migrate --from gdocs` — design

- **Date filed**: 2026-05-09
- **Sprint story**: [Story 0.2 — Define canonical repo format](../SprintLog.md#story-02---define-canonical-repo-format) (the corpus-bootstrap half of the story; the other half — the format itself — is locked by ADR 0001 + ADR 0005).
- **ADRs to produce**: ADR 0015 (will lock the design decisions resolved here).
- **Touches**: [ADR 0001](../adrs/0001-click-cli-with-persona-floater-registries.md) (CLI subcommand surface), [ADR 0003](../adrs/0003-cantilever-bootstrap-orchestrator.md) (auth scope policy), [ADR 0005](../adrs/0005-roles-as-floaters-and-opus-naming.md) (opus naming), [ADR 0006](../adrs/0006-editor-collaboration-sliced-repos.md) (corpus repo per opus), [ADR 0014](../adrs/0014-sync-transport-and-settings-cascade.md) (sync transport detection), [Hierarchy.md](../Hierarchy.md) (opus → compendium → book → section → chapter), `ergodix/auth.py` (Google OAuth flow currently `NotImplementedError`).
- **Status**: Open question — design surface enumerated, not yet resolved. ADR 0015 lands when the questions below are settled.

## Question

`ergodix migrate --from gdocs` is the path that turns a Google-Docs-shaped corpus (the way the project's first author has been writing for ~a decade) into the Pandoc-Markdown corpus the rest of ErgodixDocs operates against. Without it, the user can't get their actual prose into the system; it's the gating step between "tooling installed" (Story 0.11 — closed) and "AI co-author working against my work" (every Sprint 1+ feature).

The CLI surface lands as a stub today (`@main.command(name="migrate")` in `ergodix/cli.py`). This spike resolves the design questions before any implementation lands.

The decisions cluster into four themes:

1. **Auth.** Drive / Docs API requires OAuth — the existing `auth.py` has scope policy locked but no token-acquisition flow.
2. **Source.** Which file types get migrated, from which folders, into what target shape?
3. **Output.** Frontmatter, hierarchy mapping, archive layout, naming.
4. **Re-run.** What happens on the second invocation? Idempotency, partial-failure recovery, drift detection.

## Discussion

### 1. Auth — OAuth flow + token storage

**Existing state**: `ergodix/auth.py` has scope constants (`drive.readonly`, `documents.readonly` per ADR 0001), a three-tier credential lookup, and stub `get_drive_service` / `get_docs_service` that raise `NotImplementedError`. C6 (credential prompts) prompts for `google_oauth_client_id` / `google_oauth_client_secret` and stores them in the keyring. The OAuth dance to exchange those for an access + refresh token has not been written.

The OAuth flow:
- Generate auth URL with the locked scopes
- User opens in browser, signs in, copies the auth code (or completes a localhost-redirect callback)
- Code → token via Google's OAuth token endpoint
- Refresh token stored at `<repo_dir>/.ergodix_tokens.json` (mode 600, gitignored — ADR 0001)
- Access token kept in memory; refreshed on demand via the refresh token

**Open considerations:**
- **Localhost-redirect vs. paste-the-code.** Localhost redirect is friendlier UX but requires the migrate command to start an HTTP server briefly. Paste-the-code is simpler to implement; copy-paste from a browser is acceptable for a one-time migrate. Lean toward paste-the-code for v1; revisit if it's painful.
- **Headless / `--ci` users.** Should migrate work non-interactively? The OAuth flow inherently requires a browser session for the first run; subsequent runs use the refresh token. `--ci` users would have to seed the tokens file manually. Acceptable; document.
- **Reauth on token revocation.** If the refresh token is revoked (user-initiated, or Google times it out), migrate detects the failure and re-runs the OAuth dance. The token file replaces, doesn't accumulate.

### 2. Source — which files, which folders

**File types under consideration:**
- `.gdoc` (Google Doc placeholder; the canonical migrate target) — extract via Docs API.
- `.docx` (Word / Scrivener export) — extract via `python-docx` (already a runtime dep per `pyproject.toml`).
- `.txt` plain text — copy-paste-ish; trivial.
- `.md` already in target format — skip if frontmatter already present; touch frontmatter if missing.
- `.gsheet`, `.gslides` — **skip**. ADR 0005 reframes the project for fiction; spreadsheets and slides aren't part of the corpus model.
- Other Drive types (.gjam etc.) — skip.

**Folder traversal:**
- Walk `CORPUS_FOLDER` recursively. Respect any `.ergodix-skip` markers (a parking-lot UX consideration; the user can drop a marker into folders they want migrate to ignore).
- Hidden directories (`._foo`, `.DS_Store`, `__pycache__`) — skip by default.

**Open considerations:**
- **`.docx` from Scrivener.** Scrivener exports vary in shape (per-chapter vs. compiled). Migrate's first cut handles per-chapter `.docx`; compiled multi-chapter `.docx` is parking-lot.
- **Embedded media.** Docs and `.docx` files can have embedded images. Pandoc-Markdown can reference images with `![]()` syntax. Migrate extracts images to `_media/<chapter>/` next to the chapter, references them with relative paths.

### 3. Output — frontmatter, hierarchy, archive

**Frontmatter (per ADR 0001 / Story 0.2 format decisions):**
```yaml
---
title: <derived from source filename>
author: <from local_config or git config>
format: pandoc-markdown
pandoc-extensions: [raw_tex, footnotes, yaml_metadata_block]
source: <relative path to original>
migrated_at: <ISO 8601 UTC>
---
```

The `source` and `migrated_at` fields are migrate-specific provenance — let the user trace each migrated file back to its original. Should they survive subsequent edits? Yes — the user might re-migrate or audit. Document as "do not remove."

**Hierarchy mapping:**
- ADR 0005's hierarchy: opus → compendium → book → section → chapter.
- Migrate's first cut: **1:1 mirror** of source folder structure into the corpus folder. The user is responsible for organizing their source folders along the hierarchy before migrating; migrate doesn't infer levels.
- Future polish: explicit mapping config (e.g., `migrate.toml` declaring "the top-level folder is the opus, second-level are compendia"). Park.

**Archive layout (where originals go after migrate):**
- Per-run timestamped folder: `<corpus>/_archive/<YYYY-MM-DD-HHMMSS>/<relative-path-of-original>`.
- Re-runs accumulate distinct archive subfolders (one per run) — no overwriting, no destruction.
- A `<corpus>/_archive/_runs/<timestamp>.toml` manifest per run lists every file processed (source path, target path, hash, status).

**Naming convention for migrated files:**
- `.gdoc` named "Chapter 3 - The Glass Tower.gdoc" → `chapter-3-the-glass-tower.md`. Slug-style: lowercase, spaces → hyphens, ASCII-only. Preserves human-readable filenames while staying portable across filesystems.
- `.docx` same.
- Existing `.md` files: untouched (frontmatter validated; missing fields filled in).

### 4. Re-run — idempotency, drift, partial failure

**Re-run semantics:**
- Default: re-run is **idempotent** at the per-file level. A previously-migrated file is detected (via the `_archive/_runs/<timestamp>.toml` manifest history + content hash) and skipped.
- `--force`: re-process everything regardless of prior runs. Existing target `.md` files are *replaced*; the existing target is moved into the archive subfolder for the new run.
- `--check`: dry-run mode. Walks the corpus, reports what would be migrated, makes no changes.

**Drift detection:**
- The first call after the v1 `_archive/_runs/` infrastructure ships is the baseline.
- Subsequent runs compare each source file's hash to the stored hash from the prior run. Unchanged → skip. Changed → re-migrate (under `--force` semantics).
- This dovetails with the [`ergodix index` parking-lot story](../SprintLog.md#story--ergodix-index--ergodixmap-corpus-content-index-near-term--after-b2) (the `_AI/ergodix.map` file). The migrate manifest and the AI-index both want per-file hashes; they could share infrastructure. Decide at activation.

**Partial-failure recovery:**
- Migrate runs in **two phases per file**: (1) extract + convert in memory, (2) write target + archive original atomically.
- If phase 2 fails (disk full, permission denied, interrupt), the source file stays in place and no target is written. Re-run safely retries.
- If phase 1 fails (Drive API error, parse error), the file is logged in the run manifest with `status="failed"` and the run continues. The user gets a summary at the end with the failed files; they can fix and retry.

### 5. CLI surface

```
ergodix migrate --from gdocs [--check] [--force] [--corpus <path>] [--limit N]
```

- `--from gdocs`: required; the importer name (per ADR 0001's plugin-registry pattern in `ergodix/importers/`).
- `--check`: dry-run.
- `--force`: re-process already-migrated files.
- `--corpus <path>`: override `CORPUS_FOLDER` from local_config (useful for testing or migrating a sibling folder before activation).
- `--limit N`: process only the first N files. Useful for early validation runs against a partial corpus.

Future importers: `--from scrivener`, `--from notion`, etc. The `ergodix/importers/<name>.py` plugin pattern (per ADR 0001) keeps this extensible — each importer module declares the file-types it recognizes and the extraction function.

## Open questions to resolve in ADR 0015

1. **OAuth UX**: paste-the-code (simpler) vs. localhost-redirect (friendlier). Lean: paste-the-code for v1.
2. **Hierarchy mapping**: 1:1 mirror (simpler) vs. explicit config (more flexible). Lean: 1:1 mirror; config is parking-lot.
3. **Archive layout**: timestamped subfolders + per-run manifest. Lean: yes, with the manifest TOML schema locked in the ADR.
4. **Idempotency mechanism**: rely on `_archive/_runs/*.toml` manifests + content hashes. Future-cross-reference: `_AI/ergodix.map` is the parallel index; share schema where possible.
5. **`.docx` support in v1?** Scrivener exports are common for fiction authors. Lean: yes — `python-docx` is already a dep.
6. **Embedded image handling**: extract to `_media/<chapter>/`, reference with relative paths. Lean: yes.
7. **Partial-failure UX**: log per-file in the run manifest; summary report at end. Lean: yes.
8. **`--check` / `--force` / `--limit`**: include in v1. Lean: yes (each is small, each closes a real workflow gap).

## Implementation chunks (post-ADR)

The implementation lands across multiple PRs after ADR 0015:

1. **OAuth flow** (`ergodix/auth.py` `get_drive_service` + `get_docs_service`). Includes the localhost redirect or paste-the-code dance, token persistence at `<repo>/.ergodix_tokens.json`.
2. **Importer plugin scaffold** (`ergodix/importers/__init__.py` registry + `ergodix/importers/gdocs.py` first plugin).
3. **Walker + manifest writer** (`ergodix/migrate.py` — walks corpus, dispatches to importer, writes archive + manifest).
4. **CLI wiring** (replace `ergodix/cli.py`'s `migrate_cmd` stub with the real command + flags).
5. **`.docx` importer** (`ergodix/importers/docx.py`). Could land in parallel with the `gdocs` importer; both consume the same walker / manifest infrastructure.
6. **Embedded-image extraction** (per-importer; touches the walker for `_media/` placement).
7. **Smoke fixture** at `examples/migrate-fixture/` analogous to `examples/showcase/` — small canned `.gdoc`s for testing without hitting real Drive.

Each chunk is a separate PR per the smaller-units cadence.

## Cross-references

- [Spike 0010 — UserWritingPreferencesInterview](0010-user-writing-preferences-interview.md): the post-migrate onboarding flow assumes the corpus is already migrated. Sequence: migrate → interview → first Plot-Planner / Continuity-Engine tool runs.
- [`ergodix index` + `_AI/ergodix.map` parking-lot story](../SprintLog.md): shares hash-based content-tracking infrastructure with migrate's manifest. Cross-pollinate when both activate.
- [ADR 0014 — sync transport](../adrs/0014-sync-transport-and-settings-cascade.md): migrate runs against `CORPUS_FOLDER` regardless of whether sync transport is drive-mirror or indy. The detected mode doesn't change migrate's behavior — both modes have the same source files at the same path.
