"""
Render pipeline: Pandoc Markdown + raw LaTeX → XeLaTeX → PDF.

Per Story 0.2's locked decisions: chapters are ``.md`` files in Pandoc
Markdown with raw LaTeX passthrough; rendering walks up the directory
tree from the chapter to the corpus root, collects every
``_preamble.tex`` it finds, concatenates them most-general-first, and
hands them to Pandoc via ``--include-in-header`` flags.

LaTeX honors override-by-redefinition (later-loaded definition wins),
so the cascade order matters: the **epoch** preamble (most general)
loads first; **compendium**, **book**, **section**, then **chapter
directory** preambles override it in turn.

Public surface:

    find_preamble_chain(chapter, corpus_root) -> list[Path]
    render(chapter, output=None, corpus_root=None) -> Path
    RenderError  (raised on chapter-missing / pandoc-missing / pandoc-fails)
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class RenderError(RuntimeError):
    """Raised when render() can't produce a PDF.

    Surfaces a friendly user-facing message: missing chapter, missing
    Pandoc, or non-zero Pandoc/XeLaTeX exit (with stderr included so
    the user has a real error to act on, not just "render failed").
    """


def find_preamble_chain(
    chapter: Path,
    corpus_root: Path | None = None,
) -> list[Path]:
    """Walk up from the chapter's parent collecting ``_preamble.tex``
    files. Return them ordered **most-general-first** (root-side first,
    leaf-side last).

    Stops when either ``corpus_root`` is reached (its preamble IS
    included; the walk stops after capturing it) or filesystem root.
    """
    chapter = chapter.resolve()
    if corpus_root is not None:
        corpus_root = corpus_root.resolve()

    visited: list[Path] = []
    current = chapter.parent

    while True:
        visited.append(current)
        if corpus_root is not None and current == corpus_root:
            break
        if current.parent == current:
            break
        if corpus_root is not None and corpus_root not in current.parents:
            break
        current = current.parent

    preambles: list[Path] = []
    for directory in reversed(visited):
        candidate = directory / "_preamble.tex"
        if candidate.exists() and candidate.is_file():
            preambles.append(candidate)
    return preambles


def render(
    chapter: Path,
    output: Path | None = None,
    corpus_root: Path | None = None,
) -> Path:
    """Render ``chapter`` to PDF via Pandoc + XeLaTeX with the preamble
    cascade applied. Returns the output PDF path. Raises ``RenderError``
    on any failure with a friendly message."""
    chapter = chapter.resolve()

    if not chapter.exists():
        raise RenderError(
            f"Chapter file not found: {chapter}. "
            "Pass an existing .md path; render reads from disk, not stdin."
        )

    if output is None:
        output = chapter.with_suffix(".pdf")
    output = output.resolve()

    preambles = find_preamble_chain(chapter, corpus_root=corpus_root)

    cmd: list[str] = [
        "pandoc",
        str(chapter),
        "--pdf-engine=xelatex",
        "-o",
        str(output),
    ]
    for preamble in preambles:
        cmd.extend(["--include-in-header", str(preamble)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RenderError(
            "Pandoc not found on PATH. Run `ergodix cantilever` to land "
            "operation A3 (install/verify Pandoc), or install manually: "
            "`brew install pandoc`."
        ) from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        last_lines = "\n".join(stderr.splitlines()[-5:]) if stderr else "(no stderr)"
        raise RenderError(f"Pandoc exited {result.returncode}. Last stderr lines:\n{last_lines}")

    return output
