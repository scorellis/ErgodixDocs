"""Tests for ergodix.importers.gdocs.

The gdocs importer turns a `.gdoc` placeholder file (a JSON pointer to a
Google Doc) into Pandoc-Markdown content. Two layers:

  * parse_gdoc_pointer(path) — pure JSON parsing of the placeholder.
  * extract(path, *, docs_service) — fetches the doc and renders it.
  * _document_to_markdown(document) — pure renderer, exercised here
    directly with canned Docs API JSON so we don't need network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from ergodix.importers import gdocs

# ─── parse_gdoc_pointer ─────────────────────────────────────────────────────


def _write_pointer(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "Chapter 3.gdoc"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_parse_gdoc_pointer_returns_doc_id_from_doc_id_field(tmp_path: Path) -> None:
    path = _write_pointer(tmp_path, {"doc_id": "abc123", "url": "..."})
    assert gdocs.parse_gdoc_pointer(path) == "abc123"


def test_parse_gdoc_pointer_falls_back_to_url(tmp_path: Path) -> None:
    path = _write_pointer(
        tmp_path,
        {"url": "https://docs.google.com/document/d/xyz789/edit"},
    )
    assert gdocs.parse_gdoc_pointer(path) == "xyz789"


def test_parse_gdoc_pointer_falls_back_to_resource_id(tmp_path: Path) -> None:
    path = _write_pointer(tmp_path, {"resource_id": "document:res-id-42"})
    assert gdocs.parse_gdoc_pointer(path) == "res-id-42"


def test_parse_gdoc_pointer_raises_on_missing_doc_id(tmp_path: Path) -> None:
    path = _write_pointer(tmp_path, {"email": "user@example.com"})
    with pytest.raises(ValueError, match="no document id"):
        gdocs.parse_gdoc_pointer(path)


def test_parse_gdoc_pointer_raises_on_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.gdoc"
    path.write_text("not json at all", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        gdocs.parse_gdoc_pointer(path)


def test_parse_gdoc_pointer_raises_on_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "absent.gdoc"
    with pytest.raises(FileNotFoundError):
        gdocs.parse_gdoc_pointer(path)


# ─── _document_to_markdown — pure renderer ──────────────────────────────────


def _para(content: str, *, style: str = "NORMAL_TEXT", **runs_extra: Any) -> dict[str, Any]:
    """Build a paragraph structural element with one plain text run."""
    return {
        "paragraph": {
            "elements": [{"textRun": {"content": content, "textStyle": {}}}],
            "paragraphStyle": {"namedStyleType": style},
            **runs_extra,
        },
    }


def _doc(*structural_elements: dict[str, Any]) -> dict[str, Any]:
    return {
        "documentId": "doc-1",
        "title": "Test Doc",
        "body": {"content": list(structural_elements)},
    }


def test_renders_normal_paragraph() -> None:
    doc = _doc(_para("Hello world.\n"))
    md = gdocs._document_to_markdown(doc)
    assert "Hello world." in md


def test_renders_h1_through_h6() -> None:
    doc = _doc(
        _para("H1\n", style="HEADING_1"),
        _para("H2\n", style="HEADING_2"),
        _para("H3\n", style="HEADING_3"),
        _para("H4\n", style="HEADING_4"),
        _para("H5\n", style="HEADING_5"),
        _para("H6\n", style="HEADING_6"),
    )
    md = gdocs._document_to_markdown(doc)
    assert "# H1" in md
    assert "## H2" in md
    assert "### H3" in md
    assert "#### H4" in md
    assert "##### H5" in md
    assert "###### H6" in md


def test_title_renders_as_h1_subtitle_as_h2() -> None:
    doc = _doc(
        _para("My Title\n", style="TITLE"),
        _para("My Subtitle\n", style="SUBTITLE"),
    )
    md = gdocs._document_to_markdown(doc)
    assert "# My Title" in md
    assert "## My Subtitle" in md


def test_bold_text_run() -> None:
    doc = _doc(
        {
            "paragraph": {
                "elements": [
                    {"textRun": {"content": "It was ", "textStyle": {}}},
                    {"textRun": {"content": "bold", "textStyle": {"bold": True}}},
                    {"textRun": {"content": ".\n", "textStyle": {}}},
                ],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            },
        }
    )
    md = gdocs._document_to_markdown(doc)
    assert "It was **bold**." in md


def test_italic_text_run() -> None:
    doc = _doc(
        {
            "paragraph": {
                "elements": [
                    {"textRun": {"content": "Walking ", "textStyle": {}}},
                    {"textRun": {"content": "alone", "textStyle": {"italic": True}}},
                    {"textRun": {"content": " home.\n", "textStyle": {}}},
                ],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            },
        }
    )
    md = gdocs._document_to_markdown(doc)
    assert "Walking *alone* home." in md


def test_bold_and_italic_combined() -> None:
    doc = _doc(
        {
            "paragraph": {
                "elements": [
                    {
                        "textRun": {
                            "content": "loud",
                            "textStyle": {"bold": True, "italic": True},
                        },
                    },
                    {"textRun": {"content": "\n", "textStyle": {}}},
                ],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            },
        }
    )
    md = gdocs._document_to_markdown(doc)
    # ***loud*** is the standard Pandoc-MD form for bold+italic.
    assert "***loud***" in md


def test_inline_link() -> None:
    doc = _doc(
        {
            "paragraph": {
                "elements": [
                    {"textRun": {"content": "See ", "textStyle": {}}},
                    {
                        "textRun": {
                            "content": "the docs",
                            "textStyle": {"link": {"url": "https://example.com"}},
                        },
                    },
                    {"textRun": {"content": ".\n", "textStyle": {}}},
                ],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            },
        }
    )
    md = gdocs._document_to_markdown(doc)
    assert "See [the docs](https://example.com)." in md


def test_bulleted_list_items() -> None:
    doc = _doc(
        {
            "paragraph": {
                "elements": [{"textRun": {"content": "first\n", "textStyle": {}}}],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                "bullet": {"listId": "kix.list-1"},
            },
        },
        {
            "paragraph": {
                "elements": [{"textRun": {"content": "second\n", "textStyle": {}}}],
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                "bullet": {"listId": "kix.list-1"},
            },
        },
    )
    md = gdocs._document_to_markdown(doc)
    assert "- first" in md
    assert "- second" in md


def test_paragraphs_separated_by_blank_line() -> None:
    doc = _doc(
        _para("First paragraph.\n"),
        _para("Second paragraph.\n"),
    )
    md = gdocs._document_to_markdown(doc)
    # Two paragraphs should be separated by at least one blank line.
    assert "First paragraph.\n\nSecond paragraph." in md


def test_section_and_page_breaks_are_ignored() -> None:
    doc = _doc(
        {"sectionBreak": {}},
        _para("Body.\n"),
        {"pageBreak": {}},
    )
    md = gdocs._document_to_markdown(doc)
    assert "Body." in md
    # No raw structural-element JSON should leak into the output.
    assert "sectionBreak" not in md
    assert "pageBreak" not in md


def test_unknown_structural_elements_skipped_not_crash() -> None:
    doc = _doc(
        _para("Before.\n"),
        {"table": {"rows": 2, "columns": 2, "tableRows": []}},
        _para("After.\n"),
    )
    md = gdocs._document_to_markdown(doc)
    assert "Before." in md
    assert "After." in md
    # Table content not implemented; raw JSON keys must not leak.
    assert "tableRows" not in md


def test_empty_document_returns_empty_string() -> None:
    md = gdocs._document_to_markdown({"body": {"content": []}})
    assert md == ""


def test_empty_paragraph_does_not_emit_blank_heading() -> None:
    """A paragraph with only a newline (Docs adds one at end-of-doc) shouldn't
    appear as a heading line or stray '#' character."""
    doc = _doc(_para("\n", style="HEADING_1"))
    md = gdocs._document_to_markdown(doc)
    assert "#" not in md or md.strip() == ""


# ─── extract — integration with mocked docs_service ────────────────────────


def test_extract_uses_docs_service_to_fetch_document(tmp_path: Path) -> None:
    pointer = _write_pointer(tmp_path, {"doc_id": "doc-42"})
    fake_doc = _doc(_para("Body line.\n"))

    docs_service = MagicMock()
    docs_service.documents.return_value.get.return_value.execute.return_value = fake_doc

    md = gdocs.extract(pointer, docs_service=docs_service)

    docs_service.documents.return_value.get.assert_called_once_with(documentId="doc-42")
    assert "Body line." in md


def test_extract_propagates_pointer_parse_error(tmp_path: Path) -> None:
    bad_pointer = tmp_path / "broken.gdoc"
    bad_pointer.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        gdocs.extract(bad_pointer, docs_service=MagicMock())


# ─── module-level constants ─────────────────────────────────────────────────


def test_module_declares_name_and_extensions() -> None:
    assert gdocs.NAME == "gdocs"
    assert ".gdoc" in gdocs.EXTENSIONS
