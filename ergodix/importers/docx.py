"""
Word / Scrivener `.docx` importer (ADR 0015 §2 + §3).

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
  * Embedded images (chunk 6) — extracted to `media_dir` when provided;
    referenced from the rendered Markdown via `![](filename)`. Images
    are saved in document-relationship order with sequential filenames
    `img-NNN.<ext>` and references appended at the end of the
    markdown body.

Tables, footnote bodies, and inline-object elements other than images
are silently skipped — not in scope for v1; a polish pass covers them.

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


# Office Open XML relationship-type tail for image parts. We match by
# substring (`"image"`) to be tolerant of the various namespace URLs
# Microsoft has shipped over the years without committing to one form.
_IMAGE_RELTYPE_TOKEN = "image"  # noqa: S105 — substring match, not a credential


def extract(
    path: Path,
    *,
    media_dir: Path | None = None,
    **_kwargs: Any,
) -> str:
    """Return Pandoc-Markdown rendered from the given `.docx` path.

    Optional ``media_dir`` enables image extraction (chunk 6 of ADR
    0015): when provided, every embedded image part is written to
    ``media_dir / "img-NNN.<ext>"`` with zero-padded sequential
    numbering and a `![](filename)` reference is appended to the
    rendered markdown. When omitted, images are silently skipped —
    matching the orchestrator's `--check` (dry-run) needs and any
    caller that doesn't yet have a media directory available.

    The ``**_kwargs`` swallows orchestrator kwargs like ``docs_service``
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

    if media_dir is not None:
        image_refs = _extract_images(document, media_dir)
        blocks.extend(image_refs)

    return "\n\n".join(blocks)


def _extract_images(document: Any, media_dir: Path) -> list[str]:
    """Save image parts under ``media_dir`` and return Markdown refs.

    Returns one `![](filename)` line per saved image, in
    relationship-iteration order. Order isn't strictly document-flow
    order (the python-docx public API doesn't surface inline image
    positions cleanly without walking the OOXML); v1 emits all image
    refs as a trailing block so authors get the bytes in their corpus
    + a complete reference list and can re-position manually if needed.
    """
    image_parts: list[Any] = []
    for rel in document.part.rels.values():
        if _IMAGE_RELTYPE_TOKEN in rel.reltype:
            image_parts.append(rel.target_part)

    if not image_parts:
        return []

    media_dir.mkdir(parents=True, exist_ok=True)

    refs: list[str] = []
    for index, part in enumerate(image_parts, start=1):
        ext = _suffix_for_image_part(part)
        filename = f"img-{index:03d}{ext}"
        out_path = media_dir / filename
        out_path.write_bytes(part.blob)
        refs.append(f"![]({filename})")
    return refs


def _suffix_for_image_part(part: Any) -> str:
    """Best-effort file extension for an image part.

    `part.partname` is something like `/word/media/image1.png`; the
    extension is the suffix. Falls back to `.bin` if the partname is
    missing or extensionless (rare; a malformed .docx).
    """
    partname = getattr(part, "partname", None)
    if partname is None:
        return ".bin"
    suffix = Path(str(partname)).suffix
    return suffix or ".bin"


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
