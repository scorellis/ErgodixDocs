# ADR 0015: `ergodix migrate --from gdocs` — locked decisions

- **Status**: Accepted
- **Date**: 2026-05-09
- **Spike**: [Spike 0012 — `ergodix migrate --from gdocs` design](../spikes/0012-migrate-from-gdocs-design.md)
- **Touches**: [ADR 0001](0001-click-cli-with-persona-floater-registries.md) (CLI subcommand pattern + importer plugin registry), [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) (auth scope policy), [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) (opus naming + fiction-only scope), [ADR 0006](0006-editor-collaboration-sliced-repos.md) (corpus-repo-per-opus topology), [Hierarchy.md](../Hierarchy.md) (opus → compendium → book → section → chapter), `ergodix/auth.py` (Google OAuth flow currently `NotImplementedError`).

## Context

Spike 0012 enumerated the design surface for `ergodix migrate --from gdocs` — Story 0.2's other big task and the next big arc after Story 0.11 closed at 100%. Without migrate, the user can't get their actual prose into the system; it's the gating step between "tooling installed" and any AI co-author feature working against real content.

The CLI subcommand is a stub today (`@main.command(name="migrate")` in `ergodix/cli.py`). This ADR locks the design decisions surfaced in Spike 0012 §"Open questions to resolve in ADR 0015" so implementation can land across multiple PRs without re-litigating the shape.

## Decision

### 1. OAuth UX: paste-the-code, not localhost-redirect

The user runs `ergodix migrate --from gdocs`. If no refresh token exists at `<repo>/.ergodix_tokens.json`, migrate prints the OAuth authorization URL, the user opens it in their browser, signs in, copies the verification code from Google's confirmation page, and pastes it back at the prompt. Migrate exchanges the code for a token pair and persists the refresh token at `<repo>/.ergodix_tokens.json` (mode 600, gitignored per ADR 0001).

**Why paste-the-code over localhost-redirect:** simpler implementation (no temporary HTTP server), no port conflicts, works through SSH / remote sessions where localhost-redirect fails. Copy-paste is one extra step for the user but tolerable for a one-time onboarding action. Revisit if a real user reports friction.

