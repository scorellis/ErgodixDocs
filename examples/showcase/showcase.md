---
title: "Ergodix Showcase"
author: "Scott R. Ellis"
format: pandoc-markdown
pandoc-extensions: [raw_tex, footnotes, yaml_metadata_block]
---

# What ErgodixDocs Can Render

This chapter is the `examples/showcase/` fixture. It is a deliberately
small Pandoc-Markdown file that exercises the typographic features an
ergodic text needs[^why-ergodic] — footnotes, sidebars, rotation,
mirroring, raw TikZ, and an embedded figure — so that any developer
working on the render pipeline can produce a real PDF in one command:

```bash
ergodix render examples/showcase/showcase.md
```

The output is `examples/showcase/showcase.pdf` next to this file.

[^why-ergodic]: An *ergodic* text is one that demands non-trivial effort
from the reader to traverse — the structure itself is part of the work.
Aarseth, Espen J. *Cybertext: Perspectives on Ergodic Literature*, 1997.

## Sidebar — what the four phases do

\begin{tcolorbox}[
  colback=gray!8,
  colframe=gray!55,
  title=\textbf{Cantilever, in one sidebar},
  fonttitle=\bfseries,
  sharp corners,
  boxrule=0.4pt,
]
The installer runs in four phases: \textbf{inspect} (read-only system
probe), \textbf{plan + consent} (one prompt, all changes shown),
\textbf{apply} (mutative, with grouped sudo), \textbf{verify} (smoke
checks). A fifth phase, \textbf{configure}, sits between apply and
verify when interactive secrets are required. See ADRs 0010 and 0012.
\end{tcolorbox}

## Rotation, mirroring, spiral

A flourish — this passage prints upside-down so the reader has to
turn the page or the device to read it: \rotatebox{180}{the reader
must turn the page to read this sentence.}

A mirrored line, useful for reflections in dream sequences:
\reflectbox{The quick brown fox jumps over the lazy dog.}

A spiral, drawn in raw TikZ — ten turns, increasing radius, rotated
labels along the curve:

\begin{center}
\begin{tikzpicture}[scale=0.55]
  \foreach \i in {0,8,...,1080} {
    \node[rotate=\i, font=\tiny\sffamily, text=gray]
      at ({(\i/360 + 0.4) * cos(\i)}, {(\i/360 + 0.4) * sin(\i)}) {ergodix};
  }
\end{tikzpicture}
\end{center}

## An embedded figure

A TikZ-drawn diagram of the corpus hierarchy from `Hierarchy.md` — vector
graphics travel inside the PDF, so the figure stays sharp at any zoom
level[^vector]:

\begin{center}
\begin{tikzpicture}[
  level distance=14mm,
  level 1/.style={sibling distance=44mm},
  level 2/.style={sibling distance=22mm},
  every node/.style={
    rectangle, rounded corners=2pt, draw=gray!60, line width=0.4pt,
    font=\small\sffamily, inner sep=4pt, fill=gray!5,
  },
  edge from parent/.style={draw=gray!60, line width=0.3pt},
]
\node {opus}
  child { node {compendium}
    child { node {book}
      child { node {section}
        child { node {chapter} }
      }
    }
  };
\end{tikzpicture}
\end{center}

[^vector]: Raster images work too — drop a PNG or JPG next to this
file and reference it with the standard Markdown image syntax,
`![alt text](my-image.png)`. We use TikZ here so the fixture stays
self-contained with no binary blobs in the repo.

## What this fixture is *not*

It is not creative source material. The repository's
[AI-prose boundary](../../README.md#ai-boundaries--prose-is-human-written)
forbids the AI from editing chapter prose; this file is an example of
the *format* the AI reads from, not an example of the kind of writing
the AI produces.
