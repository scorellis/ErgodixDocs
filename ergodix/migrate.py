"""
Migration walker, helpers, and (eventually) orchestrator.

Chunk 3a (this module's first slice) provides the pure helpers and the
read-only corpus walker that the migrate command will compose with the
manifest writer (chunk 3b) and the orchestrator (chunk 3c). All public
surface here is side-effect-free — `walk_corpus` reads the filesystem
but doesn't write — so unit tests don't need network or OAuth.

Per ADR 0015 §3 / §4:

  * `slugify_filename` — humans get nice filenames; filesystems get
    portable ones.
  * `build_target_path` — slugifies just the basename, leaves parent
    folder names untouched (the user organizes their corpus tree along
    the opus → compendium → book hierarchy and we don't second-guess
    folder names).
  * `compute_sha256` — hashes the EXTRACTED markdown, not the source
    file's raw bytes. Drives idempotency: same extracted content =
    skip on re-run.
  * `build_frontmatter` — produces the YAML block that every migrated
    chapter gets, including migrate-specific provenance (`source`,
    `migrated_at`).
  * `walk_corpus` — yields one `WalkEntry` per file under the corpus
    root, skipping hidden dirs, scratch dirs, the `_archive` tree we
    own, and any folder containing a `.ergodix-skip` marker.

Everything is pure-ish on purpose. Chunk 3b adds the manifest TOML
schema and archive mover; chunk 3c stitches the orchestrator together
with re-run idempotency, two-phase atomicity, and partial-failure
recovery.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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
