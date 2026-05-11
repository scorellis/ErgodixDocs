# Consuming `ergodix.map` — the read API for downstream tools

This document is for authors of **downstream tools** that read the corpus
content index — Continuity-Engine, Plot-Planner, the future MCP server, any
ergodite that needs to know "which chapters changed since I last looked." It
is not for end users; if you're an author looking to produce the map, run
`ergodix index` (see the [stories/active/ergodix-index.md](../stories/active/ergodix-index.md)
story and [ADR 0016](../adrs/0016-ergodix-index-design.md)).

## What the map is

`<corpus>/_AI/ergodix.map` is the **content index** for the corpus: a TOML
file recording one entry per indexable file (chapters + preambles), each
carrying the file's SHA-256 hash, size, mtime, and POSIX-relative path. It's
regenerated on demand by `ergodix index`.

It exists for one reason: so incremental analyses don't re-tokenize the whole
opus on every run. With a map, a tool that previously analyzed the corpus
can diff its prior view (the map it saw last) against the current state and
only re-process the chapters whose `sha256` changed. Without a map, every
continuity-check pass on a 1M-word corpus re-pays the full tokenization cost.

The map's place in the ecosystem is established by [ADR 0016 §9](../adrs/0016-ergodix-index-design.md):
the `_AI/` namespace is the project-wide canonical location for AI-emitted
artifacts. Every tool that scans the corpus reads the map first.

## The read API — `read_map(path)`

**Read via the Python helper, never the raw TOML.** This is the API contract
locked by [ADR 0016 §7](../adrs/0016-ergodix-index-design.md). It exists for
two reasons:

1. **Schema evolution survives.** If the map's schema ever moves beyond
   `version = 1`, `read_map` translates back to the consumer's expected
   shape (or raises clearly). Tools that parsed the TOML directly would
   silently consume a malformed record.
2. **Strict version refusal is uniform.** `read_map` raises `ValueError` on
   an unknown / missing schema version, so a corrupted or future-version
   map never produces a half-interpreted `Map` object that fails cryptically
   downstream.

```python
from ergodix.index import read_map

m = read_map(corpus_root / "_AI" / "ergodix.map")
# m is a Map dataclass (see Data shape, below).
```

`read_map` raises:

- `FileNotFoundError` — the map doesn't exist. Most consumers will treat
  this as "no prior state; everything is new" and proceed with an empty
  `Map`.
- `ValueError` — schema version mismatch, missing `[meta]` block, or
  missing required fields. Surface the error to the user; do not paper over
  it.

## Data shape

```python
@dataclass(frozen=True)
class IndexEntry:
    path: str            # POSIX-relative to corpus_root.
    sha256: str          # Lowercase hex digest. Authoritative for drift.
    size_bytes: int
    mtime: str           # ISO-8601 UTC. Advisory only (ADR 0016 §3).

@dataclass(frozen=True)
class Map:
    version: int         # Currently 1.
    generated_at: str    # ISO-8601 UTC. When the map was written.
    generator: str       # e.g. "ergodix 1.x.y index".
    corpus_root: str     # Absolute path of the corpus this map describes.
    files: tuple[IndexEntry, ...]
```

Both dataclasses are **frozen** — mutating an entry after `read_map` returned
it is not part of the contract.

### What you can rely on

- **`sha256` is authoritative for drift.** Two entries with the same `sha256`
  represent the same content, regardless of `mtime` or `size_bytes`.
  ([ADR 0016 §3](../adrs/0016-ergodix-index-design.md).)
- **`path` is POSIX, not host-OS.** A map produced on macOS and consumed on
  Linux uses the same path strings. Construct full paths with
  `Path(map.corpus_root) / entry.path`.
- **`files` is sorted by `path`.** Re-runs of `ergodix index` on the same
  corpus state produce byte-identical maps (modulo `generated_at`).
- **The schema version is locked at 1.** Future schema changes require an
  ADR and a code update; `read_map` will refuse to interpret a `version`
  it doesn't recognize.

### What you should NOT rely on

- **Filesystem `mtime`s match `entry.mtime`.** `mtime` is recorded for
  diagnostic value, but it's advisory only. Don't use it for change
  detection.
