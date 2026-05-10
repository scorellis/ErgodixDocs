"""Hermetic end-to-end tests against `examples/migrate-fixture/`.

Mirrors the role `examples/showcase/` plays for render: a checked-in
corpus shape that exercises every layer of migrate (walker, importer,
orchestrator, frontmatter, manifest, archive) on real on-disk inputs
without needing Drive or network. The `.gdoc` is a placeholder (JSON
pointer); the test injects a mocked `docs_service` that returns canned
Docs API JSON for the placeholder's doc_id. The `.docx` is a real
binary built by `examples/migrate-fixture/build_docx_fixtures.py`.

A regression in any layer surfaces here as a fixture-test failure
rather than a unit-test failure scoped to one layer.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from ergodix.migrate import migrate_run, read_manifest

FIXTURE_ROOT = Path(__file__).parent.parent / "examples" / "migrate-fixture"


# ─── Canned Docs API JSON for Chapter 1.gdoc ────────────────────────────────


def _para(text: str, *, style: str = "NORMAL_TEXT") -> dict[str, Any]:
    return {
        "paragraph": {
            "elements": [{"textRun": {"content": text, "textStyle": {}}}],
            "paragraphStyle": {"namedStyleType": style},
        },
    }


def _styled_para(parts: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    return {
        "paragraph": {
            "elements": [
                {"textRun": {"content": text, "textStyle": style}} for text, style in parts
            ],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        },
    }


_CHAPTER_1_DOC: dict[str, Any] = {
    "documentId": "fixture-doc-chapter-1",
    "title": "Chapter 1 — The Glass Tower",
    "body": {
        "content": [
            _para("Chapter 1 — The Glass Tower\n", style="HEADING_1"),
            _para(
                "The tower rose without rhythm, without rhyme — without "
                "the steadiness Theron's father's stones had once promised.\n"
            ),
            _styled_para(
                [
                    ("It was ", {}),
                    ("strange", {"italic": True}),
                    (", and it was ", {}),
                    ("growing", {"bold": True}),
                    (".\n", {}),
                ]
            ),
        ],
    },
}


def _make_mock_docs_service() -> MagicMock:
    service = MagicMock()

    def get(*, documentId: str) -> MagicMock:
        request = MagicMock()
        if documentId == "fixture-doc-chapter-1":
            request.execute.return_value = _CHAPTER_1_DOC
        else:
            request.execute.side_effect = RuntimeError(f"unexpected doc {documentId}")
        return request

    service.documents.return_value.get.side_effect = get
    return service


# ─── Helpers ────────────────────────────────────────────────────────────────


def _copy_fixture(tmp_path: Path) -> Path:
    """Copy the immutable fixture into tmp_path so migrate's archive
    moves don't mutate the checked-in corpus."""
    target = tmp_path / "corpus"
    shutil.copytree(FIXTURE_ROOT, target)
    return target


_RUN_TIME = datetime(2026, 5, 10, 14, 0, 0, tzinfo=UTC)
_RUN_ID = "2026-05-10-140000"


# ─── Tests ──────────────────────────────────────────────────────────────────


def test_fixture_shape_on_disk() -> None:
    """The fixture's expected files are present in the source tree.

    Pins the contract so a refactor that accidentally moves / renames
    fixture files surfaces as a fast unit-test failure rather than as
    a confusing skip in the e2e tests below.
    """
    assert (FIXTURE_ROOT / "Book 1" / "Chapter 1.gdoc").exists()
    assert (FIXTURE_ROOT / "Book 1" / "Chapter 2.docx").exists()
    assert (FIXTURE_ROOT / "Notes.gsheet").exists()
    assert (FIXTURE_ROOT / "README.md").exists()
    # The .docx builder lives under tests/ (not inside the fixture)
    # so the walker doesn't see the .py script as an out-of-scope file.
    builder = Path(__file__).parent / "build_migrate_docx_fixture.py"
    assert builder.exists()