Subsequent runs use the persisted refresh token; access tokens are kept in memory and refreshed on demand. If the refresh token is revoked (user-initiated revocation in their Google account, or Google's own timeout), migrate detects the failure on the next run, deletes the stale tokens file, and re-runs the OAuth dance.

### 2. Source: `.gdoc` primary, `.docx` first-class, others scoped

| Extension | Status | Mechanism |
|---|---|---|
| `.gdoc` | **In scope (primary)** | Docs API extraction — fetch the document via `documents.readonly` |
| `.docx` | **In scope (Scrivener / Word)** | `python-docx` extraction (already a runtime dep in `pyproject.toml`) |
| `.txt` | **In scope (trivial)** | Direct copy with frontmatter prepended |
| `.md` already in target format | **Touched, not migrated** | Frontmatter validated; missing fields filled in; content untouched |
| `.gsheet`, `.gslides` | **Out of scope** | ADR 0005 reframes the project for fiction; spreadsheets and slides aren't part of the corpus model |
| `.gjam`, `.gform`, etc. | Out of scope | Same reasoning |

Folder traversal walks `CORPUS_FOLDER` recursively. Hidden directories (starting with `.`) and OS scratch (`__pycache__`, `.DS_Store`) are skipped. A `.ergodix-skip` marker file in any folder skips that folder and its descendants — gives the user an explicit out for source material they don't want migrated (drafts, private notes, unfinished sub-projects).

### 3. Output: 1:1 hierarchy mirror with provenance frontmatter

**Hierarchy mapping**: 1:1 mirror of source folder structure. The user is responsible for organizing their source folders along the opus → compendium → book → section → chapter model from Hierarchy.md before running migrate. Migrate doesn't infer hierarchy levels from folder depth or filenames.

A future explicit-mapping config (`migrate.toml` declaring which top-level folders are which hierarchy levels) is parking-lot — wait for a real user who needs it.

**Frontmatter** (per ADR 0001 / Story 0.2 format decisions, with migrate-specific provenance fields appended):

```yaml
---
title: "Chapter 3 — The Glass Tower"      # derived from source filename, with hyphen-prettified
author: "Scott R. Ellis"                  # from local_config AUTHOR field, falling back to git config
format: pandoc-markdown
pandoc-extensions: [raw_tex, footnotes, yaml_metadata_block]
source: "Tapestry of the Mind/Book 1/Chapter 3.gdoc"  # relative to CORPUS_FOLDER
migrated_at: "2026-05-09T22:14:00Z"       # ISO 8601 UTC
---
```

The `source` and `migrated_at` fields are migrate-specific provenance — they let the user trace each migrated chapter back to its original. Document in `Hierarchy.md` as "do not remove from migrated chapters."

**Naming convention**: source filename → slug-style target. `"Chapter 3 — The Glass Tower.gdoc"` → `chapter-3-the-glass-tower.md`. Lowercase, spaces → hyphens, em-dash → space → hyphen, ASCII-only. Preserves human readability while staying portable across filesystems and quoting-safe in shell commands.

**Embedded media**: extracted to `_media/<chapter-slug>/` next to the chapter, referenced via Pandoc's standard `![alt text](_media/<chapter>/img-NN.png)` syntax. The `_media/` convention is per-chapter so renaming or moving a chapter takes its media with it.

### 4. Archive: timestamped subfolders + per-run TOML manifest

After successful migration, the original file moves into `<corpus>/_archive/<YYYY-MM-DD-HHMMSS>/<relative-path>`. Re-runs accumulate distinct archive subfolders — no overwrites, no deletions.

A run manifest at `<corpus>/_archive/_runs/<timestamp>.toml` lists every file processed in that run:

```toml
[meta]
version = 1
started_at = "2026-05-09T22:14:00Z"
finished_at = "2026-05-09T22:18:42Z"
generator = "ergodix 0.x.y migrate --from gdocs"
corpus_root = "/Users/scott/My Drive/MyOpus"

[[files]]
source = "Book 1/Chapter 3.gdoc"
target = "Book 1/chapter-3-the-glass-tower.md"
sha256 = "abc123..."        # SHA-256 of the EXTRACTED content (lets re-runs detect drift)
status = "migrated"          # migrated | skipped | failed
size_bytes = 4823

[[files]]
source = "Book 1/Notes.gsheet"
status = "skipped"
reason = "out-of-scope file type"
```

The manifest is the source of truth for "what happened in run X." It also serves as the idempotency anchor for re-runs (see #5).

### 5. Re-run semantics: idempotent by default, `--force` to redo, `--check` for dry-run

**Default re-run**: walks the corpus, consults the most recent run manifest at `_archive/_runs/`, and **skips** any source file whose SHA-256 still matches what was migrated last time. Files added since the last run are migrated. Files modified since the last run are reported as drift (`status="drift-detected"` in the new manifest) and are NOT re-migrated unless `--force` is passed — protects the user from accidentally clobbering edits they made to the migrated `.md` after the fact.

**`--force`**: re-process every file regardless of manifest history. Existing target `.md` files are moved into the new archive subfolder and replaced. The run manifest records the prior target's hash before replacement.

**`--check`**: dry-run. Walks the corpus, prints what would be migrated / skipped / drift-detected, makes no filesystem changes. No manifest written.

**Partial-failure recovery**: each file is migrated in two phases — (1) extract + convert in memory, (2) write target + archive original. If phase 2 fails, the source file stays in place untouched and no target is written; the manifest records `status="failed"` with the error message; the run continues with the next file. Re-run safely retries the failed files.

### 6. CLI surface

```
ergodix migrate --from <importer> [--check] [--force] [--corpus <path>] [--limit N]
```

- `--from <importer>` — required. Importer plugin name (`gdocs`, future `scrivener`, `notion`, etc.).
- `--check` — dry-run. Mutually exclusive with `--force`.
- `--force` — re-process every file regardless of manifest history.
- `--corpus <path>` — override `CORPUS_FOLDER` from `local_config.py`. Useful for testing or migrating a sibling folder before activation.
- `--limit N` — process only the first N matching files. Useful for early validation runs against a large corpus.

The importer plugin pattern (`ergodix/importers/<name>.py` per ADR 0001) keeps `--from` extensible. Each importer module declares the file extensions it recognizes and exposes an `extract(path: Path) -> str` function returning Pandoc Markdown content.

## Consequences

- **`ergodix/auth.py`**: the `get_drive_service` / `get_docs_service` stubs become real, including the OAuth paste-the-code flow + token persistence. C6 (credential prompts) already covers acquiring `google_oauth_client_id` / `google_oauth_client_secret`; ADR 0015 adds the token-exchange and refresh dance on top.
- **`ergodix/importers/`**: new package. First plugin `gdocs.py`; `docx.py` lands in parallel since the walker / manifest infrastructure is shared.
- **`ergodix/migrate.py`**: new module with the walker, manifest writer, archive logic, and re-run idempotency check. The CLI command in `ergodix/cli.py` becomes a thin dispatcher.
- **`ergodix/cli.py`**: replace the `migrate_cmd` stub with the real implementation, including `--check` / `--force` / `--corpus` / `--limit` flags.
- **Tests**: `examples/migrate-fixture/` ships canned `.gdoc` and `.docx` test fixtures so tests run without hitting real Drive (analogous to `examples/showcase/` for render).
- **`local_config.example.py`**: gains an `AUTHOR` field used as the default frontmatter `author:`. Falls back to `git config user.name` if unset.
- **`Hierarchy.md`**: gains a "Migrated frontmatter provenance" subsection documenting the `source` and `migrated_at` fields and the "do not remove" rule.

## Alternatives considered

- **Localhost-redirect OAuth**: rejected for v1. Friendlier UX but adds an HTTP server with port-conflict failure modes; doesn't work over SSH. Paste-the-code is the safer floor.
- **Heuristic hierarchy detection** (folder depth implies opus / compendium / book / etc.): rejected. Heuristics that look right for one corpus structure misclassify another; explicit user control wins. The 1:1 mirror lets the user pre-organize and removes ambiguity.
- **Single archive folder (no per-run timestamping)**: rejected. Would conflate distinct runs; can't tell "what changed in last night's run" without per-run separation. The disk cost of timestamped subfolders is negligible.
- **Aggressive overwrite by default, opt-out via flag**: rejected. The drift-protection default (skip drifted files unless `--force`) is the right safety floor — the user shouldn't lose edits to "I forgot to pass `--no-overwrite`."
- **Embedded media as base64 in frontmatter**: rejected. Bloats the markdown file and breaks Pandoc's standard image syntax. Per-chapter `_media/` directory is the right shape.
- **Multi-file `.gdoc` aggregation**: rejected for v1. One source file → one target file. Authors who keep one chapter per `.gdoc` work directly; authors with one `.gdoc` per Book containing multiple chapters need to either pre-split (Drive-side) or wait for a future "split-on-heading" feature.

## Implementation chunks

Per the smaller-units cadence, implementation lands across multiple PRs:

1. **OAuth flow** — `ergodix/auth.py` `get_drive_service` + `get_docs_service` + paste-the-code dance + token persistence + reauth-on-revocation.
2. **Importer plugin scaffold** — `ergodix/importers/__init__.py` registry, `ergodix/importers/gdocs.py` (Docs API extraction).
3. **Walker + manifest writer** — `ergodix/migrate.py` (corpus walker, slug-namer, frontmatter generator, manifest TOML writer, archive mover).
4. **CLI wiring** — replace `migrate_cmd` stub with real command; add `--check` / `--force` / `--corpus` / `--limit`.
5. **`.docx` importer** — `ergodix/importers/docx.py`. Ships in parallel with #2 once the registry shape is locked.
6. **Embedded-image extraction** — per-importer; touches the walker for `_media/` placement.
7. **Migrate fixture** — `examples/migrate-fixture/` with canned `.gdoc` + `.docx` for hermetic tests.

Each chunk is independently mergeable behind tests.
