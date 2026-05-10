# ADR 0016: `ergodix index` + `_AI/ergodix.map` — locked decisions

- **Status**: Accepted
- **Date**: 2026-05-10
- **Spike**: [Spike 0015 — `ergodix index` + `_AI/ergodix.map` design](../spikes/0015-ergodix-index-design.md)
- **Touches**: [ADR 0001](0001-click-cli-with-persona-floater-registries.md) (CLI subcommand surface), [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) (no role gating — index runs under any floater), [ADR 0006](0006-editor-collaboration-sliced-repos.md) (sharing the map across collaborators), [ADR 0013](0013-ai-permitted-actions-boundary.md) (the map is tooling metadata, not corpus content — boundary preserved), [ADR 0014](0014-sync-transport-and-settings-cascade.md) (the map respects sync-transport conventions for paths), [ADR 0015](0015-migrate-from-gdocs.md) (the manifest's per-file SHA-256 shares conceptual ground with the index).

## Context

`ergodix index` is the corpus-content index that lets incremental AI tools (Plot-Planner, Continuity-Engine, scoring, future MCP-server consumers) diff "what changed since I last looked" against "everything." Without it, every Sprint 1 tool that operates over the corpus re-tokenizes the entire opus on every run.

Spike 0015 enumerated the design surface and resolved most of it directly; nine items were left as explicit "open questions to resolve in ADR 0016." This ADR locks them. Implementation lands across chunks 1–6 (Spike 0015 §"Implementation chunks").

## Decision

### 1. Schema version field — strict refusal on unknown version

The map declares `version = 1` in its `[meta]` block. A reader encountering an unknown version raises a clear error and refuses to interpret the file — same posture as migrate's manifest ([ADR 0015 §4](0015-migrate-from-gdocs.md)). Forward-compatibility is not a v1 concern: we'd rather force a deliberate code change when the schema evolves than silently treat an old reader's interpretation as authoritative on a newer file.

### 2. No `kind` field per file

Spike 0015 §1's "open question" — leaning no — is **locked: no**. The file's path and extension carry the kind information (chapter `.md`, `_preamble.tex`, custom `*.tex`). Adding a redundant field is over-engineering for v1. Downstream consumers that need to filter by kind derive it from `path`.

### 3. `mtime` is advisory only; SHA-256 is authoritative

The per-file `mtime` field exists for diagnostic value (humans inspecting the map ask "when did this last change?") and is **not** consulted by drift-detection. Two files with different `mtime` but identical `sha256` are equivalent. Two files with identical `mtime` but different `sha256` are different. This matches migrate's manifest semantics.

### 4. Tracked in git (not gitignored); conflicts auto-recover via re-run

The map lives at `<corpus>/_AI/ergodix.map` and is **tracked** in the corpus repo. Merge conflicts on the map are real but recoverable: re-running `ergodix index` regenerates from the actual filesystem state, discarding both sides of any textual merge. The audit value of "what was the corpus state at this commit?" outweighs the conflict friction.

Sliced editor repos ([ADR 0006](0006-editor-collaboration-sliced-repos.md)) carry their own copy of the map regenerated at sync time; see decision §8.

### 5. Walker factoring — resolve at chunk-1 impl, not pre-emptively

Spike 0015 §2's open question on whether to reuse `ergodix.migrate.walk_corpus` or factor a shared `corpus_walker.py` helper is **deferred to implementation**: chunk 1 lands a duplicate of the small loop. If the loop grows non-trivially during chunks 2–4, refactor to `corpus_walker.py` and call from both modules. The lean against pre-emptive factoring is deliberate — premature abstraction is the bigger risk than mild duplication.

### 6. `--check` exits 1 on drift

`ergodix index --check` walks the corpus, computes hashes, compares to the existing `_AI/ergodix.map`, prints a drift report (new / changed / removed files), and exits **1** if any drift is found, **0** if the map is current. Mirrors migrate's `--check` exit-code convention exactly. CI uses this: `ergodix index --check` in a check-only step fails the PR if the map is stale.

Non-`--check` mode never exits 1 on drift — it's expected to find drift and the whole purpose of the run is to rewrite the map.

### 7. First-consumer interface — read via a Python helper, never raw TOML

Downstream consumers (Continuity-Engine, Plot-Planner, future MCP server) read the map via a `read_map(path) -> Map` helper authored alongside `write_map(map, path)`. The helper handles schema-version refusal, path resolution, and the eventual hash-cache fast path; consumers never parse the TOML themselves. This is the API surface that survives schema evolution — if `version = 2` adds fields, `read_map` translates back to the consumer's expected shape (or fails loudly).

The per-file `sha256` is the load-bearing field consumers actually use. Everything else (`mtime`, `size_bytes`) is diagnostic.

### 8. Sliced-editor-repo behavior — editor regenerates locally

The map is **not** carried by `ergodix sync-out` into the editor's sliced corpus repo ([ADR 0006](0006-editor-collaboration-sliced-repos.md)). The editor's slice contains corpus *content*; the map is *tooling metadata* derived from that content. The editor's first `ergodix index` run after sync-in regenerates the map locally against their slice.

Reason: the editor's slice is a subset of the full corpus (per ADR 0006's slicing), so the writer's map references files the editor doesn't have. Carrying it would either confuse the editor's tools (broken references) or force a "filter to slice" step that's more complex than just regenerating.

### 9. `_AI/` namespace is canonical for AI-emitted artifacts

This ADR documents the project-wide convention that **all AI-emitted artifacts** — `ergodix.map`, future Continuity-Engine continuity reports, Plot-Planner scoring runs, MCP-server caches — live under `<corpus>/_AI/` at the corpus root. Subfolders organize by tool (`_AI/continuity-engine/`, `_AI/plot-planner/`, etc.); the map is the only top-level `_AI/` file because every other tool reads it.

The `_AI/` namespace is tracked in git by default (the audit value applies to every artifact, not just the map), but tools may write to `_AI/<tool>/cache/` paths that are individually gitignored if the cache is genuinely ephemeral. Each tool documents its own retention/gitignore posture in its companion ADR.

This codifies an implicit convention that's been growing across the parking-lot stories ([continuity-engine](../stories/parking-lot/continuity-engine.md), [plot-planner](../stories/parking-lot/plot-planner.md), [skill-factory-seal-protection](../stories/parking-lot/skill-factory-seal-protection.md)).

## Consequences

- Spike 0015's six implementation chunks become a linear PR sequence: helpers → orchestrator → drift comparison → CLI wiring → fixture extension → consumer doc. Each is small enough for the smaller-units cadence.
- Continuity-Engine, Plot-Planner, and any future tool that scans the corpus depends on the `_AI/` convention. Worth documenting once in this ADR rather than re-deciding per tool.
- Tracked-in-git is a deliberate cost: every prose-edit PR will touch the map. Acceptable because conflict-recovery is "re-run `ergodix index`."
- The `read_map` helper is the public API surface. Schema evolution beyond `version = 1` requires updating the helper, but consumers stay unchanged.

## Open follow-ups

- The hash-cache decision (Spike 0015 §5, leaning "no caching for v1") is **not** an open question for ADR 0016 — it was already resolved in the spike. Re-open as a separate ADR if corpus size ever makes cold-hashing painful.
- The first-consumer ADR (Continuity-Engine or Plot-Planner) will reference this ADR for its `_AI/` namespace placement; no follow-up needed here.
