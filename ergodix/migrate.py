"""
Migration walker, helpers, manifest I/O, archive mover.

Chunks 3a + 3b together. The orchestrator (chunk 3c) will compose
these into the full migrate run.

Chunk 3a — pure helpers + read-only walker:

  * `slugify_filename`
  * `build_target_path`
  * `compute_sha256`
  * `build_frontmatter`
  * `walk_corpus` / `WalkEntry`

Chunk 3b — manifest schema + I/O + archive mover:

  * `Manifest`, `ManifestEntry` (frozen dataclasses)
  * `format_run_id(dt)`
  * `manifest_path_for_run(corpus_root, run_id)`
  * `archive_path_for(corpus_root, run_id, source_rel)`
  * `write_manifest(manifest, path)` — atomic tmp+rename
  * `read_manifest(path)` — round-trip
  * `find_latest_manifest(corpus_root)`
  * `move_to_archive(source_path, target_path)` — fails if dst exists

Schema is locked by ADR 0015 §4. The TOML serializer is hand-written
(rather than pulling in `tomli-w`) because the schema is small, stdlib
`tomllib` already handles the read side, and the dependency footprint
stays minimal per CLAUDE.md.
"""

from __future__ import annotations

import hashlib
import os
import re
import tomllib
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from ergodix.importers import extension_to_importer

# Folder names we never descend into. Tied to migrate's archive layout
# (`_archive/`) and to common scratch dirs that might land in a corpus
# root by accident. A `.ergodix-skip` marker in any other folder skips
# that folder and its descendants — see `walk_corpus`.
_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        "_archive",
        "__pycache__",
        "node_modules",
    }
)

_DEFAULT_PANDOC_EXTENSIONS: tuple[str, ...] = (
    "raw_tex",
    "footnotes",
    "yaml_metadata_block",
)


# ─── slugify ───────────────────────────────────────────────────────────────


def slugify_filename(stem: str) -> str:
    """Return a portable lowercase ASCII slug for a filename stem.

    Applies NFKD normalization to peel diacritics off (``café`` →
    ``cafe``), strips remaining non-ASCII, lowercases, and collapses
    any run of non-alphanumerics into a single hyphen. Trims leading
    and trailing hyphens. Falls back to ``"untitled"`` when the result
    would otherwise be empty (input was punctuation-only or empty).

    Note: pass the stem (no extension). The caller controls the
    extension change via `build_target_path`.
    """
    decomposed = unicodedata.normalize("NFKD", stem)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    slugged = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slugged or "untitled"


# ─── build_target_path ─────────────────────────────────────────────────────


def build_target_path(source_rel: Path) -> Path:
    """Map a source file's relative path to its `.md` migration target.

    Only the basename is slugified; parent folder names pass through
    unchanged so the user's folder organization (their hierarchy
    decisions per ADR 0015 §3) is preserved.
    """
    return source_rel.parent / (slugify_filename(source_rel.stem) + ".md")


# ─── compute_sha256 ────────────────────────────────────────────────────────


