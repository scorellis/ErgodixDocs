"""Tests for chunk 3b of ergodix.migrate: manifest TOML I/O + archive mover.

Covers:
  * format_run_id(dt)
  * manifest_path_for_run(corpus_root, run_id)
  * archive_path_for(corpus_root, run_id, source_rel)
  * write_manifest(manifest, path)         — atomic tmp+rename
  * read_manifest(path)
  * find_latest_manifest(corpus_root)
  * move_to_archive(source_path, target_path)
  * Manifest / ManifestEntry dataclass shapes

The schema is locked in ADR 0015 §4. Round-trip tests serve as the
TOML-format regression lock.
"""

from __future__ import annotations

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ergodix.migrate import (
    Manifest,
    ManifestEntry,
    archive_path_for,
    find_latest_manifest,
    format_run_id,
    manifest_path_for_run,
    move_to_archive,
    read_manifest,
    write_manifest,
)

# ─── format_run_id ─────────────────────────────────────────────────────────


def test_format_run_id_yyyy_mm_dd_hhmmss() -> None:
    dt = datetime(2026, 5, 9, 22, 14, 5, tzinfo=UTC)
    assert format_run_id(dt) == "2026-05-09-221405"


def test_format_run_id_pads_single_digits() -> None:
    dt = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert format_run_id(dt) == "2026-01-02-030405"


def test_format_run_id_strips_microseconds() -> None:
    dt = datetime(2026, 5, 9, 22, 14, 5, 999999, tzinfo=UTC)
    assert format_run_id(dt) == "2026-05-09-221405"


def test_format_run_ids_are_lex_sortable_chronologically() -> None:
    earlier = format_run_id(datetime(2026, 5, 9, 22, 14, 0, tzinfo=UTC))
    later = format_run_id(datetime(2026, 5, 10, 1, 0, 0, tzinfo=UTC))
    assert earlier < later


# ─── path helpers ──────────────────────────────────────────────────────────


def test_manifest_path_for_run(tmp_path: Path) -> None:
    p = manifest_path_for_run(tmp_path, "2026-05-10-120000")
    assert p == tmp_path / "_archive" / "_runs" / "2026-05-10-120000.toml"


def test_archive_path_for_simple(tmp_path: Path) -> None:
    p = archive_path_for(tmp_path, "2026-05-10-120000", Path("Book 1/Chapter 3.gdoc"))
    assert p == tmp_path / "_archive" / "2026-05-10-120000" / "Book 1" / "Chapter 3.gdoc"


def test_archive_path_for_root_level(tmp_path: Path) -> None:
    p = archive_path_for(tmp_path, "2026-05-10-120000", Path("Notes.gdoc"))
    assert p == tmp_path / "_archive" / "2026-05-10-120000" / "Notes.gdoc"


# ─── write_manifest / read_manifest ────────────────────────────────────────


def _example_manifest(corpus_root: Path) -> Manifest:
    return Manifest(
        version=1,
        started_at=datetime(2026, 5, 10, 14, 0, 0, tzinfo=UTC),
        finished_at=datetime(2026, 5, 10, 14, 5, 0, tzinfo=UTC),
        generator="ergodix 1.47.0 migrate --from gdocs",
        corpus_root=corpus_root,
        files=(
            ManifestEntry(
                source=Path("Book 1/Chapter 3.gdoc"),
                status="migrated",
                target=Path("Book 1/chapter-3-the-glass-tower.md"),
                sha256="abc123" * 10 + "ab" + "cd",  # 64 chars
                size_bytes=4823,
            ),
            ManifestEntry(
                source=Path("Book 1/Notes.gsheet"),
                status="skipped",
                reason="out-of-scope file type",
            ),
            ManifestEntry(
                source=Path("Book 1/Broken.gdoc"),
                status="failed",
                reason="Docs API returned HTTP 500",
            ),
            ManifestEntry(
                source=Path("Book 2/Chapter 1.gdoc"),
                status="drift-detected",
                target=Path("Book 2/chapter-1.md"),
            ),
        ),
    )


def test_write_manifest_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "_archive" / "_runs" / "2026-05-10-120000.toml"
    assert not target.parent.exists()
    write_manifest(_example_manifest(tmp_path), target)
    assert target.exists()
    assert target.parent.is_dir()


