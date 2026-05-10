"""Tests for the pure helpers in ergodix.migrate.

Helpers covered here:

  * slugify_filename(stem) -> str
  * build_target_path(source_rel) -> Path
  * compute_sha256(content) -> str
  * build_frontmatter(...) -> str
  * walk_corpus(corpus_root) -> Iterator[WalkEntry]

The walker tests build small temporary corpus trees with tmp_path; nothing
in this file touches network, OAuth, or the migrate orchestrator (still
parking-lot for chunk 3c).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from ergodix.migrate import (
    WalkEntry,
    build_frontmatter,
    build_target_path,
    compute_sha256,
    slugify_filename,
    walk_corpus,
)

# ─── slugify_filename ───────────────────────────────────────────────────────


def test_slugify_lowercases_and_hyphenates_spaces() -> None:
    assert slugify_filename("Chapter 3 The Glass Tower") == "chapter-3-the-glass-tower"


def test_slugify_handles_em_dash() -> None:
    assert slugify_filename("Chapter 3 — The Glass Tower") == "chapter-3-the-glass-tower"


def test_slugify_handles_en_dash() -> None:
    # en-dash (U+2013) is intentional; the test verifies it gets normalized.
    assert (
        slugify_filename("Chapter 3 – The Glass Tower")  # noqa: RUF001
        == "chapter-3-the-glass-tower"
    )


def test_slugify_collapses_multiple_separators() -> None:
    assert slugify_filename("Chapter   3 ---  Tower") == "chapter-3-tower"


def test_slugify_strips_diacritics() -> None:
    assert slugify_filename("Café Müller naïve") == "cafe-muller-naive"


def test_slugify_drops_punctuation() -> None:
    assert slugify_filename("Hello, world! (yes?)") == "hello-world-yes"


def test_slugify_trims_leading_trailing_hyphens() -> None:
    assert slugify_filename("---weird---") == "weird"


def test_slugify_empty_or_punctuation_only_falls_back_to_untitled() -> None:
    assert slugify_filename("") == "untitled"
    assert slugify_filename("???") == "untitled"
    assert slugify_filename("---") == "untitled"


def test_slugify_preserves_digits() -> None:
    assert slugify_filename("Chapter 12") == "chapter-12"


# ─── build_target_path ─────────────────────────────────────────────────────


def test_build_target_path_simple() -> None:
    src = Path("Book 1/Chapter 3 — The Glass Tower.gdoc")
    assert build_target_path(src) == Path("Book 1/chapter-3-the-glass-tower.md")


def test_build_target_path_root_level() -> None:
    src = Path("Notes.gdoc")
    assert build_target_path(src) == Path("notes.md")


def test_build_target_path_nested() -> None:
    src = Path("Tapestry/Book 1/Section A/Chapter 1.docx")
    assert build_target_path(src) == Path("Tapestry/Book 1/Section A/chapter-1.md")


# Note: the parent dirs are NOT slugified — only the filename. The user
# organizes their corpus folders deliberately along the hierarchy
# (per ADR 0015 §3); we don't second-guess folder names.


# ─── compute_sha256 ────────────────────────────────────────────────────────


def test_compute_sha256_matches_hashlib() -> None:
    content = "Hello, world!\n"
    expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert compute_sha256(content) == expected


def test_compute_sha256_returns_64_hex_chars() -> None:
    digest = compute_sha256("anything")
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_compute_sha256_empty_string() -> None:
    # SHA-256 of empty bytes is well-known.
    assert compute_sha256("") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


# ─── build_frontmatter ─────────────────────────────────────────────────────


def test_frontmatter_starts_and_ends_with_triple_dash() -> None:
    fm = build_frontmatter(
        title="Chapter 3",
        author="Scott R. Ellis",
        source_rel=Path("Book 1/Chapter 3.gdoc"),
        migrated_at=datetime(2026, 5, 10, 14, 30, 0, tzinfo=UTC),
    )
    assert fm.startswith("---\n")
    assert fm.rstrip().endswith("---")


def test_frontmatter_includes_required_fields() -> None:
    fm = build_frontmatter(
        title="Chapter 3 — The Glass Tower",
        author="Scott R. Ellis",
        source_rel=Path("Book 1/Chapter 3.gdoc"),
        migrated_at=datetime(2026, 5, 10, 14, 30, 0, tzinfo=UTC),
    )
    assert 'title: "Chapter 3 — The Glass Tower"' in fm
    assert 'author: "Scott R. Ellis"' in fm
    assert "format: pandoc-markdown" in fm
    assert "pandoc-extensions:" in fm
    assert 'source: "Book 1/Chapter 3.gdoc"' in fm
    assert 'migrated_at: "2026-05-10T14:30:00Z"' in fm


def test_frontmatter_default_pandoc_extensions() -> None:
    fm = build_frontmatter(
        title="x",
        author="x",
        source_rel=Path("x.gdoc"),
        migrated_at=datetime(2026, 5, 10, tzinfo=UTC),
    )
    assert "[raw_tex, footnotes, yaml_metadata_block]" in fm


def test_frontmatter_custom_pandoc_extensions() -> None:
    fm = build_frontmatter(
        title="x",
        author="x",
        source_rel=Path("x.gdoc"),
        migrated_at=datetime(2026, 5, 10, tzinfo=UTC),
        pandoc_extensions=("raw_tex",),
    )
    assert "[raw_tex]" in fm
    assert "footnotes" not in fm


def test_frontmatter_uses_forward_slashes_in_source() -> None:
    """Frontmatter is repo-portable; paths use POSIX separators even on Windows."""
    fm = build_frontmatter(
        title="x",
        author="x",
        source_rel=Path("Book 1") / "Section" / "Chapter 1.gdoc",
        migrated_at=datetime(2026, 5, 10, tzinfo=UTC),
    )
    assert 'source: "Book 1/Section/Chapter 1.gdoc"' in fm


def test_frontmatter_iso8601_z_suffix() -> None:
    fm = build_frontmatter(
        title="x",
        author="x",
        source_rel=Path("x.gdoc"),
        migrated_at=datetime(2026, 5, 10, 14, 30, 5, tzinfo=UTC),
    )
    # Always ends with Z (no microseconds, no +00:00 form).
    assert 'migrated_at: "2026-05-10T14:30:05Z"' in fm


# ─── walk_corpus ───────────────────────────────────────────────────────────


def _touch(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _entries(corpus_root: Path) -> list[WalkEntry]:
    return list(walk_corpus(corpus_root))


def _rel_paths(entries: list[WalkEntry]) -> set[Path]:
    return {e.relative_path for e in entries}


def test_walk_corpus_yields_files_with_relative_paths(tmp_path: Path) -> None:
    _touch(tmp_path / "Book 1" / "Chapter 1.gdoc")
    _touch(tmp_path / "Book 1" / "Chapter 2.gdoc")
    _touch(tmp_path / "Notes.txt")
    rel = _rel_paths(_entries(tmp_path))
    assert Path("Book 1/Chapter 1.gdoc") in rel
    assert Path("Book 1/Chapter 2.gdoc") in rel
    assert Path("Notes.txt") in rel


def test_walk_corpus_attaches_importer_name_for_known_extensions(tmp_path: Path) -> None:
    _touch(tmp_path / "Chapter 1.gdoc")
    _touch(tmp_path / "Notes.txt")
    by_rel = {e.relative_path: e for e in _entries(tmp_path)}
    assert by_rel[Path("Chapter 1.gdoc")].importer_name == "gdocs"
    # .txt has no importer registered yet — None, not omitted.
    assert by_rel[Path("Notes.txt")].importer_name is None


def test_walk_corpus_skips_hidden_dirs(tmp_path: Path) -> None:
    _touch(tmp_path / ".hidden" / "secret.gdoc")
    _touch(tmp_path / "visible" / "Chapter 1.gdoc")
    rel = _rel_paths(_entries(tmp_path))
    assert Path("visible/Chapter 1.gdoc") in rel
    assert Path(".hidden/secret.gdoc") not in rel


def test_walk_corpus_skips_hidden_files(tmp_path: Path) -> None:
    _touch(tmp_path / ".DS_Store")
    _touch(tmp_path / "visible.gdoc")
    rel = _rel_paths(_entries(tmp_path))
    assert Path(".DS_Store") not in rel
    assert Path("visible.gdoc") in rel


def test_walk_corpus_skips_archive_dir(tmp_path: Path) -> None:
    _touch(tmp_path / "_archive" / "2026-05-10-141500" / "Chapter 1.gdoc")
    _touch(tmp_path / "Chapter 2.gdoc")
    rel = _rel_paths(_entries(tmp_path))
    assert Path("Chapter 2.gdoc") in rel
    assert not any(p.parts and p.parts[0] == "_archive" for p in rel)


def test_walk_corpus_skips_pycache_and_node_modules(tmp_path: Path) -> None:
    _touch(tmp_path / "__pycache__" / "junk.pyc")
    _touch(tmp_path / "node_modules" / "junk.js")
    _touch(tmp_path / "Chapter 1.gdoc")
    rel = _rel_paths(_entries(tmp_path))
    assert Path("Chapter 1.gdoc") in rel
    assert not any("__pycache__" in p.parts for p in rel)
    assert not any("node_modules" in p.parts for p in rel)


def test_walk_corpus_respects_ergodix_skip_marker(tmp_path: Path) -> None:
    _touch(tmp_path / "Drafts" / ".ergodix-skip")
    _touch(tmp_path / "Drafts" / "rough.gdoc")
    _touch(tmp_path / "Drafts" / "subfolder" / "rougher.gdoc")
    _touch(tmp_path / "Polished" / "Chapter 1.gdoc")
    rel = _rel_paths(_entries(tmp_path))
    assert Path("Polished/Chapter 1.gdoc") in rel
    assert not any("Drafts" in p.parts for p in rel)


def test_walk_corpus_yields_absolute_source_path(tmp_path: Path) -> None:
    _touch(tmp_path / "Chapter 1.gdoc")
    entries = _entries(tmp_path)
    assert len(entries) == 1
    assert entries[0].source_path.is_absolute()
    assert entries[0].source_path == (tmp_path / "Chapter 1.gdoc").resolve()


def test_walk_corpus_handles_empty_corpus(tmp_path: Path) -> None:
    assert _entries(tmp_path) == []


def test_walk_corpus_handles_corpus_with_only_skipped_dirs(tmp_path: Path) -> None:
    _touch(tmp_path / ".git" / "HEAD")
    _touch(tmp_path / "_archive" / "x.gdoc")
    _touch(tmp_path / "__pycache__" / "junk.pyc")
    assert _entries(tmp_path) == []


def test_walk_corpus_extension_lookup_is_case_insensitive(tmp_path: Path) -> None:
    _touch(tmp_path / "Chapter.GDOC")
    by_rel = {e.relative_path: e for e in _entries(tmp_path)}
    assert by_rel[Path("Chapter.GDOC")].importer_name == "gdocs"