def compute_sha256(content: str) -> str:
    """Lowercase hex SHA-256 digest of ``content`` encoded as UTF-8."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ─── build_frontmatter ─────────────────────────────────────────────────────


def build_frontmatter(
    *,
    title: str,
    author: str,
    source_rel: Path,
    migrated_at: datetime,
    pandoc_extensions: tuple[str, ...] = _DEFAULT_PANDOC_EXTENSIONS,
) -> str:
    """Build the YAML frontmatter block for a migrated chapter.

    The block opens and closes with ``---`` on its own line and
    contains the locked fields from ADR 0015 §3 plus the migrate
    provenance fields ``source`` and ``migrated_at``. Path separators
    in ``source`` are normalized to forward slashes so the frontmatter
    is portable across operating systems.

    ``migrated_at`` is rendered as RFC-3339 / ISO-8601 with a literal
    ``Z`` suffix (UTC, microseconds dropped). The caller is responsible
    for passing a timezone-aware UTC datetime — we don't massage
    naive datetimes.
    """
    posix_source = source_rel.as_posix()
    extensions_yaml = "[" + ", ".join(pandoc_extensions) + "]"
    timestamp = migrated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        "---\n"
        f'title: "{title}"\n'
        f'author: "{author}"\n'
        "format: pandoc-markdown\n"
        f"pandoc-extensions: {extensions_yaml}\n"
        f'source: "{posix_source}"\n'
        f'migrated_at: "{timestamp}"\n'
        "---\n"
    )


# ─── walk_corpus ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class WalkEntry:
    """One file discovered by `walk_corpus`.

    Attributes:
        source_path: Resolved absolute path to the file.
        relative_path: Path relative to the corpus root passed to
            `walk_corpus`. POSIX style — useful for manifest entries
            and frontmatter `source` fields.
        importer_name: Name of the registered importer that claims
            this file's extension, or ``None`` if no importer is
            registered for it. ``None`` covers both out-of-scope file
            types (per ADR 0015 §2) and `.md` files already in target
            format (those follow the "touch frontmatter, leave content"
            path the orchestrator implements separately).
    """

    source_path: Path
    relative_path: Path
    importer_name: str | None


def walk_corpus(corpus_root: Path) -> Iterator[WalkEntry]:
    """Walk a corpus tree and yield every file we'd consider migrating.

    Skipped (never yielded, never descended into):
      * Hidden files and directories (name starts with ``.``).
      * `_archive/` (migrate's own output — we don't re-process).
      * `__pycache__/`, `node_modules/`, and similar scratch (see
        `_SKIP_DIR_NAMES`).
      * Any directory whose contents include a `.ergodix-skip` marker
        file. The marker scopes to that directory and all descendants;
        the user's escape hatch for "don't migrate this folder."

    Every yielded `WalkEntry` carries the importer name (from the
    `ergodix.importers` registry) for files whose extension is claimed,
    else ``None``. Hidden files at any depth (e.g. `.DS_Store`) are
    silently dropped so they never appear in the run manifest.

    Iteration order is filesystem-defined (whatever `os.walk` /
    `Path.iterdir` give); callers that need stable ordering should sort
    the entries themselves.
    """
    root = corpus_root.resolve()
    yield from _walk(root, root)


def _walk(current: Path, root: Path) -> Iterator[WalkEntry]:
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
            yield from _walk(entry, root)
            continue
        if not entry.is_file():
            continue
        importer = extension_to_importer(entry.suffix)
        yield WalkEntry(
            source_path=entry.resolve(),
            relative_path=entry.relative_to(root),
            importer_name=importer.name if importer is not None else None,
        )


# ─── Manifest schema (ADR 0015 §4) ─────────────────────────────────────────


ManifestStatus = Literal["migrated", "skipped", "failed", "drift-detected"]

_MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ManifestEntry:
    """One file's outcome inside a run manifest.

    Field presence varies by status — `migrated` carries target +
    sha256 + size_bytes, `skipped`/`failed` carry a `reason`,
    `drift-detected` carries the existing target. The serializer omits
    fields whose value is ``None`` so the on-disk TOML stays compact
    and matches the ADR 0015 §4 example exactly.
    """

    source: Path
    status: ManifestStatus
    target: Path | None = None
    sha256: str | None = None
    size_bytes: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class Manifest:
    """One run's manifest, written to `_archive/_runs/<run_id>.toml`."""

    version: int
    started_at: datetime
    finished_at: datetime
    generator: str
    corpus_root: Path
    files: tuple[ManifestEntry, ...]


# ─── Path / id helpers ─────────────────────────────────────────────────────


def format_run_id(dt: datetime) -> str:
    """`YYYY-MM-DD-HHMMSS` per ADR 0015 §4. Microseconds dropped.

    The format is intentionally lex-sortable so plain string ordering
    over filenames in `_archive/_runs/` matches chronological order —
    `find_latest_manifest` relies on this.
    """
    return dt.strftime("%Y-%m-%d-%H%M%S")


def manifest_path_for_run(corpus_root: Path, run_id: str) -> Path:
    """`<corpus>/_archive/_runs/<run_id>.toml`."""
    return corpus_root / "_archive" / "_runs" / f"{run_id}.toml"


def archive_path_for(corpus_root: Path, run_id: str, source_rel: Path) -> Path:
    """`<corpus>/_archive/<run_id>/<source_rel>`."""
    return corpus_root / "_archive" / run_id / source_rel


# ─── TOML serialization (hand-written, small + controlled schema) ──────────


def _toml_string(s: str) -> str:
    """Quote ``s`` as a TOML basic string with full escape handling.

    Per TOML 1.0: `\\`, `"`, `\\b`, `\\t`, `\\n`, `\\f`, `\\r` get
    backslash-escaped. Other control chars (U+0000 to U+001F, U+007F)
    use `\\uXXXX`. Everything else passes through unchanged so unicode
    titles ("Cafe Muller") survive intact.
    """
    out: list[str] = ['"']
    for c in s:
        if c == "\\":
            out.append("\\\\")
        elif c == '"':
            out.append('\\"')
        elif c == "\b":
            out.append("\\b")
        elif c == "\t":
            out.append("\\t")
        elif c == "\n":
            out.append("\\n")
        elif c == "\f":
            out.append("\\f")
        elif c == "\r":
            out.append("\\r")
        elif ord(c) < 0x20 or ord(c) == 0x7F:
            out.append(f"\\u{ord(c):04X}")
        else:
            out.append(c)
    out.append('"')
    return "".join(out)


