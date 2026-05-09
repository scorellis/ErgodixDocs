# Showcase fixture

A one-chapter Pandoc-Markdown example that exercises every typographic
feature ErgodixDocs supports today — footnotes, sidebars (`tcolorbox`),
rotation (`\rotatebox`), mirroring (`\reflectbox`), raw TikZ, and an
embedded vector figure.

## Render it

From the repo root, after `bootstrap.sh` has installed `ergodix` on
PATH:

```bash
ergodix render examples/showcase/showcase.md
```

That writes `examples/showcase/showcase.pdf` next to the source.

The render pipeline:

1. Walks up from `showcase.md` to the corpus root and collects every
   `_preamble.tex` it finds, ordered most-general-first (so leaf-most
   preambles override ancestors). For this fixture, only one preamble
   is in play.
2. Invokes `pandoc showcase.md --pdf-engine=xelatex
   --include-in-header _preamble.tex -o showcase.pdf`.

## Why this lives in the repo

Two reasons:

- **Manual smoke test.** When a render-pipeline change lands, this
  fixture is the fastest end-to-end check that produces a real PDF.
- **Format reference.** New contributors can read `showcase.md` to
  see exactly which Pandoc and raw-LaTeX patterns the project supports.

The PDF itself is *not* committed (it's gitignored at the repo level
via `*.pdf`). Each developer renders their own.
