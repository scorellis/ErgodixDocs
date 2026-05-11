"""Pure helpers for `ergodix index` (Spike 0015 / ADR 0016).

This module is chunk 1 of the index implementation arc — pure functions
only, no FS orchestration. The orchestrator (chunk 2) composes these
into the user-facing `generate_index()`; drift comparison (chunk 3)
composes them with `read_map()`; CLI wiring (chunk 4) glues it all to
the `ergodix index` subcommand.

Exposed surface:

  * MAP_SCHEMA_VERSION         — locked at 1 per ADR 0016 §1.
  * IndexEntry                  — frozen dataclass; one entry per file.
  * Map                         — frozen dataclass; the full map shape.
  * compute_sha256_of_file      — lowercase hex SHA-256 over file bytes.
  * walk_corpus_for_index       — yields indexable file paths per
                                  Spike 0015 §2 (.md / _preamble.tex /
                                  *.tex; skip hidden / _archive /
                                  __pycache__ / node_modules / _media /
                                  .gdoc / .gsheet / .ergodix-skip-scoped).
  * build_map_entry             — file path → IndexEntry (sha256 + size +
                                  mtime + POSIX-relative path).
  * serialize_map_toml          — Map → TOML text in the schema fixed
                                  by ADR 0016 §1 (single `[meta]` block,
                                  one `[[files]]` array entry per file).
  * parse_map_toml              — TOML text → Map; strict refusal on
                                  unknown / missing version per
                                  ADR 0016 §1.

The walker duplicates the small `_walk` loop from ergodix.migrate per
ADR 0016 §5 ("duplicate the small loop first, refactor to
`corpus_walker.py` only when chunks 2-4 show real coupling pressure").
The two walkers diverge in scope (migrate hands off to importer
registry; index has a fixed extension allowlist) so factoring up-front
would have been premature.
"""

from __future__ import annotations

import hashlib
import os
import tomllib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ergodix.version import __version__

MAP_SCHEMA_VERSION: int = 1
"""ADR 0016 §1: v1 schema is locked at version = 1. Readers refuse
unknown versions and raise ValueError. Forward-compatibility is a
deliberate non-goal for v1 — schema evolution requires a code change."""


_INDEXABLE_SUFFIXES: frozenset[str] = frozenset({".md", ".tex"})
"""Spike 0015 §2 walker scope. .md is the chapter format. .tex covers
_preamble.tex and any sub-folder custom preambles. Anything else (images
under _media/, .gdoc / .gsheet placeholders, etc.) is silently
skipped."""


_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        "_AI",
        "_archive",
        "_media",
        "__pycache__",
        "node_modules",
    }
)
"""Spike 0015 §2 directory excludes. _AI holds the index's own output
plus future tool outputs (Continuity-Engine reports, Plot-Planner runs);
indexing it would create a self-referential update loop. _archive holds
migrate's preserved originals; _media holds chapter images (binary, out
of scope for v1); __pycache__ / node_modules are scratch."""


# ─── Dataclasses ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class IndexEntry:
    """One file in the corpus map.

    Per ADR 0016 §1 schema:
        path        POSIX-relative to corpus_root.
        sha256      Lowercase hex digest of file bytes. Authoritative.
        size_bytes  File size in bytes.
        mtime       ISO-8601 UTC mtime. Advisory only (ADR 0016 §3) —
                    hash, not mtime, decides drift.
    """

    path: str
    sha256: str
    size_bytes: int
    mtime: str


@dataclass(frozen=True)
class Map:
    """The full corpus map.

    Per ADR 0016 §1 schema:
        version       MAP_SCHEMA_VERSION (currently 1).
        generated_at  ISO-8601 UTC timestamp of the run that produced it.
        generator     Human-readable producer identifier
                      (e.g. "ergodix 1.x.y index").
        corpus_root   Absolute path to the corpus root the walker ran
                      against. Recorded for diagnostic value.
        files         Tuple of IndexEntry, one per indexable file.
                      Tuple (not list) so Map remains hashable.
    """

    version: int
    generated_at: str
    generator: str
    corpus_root: str
    files: tuple[IndexEntry, ...]


# ─── compute_sha256_of_file ─────────────────────────────────────────────────


