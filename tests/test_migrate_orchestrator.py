"""Tests for chunk 3c — the migrate_run() orchestrator.

The orchestrator stitches helpers + walker + importer registry +
manifest + archive together. These tests exercise it against a real
gdocs importer with a mocked docs_service so no test touches network.
Per ADR 0015 §5, re-run semantics are: skip unchanged, flag drift,
honor --force, and --check is a clean dry-run.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from ergodix.migrate import (
    MigrateResult,
    migrate_run,
    read_manifest,
)

# ─── helpers ───────────────────────────────────────────────────────────────


def _write_gdoc(path: Path, doc_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"doc_id": doc_id}), encoding="utf-8")


def _para(text: str, *, style: str = "NORMAL_TEXT") -> dict[str, Any]:
    return {
        "paragraph": {
            "elements": [{"textRun": {"content": text, "textStyle": {}}}],
            "paragraphStyle": {"namedStyleType": style},
        },
    }


def _doc(text: str) -> dict[str, Any]:
    """Fake Docs API document containing one normal paragraph."""
    return {
        "documentId": "x",
        "title": "x",
        "body": {"content": [_para(text + "\n")]},
    }


def _mock_docs_service(docs_by_id: dict[str, dict[str, Any]]) -> MagicMock:
    service = MagicMock()

    def get(*, documentId: str) -> MagicMock:
        request = MagicMock()
        if documentId in docs_by_id:
            request.execute.return_value = docs_by_id[documentId]
        else:
            request.execute.side_effect = RuntimeError(f"unknown doc {documentId}")
        return request

    service.documents.return_value.get.side_effect = get
    return service


def _frozen_now(dt: datetime) -> Any:
    return lambda: dt


_RUN_TIME = datetime(2026, 5, 10, 14, 0, 0, tzinfo=UTC)
_RUN_ID = "2026-05-10-140000"


# ─── happy paths ───────────────────────────────────────────────────────────


def test_happy_path_single_file(tmp_path: Path) -> None:
    _write_gdoc(tmp_path / "Chapter 1.gdoc", "doc-1")
    docs = _mock_docs_service({"doc-1": _doc("Hello world.")})

    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs,
        author="Test Author",
        now_fn=_frozen_now(_RUN_TIME),
    )

    assert isinstance(result, MigrateResult)
    assert result.counts == {"migrated": 1}
    assert result.run_id == _RUN_ID

    target = tmp_path / "chapter-1.md"
    assert target.exists()
    body = target.read_text(encoding="utf-8")
    assert "Hello world." in body
    assert 'title: "Chapter 1"' in body
    assert 'author: "Test Author"' in body
    assert 'source: "Chapter 1.gdoc"' in body
    assert 'migrated_at: "2026-05-10T14:00:00Z"' in body

    archived = tmp_path / "_archive" / _RUN_ID / "Chapter 1.gdoc"
    assert archived.exists()
    assert not (tmp_path / "Chapter 1.gdoc").exists()

    manifest_path = tmp_path / "_archive" / "_runs" / f"{_RUN_ID}.toml"
    manifest = read_manifest(manifest_path)
    assert manifest.generator.startswith("ergodix ")
    assert "migrate --from gdocs" in manifest.generator
    entry = manifest.files[0]
    assert entry.status == "migrated"
    assert entry.source == Path("Chapter 1.gdoc")
    assert entry.target == Path("chapter-1.md")
    assert entry.sha256 is not None
    assert entry.size_bytes is not None
    assert entry.size_bytes > 0


def test_happy_path_multiple_files_nested(tmp_path: Path) -> None:
    _write_gdoc(tmp_path / "Book 1" / "Chapter 1.gdoc", "doc-1")
    _write_gdoc(tmp_path / "Book 1" / "Chapter 2.gdoc", "doc-2")
    _write_gdoc(tmp_path / "Book 2" / "Chapter A.gdoc", "doc-3")
    docs = _mock_docs_service(
        {
            "doc-1": _doc("First."),
            "doc-2": _doc("Second."),
            "doc-3": _doc("Third."),
        }
    )

    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs,
        author="A",
        now_fn=_frozen_now(_RUN_TIME),
    )

    assert result.counts == {"migrated": 3}
    assert (tmp_path / "Book 1" / "chapter-1.md").exists()
    assert (tmp_path / "Book 1" / "chapter-2.md").exists()
    assert (tmp_path / "Book 2" / "chapter-a.md").exists()
    assert (tmp_path / "_archive" / _RUN_ID / "Book 1" / "Chapter 1.gdoc").exists()


# ─── --check (dry-run) ─────────────────────────────────────────────────────


def test_check_makes_no_filesystem_changes(tmp_path: Path) -> None:
    _write_gdoc(tmp_path / "Chapter 1.gdoc", "doc-1")
    docs = _mock_docs_service({"doc-1": _doc("Hello.")})

    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs,
        author="A",
        check=True,
        now_fn=_frozen_now(_RUN_TIME),
    )

    assert result.counts == {"migrated": 1}
    assert result.manifest_path is None

    # Source not moved, target not written, no _archive at all.
    assert (tmp_path / "Chapter 1.gdoc").exists()
    assert not (tmp_path / "chapter-1.md").exists()
    assert not (tmp_path / "_archive").exists()


def test_check_still_classifies_outcomes(tmp_path: Path) -> None:
    _write_gdoc(tmp_path / "Chapter 1.gdoc", "doc-1")
    (tmp_path / "Notes.gsheet").write_text("{}", encoding="utf-8")
    docs = _mock_docs_service({"doc-1": _doc("Hello.")})

    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs,
        author="A",
        check=True,
        now_fn=_frozen_now(_RUN_TIME),
    )

    statuses = {f.source.name: f.status for f in result.files}
    assert statuses["Chapter 1.gdoc"] == "migrated"
    assert statuses["Notes.gsheet"] == "skipped"


# ─── out-of-scope / wrong-importer files ──────────────────────────────────


def test_out_of_scope_files_recorded_as_skipped(tmp_path: Path) -> None:
    _write_gdoc(tmp_path / "Chapter 1.gdoc", "doc-1")
    (tmp_path / "Notes.gsheet").write_text("{}", encoding="utf-8")
    (tmp_path / "Random.xyz").write_text("noise", encoding="utf-8")
    docs = _mock_docs_service({"doc-1": _doc("Hello.")})

    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs,
        author="A",
        now_fn=_frozen_now(_RUN_TIME),
    )

    assert result.counts.get("migrated") == 1
    assert result.counts.get("skipped") == 2
    skipped = [f for f in result.files if f.status == "skipped"]
    reasons = {f.source.name: f.reason for f in skipped}
    assert "out-of-scope" in (reasons["Notes.gsheet"] or "").lower()
    assert "out-of-scope" in (reasons["Random.xyz"] or "").lower()


# ─── --limit ───────────────────────────────────────────────────────────────


def test_limit_caps_eligible_files(tmp_path: Path) -> None:
    for i in range(5):
        _write_gdoc(tmp_path / f"Chapter {i}.gdoc", f"doc-{i}")
    docs = _mock_docs_service({f"doc-{i}": _doc(f"#{i}") for i in range(5)})

    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs,
        author="A",
        limit=2,
        now_fn=_frozen_now(_RUN_TIME),
    )

    assert result.counts.get("migrated") == 2
    # Three left in place at original location.
    remaining = list(tmp_path.glob("Chapter *.gdoc"))
    assert len(remaining) == 3


# ─── phase 1 failures ──────────────────────────────────────────────────────


def test_phase_1_extraction_failure_records_failed_status(tmp_path: Path) -> None:
    _write_gdoc(tmp_path / "Good.gdoc", "doc-good")
    _write_gdoc(tmp_path / "Bad.gdoc", "doc-bad")
    docs = MagicMock()

    def get(*, documentId: str) -> MagicMock:
        request = MagicMock()
        if documentId == "doc-good":
            request.execute.return_value = _doc("Good content.")
        else:
            request.execute.side_effect = RuntimeError("Docs API HTTP 500")
        return request

    docs.documents.return_value.get.side_effect = get

    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs,
        author="A",
        now_fn=_frozen_now(_RUN_TIME),
    )

    assert result.counts.get("migrated") == 1
    assert result.counts.get("failed") == 1
    failed = next(f for f in result.files if f.status == "failed")
    assert failed.source == Path("Bad.gdoc")
    assert failed.reason is not None
    assert "Docs API HTTP 500" in failed.reason
    # Bad source must remain at its original location for re-run.
    assert (tmp_path / "Bad.gdoc").exists()
    # Good source was archived.
    assert not (tmp_path / "Good.gdoc").exists()


# ─── re-run semantics: unchanged / drift / --force ─────────────────────────


def test_rerun_unchanged_source_skipped(tmp_path: Path) -> None:
    """If a previously-migrated source reappears with identical content, skip it."""
    _write_gdoc(tmp_path / "Chapter 1.gdoc", "doc-1")
    docs = _mock_docs_service({"doc-1": _doc("Stable content.")})

    # First run.
    migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs,
        author="A",
        now_fn=_frozen_now(_RUN_TIME),
    )

    # Simulate the source reappearing at original location (e.g. via Drive Mirror).
    _write_gdoc(tmp_path / "Chapter 1.gdoc", "doc-1")

    # Second run, an hour later.
    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs,
        author="A",
        now_fn=_frozen_now(datetime(2026, 5, 10, 15, 0, 0, tzinfo=UTC)),
    )

    assert result.counts == {"skipped": 1}
    skipped = result.files[0]
    assert "unchanged" in (skipped.reason or "").lower()
    # Source not moved (stayed in place since we skipped it).
    assert (tmp_path / "Chapter 1.gdoc").exists()


def test_rerun_drift_recorded_not_remigrated(tmp_path: Path) -> None:
    """Source content changed since last migrate → drift-detected, no re-migrate."""
    _write_gdoc(tmp_path / "Chapter 1.gdoc", "doc-1")
    docs_v1 = _mock_docs_service({"doc-1": _doc("Original content.")})

    migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs_v1,
        author="A",
        now_fn=_frozen_now(_RUN_TIME),
    )

    # Simulate drift: source reappears, but the underlying Doc has been edited.
    _write_gdoc(tmp_path / "Chapter 1.gdoc", "doc-1")
    docs_v2 = _mock_docs_service({"doc-1": _doc("Edited content!")})

    target_before = (tmp_path / "chapter-1.md").read_text(encoding="utf-8")

    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs_v2,
        author="A",
        now_fn=_frozen_now(datetime(2026, 5, 10, 15, 0, 0, tzinfo=UTC)),
    )

    assert result.counts == {"drift-detected": 1}
    # Existing target untouched.
    assert (tmp_path / "chapter-1.md").read_text(encoding="utf-8") == target_before
    # Source still at original location (we didn't move what we didn't migrate).
    assert (tmp_path / "Chapter 1.gdoc").exists()


def test_rerun_force_remigrates_drifted_source(tmp_path: Path) -> None:
    _write_gdoc(tmp_path / "Chapter 1.gdoc", "doc-1")
    docs_v1 = _mock_docs_service({"doc-1": _doc("Original content.")})

    migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs_v1,
        author="A",
        now_fn=_frozen_now(_RUN_TIME),
    )

    _write_gdoc(tmp_path / "Chapter 1.gdoc", "doc-1")
    docs_v2 = _mock_docs_service({"doc-1": _doc("Edited content!")})

    later = datetime(2026, 5, 10, 15, 0, 0, tzinfo=UTC)
    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs_v2,
        author="A",
        force=True,
        now_fn=_frozen_now(later),
    )

    assert result.counts == {"migrated": 1}
    body = (tmp_path / "chapter-1.md").read_text(encoding="utf-8")
    assert "Edited content!" in body
    # Source moved to the new run's archive.
    assert (tmp_path / "_archive" / "2026-05-10-150000" / "Chapter 1.gdoc").exists()


# ─── miscellaneous shape assertions ────────────────────────────────────────


def test_empty_corpus_returns_empty_result(tmp_path: Path) -> None:
    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=MagicMock(),
        author="A",
        now_fn=_frozen_now(_RUN_TIME),
    )
    assert result.counts == {}
    assert result.files == ()


def test_unknown_importer_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError, match="unknown importer"):
        migrate_run(
            corpus_root=tmp_path,
            importer_name="totally-fake",
            docs_service=MagicMock(),
            author="A",
            now_fn=_frozen_now(_RUN_TIME),
        )


def test_ergodix_skip_marker_excludes_folder(tmp_path: Path) -> None:
    _write_gdoc(tmp_path / "Drafts" / "rough.gdoc", "doc-rough")
    (tmp_path / "Drafts" / ".ergodix-skip").write_text("", encoding="utf-8")
    _write_gdoc(tmp_path / "Polished" / "Chapter 1.gdoc", "doc-clean")
    docs = _mock_docs_service(
        {
            "doc-rough": _doc("rough"),
            "doc-clean": _doc("clean"),
        }
    )

    result = migrate_run(
        corpus_root=tmp_path,
        importer_name="gdocs",
        docs_service=docs,
        author="A",
        now_fn=_frozen_now(_RUN_TIME),
    )

    assert result.counts == {"migrated": 1}
    sources = {f.source for f in result.files}
    assert Path("Polished/Chapter 1.gdoc") in sources
    assert not any("Drafts" in p.parts for p in sources)
