"""Tests for ergodix.importers.docx — Word/Scrivener .docx → Pandoc-Markdown.

Per ADR 0015 §2: `.docx` is a first-class import target, extracted via
`python-docx` (already a runtime dep). Coverage in v1 mirrors the gdocs
extractor: paragraphs, headings (Heading 1-6 + Title), bold/italic,
inline links, bulleted lists. Tables / images / footnotes deferred to
chunks 6+ per ADR 0015's chunk plan.

Tests build sample `.docx` files in `tmp_path` using `python-docx`
itself, then call `docx.extract` and assert on the rendered Markdown.
No network, no Drive, no OAuth.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ergodix.importers import docx as docx_importer


def _build_docx(tmp_path: Path, build_fn: object) -> Path:
    """Build a .docx via python-docx, return the path."""
    from docx import Document

    document = Document()
    build_fn(document)
    out = tmp_path / "test.docx"
    document.save(str(out))
    return out


# ─── module shape ──────────────────────────────────────────────────────────


def test_module_declares_name_and_extensions() -> None:
    assert docx_importer.NAME == "docx"
    assert ".docx" in docx_importer.EXTENSIONS


def test_module_registered_in_importer_registry() -> None:
    from ergodix import importers

    assert "docx" in importers.available_importers()
    assert importers.extension_to_importer(".docx") is not None
    assert importers.extension_to_importer(".docx").name == "docx"


# ─── extract — happy paths ─────────────────────────────────────────────────


def test_renders_normal_paragraph(tmp_path: Path) -> None:
    def build(doc: object) -> None:
        doc.add_paragraph("Hello world.")

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    assert "Hello world." in md


def test_renders_h1_through_h6(tmp_path: Path) -> None:
    def build(doc: object) -> None:
        for level in range(1, 7):
            doc.add_heading(f"Heading {level}", level=level)

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    assert "# Heading 1" in md
    assert "## Heading 2" in md
    assert "### Heading 3" in md
    assert "#### Heading 4" in md
    assert "##### Heading 5" in md
    assert "###### Heading 6" in md


def test_title_renders_as_h1(tmp_path: Path) -> None:
    def build(doc: object) -> None:
        # python-docx's add_heading(level=0) maps to "Title" style.
        doc.add_heading("My Title", level=0)

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    assert "# My Title" in md


def test_bold_run(tmp_path: Path) -> None:
    def build(doc: object) -> None:
        para = doc.add_paragraph("It was ")
        run = para.add_run("bold")
        run.bold = True
        para.add_run(".")

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    assert "It was **bold**." in md


def test_italic_run(tmp_path: Path) -> None:
    def build(doc: object) -> None:
        para = doc.add_paragraph("Walking ")
        run = para.add_run("alone")
        run.italic = True
        para.add_run(" home.")

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    assert "Walking *alone* home." in md


def test_bold_and_italic_combined(tmp_path: Path) -> None:
    def build(doc: object) -> None:
        para = doc.add_paragraph()
        run = para.add_run("loud")
        run.bold = True
        run.italic = True

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    assert "***loud***" in md


def test_paragraphs_separated_by_blank_line(tmp_path: Path) -> None:
    def build(doc: object) -> None:
        doc.add_paragraph("First paragraph.")
        doc.add_paragraph("Second paragraph.")

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    assert "First paragraph.\n\nSecond paragraph." in md


def test_bulleted_list_items(tmp_path: Path) -> None:
    def build(doc: object) -> None:
        doc.add_paragraph("first", style="List Bullet")
        doc.add_paragraph("second", style="List Bullet")

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    assert "- first" in md
    assert "- second" in md


def test_empty_document_returns_empty_string(tmp_path: Path) -> None:
    def build(doc: object) -> None:
        pass  # No paragraphs added.

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    # python-docx adds one empty paragraph automatically — should still render empty.
    assert md == ""


def test_skips_empty_paragraphs(tmp_path: Path) -> None:
    """Empty paragraphs (just whitespace / no runs) shouldn't emit blank lines."""

    def build(doc: object) -> None:
        doc.add_paragraph("Real content.")
        doc.add_paragraph("")  # empty
        doc.add_paragraph("More content.")

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    assert "Real content." in md
    assert "More content." in md
    # No triple-blank-line gap.
    assert "\n\n\n" not in md


def test_extract_raises_on_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "absent.docx"
    with pytest.raises(FileNotFoundError):
        docx_importer.extract(missing)


def test_extract_accepts_unknown_kwargs(tmp_path: Path) -> None:
    """The orchestrator passes docs_service to every importer; non-gdocs
    importers must accept (and ignore) it without raising."""

    def build(doc: object) -> None:
        doc.add_paragraph("Hello.")

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path, docs_service=object())
    assert "Hello." in md


def test_unknown_paragraph_styles_pass_through_as_plain_text(tmp_path: Path) -> None:
    """A paragraph with an unrecognized style (custom Word template) renders
    as plain markdown rather than dropping content."""

    def build(doc: object) -> None:
        # Use a built-in but unhandled-by-our-renderer style.
        doc.add_paragraph("Normal-style content.")
        doc.add_paragraph("Subtitle content.", style="Subtitle")

    path = _build_docx(tmp_path, build)
    md = docx_importer.extract(path)
    assert "Normal-style content." in md
    assert "Subtitle content." in md