def compute_sha256_of_file(path: Path) -> str:
    """Lowercase hex SHA-256 over the file's raw bytes.

    Streams the file in 64 KiB chunks so the helper works on the rare
    multi-megabyte chapter (or, in the future, on the cumulative
    `_AI/` artifacts the index may also hash).
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ─── walk_corpus_for_index ──────────────────────────────────────────────────


def walk_corpus_for_index(corpus_root: Path) -> Iterator[Path]:
    """Walk a corpus tree and yield every indexable file.

    Yielded: regular files whose suffix is in `_INDEXABLE_SUFFIXES`
    (.md / .tex), excluding everything below a hidden file, a hidden
    directory, a `_SKIP_DIR_NAMES`-named directory, or a directory
    containing a `.ergodix-skip` marker.

    Iteration order is filesystem-defined; callers that need stable
    ordering should sort the result themselves (the orchestrator does
    so before serializing).
    """
    root = corpus_root.resolve()
    yield from _walk(root)


def _walk(current: Path) -> Iterator[Path]:
    if not current.is_dir():
        return
    if (current / ".ergodix-skip").exists():
        return

    for entry in current.iterdir():
        name = entry.name
        if name.startswith("."):
            continue
        if entry.is_dir():
            if name in _SKIP_DIR_NAMES:
                continue
            yield from _walk(entry)
            continue
        if not entry.is_file():
            continue
        if entry.suffix in _INDEXABLE_SUFFIXES:
            yield entry


# ─── build_map_entry ────────────────────────────────────────────────────────


def build_map_entry(*, corpus_root: Path, file_path: Path) -> IndexEntry:
    """Build one IndexEntry for ``file_path`` relative to ``corpus_root``.

    The caller is responsible for ensuring ``file_path`` is within
    ``corpus_root`` (the walker guarantees this; direct callers should
    too). Path stored as POSIX-style ("Book 1/Chapter 1.md") regardless
    of host OS, so the map is portable across machines per ADR 0016 §4
    (tracked-in-git pattern).
    """
    rel = file_path.relative_to(corpus_root)
    stat = file_path.stat()
    mtime_dt = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
    return IndexEntry(
        path=rel.as_posix(),
        sha256=compute_sha256_of_file(file_path),
        size_bytes=stat.st_size,
        mtime=mtime_dt.isoformat(),
    )


# ─── serialize_map_toml ─────────────────────────────────────────────────────


def serialize_map_toml(map_data: Map) -> str:
    """Serialize a Map to TOML text per ADR 0016 §1's schema.

    We hand-write the TOML rather than reach for a writer library —
    Python's stdlib `tomllib` is read-only (parser only), and pulling in
    a TOML writer for a fixed-shape document is overkill. The format
    matches what `tomllib.loads` round-trips through, which the tests
    pin.
    """
    lines: list[str] = []
    lines.append("[meta]")
    lines.append(f"version = {map_data.version}")
    lines.append(f'generated_at = "{map_data.generated_at}"')
    lines.append(f'generator = "{map_data.generator}"')
    lines.append(f'corpus_root = "{_toml_escape(map_data.corpus_root)}"')

    for entry in map_data.files:
        lines.append("")
        lines.append("[[files]]")
        lines.append(f'path = "{_toml_escape(entry.path)}"')
        lines.append(f'sha256 = "{entry.sha256}"')
        lines.append(f"size_bytes = {entry.size_bytes}")
        lines.append(f'mtime = "{entry.mtime}"')

    return "\n".join(lines) + "\n"


def _toml_escape(s: str) -> str:
    """Minimal TOML-string escaping for the fields we emit.

    We only emit fields the user (or filesystem) controls within: paths,
    timestamps, generator id. None of those carry control chars in
    practice, but backslashes and double-quotes can appear in path
    components on weird filesystems, so escape them.
    """
    return s.replace("\\", "\\\\").replace('"', '\\"')


# ─── parse_map_toml ─────────────────────────────────────────────────────────


# ─── Atomic write_map ───────────────────────────────────────────────────────


def write_map(map_data: Map, path: Path) -> None:
    """Write ``map_data`` to ``path`` atomically.

    Creates parent dirs. Writes to a sibling ``.tmp`` file then
    ``os.replace``s it onto the target so a crashed write never leaves
    a half-written map visible. Matches migrate's ``write_manifest``
    pattern (ergodix.migrate §"Read / write / find").
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    body = serialize_map_toml(map_data)
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, path)


# ─── IndexSummary + generate_index orchestrator ─────────────────────────────


@dataclass(frozen=True)
class IndexSummary:
    """The orchestrator's return value.

    Carries enough information for the CLI to print a one-line summary
    and for downstream callers (chunk 3 drift comparison, chunk 4 CLI)
    to reason about what just happened without re-reading the map.
    """

    map_path: Path
    file_count: int
    total_bytes: int
    generated_at: str


def _default_now() -> datetime:
    return datetime.now(tz=UTC)