def _iso_z(dt: datetime) -> str:
    """RFC-3339 / ISO-8601 with literal Z suffix; microseconds dropped."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _serialize_manifest(manifest: Manifest) -> str:
    lines: list[str] = ["[meta]"]
    lines.append(f"version = {manifest.version}")
    lines.append(f"started_at = {_toml_string(_iso_z(manifest.started_at))}")
    lines.append(f"finished_at = {_toml_string(_iso_z(manifest.finished_at))}")
    lines.append(f"generator = {_toml_string(manifest.generator)}")
    lines.append(f"corpus_root = {_toml_string(manifest.corpus_root.as_posix())}")

    for entry in manifest.files:
        lines.append("")
        lines.append("[[files]]")
        lines.append(f"source = {_toml_string(entry.source.as_posix())}")
        lines.append(f"status = {_toml_string(entry.status)}")
        if entry.target is not None:
            lines.append(f"target = {_toml_string(entry.target.as_posix())}")
        if entry.sha256 is not None:
            lines.append(f"sha256 = {_toml_string(entry.sha256)}")
        if entry.size_bytes is not None:
            lines.append(f"size_bytes = {entry.size_bytes}")
        if entry.reason is not None:
            lines.append(f"reason = {_toml_string(entry.reason)}")

    return "\n".join(lines) + "\n"


# ─── Read / write / find ───────────────────────────────────────────────────


def write_manifest(manifest: Manifest, path: Path) -> None:
    """Write ``manifest`` to ``path`` atomically.

    Creates parent dirs. Writes to a sibling `.tmp` file then
    `os.replace`s it onto the target so a crashed write never leaves a
    half-written manifest visible. On a re-run with the same path, the
    old manifest is replaced with no leftover `.tmp` siblings.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    body = _serialize_manifest(manifest)
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, path)


def _parse_iso_z(value: str) -> datetime:
    """Parse a Z-suffixed ISO-8601 timestamp into a UTC-aware datetime."""
    return datetime.fromisoformat(value)


def read_manifest(path: Path) -> Manifest:
    """Parse a run manifest from ``path``.

    Validates the schema version — we refuse to interpret a manifest
    written by a future migrate version we don't understand. The
    caller deals with that by either upgrading or aborting the run.
    """
    with path.open("rb") as fh:
        data = tomllib.load(fh)

    meta = data.get("meta") or {}
    version = meta.get("version")
    if version != _MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"unknown manifest schema version: {version!r} "
            f"(this migrate understands {_MANIFEST_SCHEMA_VERSION})"
        )

    files: list[ManifestEntry] = []
    for raw in data.get("files") or []:
        files.append(
            ManifestEntry(
                source=Path(raw["source"]),
                status=raw["status"],
                target=Path(raw["target"]) if raw.get("target") else None,
                sha256=raw.get("sha256"),
                size_bytes=raw.get("size_bytes"),
                reason=raw.get("reason"),
            )
        )

    return Manifest(
        version=version,
        started_at=_parse_iso_z(meta["started_at"]),
        finished_at=_parse_iso_z(meta["finished_at"]),
        generator=meta["generator"],
        corpus_root=Path(meta["corpus_root"]),
        files=tuple(files),
    )


def find_latest_manifest(corpus_root: Path) -> Manifest | None:
    """Return the most recent run manifest, or ``None`` if no runs yet.

    Looks under `_archive/_runs/`, takes the lex-largest `.toml` file
    (which equals chronological-latest given the run-id format), and
    parses it. Non-`.toml` files in the runs dir are ignored.
    """
    runs_dir = corpus_root / "_archive" / "_runs"
    if not runs_dir.is_dir():
        return None
    candidates = sorted(p for p in runs_dir.iterdir() if p.suffix == ".toml")
    if not candidates:
        return None
    return read_manifest(candidates[-1])


# ─── Archive mover ─────────────────────────────────────────────────────────


def move_to_archive(source_path: Path, target_path: Path) -> None:
    """Move ``source_path`` to ``target_path``, refusing to overwrite.

    Creates parent dirs. Two distinct runs would land in different
    timestamped subfolders so collisions shouldn't happen; if one does
    (clock skew, manual archive surgery), we raise rather than
    silently clobber. ``os.rename`` semantics differ between POSIX
    (silently replaces) and Windows (raises), so we do an explicit
    pre-check for portable "fail if exists" behavior.
    """
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if target_path.exists():
        raise FileExistsError(f"archive target already exists: {target_path}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    os.rename(source_path, target_path)
