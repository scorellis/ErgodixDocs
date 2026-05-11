"""Tests for the `ergodix index` CLI subcommand — chunk 4 of the index arc.

Spike 0015 §"Implementation chunks" #4: real CLI command with
``--check`` / ``--corpus`` / ``--quiet``. Exit codes match Spike 0015
§4 / ADR 0016 §6:

  0 = no drift detected (or, in non-check mode, map updated successfully)
  1 = drift detected (in --check mode only)
  2 = bad invocation (missing corpus, etc.)
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from ergodix.cli import main
from ergodix.index import read_map

# ─── Default mode: regenerates the map ──────────────────────────────────────


def test_index_default_writes_map(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("hello")
    result = CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "_AI" / "ergodix.map").exists()


def test_index_default_prints_summary(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("a")
    (tmp_path / "Chapter 2.md").write_text("b")
    result = CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])
    assert result.exit_code == 0
    # Summary mentions the file count somewhere.
    assert "2" in result.output


def test_index_default_replaces_existing_map(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("v1")
    CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])

    (tmp_path / "Chapter 1.md").write_text("v2-different")
    result = CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])
    assert result.exit_code == 0
    written = read_map(tmp_path / "_AI" / "ergodix.map")
    # The new content's hash must be in the map.
    import hashlib

    expected = hashlib.sha256(b"v2-different").hexdigest()
    assert written.files[0].sha256 == expected


# ─── --check mode: drift detection, no write ────────────────────────────────


def test_index_check_exits_0_when_map_matches(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("hello")
    # Establish the baseline map.
    CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])
    # Re-check with no changes.
    result = CliRunner().invoke(main, ["index", "--check", "--corpus", str(tmp_path)])
    assert result.exit_code == 0


def test_index_check_exits_1_on_drift_new_file(tmp_path: Path) -> None:
    """Per ADR 0016 §6: --check exits 1 on drift."""
    (tmp_path / "Chapter 1.md").write_text("hello")
    CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])

    # Add a new file -> drift.
    (tmp_path / "Chapter 2.md").write_text("world")
    result = CliRunner().invoke(main, ["index", "--check", "--corpus", str(tmp_path)])
    assert result.exit_code == 1


def test_index_check_exits_1_on_drift_changed_content(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("hello")
    CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])

    (tmp_path / "Chapter 1.md").write_text("modified")
    result = CliRunner().invoke(main, ["index", "--check", "--corpus", str(tmp_path)])
    assert result.exit_code == 1


def test_index_check_exits_1_on_drift_removed_file(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("hello")
    (tmp_path / "Chapter 2.md").write_text("world")
    CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])

    (tmp_path / "Chapter 2.md").unlink()
    result = CliRunner().invoke(main, ["index", "--check", "--corpus", str(tmp_path)])
    assert result.exit_code == 1


def test_index_check_does_not_write_map(tmp_path: Path) -> None:
    """--check must NOT touch _AI/ergodix.map — it's read-only."""
    (tmp_path / "Chapter 1.md").write_text("hello")
    CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])

    map_path = tmp_path / "_AI" / "ergodix.map"
    before = map_path.read_text()

    (tmp_path / "Chapter 2.md").write_text("drift")
    CliRunner().invoke(main, ["index", "--check", "--corpus", str(tmp_path)])

    after = map_path.read_text()
    assert before == after


def test_index_check_reports_drift_buckets(tmp_path: Path) -> None:
    """Drift output mentions new / changed / removed files."""
    (tmp_path / "Stays.md").write_text("unchanged")
    (tmp_path / "Changes.md").write_text("v1")
    (tmp_path / "Removed.md").write_text("doomed")
    CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])

    (tmp_path / "Changes.md").write_text("v2")
    (tmp_path / "Removed.md").unlink()
    (tmp_path / "New.md").write_text("appeared")

    result = CliRunner().invoke(main, ["index", "--check", "--corpus", str(tmp_path)])
    assert result.exit_code == 1
    assert "New.md" in result.output
    assert "Changes.md" in result.output
    assert "Removed.md" in result.output


def test_index_check_with_no_prior_map_treats_all_as_new(tmp_path: Path) -> None:
    """If _AI/ergodix.map doesn't exist, --check reports every current
    file as 'new' and exits 1."""
    (tmp_path / "Chapter 1.md").write_text("hello")
    result = CliRunner().invoke(main, ["index", "--check", "--corpus", str(tmp_path)])
    assert result.exit_code == 1
    assert "Chapter 1.md" in result.output


# ─── --quiet ────────────────────────────────────────────────────────────────


def test_index_quiet_suppresses_per_file_output(tmp_path: Path) -> None:
    (tmp_path / "Chapter 1.md").write_text("a")
    (tmp_path / "Chapter 2.md").write_text("b")
    result = CliRunner().invoke(main, ["index", "--quiet", "--corpus", str(tmp_path)])
    assert result.exit_code == 0
    # Per-file paths should not be in the output under --quiet.
    assert "Chapter 1.md" not in result.output
    assert "Chapter 2.md" not in result.output


def test_index_quiet_still_prints_summary_line(tmp_path: Path) -> None:
    """--quiet keeps the one-line summary; only suppresses per-file detail."""
    (tmp_path / "Chapter 1.md").write_text("a")
    result = CliRunner().invoke(main, ["index", "--quiet", "--corpus", str(tmp_path)])
    assert result.exit_code == 0
    # Some summary text appears — at minimum the file count.
    assert "1" in result.output


# ─── --corpus override + missing corpus ─────────────────────────────────────


def test_index_missing_corpus_arg_and_no_local_config_exits_1(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """No --corpus and no CORPUS_FOLDER in local_config.py → exit 1 with
    a clear error. Mirrors migrate's behavior (ergodix/cli.py around the
    `read_corpus_folder_from_local_config` block)."""
    # Run from a directory that has no local_config.py.
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["index"])
    assert result.exit_code == 1
    assert "corpus" in result.output.lower()


# ─── End-to-end: default run then --check round-trip ────────────────────────


def test_index_end_to_end_round_trip(tmp_path: Path) -> None:
    """Realistic workflow: generate, then --check confirms no drift,
    then a modification triggers drift, then a re-generate clears it."""
    (tmp_path / "Book 1").mkdir()
    (tmp_path / "Book 1" / "Chapter 1.md").write_text("dragons")
    (tmp_path / "_preamble.tex").write_text("\\usepackage{amsmath}")

    # 1. Generate baseline.
    r = CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])
    assert r.exit_code == 0

    # 2. --check should pass.
    r = CliRunner().invoke(main, ["index", "--check", "--corpus", str(tmp_path)])
    assert r.exit_code == 0

    # 3. Modify a chapter -> --check fails.
    (tmp_path / "Book 1" / "Chapter 1.md").write_text("dragons and trains")
    r = CliRunner().invoke(main, ["index", "--check", "--corpus", str(tmp_path)])
    assert r.exit_code == 1

    # 4. Re-generate clears drift -> --check passes again.
    r = CliRunner().invoke(main, ["index", "--corpus", str(tmp_path)])
    assert r.exit_code == 0
    r = CliRunner().invoke(main, ["index", "--check", "--corpus", str(tmp_path)])
    assert r.exit_code == 0
