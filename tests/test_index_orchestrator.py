"""Tests for ergodix.index.generate_index — chunk 2 of the index arc.

Spike 0015 §"Implementation chunks" #2: the orchestrator walks the
corpus, builds the Map, writes `_AI/ergodix.map` atomically (tmp +
rename), and returns a summary record.

Tests against tmp-corpus fixtures only — no network, no real Drive.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ergodix.index import (
    MAP_SCHEMA_VERSION,
    IndexSummary,
    generate_index,
    parse_map_toml,
    write_map,
)

# ─── Happy path ─────────────────────────────────────────────────────────────


def _frozen_now() -> datetime:
    """Deterministic timestamp for tests that pin generated_at."""
    return datetime(2026, 5, 11, 14, 30, 0, tzinfo=UTC)


def test_generate_index_writes_map_at_AI_subdir(tmp_path: Path) -> None:
    """Per ADR 0016 §9: map lives at <corpus>/_AI/ergodix.map."""
    (tmp_path / "Chapter 1.md").write_text("hello")
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    assert summary.map_path == tmp_path / "_AI" / "ergodix.map"
    assert summary.map_path.exists()


def test_generate_index_creates_AI_dir_if_missing(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("hello")
    generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    assert (tmp_path / "_AI").is_dir()


def test_generate_index_returns_file_count(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("a")
    (tmp_path / "Chapter 2.md").write_text("b")
    (tmp_path / "_preamble.tex").write_text("c")
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    assert summary.file_count == 3


def test_generate_index_returns_total_bytes(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_bytes(b"x" * 10)
    (tmp_path / "b.md").write_bytes(b"y" * 25)
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    assert summary.total_bytes == 35


def test_generate_index_uses_now_fn_for_generated_at(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("hello")
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    assert summary.generated_at == "2026-05-11T14:30:00+00:00"


def test_generate_index_map_matches_summary(tmp_path: Path) -> None:
    """The written map and the returned summary agree on generated_at +
    file count."""
    (tmp_path / "Chapter 1.md").write_text("a")
    (tmp_path / "Chapter 2.md").write_text("b")
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    written = parse_map_toml(summary.map_path.read_text(encoding="utf-8"))
    assert written.generated_at == summary.generated_at
    assert len(written.files) == summary.file_count


def test_generate_index_map_has_schema_version_1(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("hello")
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    written = parse_map_toml(summary.map_path.read_text(encoding="utf-8"))
    assert written.version == MAP_SCHEMA_VERSION


def test_generate_index_records_corpus_root_absolute(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("hello")
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    written = parse_map_toml(summary.map_path.read_text(encoding="utf-8"))
    assert Path(written.corpus_root) == tmp_path.resolve()


# ─── Determinism ────────────────────────────────────────────────────────────


def test_generate_index_sorts_entries_by_path(tmp_path: Path) -> None:
    """Determinism: entries always emitted in sorted-path order so the
    serialized map is byte-stable across runs on the same corpus state
    (modulo generated_at)."""
    (tmp_path / "Zebra.md").write_text("z")
    (tmp_path / "Apple.md").write_text("a")
    (tmp_path / "Middle.md").write_text("m")
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    written = parse_map_toml(summary.map_path.read_text(encoding="utf-8"))
    paths = [e.path for e in written.files]
    assert paths == sorted(paths)


def test_generate_index_byte_stable_across_runs(tmp_path: Path) -> None:
    """Spike 0015 §5: 'Re-running on an unchanged corpus produces a
    byte-identical map (modulo the generated_at timestamp).'"""
    (tmp_path / "Chapter 1.md").write_text("hello")
    (tmp_path / "Chapter 2.md").write_text("world")

    generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    first = (tmp_path / "_AI" / "ergodix.map").read_text(encoding="utf-8")

    generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    second = (tmp_path / "_AI" / "ergodix.map").read_text(encoding="utf-8")

    assert first == second


# ─── Atomic write ───────────────────────────────────────────────────────────