def test_e2e_gdocs_run_against_fixture(tmp_path: Path) -> None:
    """Run migrate --from gdocs against the fixture: exercises walker,
    gdocs importer (mocked Docs API), orchestrator, frontmatter,
    manifest, archive."""
    corpus = _copy_fixture(tmp_path)
    docs = _make_mock_docs_service()

    result = migrate_run(
        corpus_root=corpus,
        importer_name="gdocs",
        docs_service=docs,
        author="Test Author",
        now_fn=lambda: _RUN_TIME,
    )

    # Counts: 1 gdoc migrated, 1 docx + 1 gsheet skipped (out-of-scope
    # for the gdocs importer in this run).
    assert result.counts.get("migrated") == 1
    assert result.counts.get("skipped") == 2

    # Target file written with frontmatter + extracted body. The
    # filename is slugified from the SOURCE filename ("Chapter 1.gdoc"
    # → "chapter-1.md"); the title field carries the source's basename
    # stem ("Chapter 1") for human readability.
    target = corpus / "Book 1" / "chapter-1.md"
    assert target.exists()
    body = target.read_text(encoding="utf-8")
    assert 'title: "Chapter 1"' in body
    assert 'author: "Test Author"' in body
    assert 'source: "Book 1/Chapter 1.gdoc"' in body
    assert "The tower rose without rhythm" in body
    assert "*strange*" in body
    assert "**growing**" in body

    # Source archived.
    archived = corpus / "_archive" / _RUN_ID / "Book 1" / "Chapter 1.gdoc"
    assert archived.exists()
    assert not (corpus / "Book 1" / "Chapter 1.gdoc").exists()

    # Manifest written and well-formed.
    manifest = read_manifest(corpus / "_archive" / "_runs" / f"{_RUN_ID}.toml")
    statuses = {entry.source.name: entry.status for entry in manifest.files}
    assert statuses["Chapter 1.gdoc"] == "migrated"
    assert statuses["Chapter 2.docx"] == "skipped"  # wrong importer for this run
    assert statuses["Notes.gsheet"] == "skipped"  # out-of-scope


def test_e2e_docx_run_against_fixture(tmp_path: Path) -> None:
    """Run migrate --from docx against the fixture: exercises the
    docx importer end-to-end (no mocks; the .docx is a real binary)."""
    corpus = _copy_fixture(tmp_path)

    result = migrate_run(
        corpus_root=corpus,
        importer_name="docx",
        docs_service=None,  # docx importer ignores the kwarg
        author="Test Author",
        now_fn=lambda: _RUN_TIME,
    )

    # 1 docx migrated; 1 gdoc + 1 gsheet skipped (out-of-scope for the docx run).
    assert result.counts.get("migrated") == 1
    assert result.counts.get("skipped") == 2

    target = corpus / "Book 1" / "chapter-2.md"
    assert target.exists()
    body = target.read_text(encoding="utf-8")
    # Frontmatter
    assert 'source: "Book 1/Chapter 2.docx"' in body
    # Heading
    assert "# Chapter 2" in body
    # Sub-heading
    assert "## What Theron carried" in body
    # Italic + bold
    assert "*not a man*" in body
    assert "**knew**" in body
    # Bulleted list
    assert "- a length of rope" in body
    assert "- a folded letter" in body

    archived = corpus / "_archive" / _RUN_ID / "Book 1" / "Chapter 2.docx"
    assert archived.exists()


def test_e2e_check_mode_against_fixture(tmp_path: Path) -> None:
    """`--check` against the fixture should classify outcomes but make
    no filesystem changes — fixture stays pristine after the run."""
    corpus = _copy_fixture(tmp_path)
    docs = _make_mock_docs_service()

    before = sorted(p.relative_to(corpus) for p in corpus.rglob("*"))

    result = migrate_run(
        corpus_root=corpus,
        importer_name="gdocs",
        docs_service=docs,
        author="A",
        check=True,
        now_fn=lambda: _RUN_TIME,
    )

    assert result.counts.get("migrated") == 1
    assert result.manifest_path is None

    after = sorted(p.relative_to(corpus) for p in corpus.rglob("*"))
    assert before == after, "check-mode altered the fixture tree"


def test_e2e_rerun_unchanged_skips(tmp_path: Path) -> None:
    """Run twice: second run should report `skipped` for the previously-
    migrated source (idempotency per ADR 0015 §5). Simulates the source
    re-appearing at its original location after archive (e.g. via
    Drive Mirror sync)."""
    corpus = _copy_fixture(tmp_path)

    migrate_run(
        corpus_root=corpus,
        importer_name="docx",
        docs_service=None,
        author="A",
        now_fn=lambda: _RUN_TIME,
    )

    # Restore Chapter 2.docx at its original location to simulate
    # re-sync.
    archived_docx = corpus / "_archive" / _RUN_ID / "Book 1" / "Chapter 2.docx"
    shutil.copy2(archived_docx, corpus / "Book 1" / "Chapter 2.docx")

    later_run_time = datetime(2026, 5, 10, 15, 0, 0, tzinfo=UTC)
    result = migrate_run(
        corpus_root=corpus,
        importer_name="docx",
        docs_service=None,
        author="A",
        now_fn=lambda: later_run_time,
    )

    # The .docx is unchanged → status="skipped", reason="unchanged...".
    docx_entry = next(e for e in result.files if e.source.name == "Chapter 2.docx")
    assert docx_entry.status == "skipped"
    assert docx_entry.reason is not None
    assert "unchanged" in docx_entry.reason.lower()
