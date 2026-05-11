"""Tests for the pure helpers in ergodix.index.

Chunk 1 of the ergodix-index implementation (Spike 0015 §"Implementation
chunks", ADR 0016). No FS orchestration; just the pure functions that
the orchestrator will later compose.

Helpers covered:
  * MAP_SCHEMA_VERSION constant
  * compute_sha256_of_file(path) -> str
  * walk_corpus_for_index(corpus_root) -> Iterator[Path]
  * build_map_entry(corpus_root, file_path) -> IndexEntry
  * serialize_map_toml(map_data) -> str
  * parse_map_toml(text) -> Map
  * Round-trip: parse(serialize(m)) == m
  * Schema-version refusal: parsing version != 1 raises ValueError
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ergodix.index import (
    MAP_SCHEMA_VERSION,
    IndexEntry,
    Map,
    build_map_entry,
    compute_sha256_of_file,
    parse_map_toml,
    serialize_map_toml,
    walk_corpus_for_index,
)

# ─── MAP_SCHEMA_VERSION ─────────────────────────────────────────────────────


def test_schema_version_is_1() -> None:
    """ADR 0016 §1: v1 schema is locked at version = 1."""
    assert MAP_SCHEMA_VERSION == 1


# ─── compute_sha256_of_file ─────────────────────────────────────────────────


def test_compute_sha256_of_file_matches_known_content(tmp_path: Path) -> None:
    """Hash matches manually computed SHA-256 over the same bytes."""
    file_path = tmp_path / "chapter.md"
    content = b"# Chapter 1\n\nThe glass tower rose against the dusk.\n"
    file_path.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    assert compute_sha256_of_file(file_path) == expected


def test_compute_sha256_of_file_lowercase_hex(tmp_path: Path) -> None:
    """Per ADR 0016 §1: lowercase hex."""
    file_path = tmp_path / "f.md"
    file_path.write_bytes(b"hello")
    h = compute_sha256_of_file(file_path)
    assert h == h.lower()
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_sha256_of_file_handles_empty(tmp_path: Path) -> None:
    file_path = tmp_path / "empty.md"
    file_path.write_bytes(b"")
    expected = hashlib.sha256(b"").hexdigest()
    assert compute_sha256_of_file(file_path) == expected


def test_compute_sha256_of_file_handles_binary(tmp_path: Path) -> None:
    """The index doesn't include binary by default, but the helper is
    byte-agnostic — it hashes whatever bytes are on disk."""
    file_path = tmp_path / "blob.bin"
    payload = bytes(range(256))
    file_path.write_bytes(payload)
    assert compute_sha256_of_file(file_path) == hashlib.sha256(payload).hexdigest()


# ─── walk_corpus_for_index ──────────────────────────────────────────────────


def test_walker_yields_md_files(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("hello")
    (tmp_path / "Chapter 2.md").write_text("world")
    results = sorted(p.name for p in walk_corpus_for_index(tmp_path))
    assert results == ["Chapter 1.md", "Chapter 2.md"]


def test_walker_yields_preamble_tex(tmp_path: Path) -> None:
    """Per Spike 0015 §2: _preamble.tex is included."""
    (tmp_path / "_preamble.tex").write_text("\\usepackage{x}")
    results = list(walk_corpus_for_index(tmp_path))
    assert any(p.name == "_preamble.tex" for p in results)


def test_walker_yields_custom_tex_files(tmp_path: Path) -> None:
    """Per Spike 0015 §2: any other *.tex is included (custom preambles)."""
    (tmp_path / "custom.tex").write_text("\\def\\foo{bar}")
    results = list(walk_corpus_for_index(tmp_path))
    assert any(p.name == "custom.tex" for p in results)


def test_walker_skips_hidden_files(tmp_path: Path) -> None:
    """Per Spike 0015 §2: hidden files / dirs excluded."""
    (tmp_path / ".DS_Store").write_text("garbage")
    (tmp_path / "real.md").write_text("real")
    results = list(walk_corpus_for_index(tmp_path))
    assert {p.name for p in results} == {"real.md"}


def test_walker_skips_hidden_dirs(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("garbage")
    (tmp_path / "Chapter 1.md").write_text("real")
    results = list(walk_corpus_for_index(tmp_path))
    assert {p.name for p in results} == {"Chapter 1.md"}


def test_walker_skips_archive_dir(tmp_path: Path) -> None:
    """Per Spike 0015 §2: _archive/ (migrate's output) excluded."""
    archive = tmp_path / "_archive"
    archive.mkdir()
    (archive / "Old Chapter.md").write_text("archived")
    (tmp_path / "Chapter 1.md").write_text("current")
    results = list(walk_corpus_for_index(tmp_path))
    assert {p.name for p in results} == {"Chapter 1.md"}


def test_walker_skips_pycache_and_node_modules(tmp_path: Path) -> None:
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "foo.pyc").write_text("x")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "bar.md").write_text("x")
    (tmp_path / "Chapter 1.md").write_text("real")
    results = list(walk_corpus_for_index(tmp_path))
    assert {p.name for p in results} == {"Chapter 1.md"}


def test_walker_respects_ergodix_skip_marker(tmp_path: Path) -> None:
    """Per Spike 0015 §2: .ergodix-skip marker scopes to dir + descendants."""
    skipped = tmp_path / "scratch"
    skipped.mkdir()
    (skipped / ".ergodix-skip").write_text("")
    (skipped / "draft.md").write_text("don't index me")
    nested = skipped / "deeper"
    nested.mkdir()
    (nested / "also.md").write_text("nor me")
    (tmp_path / "real.md").write_text("real")
    results = list(walk_corpus_for_index(tmp_path))
    assert {p.name for p in results} == {"real.md"}


