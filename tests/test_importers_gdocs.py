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


# ─── Inline image extraction (chunk 6b) ─────────────────────────────────────


_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a"
    "0000000d49484452"
    "0000000100000001"
    "0100000000376ef9"
    "240000000a494441"
    "54789c6300000000"
    "0200015fc7c2bd00"
    "00000049454e44ae"
    "426082"
)


def _doc_with_inline_image(
    *,
    inline_object_id: str = "kix.inline.42",
    content_uri: str = "https://lh3.googleusercontent.com/fixture-image-uri",
) -> dict[str, Any]:
    """Build a Docs API document containing one paragraph with an
    inline-object element pointing at one image."""
    return {
        "documentId": "doc-with-image",
        "title": "Doc with image",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Before. ", "textStyle": {}}},
                            {
                                "inlineObjectElement": {
                                    "inlineObjectId": inline_object_id,
                                },
                            },
                            {"textRun": {"content": " After.\n", "textStyle": {}}},
                        ],
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                    },
                },
            ],
        },
        "inlineObjects": {
            inline_object_id: {
                "inlineObjectProperties": {
                    "embeddedObject": {
                        "imageProperties": {
                            "contentUri": content_uri,
                        },
                    },
                },
            },
        },
    }


def test_extract_writes_inline_image_to_media_dir(tmp_path: Path) -> None:
    """When `media_dir` is set, gdocs.extract fetches inline-object
    images via the supplied `image_fetcher`, saves bytes, emits a
    `![](filename)` reference."""
    pointer = _write_pointer(tmp_path, {"doc_id": "doc-with-image"})
    fake_doc = _doc_with_inline_image(content_uri="https://lh3.test/x")

    docs_service = MagicMock()
    docs_service.documents.return_value.get.return_value.execute.return_value = fake_doc

    fetched_uris: list[str] = []

    def fetch(uri: str) -> bytes:
        fetched_uris.append(uri)
        return _TINY_PNG

    media = tmp_path / "_media" / "chapter"
    md = gdocs.extract(
        pointer,
        docs_service=docs_service,
        media_dir=media,
        image_fetcher=fetch,
    )

    assert fetched_uris == ["https://lh3.test/x"]
    images = sorted(media.iterdir())
    assert len(images) == 1
    assert images[0].read_bytes() == _TINY_PNG
    assert "Before." in md
    assert "After." in md
    assert "![](" + images[0].name + ")" in md


def test_extract_skips_image_extraction_when_media_dir_omitted(
    tmp_path: Path,
) -> None:
    """No `media_dir` → no fetcher invocation, no media files. Body
    content still renders unchanged."""
    pointer = _write_pointer(tmp_path, {"doc_id": "doc-with-image"})
    fake_doc = _doc_with_inline_image()
    docs_service = MagicMock()
    docs_service.documents.return_value.get.return_value.execute.return_value = fake_doc

    fetched: list[str] = []

    def fetch(uri: str) -> bytes:
        fetched.append(uri)
        return b"unused"

    md = gdocs.extract(pointer, docs_service=docs_service, image_fetcher=fetch)

    assert fetched == []
    assert "Before." in md
    assert not (tmp_path / "_media").exists()


def test_extract_handles_failed_image_fetch_gracefully(tmp_path: Path) -> None:
    """Fetcher returning None (auth / network failure) doesn't crash
    extract — body content still renders, the failed image is silently
    omitted from the references."""
    pointer = _write_pointer(tmp_path, {"doc_id": "doc-with-image"})
    fake_doc = _doc_with_inline_image()
    docs_service = MagicMock()
    docs_service.documents.return_value.get.return_value.execute.return_value = fake_doc

    media = tmp_path / "_media" / "chapter"
    md = gdocs.extract(
        pointer,
        docs_service=docs_service,
        media_dir=media,
        image_fetcher=lambda _uri: None,
    )

    assert "Before." in md
    assert "After." in md
    # No image saved.
    if media.exists():
        assert list(media.iterdir()) == []
    # No reference emitted for the failed image.
    assert "![]" not in md