def test_write_manifest_produces_valid_toml(tmp_path: Path) -> None:
    target = tmp_path / "manifest.toml"
    write_manifest(_example_manifest(tmp_path), target)
    parsed = tomllib.loads(target.read_text(encoding="utf-8"))
    assert parsed["meta"]["version"] == 1
    assert parsed["meta"]["generator"] == "ergodix 1.47.0 migrate --from gdocs"
    assert len(parsed["files"]) == 4


def test_write_manifest_includes_all_fields_for_migrated(tmp_path: Path) -> None:
    target = tmp_path / "manifest.toml"
    write_manifest(_example_manifest(tmp_path), target)
    parsed = tomllib.loads(target.read_text(encoding="utf-8"))
    migrated = next(f for f in parsed["files"] if f["status"] == "migrated")
    assert migrated["source"] == "Book 1/Chapter 3.gdoc"
    assert migrated["target"] == "Book 1/chapter-3-the-glass-tower.md"
    assert migrated["sha256"].startswith("abc123")
    assert migrated["size_bytes"] == 4823


def test_write_manifest_omits_unset_fields_for_skipped(tmp_path: Path) -> None:
    """Skipped entries shouldn't carry empty target/sha256/size_bytes keys."""
    target = tmp_path / "manifest.toml"
    write_manifest(_example_manifest(tmp_path), target)
    parsed = tomllib.loads(target.read_text(encoding="utf-8"))
    skipped = next(f for f in parsed["files"] if f["status"] == "skipped")
    assert "target" not in skipped
    assert "sha256" not in skipped
    assert "size_bytes" not in skipped
    assert skipped["reason"] == "out-of-scope file type"


def test_write_manifest_uses_posix_paths(tmp_path: Path) -> None:
    """source/target/corpus_root paths must use forward slashes regardless of OS."""
    target = tmp_path / "manifest.toml"
    nested = Manifest(
        version=1,
        started_at=datetime(2026, 5, 10, tzinfo=UTC),
        finished_at=datetime(2026, 5, 10, tzinfo=UTC),
        generator="ergodix 1.47.0",
        corpus_root=tmp_path,
        files=(
            ManifestEntry(
                source=Path("Book 1") / "Section A" / "Chapter 1.gdoc",
                status="migrated",
                target=Path("Book 1") / "Section A" / "chapter-1.md",
                sha256="0" * 64,
                size_bytes=100,
            ),
        ),
    )
    write_manifest(nested, target)
    parsed = tomllib.loads(target.read_text(encoding="utf-8"))
    assert parsed["files"][0]["source"] == "Book 1/Section A/Chapter 1.gdoc"
    assert parsed["files"][0]["target"] == "Book 1/Section A/chapter-1.md"


def test_write_manifest_iso_timestamps_with_z_suffix(tmp_path: Path) -> None:
    target = tmp_path / "manifest.toml"
    write_manifest(_example_manifest(tmp_path), target)
    body = target.read_text(encoding="utf-8")
    assert 'started_at = "2026-05-10T14:00:00Z"' in body
    assert 'finished_at = "2026-05-10T14:05:00Z"' in body


def test_write_manifest_atomic_no_partial_on_rerun(tmp_path: Path) -> None:
    """A second write replaces atomically — no leftover .tmp file beside the target."""
    target = tmp_path / "manifest.toml"
    write_manifest(_example_manifest(tmp_path), target)
    write_manifest(_example_manifest(tmp_path), target)
    siblings = [p.name for p in target.parent.iterdir()]
    assert siblings == ["manifest.toml"]


def test_read_manifest_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "manifest.toml"
    original = _example_manifest(tmp_path)
    write_manifest(original, target)
    loaded = read_manifest(target)
    assert loaded == original


