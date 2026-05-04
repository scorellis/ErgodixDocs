# Comments and Review Markup — How They Work in ErgodixDocs

This doc explains the in-source markup conventions used for review, annotation, and editorial work in chapter `.md` files. It covers what each looks like on disk, how each renders through Pandoc → XeLaTeX → PDF, and what tooling helps you read or write each one.

## The four kinds of in-source markup

| Kind | When to use | Renders to PDF? |
|---|---|---|
| **CriticMarkup** | Editorial review (insertions, deletions, substitutions, comments, highlights) | Yes — visible during review; invisible after `--track-changes=accept` |
| **HTML comments** (`<!-- ... -->`) | Author's private notes; reminders; TODOs | No — stripped by Pandoc |
| **LaTeX comments** (`% ...`) | Lower-level annotations inside raw LaTeX blocks; sync metadata (per ADR 0006) | No — stripped by LaTeX |
| **Pandoc spans/divs with attributes** | Semantic markup (named callouts, color-coded passages, conditional rendering) | Yes — controllable per-class |

## CriticMarkup — the editorial review surface

Five syntactic patterns, all plain ASCII:

| Syntax | Meaning |
|---|---|
| `{++ added text ++}` | Editor wants this added |
| `{-- removed text --}` | Editor wants this removed |
| `{~~ old ~> new ~~}` | Editor wants old replaced with new |
| `{>> comment <<}` | Editor's standalone comment, no proposed change |
| `{== highlighted ==}{>> comment about it <<}` | Highlighted span with attached comment |

### Worked example

Source:

```markdown
The chamber {--spun around her--}{++rotated about her++}, and 
the words {==resolved themselves==}{>>this verb feels weak<<}
into a single coherent shape.
```

Three review states from the same source:

1. **Pandoc with `--track-changes=accept`**: applies all edits, drops comments. The reader's PDF.
   > The chamber rotated about her, and the words resolved themselves into a single coherent shape.

2. **Pandoc with `--track-changes=reject`**: undoes all edits, drops comments. The pre-edit version.
   > The chamber spun around her, and the words resolved themselves into a single coherent shape.

3. **Pandoc with `--track-changes=all`**: renders edits visibly with strikethrough/underline and comments as marginalia. The author's review PDF.

### Source-tagging convention (per Story 0.3)

To distinguish who wrote a comment, prefix the comment text with a bracketed tag:

```markdown
{>>[ED] this verb feels weak<<}
{>>[AI] continuity flag: chapter 4 timeline conflict<<}
{>>[NOTE] revisit after sleeping on it<<}
```

Tags are convention only — Pandoc treats them as plain text. They let the author filter or grep for specific reviewer voices.

### VS Code support

Extension: **CriticMarkup** (search the marketplace). Highlights the five patterns in distinct colors; provides a sidebar listing all comments and edits in the open file.

## HTML comments — author's private notes

Standard HTML comment syntax works inside Markdown:

```markdown
<!-- Remember: clarify Mira's age in chapter 7 before sending to Phil. -->

The chamber spun around her, and the words resolved themselves
into a single coherent shape.

<!-- TODO: this scene needs a sensory anchor — smell? sound? -->
```

**Pandoc strips all HTML comments before rendering.** They never appear in the PDF, the .docx, or any output format. Use them for notes you want to keep with the prose without exposing them to readers or editors.

Tradeoff vs. CriticMarkup `{>> ... <<}`: HTML comments are lower-key (no implied "review" semantics) and cheaper to type. CriticMarkup carries review-workflow meaning. Author's call which to use; convention is HTML comments for private notes, CriticMarkup for anything that's part of editorial review.

## LaTeX comments — inside raw LaTeX blocks only

Inside a raw LaTeX block, the LaTeX comment syntax is a single percent sign:

```markdown
\begin{landscape}
% This page must be rotated 90° clockwise per the ergodic structure.
% The reader physically reorients the book here.
\rotatebox{90}{%
  Some text the reader has to physically rotate the book to read.
}
\end{landscape}
```

XeLaTeX strips lines starting with `%` from output. They never appear in the PDF.

Use case in our pipeline: the **`% ergodix-sync:` header** that ADR 0006's publish command injects into each chapter file. It records the master commit baseline + editor + publish timestamp. Invisible to the reader; visible to humans reading the source; ignored by the renderer.

## Pandoc spans and divs — semantic markup

Pandoc Markdown supports inline spans and block divs with attributes, drawn from raw LaTeX-ish syntax:

```markdown
This is a [forbidden phrase]{.redacted .never-published} embedded in the prose.

::: {.warning}
This entire block is a callout box.
:::
```

These render conditionally based on the Pandoc template / filter you use. The default behavior is "render as a styled span/div in HTML, ignore in LaTeX." With a custom template, you can:

- Hide redacted content from the public PDF (`\newcommand{\redacted}[1]{}`)
- Style callouts with framed boxes
- Conditionally include sections based on output format

This is the most powerful and the most invasive of the four mechanisms. Reach for it only when CriticMarkup, HTML comments, and LaTeX comments don't fit the use case.

## How review actually flows

Per [ADR 0006](../adrs/0006-editor-collaboration-sliced-repos.md), the editor's primary review mechanism is **direct prose edits via signed git commits in their slice repo**, not CriticMarkup. CriticMarkup remains useful for:

- The editor leaving a comment without proposing a change
- The author's own self-notes
- AI-generated continuity flags (which the AI writes as `{>>[AI] ...<<}` markers)

Author runs `ergodix ingest --editor <name>`, gets a review branch on master with the editor's commits; reviews diffs in GitHub or VS Code; merges accepted changes; rejects others by closing the branch.

For PDFs the author wants to send a non-git editor (focus reader, line editor without git access), `ergodix render --track-changes=all` produces a markup-visible PDF; `ergodix render --track-changes=accept` produces a clean reader PDF.

## Quick cheat sheet

| You want to… | Use this | Survives render? |
|---|---|---|
| Suggest an edit to the author | CriticMarkup `{++ ++}` `{-- --}` `{~~ ~> ~~}` | Yes — visible in review PDFs |
| Leave a comment for the author | CriticMarkup `{>> <<}` | Yes — visible in review PDFs |
| Highlight a passage and comment on it | CriticMarkup `{== ==}{>> <<}` | Yes — visible in review PDFs |
| Write a private note to yourself | HTML comment `<!-- -->` | No — stripped |
| Annotate inside a raw LaTeX block | LaTeX comment `%` | No — stripped |
| Tag prose for conditional rendering | Pandoc span `[text]{.class}` or div `::: {.class}` | Depends on template |

## Tooling summary

- **CriticMarkup VS Code extension** — syntax highlighting, sidebar listing.
- **Pandoc** — `--track-changes={accept,reject,all}` flag for CriticMarkup-aware rendering.
- **`pandoc-crossref` filter** — cross-references (referenced in [ADR 0005's format inventory](../adrs/0005-roles-as-floaters-and-opus-naming.md), separate from comment markup).
- **VS Code Markdown All-in-One** — general Markdown ergonomics.
- **`ergodix render`** (planned, Story 0.2) — wraps Pandoc + XeLaTeX with the right flags per output mode.