def test_extract_handles_multiple_inline_images(tmp_path: Path) -> None:
    """Two inline-object elements get fetched in document order with
    sequential filenames (img-001, img-002)."""
    pointer = _write_pointer(tmp_path, {"doc_id": "x"})
    document: dict[str, Any] = {
        "documentId": "x",
        "title": "x",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"inlineObjectElement": {"inlineObjectId": "obj-1"}},
                            {"textRun": {"content": " mid ", "textStyle": {}}},
                            {"inlineObjectElement": {"inlineObjectId": "obj-2"}},
                            {"textRun": {"content": "\n", "textStyle": {}}},
                        ],
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                    },
                },
            ],
        },
        "inlineObjects": {
            "obj-1": {
                "inlineObjectProperties": {
                    "embeddedObject": {
                        "imageProperties": {"contentUri": "https://example/img1"},
                    },
                },
            },
            "obj-2": {
                "inlineObjectProperties": {
                    "embeddedObject": {
                        "imageProperties": {"contentUri": "https://example/img2"},
                    },
                },
            },
        },
    }
    docs_service = MagicMock()
    docs_service.documents.return_value.get.return_value.execute.return_value = document

    counter = {"n": 0}

    def fetch(_uri: str) -> bytes:
        counter["n"] += 1
        return _TINY_PNG[: -counter["n"]] + bytes([counter["n"]])

    media = tmp_path / "_media" / "chapter"
    gdocs.extract(
        pointer,
        docs_service=docs_service,
        media_dir=media,
        image_fetcher=fetch,
    )

    images = sorted(media.iterdir())
    assert len(images) == 2
    assert images[0].name.startswith("img-001")
    assert images[1].name.startswith("img-002")


def test_guess_extension_prefers_magic_bytes_over_uri() -> None:
    """Magic-byte sniffing wins over URI suffix when they conflict."""
    png_bytes = bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 20
    assert gdocs._guess_image_extension(png_bytes, "https://example.com/wrong.jpg") == ".png"


def test_guess_extension_uri_fallback_when_magic_unknown() -> None:
    """When magic bytes don't match a known type, fall back to URI
    suffix scan. `.jpeg` normalizes to `.jpg`."""
    unknown = b"\x00\x01\x02\x03" + b"\x00" * 20
    assert gdocs._guess_image_extension(unknown, "https://example.com/x.jpeg") == ".jpg"
    assert gdocs._guess_image_extension(unknown, "https://example.com/x.png") == ".png"
    assert gdocs._guess_image_extension(unknown, "https://example.com/x.webp") == ".webp"


def test_guess_extension_strips_query_string_from_uri() -> None:
    """URI-suffix detection should ignore query parameters."""
    unknown = b"\x00\x01\x02\x03" + b"\x00" * 20
    assert (
        gdocs._guess_image_extension(unknown, "https://example.com/img.png?cache=42&v=3") == ".png"
    )


def test_guess_extension_falls_back_to_bin_for_docs_style_url() -> None:
    """Docs API contentUris look like `https://lh3.googleusercontent.com/...`
    — typically no recognizable extension suffix in the path. With
    no magic-byte match either, fallback is `.bin`."""
    unknown = b"\x00\x01\x02\x03" + b"\x00" * 20
    docs_uri = "https://lh3.googleusercontent.com/J3-_E2gQUEH_xX-fixture-blob"
    assert gdocs._guess_image_extension(unknown, docs_uri) == ".bin"


def test_guess_extension_recognizes_jpeg_gif_webp_magic() -> None:
    jpeg_bytes = b"\xff\xd8\xff" + b"\x00" * 20
    gif87 = b"GIF87a" + b"\x00" * 20
    gif89 = b"GIF89a" + b"\x00" * 20
    webp_bytes = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 20
    assert gdocs._guess_image_extension(jpeg_bytes, "https://example/x") == ".jpg"
    assert gdocs._guess_image_extension(gif87, "https://example/x") == ".gif"
    assert gdocs._guess_image_extension(gif89, "https://example/x") == ".gif"
    assert gdocs._guess_image_extension(webp_bytes, "https://example/x") == ".webp"
