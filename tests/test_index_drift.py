"""Tests for compare_to_map + drift report — chunk 3 of the index arc.

Spike 0015 §"Implementation chunks" #3: given an existing map and a
fresh walk, compute new / changed / removed file sets. Pure functions
(no FS); the CLI in chunk 4 will compose `read_map` + `generate_index`
(without write) and pass both Maps to `compare_to_map`.

Also covers `read_map(path)` — companion to chunk 2's `write_map`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ergodix.index import (
    MAP_SCHEMA_VERSION,
    DriftReport,
    IndexEntry,
    Map,
    compare_to_map,
    read_map,
    write_map,
)


def _map(*entries: IndexEntry, generated_at: str = "2026-05-11T00:00:00+00:00") -> Map:
    return Map(
        version=MAP_SCHEMA_VERSION,
        generated_at=generated_at,
        generator="ergodix test",
        corpus_root="/var/folders/example/corpus",
        files=tuple(entries),
    )


def _entry(path: str, sha: str = "a" * 64, size: int = 100) -> IndexEntry:
    return IndexEntry(
        path=path,
        sha256=sha,
        size_bytes=size,
        mtime="2026-05-11T00:00:00+00:00",
    )


# ─── compare_to_map ─────────────────────────────────────────────────────────


def test_compare_identical_maps_has_no_drift() -> None:
    existing = _map(_entry("Chapter 1.md"), _entry("Chapter 2.md"))
    current = _map(_entry("Chapter 1.md"), _entry("Chapter 2.md"))
    report = compare_to_map(existing=existing, current=current)
    assert report.new_files == ()
    assert report.changed_files == ()
    assert report.removed_files == ()
    assert not report.has_drift


def test_compare_detects_new_file() -> None:
    existing = _map(_entry("Chapter 1.md"))
    current = _map(_entry("Chapter 1.md"), _entry("Chapter 2.md"))
    report = compare_to_map(existing=existing, current=current)
    assert report.new_files == ("Chapter 2.md",)
    assert report.changed_files == ()
    assert report.removed_files == ()
    assert report.has_drift


def test_compare_detects_removed_file() -> None:
    existing = _map(_entry("Chapter 1.md"), _entry("Chapter 2.md"))
    current = _map(_entry("Chapter 1.md"))
    report = compare_to_map(existing=existing, current=current)
    assert report.new_files == ()
    assert report.changed_files == ()
    assert report.removed_files == ("Chapter 2.md",)
    assert report.has_drift


def test_compare_detects_changed_file_by_sha256() -> None:
    """Per ADR 0016 §3: SHA-256 is authoritative for drift; mtime is
    advisory only."""
    existing = _map(_entry("Chapter 1.md", sha="a" * 64))
    current = _map(_entry("Chapter 1.md", sha="b" * 64))
    report = compare_to_map(existing=existing, current=current)
    assert report.new_files == ()
    assert report.changed_files == ("Chapter 1.md",)
    assert report.removed_files == ()
    assert report.has_drift


def test_compare_ignores_mtime_when_sha_matches() -> None:
    """ADR 0016 §3: two entries with different mtime but matching sha
    are equivalent."""
    existing_entry = IndexEntry(
        path="Chapter 1.md",
        sha256="a" * 64,
        size_bytes=100,
        mtime="2026-01-01T00:00:00+00:00",
    )
    current_entry = IndexEntry(
        path="Chapter 1.md",
        sha256="a" * 64,
        size_bytes=100,
        mtime="2026-12-31T23:59:59+00:00",
    )
    report = compare_to_map(existing=_map(existing_entry), current=_map(current_entry))
    assert not report.has_drift


def test_compare_handles_all_three_classes_at_once() -> None:
    existing = _map(
        _entry("Removed.md"),
        _entry("Unchanged.md", sha="c" * 64),
        _entry("Changed.md", sha="a" * 64),
    )
    current = _map(
        _entry("Unchanged.md", sha="c" * 64),
        _entry("Changed.md", sha="b" * 64),
        _entry("New.md"),
    )
    report = compare_to_map(existing=existing, current=current)
    assert report.new_files == ("New.md",)
    assert report.changed_files == ("Changed.md",)
    assert report.removed_files == ("Removed.md",)


def test_compare_sorts_paths_in_each_bucket() -> None:
    """Determinism: paths within each bucket are sorted so the report
    is reproducible regardless of input order."""
    existing = _map()
    current = _map(_entry("Zebra.md"), _entry("Apple.md"), _entry("Middle.md"))
    report = compare_to_map(existing=existing, current=current)
    assert report.new_files == ("Apple.md", "Middle.md", "Zebra.md")


def test_compare_empty_to_empty() -> None:
    report = compare_to_map(existing=_map(), current=_map())
    assert not report.has_drift


def test_compare_empty_to_populated_all_new() -> None:
    """Initial-index case: comparing against an empty/missing prior
    state reports every current file as new."""
    existing = _map()
    current = _map(_entry("Chapter 1.md"), _entry("Chapter 2.md"))
    report = compare_to_map(existing=existing, current=current)
    assert report.new_files == ("Chapter 1.md", "Chapter 2.md")
    assert report.changed_files == ()
    assert report.removed_files == ()


def test_compare_populated_to_empty_all_removed() -> None:
    """Corpus-deleted case: every existing entry reports as removed."""
    existing = _map(_entry("Chapter 1.md"), _entry("Chapter 2.md"))
    current = _map()
    report = compare_to_map(existing=existing, current=current)
    assert report.new_files == ()
    assert report.changed_files == ()
    assert report.removed_files == ("Chapter 1.md", "Chapter 2.md")


# ─── DriftReport dataclass ──────────────────────────────────────────────────


def test_drift_report_is_frozen() -> None:
    report = DriftReport(
        new_files=("a.md",),
        changed_files=(),
        removed_files=(),
    )
    with pytest.raises((AttributeError, Exception)):
        report.new_files = ()  # type: ignore[misc]


def test_drift_report_has_drift_property_true_on_any_diff() -> None:
    assert DriftReport(new_files=("a.md",), changed_files=(), removed_files=()).has_drift
    assert DriftReport(new_files=(), changed_files=("a.md",), removed_files=()).has_drift
    assert DriftReport(new_files=(), changed_files=(), removed_files=("a.md",)).has_drift


def test_drift_report_has_drift_property_false_when_all_empty() -> None:
    assert not DriftReport(new_files=(), changed_files=(), removed_files=()).has_drift


# ─── read_map ───────────────────────────────────────────────────────────────


def test_read_map_round_trips_write_map(tmp_path: Path) -> None:
    """read_map + write_map are inverses (composition of the two
    yields the original Map)."""
    original = _map(_entry("Chapter 1.md"), _entry("Chapter 2.md"))
    target = tmp_path / "ergodix.map"
    write_map(original, target)
    loaded = read_map(target)
    assert loaded == original


def test_read_map_refuses_unknown_version(tmp_path: Path) -> None:
    """Per ADR 0016 §1: strict version refusal applies at the read
    helper too — same defense for the disk path that parse_map_toml
    enforces for raw text."""
    bad = tmp_path / "ergodix.map"
    bad.write_text(
        """[meta]
version = 99
generated_at = "2026-05-11T00:00:00+00:00"
generator = "x"
corpus_root = "/var/folders/example/corpus"
"""
    )
    with pytest.raises(ValueError, match="version"):
        read_map(bad)


def test_read_map_raises_on_missing_file(tmp_path: Path) -> None:
    """read_map on a path that doesn't exist raises FileNotFoundError
    (the caller — chunk 4 CLI — handles this to print 'no prior
    index' vs proceeding with `Map(files=())`)."""
    with pytest.raises(FileNotFoundError):
        read_map(tmp_path / "missing.map")
