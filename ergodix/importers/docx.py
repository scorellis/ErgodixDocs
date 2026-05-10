"""
Word / Scrivener `.docx` importer (ADR 0015 §2).

Scrivener exports as `.docx` (per-chapter compile is the supported v1
shape; multi-chapter compile is parking-lot per Spike 0012). Microsoft
Word also produces `.docx` natively. This importer takes a path to a
`.docx` file and returns Pandoc-Markdown content suitable for the
migrate orchestrator's frontmatter + body pipeline.

Coverage in v1 mirrors the gdocs importer:

  * Paragraphs (Normal style)
  * Headings (Heading 1..6, Title)
  * Bold + italic + bold+italic (run-level)
  * Bulleted lists (paragraph style "List Bullet")

Tables, embedded images, footnote bodies, and inline-object elements
are silently skipped — not in scope for chunk 5; chunk 6 (image
extraction) and a future polish pass cover them.

Implementation note: `python-docx` is already a runtime dep in
`pyproject.toml` (added back in Story 0.1's installer scaffolding).
We import it lazily inside `extract` so that test collection on
machines without `python-docx` installed doesn't fail at module-load
time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

NAME = "docx"
EXTENSIONS: tuple[str, ...] = (".docx",)


_HEADING_STYLES: dict[str, int] = {
    "Title": 1,
    "Heading 1": 1,
    "Heading 2": 2,
    "Heading 3": 3,
    "Heading 4": 4,
    "Heading 5": 5,
    "Heading 6": 6,
    "Subtitle": 2,
}


def extract(path: Path, **_kwargs: Any) -> str:
    """Return Pandoc-Markdown rendered from the given `.docx` path.

    The `**_kwargs` swallows orchestrator kwargs like `docs_service`
    that this importer doesn't use — keeps the orchestrator's
    "pass-everything-through" call shape working without a registry of
    per-importer signatures.

    Raises:
        FileNotFoundError: ``path`` doesn't exist.
    """
    if not path.exists():
        raise FileNotFoundError(path)

    from docx import Document

    document = Document(str(path))
    blocks: list[str] = []
    for paragraph in document.paragraphs:
        rendered = _render_paragraph(paragraph)
        if rendered:
            blocks.append(rendered)
    return "\n\n".join(blocks)


def _render_paragraph(paragraph: Any) -> str:
    """Render one ``python-docx`` paragraph to a Markdown block.

    Returns the empty string for paragraphs with no visible content
    (the trailing empty paragraph python-docx emits on every Document
    falls into this bucket).
    """
    text = "".join(_render_run(run) for run in paragraph.runs)
    text = text.strip()
    if not text:
        return ""

    style_name = ""
    if paragraph.style is not None and paragraph.style.name:
        style_name = paragraph.style.name

    # List paragraphs (List Bullet, List Bullet 2, etc.). Ordered-list
    # detection (List Number) deferred — fiction prose rarely uses it.
    if style_name.startswith("List Bullet"):
        return f"- {text}"

    if style_name in _HEADING_STYLES:
        level = _HEADING_STYLES[style_name]
        return f"{'#' * level} {text}"

    return text


def _render_run(run: Any) -> str:
    """Render one text run with bold / italic styling applied."""
    raw = run.text
    if not raw:
        return ""
    text: str = str(raw)

    bold = bool(run.bold)
    italic = bool(run.italic)
    if bold and italic:
        return f"***{text}***"
    if bold:
        return f"**{text}**"
    if italic:
        return f"*{text}*"
    return text
