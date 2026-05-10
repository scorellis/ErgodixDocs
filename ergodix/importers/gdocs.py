"""
Google Docs importer (ADR 0015 §2).

A `.gdoc` file in a Drive-mounted folder is a JSON pointer:

    {"url": "https://docs.google.com/document/d/<id>/edit",
     "doc_id": "<id>",
     "resource_id": "document:<id>",
     "email": "..."}

Migration extracts the doc_id, fetches the document via Google's Docs
API (``documents.readonly`` scope per ADR 0001), and renders the
structured response as Pandoc-Markdown.

The renderer (``_document_to_markdown``) is a pure function — no
network, no auth, no I/O — so it can be exercised directly in tests
with canned Docs API JSON. The public ``extract`` wraps it with the
Drive lookup.

Coverage in v1: paragraphs, headings (H1-H6, TITLE, SUBTITLE), bold,
italic, bold+italic, inline links, and bulleted lists. Tables, ordered
lists, footnote bodies, embedded images, and inline objects are parked
for follow-up chunks (per ADR 0015's chunk plan, embedded images are
chunk 6). Unknown structural elements are silently skipped — a partial
render beats a hard crash on a Docs feature we haven't taught the
importer about yet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NAME = "gdocs"
EXTENSIONS: tuple[str, ...] = (".gdoc",)


# ─── Pointer parsing ───────────────────────────────────────────────────────


def parse_gdoc_pointer(path: Path) -> str:
    """Read a `.gdoc` placeholder and return its document id.

    The placeholder is a JSON object that may have any of ``doc_id``,
    ``resource_id`` (in ``"document:<id>"`` form), or ``url`` (a Docs
    web URL with ``/document/d/<id>/`` in the path). We try them in
    that order — ``doc_id`` is the most explicit.

    Raises:
        FileNotFoundError: ``path`` doesn't exist.
        ValueError: file contents aren't valid JSON, or none of the
            recognized fields are present / parseable.
    """
    text = path.read_text(encoding="utf-8")
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: not valid JSON ({exc.msg})") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object, got {type(data).__name__}")

    doc_id = data.get("doc_id")
    if isinstance(doc_id, str) and doc_id:
        return doc_id

    resource_id = data.get("resource_id")
    if isinstance(resource_id, str) and resource_id.startswith("document:"):
        return resource_id.removeprefix("document:")

    url = data.get("url")
    if isinstance(url, str) and "/document/d/" in url:
        tail = url.split("/document/d/", 1)[1]
        candidate = tail.split("/", 1)[0]
        if candidate:
            return candidate

    raise ValueError(f"{path}: no document id (doc_id / resource_id / url)")


# ─── Renderer ──────────────────────────────────────────────────────────────


_HEADING_LEVELS: dict[str, int] = {
    "TITLE": 1,
    "SUBTITLE": 2,
    "HEADING_1": 1,
    "HEADING_2": 2,
    "HEADING_3": 3,
    "HEADING_4": 4,
    "HEADING_5": 5,
    "HEADING_6": 6,
}


def _document_to_markdown(document: dict[str, Any]) -> str:
    """Render a Docs API ``Document`` resource as Pandoc-Markdown.

    The body is a list of ``StructuralElement``; only ``paragraph``
    elements contribute to the output. Other element kinds (sectionBreak,
    pageBreak, table, tableOfContents) are skipped — table support is a
    parking-lot item per ADR 0015.
    """
    body = document.get("body") or {}
    content: list[Any] = body.get("content") or []

    blocks: list[str] = []
    for element in content:
        if not isinstance(element, dict):
            continue
        paragraph = element.get("paragraph")
        if not isinstance(paragraph, dict):
            continue
        rendered = _render_paragraph(paragraph)
        if rendered:
            blocks.append(rendered)

    return "\n\n".join(blocks)


def _render_paragraph(paragraph: dict[str, Any]) -> str:
    """Render a single ``Paragraph`` element to one Markdown block.

    Returns the empty string for paragraphs that produce no visible
    content (e.g. Docs's trailing newline-only paragraph at end-of-doc).
    """
    text = _render_runs(paragraph.get("elements") or [])
    text = text.rstrip("\n")
    if not text:
        return ""

    # Bullet field signals list membership. Ordered-list detection is
    # parking-lot; unordered "-" is fine for fiction-writing prose, which
    # rarely uses ordered lists in chapter bodies.
    if "bullet" in paragraph:
        return f"- {text}"

    style = paragraph.get("paragraphStyle") or {}
    named = style.get("namedStyleType")
    level = _HEADING_LEVELS.get(named) if isinstance(named, str) else None
    if level is not None:
        return f"{'#' * level} {text}"

    return text


def _render_runs(elements: list[Any]) -> str:
    """Concatenate paragraph elements into a single string of Markdown.

    Each element is one of the ParagraphElement variants; we handle
    ``textRun`` (with bold/italic/link styling) and ignore the rest
    (footnoteReference, inlineObjectElement, etc.) — they're parking-lot
    per ADR 0015 §"Implementation chunks".
    """
    parts: list[str] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        text_run = element.get("textRun")
        if isinstance(text_run, dict):
            parts.append(_render_text_run(text_run))
    return "".join(parts)


def _render_text_run(text_run: dict[str, Any]) -> str:
    """Render one ``textRun`` to Markdown, applying inline styling.

    Order of wrapping matters in Pandoc-Markdown: a link wraps the
    styled inner text, then bold/italic wrap the link. ``***x***`` is
    Pandoc's combined bold+italic form.
    """
    content = text_run.get("content")
    if not isinstance(content, str) or not content:
        return ""

    # Strip the trailing newline that Docs appends to every run; paragraph
    # boundaries are reintroduced by the caller via "\n\n".
    text = content.rstrip("\n")
    if not text:
        return ""

    style = text_run.get("textStyle") or {}

    link = style.get("link")
    if isinstance(link, dict):
        url = link.get("url")
        if isinstance(url, str) and url:
            text = f"[{text}]({url})"

    bold = bool(style.get("bold"))
    italic = bool(style.get("italic"))
    if bold and italic:
        text = f"***{text}***"
    elif bold:
        text = f"**{text}**"
    elif italic:
        text = f"*{text}*"

    return text


# ─── Public extractor ──────────────────────────────────────────────────────


def extract(
    path: Path,
    *,
    docs_service: Any | None = None,
    media_dir: Path | None = None,  # accepted for orchestrator parity; image fetching not yet wired
    **_kwargs: Any,
) -> str:
    """Fetch the Doc referenced by ``path`` and return Pandoc-Markdown.

    ``docs_service`` is a googleapiclient ``Resource`` for the Docs API.
    If omitted, ``ergodix.auth.get_docs_service`` is used — which runs
    the OAuth dance on first use. Callers in tests pass an explicit
    mock; the migrate walker passes the long-lived service it built once
    per run.

    ``media_dir`` is accepted for orchestrator-call-shape parity with
    `docx.extract` (chunk 6) but image extraction over the Docs API
    is **not yet wired** in v1 — Docs API inline images need a Drive
    API auth flow + contentUri fetch that's its own polish chunk.
    Inline images in the source doc are silently skipped for now.
    """
    doc_id = parse_gdoc_pointer(path)
    if docs_service is None:
        from ergodix.auth import get_docs_service

        docs_service = get_docs_service()
    document = docs_service.documents().get(documentId=doc_id).execute()
    if not isinstance(document, dict):
        raise ValueError(f"{path}: Docs API returned non-dict response")
    return _document_to_markdown(document)