def generate_index(
    *,
    corpus_root: Path,
    now_fn: Callable[[], datetime] = _default_now,
) -> IndexSummary:
    """Walk ``corpus_root``, build a Map, write it to
    ``<corpus_root>/_AI/ergodix.map`` atomically, and return a summary.

    Per Spike 0015 §5: deterministic — entries sorted by POSIX path so
    re-runs on an unchanged corpus produce byte-identical maps (modulo
    ``generated_at``). Per ADR 0016 §4: atomic-write pattern matches
    migrate's manifest writer.

    The ``_AI/`` directory is excluded from the walk via
    ``_SKIP_DIR_NAMES`` — the map never indexes itself or any sibling
    AI-emitted artifact (Continuity-Engine reports, Plot-Planner runs).
    """
    root = corpus_root.resolve()
    entries = sorted(
        (build_map_entry(corpus_root=root, file_path=p) for p in walk_corpus_for_index(root)),
        key=lambda e: e.path,
    )
    generated_at = now_fn().isoformat()
    map_data = Map(
        version=MAP_SCHEMA_VERSION,
        generated_at=generated_at,
        generator=f"ergodix {__version__} index",
        corpus_root=str(root),
        files=tuple(entries),
    )
    map_path = root / "_AI" / "ergodix.map"
    write_map(map_data, map_path)
    return IndexSummary(
        map_path=map_path,
        file_count=len(entries),
        total_bytes=sum(e.size_bytes for e in entries),
        generated_at=generated_at,
    )


# ─── read_map (disk-side companion to write_map) ────────────────────────────


def read_map(path: Path) -> Map:
    """Load a Map from ``path``.

    Composes ``parse_map_toml`` with disk I/O. Same strict-version
    refusal applies — a map declaring an unknown schema version raises
    ``ValueError`` before any consumer sees a half-interpreted record.
    Callers that want "missing prior index → empty Map" semantics
    catch ``FileNotFoundError`` themselves.
    """
    return parse_map_toml(path.read_text(encoding="utf-8"))


# ─── DriftReport + compare_to_map ───────────────────────────────────────────


@dataclass(frozen=True)
class DriftReport:
    """The output of comparing an existing map against a fresh walk.

    Per ADR 0016 §3: SHA-256 is authoritative for `changed_files`;
    mtime differences alone are not drift. Each bucket is sorted so the
    report is deterministic regardless of input order.
    """

    new_files: tuple[str, ...]
    changed_files: tuple[str, ...]
    removed_files: tuple[str, ...]

    @property
    def has_drift(self) -> bool:
        """True if any of the three buckets is non-empty."""
        return bool(self.new_files or self.changed_files or self.removed_files)


def compare_to_map(*, existing: Map, current: Map) -> DriftReport:
    """Compute the drift between two Maps.

    Pure function — no I/O. The CLI (chunk 4) is the composer that
    reads the existing map from disk via ``read_map`` and builds the
    current Map via ``walk_corpus_for_index`` + ``build_map_entry``
    (without writing).

    Buckets:
      * new_files     — paths in ``current`` that aren't in ``existing``.
      * changed_files — paths in both, whose ``sha256`` differs. Per
                        ADR 0016 §3, mtime is ignored for this check.
      * removed_files — paths in ``existing`` that aren't in ``current``.
    """
    existing_by_path = {e.path: e for e in existing.files}
    current_by_path = {e.path: e for e in current.files}

    existing_paths = set(existing_by_path)
    current_paths = set(current_by_path)

    new = current_paths - existing_paths
    removed = existing_paths - current_paths
    changed = {
        p
        for p in existing_paths & current_paths
        if existing_by_path[p].sha256 != current_by_path[p].sha256
    }

    return DriftReport(
        new_files=tuple(sorted(new)),
        changed_files=tuple(sorted(changed)),
        removed_files=tuple(sorted(removed)),
    )


# ─── parse_map_toml ─────────────────────────────────────────────────────────


def parse_map_toml(text: str) -> Map:
    """Parse TOML text into a Map.

    Per ADR 0016 §1: refuses any version != MAP_SCHEMA_VERSION (raises
    ValueError). Missing `[meta]` block or missing `version` field also
    raises ValueError — better to fail loudly than load a partial Map
    that downstream consumers would have to defensively re-check.
    """
    data = tomllib.loads(text)
    meta = data.get("meta")
    if not isinstance(meta, dict):
        raise ValueError("ergodix.map missing required [meta] block")

    version = meta.get("version")
    if version is None:
        raise ValueError("ergodix.map missing required meta.version field")
    if version != MAP_SCHEMA_VERSION:
        raise ValueError(
            f"ergodix.map declares schema version={version}; this build "
            f"only reads version={MAP_SCHEMA_VERSION}. Re-run `ergodix index` "
            "on a build that understands this schema, or upgrade ergodix."
        )

    files_raw = data.get("files", [])
    files = tuple(
        IndexEntry(
            path=f["path"],
            sha256=f["sha256"],
            size_bytes=f["size_bytes"],
            mtime=f["mtime"],
        )
        for f in files_raw
    )

    return Map(
        version=version,
        generated_at=meta["generated_at"],
        generator=meta["generator"],
        corpus_root=meta["corpus_root"],
        files=files,
    )