def test_generate_index_atomic_write_no_tmp_residue(tmp_path: Path) -> None:
    """After a successful run, no .tmp file is left at _AI/."""
    (tmp_path / "Chapter 1.md").write_text("hello")
    generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    ai_dir = tmp_path / "_AI"
    tmp_files = list(ai_dir.glob("*.tmp"))
    assert tmp_files == []


def test_generate_index_replaces_existing_map(tmp_path: Path) -> None:
    """Re-runs overwrite the prior map (per Spike 0015 §5)."""
    (tmp_path / "Chapter 1.md").write_text("v1")
    generate_index(corpus_root=tmp_path, now_fn=_frozen_now)

    (tmp_path / "Chapter 1.md").write_text("v2-different-content")
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    written = parse_map_toml(summary.map_path.read_text(encoding="utf-8"))
    # Hash of "v2-different-content" must be in the new map.
    import hashlib

    expected = hashlib.sha256(b"v2-different-content").hexdigest()
    assert written.files[0].sha256 == expected


# ─── Edge cases ─────────────────────────────────────────────────────────────


def test_generate_index_empty_corpus(tmp_path: Path) -> None:
    """A corpus with zero indexable files still writes a valid map with
    an empty files array."""
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    assert summary.file_count == 0
    assert summary.total_bytes == 0
    assert summary.map_path.exists()
    written = parse_map_toml(summary.map_path.read_text(encoding="utf-8"))
    assert written.files == ()


def test_generate_index_does_not_index_its_own_map(tmp_path: Path) -> None:
    """The _AI/ergodix.map we just wrote must NOT appear in the next
    run's file list — _AI/ is excluded from the walker (it's not a
    corpus content directory; it's tooling output)."""
    (tmp_path / "Chapter 1.md").write_text("hello")
    generate_index(corpus_root=tmp_path, now_fn=_frozen_now)

    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    written = parse_map_toml(summary.map_path.read_text(encoding="utf-8"))
    assert all("_AI" not in e.path for e in written.files)
    assert summary.file_count == 1


def test_generate_index_skips_existing_map_file_via_skip_dir(tmp_path: Path) -> None:
    """Even if a user manually placed a file under _AI/, the walker
    skips the entire directory."""
    (tmp_path / "_AI").mkdir()
    (tmp_path / "_AI" / "stale.md").write_text("not corpus content")
    (tmp_path / "Chapter 1.md").write_text("real")
    summary = generate_index(corpus_root=tmp_path, now_fn=_frozen_now)
    written = parse_map_toml(summary.map_path.read_text(encoding="utf-8"))
    paths = [e.path for e in written.files]
    assert paths == ["Chapter 1.md"]


# ─── write_map (the helper used by generate_index + later read_map) ─────────


def test_write_map_creates_parent_dirs(tmp_path: Path) -> None:
    """write_map should create the _AI/ dir if missing."""
    from ergodix.index import Map

    m = Map(
        version=MAP_SCHEMA_VERSION,
        generated_at="2026-05-11T14:30:00+00:00",
        generator="ergodix test",
        corpus_root=str(tmp_path),
        files=(),
    )
    target = tmp_path / "deep" / "nest" / "ergodix.map"
    write_map(m, target)
    assert target.exists()


def test_write_map_is_atomic_no_tmp_residue(tmp_path: Path) -> None:
    from ergodix.index import Map

    m = Map(
        version=MAP_SCHEMA_VERSION,
        generated_at="2026-05-11T14:30:00+00:00",
        generator="ergodix test",
        corpus_root=str(tmp_path),
        files=(),
    )
    target = tmp_path / "ergodix.map"
    write_map(m, target)
    assert list(tmp_path.glob("*.tmp")) == []


# ─── IndexSummary dataclass ─────────────────────────────────────────────────


def test_index_summary_is_a_frozen_dataclass() -> None:
    """Per the pattern of MigrateResult — frozen so callers can't
    mutate the record after the orchestrator returned it."""
    summary = IndexSummary(
        map_path=Path("/var/folders/example/_AI/ergodix.map"),
        file_count=3,
        total_bytes=4567,
        generated_at="2026-05-11T14:30:00+00:00",
    )
    with pytest.raises((AttributeError, Exception)):
        summary.file_count = 99  # type: ignore[misc]
