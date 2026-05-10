"""
Google Docs importer (ADR 0015 §2 + §3).

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
with canned Docs API JSON.

Coverage:
  * Paragraphs, headings (H1-H6, TITLE, SUBTITLE), bold, italic,
    bold+italic, inline links, bulleted lists.
  * Inline-object **images** (chunk 6b): when ``media_dir`` is
    provided, ``inlineObjectElement`` references in the body are
    resolved against ``document.inlineObjects``, the image is fetched
    from its ``contentUri`` via an authenticated HTTP session, and
    bytes are saved as ``media_dir / "img-NNN<ext>"`` with `![]()`
    references appended to the rendered Markdown body.

Tables, ordered lists, footnote bodies, and other inline-object kinds
remain parking-lot.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

NAME = "gdocs"
EXTENSIONS: tuple[str, ...] = (".gdoc",)

ImageFetcher = Callable[[str], bytes | None]
"""Authenticated-HTTP fetcher: takes a contentUri, returns image bytes
or ``None`` on failure. Production builds one from OAuth credentials;
tests inject a stub that returns canned bytes."""


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
    media_dir: Path | None = None,
    image_fetcher: ImageFetcher | None = None,
    **_kwargs: Any,
) -> str:
    """Fetch the Doc referenced by ``path`` and return Pandoc-Markdown.

    ``docs_service`` is a googleapiclient ``Resource`` for the Docs API.
    If omitted, ``ergodix.auth.get_docs_service`` is used — which runs
    the OAuth dance on first use. Callers in tests pass an explicit
    mock; the migrate walker passes the long-lived service it built
    once per run.

    ``media_dir`` enables image extraction (chunk 6 of ADR 0015): when
    set, every ``inlineObjectElement`` in the body that resolves to an
    embedded image is fetched, saved as
    ``media_dir / "img-NNN<ext>"`` (zero-padded sequential numbering,
    extension inferred from the response's ``Content-Type``), and a
    ``![](filename)`` reference is appended to the rendered Markdown.
    When ``media_dir`` is None, inline images are silently skipped —
    matching the orchestrator's `--check` (dry-run) needs.

    ``image_fetcher`` is the authenticated HTTP fetcher used to resolve
    ``contentUri`` URLs. When None and ``media_dir`` is set, a default
    fetcher is built lazily from the project's OAuth credentials (via
    ``ergodix.oauth.load_or_acquire_credentials`` +
    ``google.auth.transport.requests.AuthorizedSession``). Tests inject
    an explicit fetcher to avoid touching the network.
    """
    doc_id = parse_gdoc_pointer(path)
    if docs_service is None:
        from ergodix.auth import get_docs_service

        docs_service = get_docs_service()
    document = docs_service.documents().get(documentId=doc_id).execute()
    if not isinstance(document, dict):
        raise ValueError(f"{path}: Docs API returned non-dict response")

    image_refs: list[str] = []
    if media_dir is not None:
        image_refs = _extract_inline_images(document, media_dir, image_fetcher)

    body = _document_to_markdown(document)
    if image_refs:
        return body + "\n\n" + "\n\n".join(image_refs) if body else "\n\n".join(image_refs)
    return body


def _extract_inline_images(
    document: dict[str, Any],
    media_dir: Path,
    fetcher: ImageFetcher | None,
) -> list[str]:
    """Walk the body for ``inlineObjectElement`` references, fetch each
    image's bytes via ``fetcher``, save under ``media_dir`` with
    sequential ``img-NNN<ext>`` filenames, return ``![]()`` references
    in document order. Images that fail to fetch (fetcher returns
    None) are silently dropped — body content still renders.

    The default ``fetcher`` (built from OAuth credentials via
    ``_build_default_image_fetcher``) is constructed **lazily** —
    only when at least one image-bearing element is encountered. That
    way a doc with no images doesn't drag in google-auth or trigger
    OAuth prompts on test runs.
    """
    inline_objects = document.get("inlineObjects") or {}
    if not isinstance(inline_objects, dict):
        return []

    refs: list[str] = []
    saved_count = 0
    resolved_fetcher: ImageFetcher | None = fetcher
    body = document.get("body") or {}
    for element in body.get("content") or []:
        if not isinstance(element, dict):
            continue
        paragraph = element.get("paragraph")
        if not isinstance(paragraph, dict):
            continue
        for sub in paragraph.get("elements") or []:
            if not isinstance(sub, dict):
                continue
            inline_obj = sub.get("inlineObjectElement")
            if not isinstance(inline_obj, dict):
                continue
            inline_id = inline_obj.get("inlineObjectId")
            if not isinstance(inline_id, str):
                continue
            obj = inline_objects.get(inline_id)
            if not isinstance(obj, dict):
                continue
            embedded = (obj.get("inlineObjectProperties") or {}).get("embeddedObject") or {}
            content_uri = (embedded.get("imageProperties") or {}).get("contentUri")
            if not isinstance(content_uri, str) or not content_uri:
                continue

            # First image we encounter — build the default fetcher now
            # so docs without inline images never trigger OAuth.
            if resolved_fetcher is None:
                resolved_fetcher = _build_default_image_fetcher()

            image_bytes = resolved_fetcher(content_uri)
            if not image_bytes:
                continue

            saved_count += 1
            ext = _guess_image_extension(image_bytes, content_uri)
            filename = f"img-{saved_count:03d}{ext}"
            # `_media/` dirs are intentionally created at umask default —
            # they hold chapter images, not credentials, and tightening
            # to 0o700 would surprise users opening them in Preview /
            # sharing with collaborators. Mirrors `docx.py::_extract_images`.
            media_dir.mkdir(parents=True, exist_ok=True)
            (media_dir / filename).write_bytes(image_bytes)
            refs.append(f"![]({filename})")

    return refs


def _guess_image_extension(image_bytes: bytes, content_uri: str) -> str:
    """Best-effort file extension from magic bytes + URI hints.

    Magic-byte sniffing covers the common image types Docs lets users
    embed (PNG, JPEG, GIF, WebP). Falls back to a URI suffix scan, then
    ``.bin`` for the truly-unknown.
    """
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        return ".gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return ".webp"
    # Fallback: scan the URI for a recognized suffix (some contentUris
    # carry the format in the path, e.g. .../image.png?...).
    uri_lower = content_uri.lower().split("?", 1)[0]
    for candidate in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        if uri_lower.endswith(candidate):
            return ".jpg" if candidate == ".jpeg" else candidate
    return ".bin"


def _build_default_image_fetcher() -> ImageFetcher:
    """Build an authenticated-HTTP fetcher backed by the project's
    OAuth credentials. Lazy-imports the google-auth dependencies so
    test collection on machines without them still succeeds.
    """
    from google.auth.transport.requests import AuthorizedSession

    from ergodix.oauth import load_or_acquire_credentials

    creds = load_or_acquire_credentials()
    session = AuthorizedSession(creds)  # type: ignore[no-untyped-call]

    def fetch(uri: str) -> bytes | None:
        try:
            response = session.get(uri)
        except Exception:
            return None
        if response.status_code != 200:
            return None
        content: bytes = response.content
        return content

    return fetch
