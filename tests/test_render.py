"""
Tests for ergodix.render — the Pandoc → XeLaTeX → PDF render pipeline
locked in Story 0.2.

Two pieces under test:

- ``find_preamble_chain(chapter, corpus_root)`` — walks up the directory
  tree from the chapter's parent to the corpus root, collects every
  ``_preamble.tex`` it finds, returns them ordered **most-general-first**
  (root-side first, leaf-side last). LaTeX honors override-by-
  redefinition, so the order matters for cascade semantics.

- ``render(chapter, output, corpus_root)`` — invokes
  ``pandoc <chapter.md> --pdf-engine=xelatex --include-in-header=...
  -o <output.pdf>`` with the cascaded preambles in order. Returns the
  output PDF path. Surfaces friendly errors when chapter is missing,
  Pandoc isn't on PATH, or Pandoc/XeLaTeX exits non-zero.

Tests use ``tmp_path`` for filesystem state and ``subprocess.run``
monkeypatching so they never actually invoke Pandoc.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

# ─── find_preamble_chain ────────────────────────────────────────────────────


def test_find_preamble_chain_empty_when_no_preambles(tmp_path: Path) -> None:
    from ergodix.render import find_preamble_chain

    chapter_dir = tmp_path / "Compendium" / "Book" / "Section"
    chapter_dir.mkdir(parents=True)
    chapter = chapter_dir / "ch3.md"
    chapter.write_text("# Hello\n")

    chain = find_preamble_chain(chapter, corpus_root=tmp_path)

    assert chain == []


def test_find_preamble_chain_finds_chapter_dir_preamble(tmp_path: Path) -> None:
    from ergodix.render import find_preamble_chain

    chapter_dir = tmp_path / "Compendium" / "Book" / "Section"
    chapter_dir.mkdir(parents=True)
    chapter = chapter_dir / "ch3.md"
    chapter.write_text("# Hello\n")
    section_preamble = chapter_dir / "_preamble.tex"
    section_preamble.write_text("% section preamble\n")

    chain = find_preamble_chain(chapter, corpus_root=tmp_path)

    assert chain == [section_preamble]


def test_find_preamble_chain_walks_up_collecting_preambles_in_order(
    tmp_path: Path,
) -> None:
    """
    The cascade must be root-most first (most-general-first) so LaTeX's
    later-definition-wins behavior gives leaf-most preambles override
    authority over more-general ancestors.
    """
    from ergodix.render import find_preamble_chain

    epoch = tmp_path  # acts as corpus root
    compendium = tmp_path / "Compendium A"
    book = compendium / "Book 1"
    section = book / "Section 2"
    section.mkdir(parents=True)

    epoch_preamble = epoch / "_preamble.tex"
    book_preamble = book / "_preamble.tex"
    section_preamble = section / "_preamble.tex"
    epoch_preamble.write_text("% epoch\n")
    book_preamble.write_text("% book\n")
    section_preamble.write_text("% section\n")

    chapter = section / "ch3.md"
    chapter.write_text("# Hello\n")

    chain = find_preamble_chain(chapter, corpus_root=tmp_path)

    # Most-general-first: epoch then book then section.
    assert chain == [epoch_preamble, book_preamble, section_preamble]


def test_find_preamble_chain_skips_dirs_without_preamble(tmp_path: Path) -> None:
    """Compendium has no preamble; book + section do. The walk must
    produce only the existing files, in cascade order."""
    from ergodix.render import find_preamble_chain

    section = tmp_path / "Compendium A" / "Book 1" / "Section 2"
    section.mkdir(parents=True)
    book_preamble = section.parent / "_preamble.tex"
    section_preamble = section / "_preamble.tex"
    book_preamble.write_text("% book\n")
    section_preamble.write_text("% section\n")

    chapter = section / "ch3.md"
    chapter.write_text("# Hello\n")

    chain = find_preamble_chain(chapter, corpus_root=tmp_path)

    assert chain == [book_preamble, section_preamble]


def test_find_preamble_chain_respects_corpus_root_boundary(tmp_path: Path) -> None:
    """A `_preamble.tex` above the corpus root must NOT be included.
    Otherwise unrelated parent directories (e.g., a workspace-level
    preamble that belongs to a different opus) would leak into the
    cascade."""
    from ergodix.render import find_preamble_chain

    above_root = tmp_path
    above_root_preamble = above_root / "_preamble.tex"
    above_root_preamble.write_text("% should NOT be included\n")

    corpus_root = tmp_path / "Tapestry"
    section = corpus_root / "Book" / "Section"
    section.mkdir(parents=True)
    corpus_preamble = corpus_root / "_preamble.tex"
    corpus_preamble.write_text("% corpus root\n")

    chapter = section / "ch.md"
    chapter.write_text("# x\n")

    chain = find_preamble_chain(chapter, corpus_root=corpus_root)

    assert above_root_preamble not in chain
    assert corpus_preamble in chain


def test_find_preamble_chain_handles_no_corpus_root_gracefully(tmp_path: Path) -> None:
    """When ``corpus_root`` is None, walk up to filesystem root.

    Real-world use: ``corpus_root`` is read from local_config.py; if the
    user hasn't configured CORPUS_FOLDER yet (placeholder) we should
    still try to render — the cascade just collects from wherever
    `_preamble.tex` files happen to be in the path."""
    from ergodix.render import find_preamble_chain

    section = tmp_path / "deep" / "deep"
    section.mkdir(parents=True)
    preamble = tmp_path / "deep" / "_preamble.tex"
    preamble.write_text("% deep\n")

    chapter = section / "ch.md"
    chapter.write_text("# x\n")

    chain = find_preamble_chain(chapter, corpus_root=None)

    # Should at least find the preamble we explicitly created in an
    # ancestor; we don't pin the full set because filesystem root may
    # contain other surprises in real environments.
    assert preamble in chain


# ─── render() ──────────────────────────────────────────────────────────────


def _record_pandoc(
    monkeypatch: pytest.MonkeyPatch, *, rc: int = 0, stderr: str = ""
) -> list[list[str]]:
    """Stub subprocess.run; capture pandoc invocations."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str] | str, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        calls.append(cmd if isinstance(cmd, list) else [cmd])
        return subprocess.CompletedProcess(cmd, returncode=rc, stdout="", stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def _make_chapter(tmp_path: Path) -> Path:
    chapter_dir = tmp_path / "Compendium A" / "Book 1" / "Section 2"
    chapter_dir.mkdir(parents=True)
    chapter = chapter_dir / "ch3.md"
    chapter.write_text(
        '---\ntitle: "Test"\nformat: pandoc-markdown\npandoc-extensions: [raw_tex]\n---\n# Hi\n'
    )
    return chapter


def test_render_invokes_pandoc_with_xelatex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.render import render

    chapter = _make_chapter(tmp_path)
    calls = _record_pandoc(monkeypatch, rc=0)

    render(chapter, corpus_root=tmp_path)

    assert calls, "pandoc was not invoked"
    cmd = calls[0]
    assert cmd[0] == "pandoc"
    assert str(chapter) in cmd
    assert "--pdf-engine=xelatex" in cmd or any(
        c == "--pdf-engine" and cmd[i + 1] == "xelatex"
        for i, c in enumerate(cmd)
        if i + 1 < len(cmd)
    )


def test_render_default_output_is_chapter_dir_with_pdf_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.render import render

    chapter = _make_chapter(tmp_path)
    calls = _record_pandoc(monkeypatch, rc=0)

    output = render(chapter, corpus_root=tmp_path)

    assert output == chapter.with_suffix(".pdf")
    cmd = calls[0]
    assert "-o" in cmd
    o_idx = cmd.index("-o")
    assert cmd[o_idx + 1] == str(chapter.with_suffix(".pdf"))


def test_render_explicit_output_overrides_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.render import render

    chapter = _make_chapter(tmp_path)
    explicit = tmp_path / "out" / "my-pdf.pdf"
    explicit.parent.mkdir(parents=True)
    calls = _record_pandoc(monkeypatch, rc=0)

    output = render(chapter, output=explicit, corpus_root=tmp_path)

    assert output == explicit
    assert str(explicit) in calls[0]


def test_render_passes_preambles_via_include_in_header_in_cascade_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multiple preambles → multiple --include-in-header flags, ordered
    most-general-first so LaTeX's later-wins semantics give the leaf
    preamble override authority."""
    from ergodix.render import render

    chapter = _make_chapter(tmp_path)
    epoch_preamble = tmp_path / "_preamble.tex"
    book_preamble = chapter.parent.parent / "_preamble.tex"
    section_preamble = chapter.parent / "_preamble.tex"
    epoch_preamble.write_text("% epoch\n")
    book_preamble.write_text("% book\n")
    section_preamble.write_text("% section\n")

    calls = _record_pandoc(monkeypatch, rc=0)

    render(chapter, corpus_root=tmp_path)

    cmd = calls[0]
    # Find positions of each preamble path in the command.
    preamble_strs = [str(epoch_preamble), str(book_preamble), str(section_preamble)]
    positions = [cmd.index(p) for p in preamble_strs]
    assert positions == sorted(positions), (
        f"preambles must appear most-general-first; got positions {positions}"
    )
    # And each should be preceded by --include-in-header.
    for p in preamble_strs:
        idx = cmd.index(p)
        assert cmd[idx - 1] == "--include-in-header"


def test_render_omits_include_in_header_when_no_preambles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.render import render

    chapter = _make_chapter(tmp_path)
    calls = _record_pandoc(monkeypatch, rc=0)

    render(chapter, corpus_root=tmp_path)

    cmd = calls[0]
    assert "--include-in-header" not in cmd


# ─── render() — error paths ────────────────────────────────────────────────


def test_render_raises_friendly_error_when_chapter_missing(tmp_path: Path) -> None:
    from ergodix.render import RenderError, render

    nonexistent = tmp_path / "no-such.md"

    with pytest.raises(RenderError) as exc:
        render(nonexistent, corpus_root=tmp_path)

    assert "not found" in str(exc.value).lower() or "exist" in str(exc.value).lower()


def test_render_raises_friendly_error_when_pandoc_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.render import RenderError, render

    chapter = _make_chapter(tmp_path)

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess:
        raise FileNotFoundError("pandoc")

    monkeypatch.setattr(subprocess, "run", boom)

    with pytest.raises(RenderError) as exc:
        render(chapter, corpus_root=tmp_path)

    msg = str(exc.value).lower()
    assert "pandoc" in msg
    # Should point user at A3 or the manual install.
    assert "install" in msg or "a3" in msg


def test_render_raises_friendly_error_when_pandoc_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.render import RenderError, render

    chapter = _make_chapter(tmp_path)
    _record_pandoc(monkeypatch, rc=1, stderr="LaTeX Error: missing package fontspec.")

    with pytest.raises(RenderError) as exc:
        render(chapter, corpus_root=tmp_path)

    msg = str(exc.value)
    # Surface the underlying stderr so the user has a real error to act on.
    assert "fontspec" in msg or "LaTeX" in msg


# ─── CLI integration ──────────────────────────────────────────────────────


def test_cli_render_subcommand_calls_render_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `ergodix render <path>` CLI subcommand must dispatch to
    ergodix.render.render. Pin so the wiring stays correct as the CLI
    surface evolves."""
    from click.testing import CliRunner

    from ergodix import render as render_module
    from ergodix.cli import main

    chapter = _make_chapter(tmp_path)

    captured: dict[str, Any] = {}

    def fake_render(
        chapter_path: Path, output: Path | None = None, corpus_root: Path | None = None
    ) -> Path:
        captured["chapter_path"] = chapter_path
        captured["output"] = output
        return chapter_path.with_suffix(".pdf")

    monkeypatch.setattr(render_module, "render", fake_render)

    runner = CliRunner()
    result = runner.invoke(main, ["render", str(chapter)])

    assert result.exit_code == 0, result.output
    assert captured["chapter_path"] == chapter


def test_cli_render_surfaces_render_error_with_nonzero_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When render() raises RenderError, the CLI must print the message
    and exit non-zero (so scripts and CI see the failure)."""
    from click.testing import CliRunner

    from ergodix import render as render_module
    from ergodix.cli import main

    chapter = _make_chapter(tmp_path)

    def fake_render(*_args: Any, **_kwargs: Any) -> Path:
        raise render_module.RenderError("Pandoc exited 1: missing package")

    monkeypatch.setattr(render_module, "render", fake_render)

    runner = CliRunner()
    result = runner.invoke(main, ["render", str(chapter)])

    assert result.exit_code != 0
    assert "missing package" in result.output or "Pandoc" in result.output
