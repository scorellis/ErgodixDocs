"""Hermetic end-to-end tests for `ergodix index` against the committed
fixture corpus at examples/index-fixture/.

Spike 0015 §"Implementation chunks" #5: cover the index path end-to-end
alongside migrate's hermetic e2e. Tests copy the fixture to a tmp_path
so they never mutate the tracked content; the CLI is invoked via
Click's CliRunner.

The fixture's expected indexable file set (per its README):

  1. README.md
  2. _preamble.tex
  3. Book 1/_preamble.tex
  4. Book 1/Chapter 1.md
  5. Book 1/Chapter 2.md
  6. Book 1/Section A/Chapter 3.md

Plus three deliberately excluded paths to verify walker rules:

  - _archive/Old Chapter.md           (skip dir per Spike 0015 §2)
  - scratch/draft.md                  (.ergodix-skip marker in dir)
  - _media/ contents (if any present) (skip dir per Spike 0015 §2)
"""

from __future__ import annotations

import shutil
from pathlib import Path

from click.testing import CliRunner

from ergodix.cli import main
from ergodix.index import read_map

FIXTURE = Path(__file__).resolve().parent.parent / "examples" / "index-fixture"

EXPECTED_PATHS = {
    "README.md",
    "_preamble.tex",
    "Book 1/_preamble.tex",
    "Book 1/Chapter 1.md",
    "Book 1/Chapter 2.md",
    "Book 1/Section A/Chapter 3.md",
}

EXCLUDED_PATHS = {
    "_archive/Old Chapter.md",
    "scratch/draft.md",
}


def _copy_fixture(tmp_path: Path) -> Path:
    """Copy the committed fixture into tmp_path/corpus and return the
    new corpus root. Hermetic: never mutates the tracked fixture."""
    dst = tmp_path / "corpus"
    shutil.copytree(FIXTURE, dst)
    return dst


def test_fixture_exists() -> None:
    """Sanity check: the fixture directory should be in-tree."""
    assert FIXTURE.is_dir(), f"missing fixture at {FIXTURE}"
    assert (FIXTURE / "README.md").is_file()
    assert (FIXTURE / "Book 1" / "Chapter 1.md").is_file()


def test_fixture_e2e_index_default_writes_map(tmp_path: Path) -> None:
    """A default `ergodix index` run against the fixture writes a map
    at _AI/ergodix.map and exits 0."""
    corpus = _copy_fixture(tmp_path)
    result = CliRunner().invoke(main, ["index", "--corpus", str(corpus)])
    assert result.exit_code == 0, result.output
    assert (corpus / "_AI" / "ergodix.map").exists()


def test_fixture_e2e_index_records_expected_files(tmp_path: Path) -> None:
    """The produced map's file paths match the fixture's expected set
    (per its README). Pins the walker scope (.md + .tex) and the skip
    rules (_archive, .ergodix-skip, _media)."""
    corpus = _copy_fixture(tmp_path)
    CliRunner().invoke(main, ["index", "--corpus", str(corpus)])

    m = read_map(corpus / "_AI" / "ergodix.map")
    indexed = {e.path for e in m.files}
    assert indexed == EXPECTED_PATHS


def test_fixture_e2e_index_excludes_archive_and_skipped(tmp_path: Path) -> None:
    """The map must NOT contain any file from _archive/ or any
    .ergodix-skip-scoped directory."""
    corpus = _copy_fixture(tmp_path)
    CliRunner().invoke(main, ["index", "--corpus", str(corpus)])

    m = read_map(corpus / "_AI" / "ergodix.map")
    indexed = {e.path for e in m.files}
    assert indexed.isdisjoint(EXCLUDED_PATHS)


def test_fixture_e2e_check_passes_after_generate(tmp_path: Path) -> None:
    """`ergodix index` followed immediately by `ergodix index --check`
    should report no drift (exit 0)."""
    corpus = _copy_fixture(tmp_path)
    CliRunner().invoke(main, ["index", "--corpus", str(corpus)])
    result = CliRunner().invoke(main, ["index", "--check", "--corpus", str(corpus)])
    assert result.exit_code == 0, result.output


def test_fixture_e2e_check_fails_after_chapter_edit(tmp_path: Path) -> None:
    """Editing a chapter's content (changing its SHA-256) makes
    `--check` report drift and exit 1 (per ADR 0016 §6)."""
    corpus = _copy_fixture(tmp_path)
    CliRunner().invoke(main, ["index", "--corpus", str(corpus)])

    chapter = corpus / "Book 1" / "Chapter 1.md"
    chapter.write_text(chapter.read_text() + "\n\nAppended for drift test.\n")

    result = CliRunner().invoke(main, ["index", "--check", "--corpus", str(corpus)])
    assert result.exit_code == 1
    assert "Book 1/Chapter 1.md" in result.output


def test_fixture_e2e_check_fails_after_new_file(tmp_path: Path) -> None:
    """Adding a new chapter to the corpus surfaces as drift in --check."""
    corpus = _copy_fixture(tmp_path)
    CliRunner().invoke(main, ["index", "--corpus", str(corpus)])

    (corpus / "Book 1" / "Chapter 4.md").write_text("New chapter content")

    result = CliRunner().invoke(main, ["index", "--check", "--corpus", str(corpus)])
    assert result.exit_code == 1
    assert "Chapter 4.md" in result.output


def test_fixture_e2e_check_fails_after_chapter_removal(tmp_path: Path) -> None:
    """Removing a chapter surfaces as drift in --check."""
    corpus = _copy_fixture(tmp_path)
    CliRunner().invoke(main, ["index", "--corpus", str(corpus)])

    (corpus / "Book 1" / "Chapter 2.md").unlink()

    result = CliRunner().invoke(main, ["index", "--check", "--corpus", str(corpus)])
    assert result.exit_code == 1
    assert "Book 1/Chapter 2.md" in result.output


def test_fixture_e2e_round_trip_clears_drift(tmp_path: Path) -> None:
    """After modifying the corpus, a fresh `ergodix index` (no flags)
    rewrites the map and a subsequent `--check` returns to exit 0."""
    corpus = _copy_fixture(tmp_path)
    CliRunner().invoke(main, ["index", "--corpus", str(corpus)])

    # Drift.
    (corpus / "Book 1" / "Chapter 1.md").write_text("modified")
    r = CliRunner().invoke(main, ["index", "--check", "--corpus", str(corpus)])
    assert r.exit_code == 1

    # Re-generate.
    r = CliRunner().invoke(main, ["index", "--corpus", str(corpus)])
    assert r.exit_code == 0

    # No drift.
    r = CliRunner().invoke(main, ["index", "--check", "--corpus", str(corpus)])
    assert r.exit_code == 0


def test_fixture_e2e_count_in_summary_matches_expected(tmp_path: Path) -> None:
    """The default-mode summary line reports 6 files (the fixture's
    expected indexable count)."""
    corpus = _copy_fixture(tmp_path)
    result = CliRunner().invoke(main, ["index", "--corpus", str(corpus)])
    assert result.exit_code == 0
    assert "6 files" in result.output