def test_read_manifest_rejects_unknown_schema_version(tmp_path: Path) -> None:
    target = tmp_path / "manifest.toml"
    target.write_text(
        '[meta]\n'
        'version = 999\n'
        'started_at = "2026-05-10T14:00:00Z"\n'
        'finished_at = "2026-05-10T14:05:00Z"\n'
        'generator = "ergodix 1.47.0"\n'
        'corpus_root = "/tmp"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="schema version"):
        read_manifest(target)


def test_read_manifest_handles_empty_files_list(tmp_path: Path) -> None:
    target = tmp_path / "manifest.toml"
    write_manifest(
        Manifest(
            version=1,
            started_at=datetime(2026, 5, 10, tzinfo=UTC),
            finished_at=datetime(2026, 5, 10, tzinfo=UTC),
            generator="ergodix 1.47.0",
            corpus_root=tmp_path,
            files=(),
        ),
        target,
    )
    loaded = read_manifest(target)
    assert loaded.files == ()


def test_write_manifest_escapes_special_chars_in_strings(tmp_path: Path) -> None:
    """Strings with backslashes / quotes / newlines must round-trip safely."""
    target = tmp_path / "manifest.toml"
    tricky = Manifest(
        version=1,
        started_at=datetime(2026, 5, 10, tzinfo=UTC),
        finished_at=datetime(2026, 5, 10, tzinfo=UTC),
        generator='ergodix 1.47.0 "test" build',
        corpus_root=tmp_path,
        files=(
            ManifestEntry(
                source=Path("weird/path with spaces.gdoc"),
                status="failed",
                reason='extract failed: "permission denied"\nat line 1',
            ),
        ),
    )
    write_manifest(tricky, target)
    loaded = read_manifest(target)
    assert loaded == tricky


# ─── find_latest_manifest ──────────────────────────────────────────────────


def test_find_latest_manifest_returns_none_when_no_archive(tmp_path: Path) -> None:
    assert find_latest_manifest(tmp_path) is None


def test_find_latest_manifest_returns_none_when_runs_dir_empty(tmp_path: Path) -> None:
    (tmp_path / "_archive" / "_runs").mkdir(parents=True)
    assert find_latest_manifest(tmp_path) is None


def test_find_latest_manifest_picks_chronological_latest(tmp_path: Path) -> None:
    earlier_path = manifest_path_for_run(tmp_path, "2026-05-09-220000")
    later_path = manifest_path_for_run(tmp_path, "2026-05-10-100000")

    earlier = Manifest(
        version=1,
        started_at=datetime(2026, 5, 9, 22, tzinfo=UTC),
        finished_at=datetime(2026, 5, 9, 22, 5, tzinfo=UTC),
        generator="ergodix 1.46.0",
        corpus_root=tmp_path,
        files=(),
    )
    later = Manifest(
        version=1,
        started_at=datetime(2026, 5, 10, 10, tzinfo=UTC),
        finished_at=datetime(2026, 5, 10, 10, 5, tzinfo=UTC),
        generator="ergodix 1.47.0",
        corpus_root=tmp_path,
        files=(),
    )
    write_manifest(earlier, earlier_path)
    write_manifest(later, later_path)

    found = find_latest_manifest(tmp_path)
    assert found == later


def test_find_latest_manifest_ignores_non_toml_files(tmp_path: Path) -> None:
    runs = tmp_path / "_archive" / "_runs"
    runs.mkdir(parents=True)
    (runs / "stray.txt").write_text("hi", encoding="utf-8")
    assert find_latest_manifest(tmp_path) is None


# ─── move_to_archive ───────────────────────────────────────────────────────


def test_move_to_archive_moves_file(tmp_path: Path) -> None:
    src = tmp_path / "Chapter 1.gdoc"
    src.write_text("payload", encoding="utf-8")
    dst = tmp_path / "_archive" / "2026-05-10-120000" / "Chapter 1.gdoc"

    move_to_archive(src, dst)

    assert not src.exists()
    assert dst.exists()
    assert dst.read_text(encoding="utf-8") == "payload"


def test_move_to_archive_creates_parent_dirs(tmp_path: Path) -> None:
    src = tmp_path / "Book 1" / "Chapter 1.gdoc"
    src.parent.mkdir(parents=True)
    src.write_text("payload", encoding="utf-8")
    dst = tmp_path / "_archive" / "2026-05-10-120000" / "Book 1" / "Chapter 1.gdoc"

    move_to_archive(src, dst)

    assert dst.exists()
    assert dst.parent.is_dir()


def test_move_to_archive_refuses_to_overwrite(tmp_path: Path) -> None:
    """Two runs with the same run_id shouldn't overwrite each other."""
    src1 = tmp_path / "first.gdoc"
    src2 = tmp_path / "second.gdoc"
    src1.write_text("first", encoding="utf-8")
    src2.write_text("second", encoding="utf-8")
    dst = tmp_path / "_archive" / "run-1" / "name.gdoc"

    move_to_archive(src1, dst)
    with pytest.raises(FileExistsError):
        move_to_archive(src2, dst)
    # Original target untouched.
    assert dst.read_text(encoding="utf-8") == "first"


def test_move_to_archive_raises_on_missing_source(tmp_path: Path) -> None:
    src = tmp_path / "absent.gdoc"
    dst = tmp_path / "_archive" / "x" / "absent.gdoc"
    with pytest.raises(FileNotFoundError):
        move_to_archive(src, dst)