- **`size_bytes` indicates anything by itself.** Two files of the same
  size can differ; rely on `sha256` for equivalence.
- **The map is fresh.** It's a snapshot of the moment `ergodix index` ran.
  If the user edits files outside `ergodix`, the map goes stale. Tools that
  need certainty should re-run `ergodix index --check` (or build a fresh
  `Map` themselves and call `compare_to_map`).

## The incremental pattern — `compare_to_map`

The drift-detection helper consumes two `Map` objects (the prior view +
the current state) and returns a `DriftReport`:

```python
from ergodix.index import (
    Map,
    build_map_entry,
    compare_to_map,
    read_map,
    walk_corpus_for_index,
)

# 1. Load your tool's last-known view of the corpus.
try:
    prior = read_map(corpus_root / "_AI" / "ergodix.map")
except FileNotFoundError:
    prior = Map(
        version=1,
        generated_at="",
        generator="",
        corpus_root="",
        files=(),
    )

# 2. Build a current Map without writing it (cheap walk + hash).
current_entries = tuple(
    sorted(
        (
            build_map_entry(corpus_root=corpus_root, file_path=p)
            for p in walk_corpus_for_index(corpus_root)
        ),
        key=lambda e: e.path,
    )
)
current = Map(
    version=1,
    generated_at="",
    generator="my-tool",
    corpus_root=str(corpus_root),
    files=current_entries,
)

# 3. Compute drift.
report = compare_to_map(existing=prior, current=current)

# 4. Re-analyze only the files that changed.
for path in report.new_files + report.changed_files:
    reanalyze(corpus_root / path)

# 5. Forget cached analyses for removed files.
for path in report.removed_files:
    drop_cache(path)
```

`DriftReport` (frozen):

- `new_files: tuple[str, ...]` — paths in `current` not in `prior`.
- `changed_files: tuple[str, ...]` — paths in both with different `sha256`.
  Per ADR 0016 §3: `mtime` differences alone are NOT drift.
- `removed_files: tuple[str, ...]` — paths in `prior` not in `current`.
- `has_drift: bool` (property) — True iff any bucket is non-empty.

Each bucket is sorted; the report is deterministic given fixed input.

## Where downstream tool output goes

Per [ADR 0016 §9](../adrs/0016-ergodix-index-design.md), all AI-emitted
artifacts live under `<corpus>/_AI/`, organized by tool:

```
<corpus>/_AI/
├── ergodix.map                       (this file — produced by ergodix index)
├── continuity-engine/
│   ├── timeline-runs/
│   │   └── 2026-05-11T14:30:00Z.toml
│   └── plot-hole-flags/
│       └── …
└── plot-planner/
    └── scoring-runs/
        └── …
```

Each tool documents its own retention + gitignore posture in its companion
ADR. The map itself is **tracked** in git (ADR 0016 §4); tool caches that
are genuinely ephemeral may be individually gitignored under their tool
subdirectory.

## Quick reference

| Need | Use |
|---|---|
| Load the current map | `read_map(corpus_root / "_AI" / "ergodix.map")` |
| Build a current Map without writing | `walk_corpus_for_index` + `build_map_entry` |
| Compare two Maps | `compare_to_map(existing=…, current=…)` |
| Check if anything changed | `report.has_drift` |
| Get list of changed files | `report.new_files + report.changed_files` |
| Detect a removed file | `report.removed_files` |
| Write a map (rare; `ergodix index` is the normal producer) | `write_map(map_data, path)` |

## Related

- [ADR 0016 — `ergodix index` design](../adrs/0016-ergodix-index-design.md):
  the locked decisions this doc references throughout.
- [Spike 0015 — design surface](../spikes/0015-ergodix-index-design.md):
  the design discussion that led to ADR 0016.
- [Continuity-Engine parking-lot story](../stories/parking-lot/continuity-engine.md):
  the first major downstream consumer.
- [Plot-Planner parking-lot story](../stories/parking-lot/plot-planner.md):
  second consumer; relies on the same incremental pattern.
- [ADR 0015 — migrate manifest](../adrs/0015-migrate-from-gdocs.md):
  conceptually adjacent (per-file `sha256`, schema-version refusal). The
  manifest is migrate's per-run record; the map is the corpus's living view.
