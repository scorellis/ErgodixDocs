# Spike 0015: `ergodix index` + `_AI/ergodix.map` — corpus content index

- **Date filed**: 2026-05-10
- **Sprint story**: First Sprint 1 implementation arc. The parking-lot entry in [SprintLog.md](../SprintLog.md) ("ergodix index + _AI/ergodix.map: corpus content index, near-term — after B2") is now activated.
- **ADRs to produce**: ADR 0016 will lock the schema + activation decisions resolved here.
- **Touches**: [ADR 0001](../adrs/0001-click-cli-with-persona-floater-registries.md) (CLI subcommand surface), [ADR 0005](../adrs/0005-roles-as-floaters-and-opus-naming.md) (no role gating; index runs under any floater), [ADR 0006](../adrs/0006-editor-collaboration-sliced-repos.md) (sharing the map across collaborators), [ADR 0013](../adrs/0013-ai-permitted-actions-boundary.md) (the map is tooling metadata, not corpus content — boundary preserved), [ADR 0014](../adrs/0014-sync-transport-and-settings-cascade.md) (the map respects sync-transport conventions for paths), [ADR 0015](../adrs/0015-migrate-from-gdocs.md) (the manifest's per-file SHA-256 shares conceptual ground with the index).
- **Status**: Open — design surface enumerated, not yet resolved. ADR 0016 follows when the questions below settle.

## Question

`ergodix index` is the corpus-content index that lets incremental AI tools (Plot-Planner, Continuity-Engine, scoring, future MCP-server consumers) diff "what changed since I last looked" against "everything." Without it, every Sprint 1 tool that operates over the corpus re-tokenizes the entire opus on every run — burning API spend and wall-clock time linearly with corpus size.

It's also the load-bearing dependency under the "multidimensional mind map" the project's longer arc points at: per-file content hashes are the join key against which plotline / character / conversation / location indexes can later be built without each tool reinventing a corpus-walker.

This spike resolves the design surface before any code lands. ADR 0016 will lock the decisions.

## Discussion

The decisions cluster into five themes.

### 1. Schema — TOML, versioned, human-readable

The map lives at `<corpus>/_AI/ergodix.map`. TOML for the same reasons migrate's manifest is TOML (ADR 0015 §4): human-readable, stdlib parser, schema versioning trivial.

```toml
[meta]
version = 1
generated_at = "2026-05-10T22:14:00Z"
generator = "ergodix 1.x.y index"
corpus_root = "/Users/scott/My Drive/Tapestry of the Mind"

[[files]]
path = "Book 1/Chapter 3.md"
sha256 = "abc123..."
size_bytes = 4823
mtime = "2026-05-09T18:42:11Z"

[[files]]
path = "_preamble.tex"
sha256 = "def456..."
size_bytes = 612
mtime = "2026-04-30T12:00:00Z"
```

Per-file fields: path (POSIX relative to corpus_root), sha256 (lowercase hex of file bytes), size_bytes, mtime (ISO-8601 UTC). `mtime` is opportunistic — included for diagnostic value, not relied on for change-detection (hash is authoritative).

**Open question:** add a `kind` field per file (chapter / preamble / other)? Lean: no. The file's path and extension carry the kind information; adding a redundant field is over-engineering for v1.

### 2. Scope — which files to index

Walk `CORPUS_FOLDER` (same walker rules as migrate's `walk_corpus` per ADR 0015 §3):

- **Include**: `*.md`, `_preamble.tex`, any other `*.tex` (custom preambles at sub-folders per ADR 0001).
- **Exclude**: hidden files / dirs (`.git`, `.DS_Store`, etc.), `_archive/` (migrate's archive layout), `__pycache__`, `node_modules`, and any folder containing a `.ergodix-skip` marker.
- **Out of scope for v1**: images under `_media/` (binary; tools that care about images can re-scan them; the index is for prose-and-preamble change detection).
- **Skipped silently**: `.gdoc` / `.gsheet` Drive placeholders if any remain post-migrate (those are pre-migrate artifacts, not corpus content).

Reuse `ergodix.migrate.walk_corpus` if its filter shape is a clean fit; otherwise factor a small `corpus_walker.py` helper both modules call. Lean: factor when chunk 1 of impl shows real coupling pressure; until then, duplicate the small loop.

### 3. Location — `_AI/` namespace + tracked or not?

ADR convention: AI-emitted artifacts live under `_AI/` at the corpus root (mentioned in [Continuity-Engine parking-lot story](../SprintLog.md)). The map lives at `<corpus>/_AI/ergodix.map`.

**Tracked or gitignored?** The parking-lot story leans tracked, with conflicts auto-resolving by re-running `ergodix index`. Confirm:

- Pros of tracked: collaborators see the same baseline; reviewing index drift is a git-diff away; the map is portable across machines.
- Pros of gitignored: no merge conflicts, no diff noise on every prose edit.
- **Lean: tracked.** Merge conflicts on the map are real but recoverable (re-run `ergodix index`); the audit value of "what was the corpus state at this commit?" outweighs the conflict friction. Sliced editor repos (ADR 0006) carry their own copy of the map regenerated at sync time.

### 4. CLI surface

```
ergodix index [--check] [--corpus <path>] [--quiet]
```

- `--check`: dry-run. Walks the corpus, computes hashes, compares to the existing `_AI/ergodix.map`. Reports drift (new / changed / removed files). Makes no filesystem changes. **Mirrors migrate's `--check`.**
- `--corpus <path>`: override `CORPUS_FOLDER` from `local_config.py`. Mirrors migrate.
- `--quiet`: suppress per-file output; print only the summary line. Useful for AI tools that want to re-run index programmatically.

Exit codes: 0 = no drift detected (or, in non-check mode, map updated). 1 = drift detected (in `--check` mode only; in non-check mode, drift is fine — we update the map). 2 = bad invocation (mutex violation, missing corpus, etc.). Matches migrate's exit-code conventions.

### 5. Re-run semantics

Default behavior is "regenerate from scratch" — walks the corpus, computes all hashes, writes a new map. Idempotent: re-running on an unchanged corpus produces a byte-identical map (modulo the `generated_at` timestamp).

**Open question:** is per-file hash caching worth the complexity? A 10k-chapter corpus is ~10 MB; hashing it from cold takes <1 second on a modern laptop. Lean: no caching for v1. If we ever index a 100x-larger corpus and re-run becomes painful, add an mtime-keyed cache then.

## Open questions to resolve in ADR 0016

1. **Schema version field's semantics.** Like migrate's manifest (ADR 0015 §4), the map declares `version = 1` and refuses to interpret an unknown version. Confirm.
2. **`kind` field per file** — yes or no? Lean: no for v1.
3. **`mtime` as advisory only** (hash is authoritative) — confirm.
4. **Tracked vs. gitignored.** Lean: tracked. Confirm and document the conflict-recovery flow.
5. **Walker factoring** — reuse `ergodix.migrate.walk_corpus` or factor `corpus_walker.py`? Resolve at chunk-1 impl time, not pre-emptively.
6. **`--check` exit code 1 on drift** — confirm. Mirrors migrate's failure-exit convention.
7. **First consumer interface.** The Continuity-Engine story is the leading consumer. The map's per-file `sha256` is the API surface they read; document that any downstream consumer reads only via `read_map()` (Python helper to be authored alongside `write_map()`), never via direct TOML parsing.
8. **Sliced-editor-repo behavior** — does `ergodix sync-out` carry the map into the editor's slice, or does the editor regenerate locally? Lean: editor regenerates locally; the map is a per-machine, per-corpus-state artifact, not a piece of the corpus itself.
9. **`_AI/` namespace convention** — document this as the canonical place for AI-emitted artifacts (continuity reports, scoring runs, future Plot-Planner outputs) so every Sprint 1+ tool follows the same rule.

## Implementation chunks

Per the smaller-units cadence (one PR per chunk):

1. **Helpers** (`ergodix/index.py`): pure functions — `compute_sha256_of_file`, `walk_corpus_for_index` (or refactor migrate's walker), `build_map_entry`, `serialize_map_toml`, `parse_map_toml`, schema constants. Round-trip tests; no FS orchestration. Mirrors migrate chunk 3a's shape.
2. **`generate_index` orchestrator**: walks the corpus, builds the `Map`, writes `_AI/ergodix.map` atomically (tmp + rename), returns a summary record. Tests against a tmp-corpus fixture.
3. **`compare_to_map` + drift report**: given an existing map and a fresh walk, compute new / changed / removed file sets. Tests.
4. **CLI wiring**: replace any stub with the real `ergodix index` command. Flags `--check` / `--corpus` / `--quiet`. Exit codes per §4.
5. **Migrate-fixture extension**: add a `_AI/ergodix.map` to the migrate fixture (or a separate `examples/index-fixture/`) so the hermetic e2e tests cover the index path end-to-end alongside migrate.
6. **First consumer doc**: a small `docs/ergodix-map-consumers.md` documenting the read API + per-file shape, so Plot-Planner / Continuity-Engine designers don't reinvent the parsing.

Each chunk is independently mergeable behind tests.

## Cross-references

- [SprintLog.md — `ergodix index` parking-lot story](../SprintLog.md): the activated story.
- [ADR 0015 §4 — migrate manifest schema](../adrs/0015-migrate-from-gdocs.md): conceptually adjacent (per-file sha256, atomic-write pattern, schema-version refusal). Reuse what makes sense.
- [Continuity-Engine parking-lot story](../SprintLog.md): the first downstream consumer of the map.
- [Plot-Planner parking-lot story](../SprintLog.md): second consumer.
- [Spike 0013 §C ergodite plugin registry](0013-style-sentinel-and-certificate.md): future ergodites that scan the corpus all read the map first.

## Why now

The migrate arc closing (chunks 1-7 + 6b on main as of 2026-05-10) and CI on GitHub (PR #86 + #87) both unblock the next major arc. The user's earlier framing: "Sprint 1 story is the load-bearing remaining piece for v1.0." `ergodix index` is the smallest Sprint-1 story that ships a real, user-runnable feature AND unblocks every subsequent Sprint 1 tool — it's the right starting move.