def test_walker_excludes_media_dirs(tmp_path: Path) -> None:
    """Per Spike 0015 §2: _media/ contents are out of scope for v1."""
    media = tmp_path / "Chapter 1" / "_media"
    media.mkdir(parents=True)
    (media / "img-001.png").write_bytes(b"\x89PNG fake")
    (tmp_path / "Chapter 1.md").write_text("real")
    results = list(walk_corpus_for_index(tmp_path))
    assert all(p.suffix != ".png" for p in results)


def test_walker_skips_gdoc_and_gsheet(tmp_path: Path) -> None:
    """Per Spike 0015 §2: .gdoc / .gsheet are pre-migrate artifacts, skipped."""
    (tmp_path / "Old.gdoc").write_text('{"doc_id": "x"}')
    (tmp_path / "Notes.gsheet").write_text('{"sheet_id": "y"}')
    (tmp_path / "Chapter 1.md").write_text("real")
    results = list(walk_corpus_for_index(tmp_path))
    assert {p.name for p in results} == {"Chapter 1.md"}


def test_walker_descends_into_nested_dirs(tmp_path: Path) -> None:
    (tmp_path / "Book 1").mkdir()
    (tmp_path / "Book 1" / "Chapter 1.md").write_text("a")
    (tmp_path / "Book 1" / "Section A").mkdir()
    (tmp_path / "Book 1" / "Section A" / "Chapter 2.md").write_text("b")
    results = sorted(p.name for p in walk_corpus_for_index(tmp_path))
    assert results == ["Chapter 1.md", "Chapter 2.md"]


# ─── build_map_entry ────────────────────────────────────────────────────────


def test_build_map_entry_records_relative_path(tmp_path: Path) -> None:
    """Per ADR 0016 schema: path is POSIX relative to corpus_root."""
    (tmp_path / "Book 1").mkdir()
    file_path = tmp_path / "Book 1" / "Chapter 1.md"
    file_path.write_text("content")

    entry = build_map_entry(corpus_root=tmp_path, file_path=file_path)
    assert entry.path == "Book 1/Chapter 1.md"


def test_build_map_entry_records_sha256(tmp_path: Path) -> None:
    file_path = tmp_path / "f.md"
    file_path.write_bytes(b"deterministic content")
    entry = build_map_entry(corpus_root=tmp_path, file_path=file_path)
    assert entry.sha256 == hashlib.sha256(b"deterministic content").hexdigest()


def test_build_map_entry_records_size_bytes(tmp_path: Path) -> None:
    file_path = tmp_path / "f.md"
    payload = b"x" * 123
    file_path.write_bytes(payload)
    entry = build_map_entry(corpus_root=tmp_path, file_path=file_path)
    assert entry.size_bytes == 123


def test_build_map_entry_records_iso_utc_mtime(tmp_path: Path) -> None:
    file_path = tmp_path / "f.md"
    file_path.write_text("x")
    entry = build_map_entry(corpus_root=tmp_path, file_path=file_path)
    parsed = datetime.fromisoformat(entry.mtime)
    assert parsed.tzinfo is UTC


# ─── serialize / parse round-trip ───────────────────────────────────────────


def _sample_map() -> Map:
    return Map(
        version=MAP_SCHEMA_VERSION,
        generated_at="2026-05-10T22:14:00Z",
        generator="ergodix 1.x.y index",
        corpus_root="/Users/scott/Tapestry",
        files=(
            IndexEntry(
                path="Book 1/Chapter 1.md",
                sha256="abc123" + "0" * 58,
                size_bytes=4823,
                mtime="2026-05-09T18:42:11+00:00",
            ),
            IndexEntry(
                path="_preamble.tex",
                sha256="def456" + "0" * 58,
                size_bytes=612,
                mtime="2026-04-30T12:00:00+00:00",
            ),
        ),
    )


def test_round_trip_preserves_map() -> None:
    """parse(serialize(m)) == m for the canonical sample."""
    m = _sample_map()
    text = serialize_map_toml(m)
    parsed = parse_map_toml(text)
    assert parsed == m


def test_serialize_includes_meta_block() -> None:
    text = serialize_map_toml(_sample_map())
    assert "[meta]" in text
    assert "version = 1" in text


def test_serialize_includes_one_files_array_entry_per_file() -> None:
    text = serialize_map_toml(_sample_map())
    assert text.count("[[files]]") == 2


def test_parse_refuses_unknown_version() -> None:
    """ADR 0016 §1: strict refusal on unknown version."""
    text = """
[meta]
version = 999
generated_at = "2026-05-10T22:14:00Z"
generator = "ergodix 999.x.y index"
corpus_root = "/Users/scott/Tapestry"

[[files]]
path = "Chapter 1.md"
sha256 = "abc123"
size_bytes = 1
mtime = "2026-05-09T18:42:11+00:00"
"""
    with pytest.raises(ValueError, match="version"):
        parse_map_toml(text)


def test_parse_refuses_missing_version() -> None:
    text = """
[meta]
generated_at = "2026-05-10T22:14:00Z"
generator = "ergodix 1.x.y index"
corpus_root = "/Users/scott/Tapestry"
"""
    with pytest.raises(ValueError, match="version"):
        parse_map_toml(text)


def test_parse_empty_files_array_is_valid() -> None:
    """A corpus with zero indexable files produces an empty `files` list."""
    text = """
[meta]
version = 1
generated_at = "2026-05-10T22:14:00Z"
generator = "ergodix 1.x.y index"
corpus_root = "/Users/scott/Tapestry"
"""
    m = parse_map_toml(text)
    assert m.files == ()
