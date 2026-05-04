# Sprint Log

## Sprint 0

Sprint 0 is intentionally infrastructure-first: local sync, file format, auth/security, and safe repo boundaries before feature implementation.

### Story 0.1 - Establish local Google Drive sync foundation **[DONE 2026-05-02]**

So that the tool can read and reconcile Google Docs content from a reliable local source,
Value: we have a concrete filesystem anchor for import/export work instead of designing blind,
Risk: Google Drive for desktop may not expose or maintain a stable local sync surface on this Mac,
Assumptions: Google Drive for desktop can be installed, signed in, and made to present synced files locally,
Tasks:
- [x] verify Google Drive is installed and signed in
- [x] identify the local Google Drive path or mounted volume → `/Users/scorellis/My Drive/`
- [x] confirm files appear locally and update when changed remotely (Mirror mode active, first sync in progress)
- [x] capture any Drive sync errors or macOS permission blockers — none observed; mode flipped Stream → Mirror without issue
- [x] BONUS: install_dependencies.sh now bootstraps Drive install + detects mount path + generates config.json

### Story 0.2 - Define canonical repo format

So that the author can edit chapters in VS Code with full ergodic-typesetting expressive power, the editor (human collaborator) can review with CriticMarkup-style comments, and the AI can read full chapter content from the local filesystem,
Value: chapters become real, full, editable, diffable text files in Drive — no Drive/Docs API needed at runtime; bidirectional sync via Drive Mirror is automatic; ergodic typesetting (rotation, special fonts, landscape pages) is fully supported,
Risk: one-time export-from-Google-Docs migration may lose fidelity on complex formatting; the Pandoc-Markdown + raw-LaTeX hybrid may feel awkward to editors unfamiliar with either; abandoning native Google Docs loses real-time collab and Docs-native comments,
Assumptions: VS Code is the primary editor going forward; Drive Mirror reliably syncs `.md`/`.tex` files across devices; Pandoc + XeLaTeX is the canonical render path to PDF; CriticMarkup is acceptable to the editor as a review surface,

#### Format Decisions

**Canonical content format**: Pandoc Markdown with raw LaTeX passthrough.

**File extension**: `.md` **[LOCKED 2026-05-02]**.

**Mandatory YAML frontmatter** at the top of every chapter file disambiguates the Pandoc dialect (since `.md` alone is ambiguous between CommonMark, GFM, Pandoc, etc.):

```yaml
---
title: "Chapter 3 — The Glass Tower"
author: "Stephen Corellis"
format: pandoc-markdown
pandoc-extensions: [raw_tex, footnotes, citations, header_attributes]
---
```

Rationale: `.md` keeps VS Code Markdown highlighting, CriticMarkup tooling, GitHub rendering, and every "Open with…" association working out of the box. Frontmatter handles the "but it's *Pandoc* Markdown" disambiguation in a way Pandoc itself reads natively. Convention follows bookdown / Quarto / most Pandoc-authored books.

**Feature inventory (where each capability comes from):**

| Feature | Source | Syntax example |
|---|---|---|
| Headings, paragraphs, emphasis, lists | Pandoc Markdown | `# Heading`, `*italic*`, `**bold**` |
| Footnotes | Pandoc Markdown | `[^1]` inline + `[^1]: text` |
| Complex tables with captions | Pandoc Markdown | Pipe tables, grid tables |
| Citations and bibliography | Pandoc Markdown + `--citeproc` | `[@author2024]` |
| Math (inline + display) | Pandoc Markdown | `$x^2$`, `$$\int...$$` |
| Cross-references (Ch. 4, Fig. 2) | `pandoc-crossref` filter | `\ref{ch:foo}` |
| Smart quotes, em-dashes | Pandoc Markdown | Built-in via `--smart` |
| Header IDs and styled spans/divs | Pandoc Markdown | `# Title {#anchor .class}`, `[text]{.italic}` |
| Inline raw HTML/LaTeX blocks | Pandoc Markdown | ` ```{=latex}` fenced blocks |
| **Rotation** | Raw LaTeX passthrough | `\rotatebox{180}{...}` |
| **Special fonts** | Raw LaTeX passthrough | `\fontspec{...}`, `{\fontfamily{...}\selectfont ...}` |
| **Landscape pages** | Raw LaTeX passthrough | `\begin{landscape}...\end{landscape}` |
| **TikZ diagrams** | Raw LaTeX passthrough | `\begin{tikzpicture}...\end{tikzpicture}` |
| **Custom LaTeX commands** | Preamble | `\newcommand{\flicker}[1]{...}` |
| **Editorial review** | CriticMarkup (plain text in file) | `{++add++} {--del--} {>>comment<<}` |

**Render pipeline**: Pandoc → XeLaTeX → PDF. XeLaTeX (not pdflatex) so Unicode and modern OpenType fonts work natively.

**Folder layout** (under `~/My Drive/Tapestry of the Mind/`):
- Mirrors the structure in [Hierarchy.md](Hierarchy.md): `Compendium/Book/Section/Chapter.md`
- AI-generated artifacts live in a parallel `_AI/` subfolder
- Optional `_archive/` holds the original `.gdoc` files post-migration as a safety net

**Tasks:**
- [x] **Lock the file extension**: `.md` chosen with mandatory YAML frontmatter declaring `format: pandoc-markdown`. Decided 2026-05-02.
- [ ] **Migration orchestrator (`ergodix migrate --from <importer>`)**: orchestrator dispatches to a plugin in `importers/`. Per [ADR 0001](adrs/0001-click-cli-with-persona-floater-registries.md), Open/Closed at the command surface — new sources land as new files in `importers/`.
  - [ ] **`importers/gdocs.py`**: walk `~/My Drive/Tapestry of the Mind/`, for each `.gdoc` call Drive's `files.export` (mimeType: `text/markdown`), write `<basename>.md` alongside with YAML frontmatter prepended, move the original `.gdoc` to `_archive/`.
  - [ ] **`importers/scrivener.py`**: read a `.scriv` bundle (filesystem-only, no API). Walk `Files/Data/<UUID>/content.rtf` per chunk; consult `Docs.xml` for hierarchy / titles. Run RTF through Pandoc → Markdown; prepend frontmatter populated from Scrivener metadata where available (synopsis, status). **v1: flat dump to `_unsorted/`** — author reorganizes into the canonical hierarchy in VS Code afterward. Mapping-manifest support deferred.
  - [ ] **Future importers** (`importers/docx.py`, `importers/text.py`, etc.) — out of Sprint 0 scope; documented as the extension model in ADR 0001.
- [ ] **Editor collaboration commands (`ergodix publish` / `ergodix ingest`)**: implement the sliced-repository workflow per [ADR 0006](adrs/0006-editor-collaboration-sliced-repos.md). Author-side, run continuously (not bootstrap).
  - [ ] **`slices/registry.json` schema implementation** in the master corpus repo: editors, slice repo URLs, public-key fingerprints, assigned files, baseline SHAs, policy flags.
  - [ ] **`ergodix publish --editor <name>`**: clone/update slice repo scratch dir, copy authorized files, inject sync header comment, commit, push, update registry baseline, commit registry to master.
  - [ ] **`ergodix ingest --editor <name>`**: fetch slice, verify signed commits, verify all changed files within `assigned_files`, generate patches via `git format-patch`, apply via `git am --3way` to a review branch on master, leave unmerged for author review.
  - [ ] **`--bundle` mode** (stretch goal): produce/consume git bundles for air-gap exchange.
  - [ ] **Tests**: clean publish, publish with file removal, ingest with no conflicts, ingest with three-way merge, ingest with unauthorized file modification (must abort), ingest with unsigned commits (must abort), path-rename rejection, registry round-trip.
- [ ] **Editor floater cantilever extensions** (per [ADR 0006](adrs/0006-editor-collaboration-sliced-repos.md) integration): generate SSH signing key (`ssh-keygen -t ed25519`), register as a signing key on GitHub via `gh ssh-key add --type signing`, configure local git to sign commits by default (`git config commit.gpgsign true`, `git config gpg.format ssh`).
- [ ] **Frontmatter template**: define the canonical YAML schema (required keys: `title`, `author`, `format`, `pandoc-extensions`; optional: `book`, `section`, `chapter`, `revision`). Migration script populates from Drive metadata where possible.
- [ ] **Migration fidelity audit**: run on a sample chapter; document what survived, what didn't, what needs hand-fix.
- [ ] **VS Code setup recipe** for both author and editor: Pandoc Markdown extension, raw LaTeX preview, CriticMarkup extension, recommended settings. Documented in `docs/vscode-setup.md` (file to be created).
- [ ] **Render command**: `ergodix render <chapter>` produces the PDF via Pandoc + XeLaTeX. Optional `--accept-edits` flag to flatten CriticMarkup before render.
- [ ] **Folder convention validation**: confirm the Hierarchy.md structure survives migration; decide on slugification rules for filenames.

### Story 0.3 - Define the in-file review and comment representation

> **Note (2026-05-03):** [ADR 0006](adrs/0006-editor-collaboration-sliced-repos.md) demoted CriticMarkup from primary editorial review surface to optional annotation. The editor's primary review mechanism is now direct prose edits via signed git commits in their slice repo, with the author reviewing via three-way merge in a review branch. CriticMarkup remains useful for: (a) the editor leaving comments without proposing changes (`{>>this paragraph feels weak<<}`), (b) the author's own self-notes, (c) AI-generated continuity flags. The tasks below are revised to reflect this — the migration to `.md` no longer needs CriticMarkup ingestion to be its primary purpose.

So that all forms of collaboration context — editor annotations (comments without proposed changes), the author's own writing notes, AI-generated continuity flags, and any legacy comments extracted from the original `.gdoc` files at migration time — share a single, plain-text, git-diffable representation inside the chapter `.md` files,
Value: review context survives every sync and every editor; nothing requires a proprietary comment store; renders cleanly to PDF with `--track-changes=accept` (or equivalent) when producing reader output,
Risk: a single representation may not fit every comment type equally well; CriticMarkup syntax may be visually noisy in long passages; legacy `.gdoc` comments may not extract cleanly via the Drive API,
Assumptions: CriticMarkup (`{++add++} {--del--} {>>comment<<} {==highlight==}{>>comment<<}`) is the right surface; Drive's `comments.list` endpoint can extract anchored comments from `.gdoc` files at migration time; AI-generated review markers can be tagged distinguishably so the author can filter them,
Tasks:
- [ ] **enumerate the comment-fidelity gap explicitly**: Google Docs comments carry author identity, ISO timestamp, thread/reply chain, resolution state, and a stable text-range anchor. CriticMarkup carries none of these natively. For each piece, decide: encode in the marker (e.g. `{>>[ED:alice 2026-05-02] foo<<}`), encode out-of-band (sidecar JSON), or accept the loss. Document the decisions before the migration script touches real comments.
- [ ] confirm CriticMarkup as the canonical syntax (decided in Story 0.2 but call it out here too)
- [ ] decide how to **tag the source** of a comment so author / editor / AI / legacy comments are distinguishable: e.g. `{>>[ED] this verb feels weak<<}`, `{>>[AI] continuity flag: chapter 4 timeline conflict<<}`, `{>>[NOTE] revisit after sleeping on it<<}`
- [ ] decide whether reply chains flatten into a single comment block, become numbered sub-comments, or get dropped (Google Docs supports nested replies; CriticMarkup is flat)
- [ ] decide what to do with **resolved** comments at migration time: drop them, archive them in a sidecar, or keep them with a `[RESOLVED]` tag
- [ ] extend the migration script to read `.gdoc` comments via `drive.comments.list` and embed them as CriticMarkup at the right anchor positions
- [ ] decide conflict / resolution behavior: when a CriticMarkup edit is accepted, is the resolution baked into the file via `pandoc --track-changes=accept`? Or do we leave a tombstone? (recommendation: bake — simpler)
- [ ] document the convention in `docs/review-syntax.md` (file to be created) so editors and collaborators have one place to learn it

### Story 0.4 - Separate tracked tools from untracked creative material **[DONE 2026-05-02]**

So that tooling can be versioned publicly without exposing the creative corpus,
Value: repository hygiene and safer publishing boundaries,
Risk: accidental commits of source material if ignore boundaries are weak,
Assumptions: local folder structure can cleanly separate tools from creative assets,
Tasks:
- [x] define tracked versus untracked directories — single-directory model adopted; boundaries enforced by `.gitignore` and conventions
- [x] add ignore rules for creative materials — `.gitignore` covers `local_config.py`, `.ergodix_*`, `.venv/`, `*.gdoc`, `*.gsheet`, `*.gslides`, `/creative/`, `/content/`, `/build/`
- [x] document the boundary in repo docs — README "Install" and "Auth & Secrets" sections
- [x] validate that common commands do not stage ignored content — verify after first commit of new files
- [x] BONUS: boundary simplified by removing `update.sh`; updates use plain `git pull`; secrets centralized in `~/.config/ergodix/` with OS keyring as primary store

### Story 0.5 - Layered auth & secrets with least privilege **[DONE 2026-05-02]**

So that we can call Anthropic and Google APIs without leaking secrets to GitHub or widening blast radius across tools,
Value: reusable auth structure across all ErgodixDocs deployments, defensible scope discipline,
Risk: per-project credentials sprawl, or over-broad OAuth scopes that grow into a security hazard,
Assumptions: OS keyrings are reliably available on the platforms ErgodixDocs targets (macOS first; Linux/Windows via keyring's portable backends),
Tasks:
- [x] decide central vs. per-project boundary — central: app-level keys (Anthropic, GCP OAuth client). Per-project: user OAuth refresh tokens.
- [x] declare minimum scopes — `drive.readonly` + `documents.readonly` only; documented in `auth.py`
- [x] enforce filesystem permissions — `~/.config/ergodix/` mode 700; `secrets.json`, `local_config.py`, `.ergodix_tokens.json` mode 600
- [x] add `auth.py` — scope constants, three-tier credential lookup, stub Drive/Docs service builders
- [x] **upgrade primary store to OS keyring** (`keyring` lib, service `ergodix`); file becomes fallback only — encrypted-at-rest, no plaintext secret on disk during normal use
- [x] add CLI: `set-key`, `delete-key`, `status`, `migrate-to-keyring`
- [x] document the model in README "Auth & Secrets" section
- [x] reframe naming for general-author distribution (no `scorellis-tools` references)

### Story 0.6 - End-to-end smoke test

So that we have proof the whole pipeline works on real Tapestry content before declaring Sprint 0 done,
Value: validates auth + migration + frontmatter + render path together; surfaces fidelity issues early; confirms the single-directory workflow holds up in practice,
Risk: the smoke test reveals integration problems that send us back to Story 0.2 for changes,
Assumptions: one representative chapter is enough to validate the pipeline (we can broaden later if it isn't),
Tasks:
- [ ] pick one representative chapter from `Tapestry of the Mind` (something with mixed prose, footnotes, maybe one ergodic moment)
- [ ] run the full loop: `ergodix migrate` on that one chapter → confirm `.md` + frontmatter is correct → open in VS Code → render via `ergodix render` → inspect the PDF
- [ ] document any fidelity loss; decide which losses block Sprint 0 closure vs. acceptable for v1
- [ ] re-run after any Story 0.2 fixes; confirm idempotent
- [ ] **bump `VERSION` to 0.2.0 and add a `[0.2.0]` entry to `CHANGELOG.md`** capturing the migrate/render/frontmatter work, smoke-test results, and any fidelity-loss notes. Move `[Unreleased]` items into the new release section.

### Story 0.8 - Architecture spike: orchestrator pattern, role-based cantilever, editor collaboration model **[DESIGN SPIKE]**

This story produces decisions, not code. Each task is a discussion topic. Discussion outcomes get recorded as updates to this story (and follow-up stories where appropriate) before any related implementation begins.

So that ErgodixDocs has one coherent operational pattern (single orchestrator + manifest-driven prereqs + small single-purpose modules) modeled on UpFlick conventions, with role-aware modes (`--writer`, `--editor`, `--developer`) and a defensible editor-collaboration + permissions model — all locked in *before* Story 0.2 / 0.3 / 0.6 implementation begins,

Value: prevents the bolt-on tooling sprawl that comes from writing standalone commands one at a time; aligns this codebase with UpFlick conventions for cross-tool consistency; surfaces editor-workflow + permissions decisions early enough that they can shape the migration script's output structure and the repo's public/private split,

Risk: design-by-committee; the chosen pattern may not survive contact with real implementation; over-specifying roles up front creates flag complexity we never use,

Assumptions: UpFlick's orchestrator + manifest pattern is well-considered enough to be a starting point; a single `ergodix` CLI with role flags is more discoverable than N separate commands; GitHub's existing access controls are sufficient for editor permissions without inventing new infrastructure,

#### Discussion Topics (each yields a decision; mark `[DECIDED: ...]` inline as we go)

- [x] **Topic 1 — Orchestrator pattern review.** **[DECIDED 2026-05-03]** Adopt **Click subcommand groups** with three plugin registries (personas, floaters, importers) for Open/Closed extensibility. See [Spike 0001](spikes/0001-orchestrator-pattern.md) for the discussion and [ADR 0001](adrs/0001-click-cli-with-persona-floater-registries.md) for the locked decision.
- [ ] **Topic 2 — Prereqs layout.** Where do prerequisite checks live and what's their interface contract? Options: subfolder `prereqs/` with one Python script per check (UpFlick-ish), single `prereqs.py` with one function per check, or a manifest file (JSON/YAML/TOML) the orchestrator interprets. Decide: what each prereq returns, how the orchestrator chains them, what happens on failure (continue / abort / prompt).
- [x] **Topic 3 — `--cantilever` semantics.** **[DECIDED 2026-05-03]** Closed by [ADR 0003](adrs/0003-cantilever-bootstrap-orchestrator.md). 22-operation menu (A1–F2 + D5), all idempotent, abort-fast with detailed remediation messaging, auto-detected connectivity, settings in `settings/` (TOML), per-machine run-record at `~/.config/ergodix/cantilever.log`. Continuous polling job spun out as [ADR 0004](adrs/0004-continuous-repo-polling.md).
- [x] **Topic 4 — Role flag matrix.** **[DECIDED 2026-05-03]** Closed by [ADR 0005](adrs/0005-roles-as-floaters-and-opus-naming.md). Personas and floaters collapsed into a single registry; every role is a floater. Each role's TOML declares `adds_operations` and (for focus-reader only) `exclusive_with`. CLI surface: `ergodix --writer --developer cantilever`, etc. Empty-flag invocations fail fast. Multi-corpus container named **opus** (locked into Story 0.X for future implementation).
- [x] **Topic 5 — Bidirectional flow architecture.** **[DECIDED 2026-05-03]** Closed by [ADR 0002](adrs/0002-repo-topology-and-editor-onboarding.md), updated by [ADR 0006](adrs/0006-editor-collaboration-sliced-repos.md). Editor's edits flow via signed commits to a per-editor slice repo; author runs `ergodix ingest` to surface a review branch on master. AI artifacts go to `_AI/` and are author-committed manually.
- [x] **Topic 6 — Permissions + public/private split.** **[DECIDED 2026-05-03]** Closed by [ADR 0002](adrs/0002-repo-topology-and-editor-onboarding.md), updated by [ADR 0006](adrs/0006-editor-collaboration-sliced-repos.md). `ErgodixDocs` (public, tooling) + per-opus master corpus repo (private) + per-editor slice repos (private, file-scoped). Hard read access control via slicing; per-editor blast radius bounded; clean revocation by ceasing to publish + rotating slice credentials.
- [ ] **Topic 7 — Pandoc / LaTeX comment representation explainer.** Educational task: write a short doc (`docs/comments-explained.md`) that shows, with examples, exactly what CriticMarkup, HTML comments, and raw LaTeX comments look like on disk; how each renders in Pandoc → XeLaTeX → PDF; what tooling (VS Code extensions, Pandoc filters, `--track-changes`) does what. This is the input to Topic 8.
- [x] **Topic 8 — Editor mode vs. plain GitHub.** **[DECIDED 2026-05-03]** Closed by [ADR 0002](adrs/0002-repo-topology-and-editor-onboarding.md), updated by [ADR 0006](adrs/0006-editor-collaboration-sliced-repos.md) and [ADR 0005](adrs/0005-roles-as-floaters-and-opus-naming.md). Editor is a real floater with concrete cantilever steps (gh auth, slice repo clone, SSH signing key generation + GitHub registration, VS Code + CriticMarkup install for optional annotations, auto-sync VS Code task targeting the slice repo). Daily flow remains zero-command via Cmd+S → debounced `ergodix sync` (now pushing to the editor's slice).
- [ ] **Topic 9 — CLI entry point & installation.** Where does the `ergodix` command live? Options: `ergodix.py` at repo root, console-script entry in `pyproject.toml` once we package, shell wrapper `bin/ergodix` that invokes `python -m ergodix`. How does it end up on the user's PATH after `./install_dependencies.sh` runs? Does activation of `.venv` matter to the end user?
- [ ] **Topic 10 — Migration plan from current `install_dependencies.sh`.** Concrete refactor: probably rename to `bootstrap.sh` (UpFlick convention), extract package list to `requirements.txt`, extract Drive detection to `prereqs/check_drive.py`, extract config generation to `prereqs/generate_config.py`, extract credential-store setup to `prereqs/setup_credstore.py`. Document what survives, what gets renamed, what gets split, and what the `bootstrap.sh` → `ergodix --cantilever` handoff looks like.

#### How this story closes

Spike closes when Topics 1–10 are all `[DECIDED]` with their resolutions inlined or linked to follow-up implementation stories (which may be created during the spike). At that point, Story 0.2's implementation tasks (`ergodix migrate`, `ergodix render`) and Story 0.3's editor workflow can proceed against a coherent design.

## Sprint 1 (placeholder — design when Sprint 0 closes)

The actual reason this project exists: AI as architectural co-author. These stories will be fleshed out when Sprint 0 ships.

### Story 1.1 - Plotline tracking
So that the author can see every active plotline across the universe and where each one is in its arc.

### Story 1.2 - Plot-hole and continuity detection
So that the AI surfaces contradictions, timeline conflicts, and broken cause-effect chains before they ship.

### Story 1.3 - On-demand summaries
So that the author can ask for a one-page summary of any book, section, or character thread without re-reading the source.

### Story 1.4 - Storyboards
So that the author can visualize scene sequencing and pacing across a book or compendium.

### Story 1.5 - Worldbuilding support
So that the AI can answer "is this consistent with what we've established?" against a living, evolving Tapestry-Mechanics knowledge base.

## Resolved Decisions (post-design)

These were open questions in earlier design discussions and have since been settled. Kept here as a record so future planning doesn't reopen them without intent.

- **Sync transport: filesystem via Drive Mirror**, not Drive/Docs API at runtime. Resolved 2026-05-02 in Story 0.2. The API is used only during the one-time `ergodix migrate` step.
- **Comment representation: CriticMarkup in-file**, not sidecar files or a centralized metadata store. Resolved 2026-05-02 in Stories 0.2 and 0.3.
- **Bidirectional sync: yes, but via Drive Mirror**, not via API write-back. Chapters edited locally in VS Code; AI-generated artifacts written locally to `_AI/`; Drive Mirror syncs everything in both directions. Resolved 2026-05-02.
- **Primary editor: VS Code, not Google Docs.** After one-time migration, native `.gdoc` files are archived. Resolved 2026-05-02 in Story 0.2.

## Parking Lot

- **Story 0.7 — Distribution prep** (deferred until Sprint 1+): pip-installable package, standalone GitHub clone, Homebrew formula? Decide *after* the tool is working end-to-end.
- **AI commenting on chapter docs** (deferred indefinitely): if the AI ever wants to write CriticMarkup directly into chapter `.md` files (rather than just emitting a flag report), revisit the AI-prose boundary policy. Currently the AI writes only into `_AI/` files, never into chapter prose.

### Story 0.X - Multi-opus support (deferred to Sprint 1+ or first real use case)

**Terminology:** an **opus** is a named bundle of (corpus path + default floater set + last-used context). Plural: **opera**. Term chosen to fit the project's classical/Latin voice without colliding with Compendium (a level in the narrative Hierarchy).

So that one machine and one identity can address multiple opera with different role-sets per opus (you on Tapestry as writer/dev/publisher; you on a friend's manuscript as focus-reader; an editor working two authors' books in parallel),

Value: makes ErgodixDocs viable as the underlying tool when adoption broadens past one author; lets a single user split work across opera without re-installing per project,

Risk: introducing the dimension prematurely costs more than waiting; conflating this with enterprise tenancy concerns that aren't actually adjacent,

Assumptions: forward-compatible architectural pieces already in place (registries, settings folder, three-tier credential lookup); `local_config.py`'s `TAPESTRY_FOLDER` becoming a dict keyed by opus name is non-breaking,

CLI shape (locked at story-open time):

```bash
ergodix opus list
ergodix opus add tapestry --corpus tapestry-of-the-mind --writer --developer --publisher
ergodix opus add friend-novel --corpus their-book --focus-reader
ergodix opus switch tapestry
ergodix cantilever                  # uses current opus
ergodix sync                        # uses current opus
```

Each opus is stateful — `opus switch <name>` sets a current-opus pointer (probably in `local_config.py`); subsequent commands inherit its corpus + floater config.

Tasks (filled out when story moves out of parking lot):
- [ ] confirm stateful (`switch`) vs. per-invocation (`--opus <name>`) — likely support both, with `switch` writing the current pointer used as default for subsequent invocations
- [ ] extend `local_config.py` schema: `OPERA = { "tapestry": {...}, "friend-novel": {...} }` plus `CURRENT_OPUS` pointer
- [ ] update cantilever to take opus context as input (which floaters apply to which opus)
- [ ] update `ergodix sync`, `migrate`, `render`, `status` to be opus-aware
- [ ] migration path for existing single-opus installs (the existing `TAPESTRY_FOLDER` becomes the first entry under `OPERA["default"]`)

### Scale concerns (deferred; activate per real signal)

The dimensions below are real architectural considerations even though they don't have urgency yet. Forward-compatibility decisions made now should not foreclose any of them. Each becomes its own story when activated.

#### Story 0.Z1 - Concurrency and write-collision handling

So that multiple editors can work on the corpus simultaneously without losing edits or producing broken merges,

Value: real-world co-editing (writer + editor + future line editor) needs to be safe; auto-sync racing against itself across machines is the failure mode this prevents,

Risk if ignored: silent data loss when two auto-syncs land in overlapping windows; surprising conflicts that bypass the editor persona's "zero-friction" promise,

Assumptions: each editor's machine works on independent feature branches by default; sync conflicts on shared branches surface as standard git conflicts; debouncing in the auto-sync VS Code task is part of the solution but not the whole solution,

Investigate when activated: per-machine sync queues; conflict detection in `ergodix sync` before push (warn user when remote has new commits on the same branch); fast-forward-only sync as default; explicit `ergodix sync --force` for the rare overrule case.

#### Story 0.Z2 - Corpus volume and AI analysis efficiency

So that the AI architectural-analysis features (plotline tracking, continuity detection, summaries, storyboards — Sprint 1) work on a full multi-book corpus (200+ chapters, 1M+ words) without per-invocation context-bloat or cost explosion,

Value: this is the actual product. "Load the whole corpus into the context window every time" stops working at corpus sizes serious authors will quickly reach,

Risk if ignored: AI features are demoware that only work on tiny samples; the tool's reason-for-existing fails to scale with the user's actual writing,

Assumptions: prompt caching meaningfully cuts repeat-analysis cost (Anthropic's prompt cache has a 5-minute TTL — useful for active sessions); per-chapter analysis with cross-chapter index is tractable; vector-store retrieval-augmented generation is a viable layer on top; incremental analysis (only re-analyze what changed) is implementable,

Investigate when activated: chapter-level analysis index; embedding-based retrieval over the corpus; prompt-caching strategy per command; result caching on disk so repeat invocations are free; batch APIs (Anthropic supports batch jobs) for non-interactive work.

#### Story 0.Z3 - Long-tail: history, retention, storage growth

So that the corpus repo remains performant after 5+ years of edits, render outputs don't bloat git, and old AI artifacts don't accumulate forever,

Value: serious authors work on multi-decade projects; the tool should not become the bottleneck,

Risk if ignored: git operations slow as history grows; PDF render outputs balloon the repo; the `_AI/` folder becomes a graveyard of stale analyses; clone times become a barrier for new contributors,

Assumptions: git LFS for binary render outputs is viable; `.gitattributes` patterns can isolate large artifacts; retention policies are configurable per opus,

Investigate when activated: git LFS for `_AI/` PDFs and render outputs; `.gitattributes` configuration; retention policy in `settings/` (e.g. "keep latest 5 render outputs per chapter, delete older"); cantilever-time pruning operation; corpus-archive command for cold-storing old material.

#### Story 0.Z4 - AI cost and quota management

So that AI architectural-analysis features have predictable cost, hard caps to prevent runaway billing, and (eventually) per-user allocation when an organization runs the tool,

Value: a writer running daily continuity analysis on a million-word corpus can rack up real bills; an enterprise running it across many authors will demand budget controls,

Risk if ignored: surprise bills become a tool-killer; users avoid AI features because cost is opaque; enterprise adoption is blocked entirely,

Assumptions: aggressive prompt caching cuts the dominant cost; monthly caps configured at cantilever time are practical; usage telemetry can be opt-in for users who want a cost dashboard; per-feature cost reporting is implementable,

Investigate when activated: prompt caching strategy; per-user / per-opus monthly cap with hard cutoff; cost dashboard (`ergodix cost report`); telemetry that respects privacy (opt-in, never includes prose); enterprise extension hooks for centralized billing (relates to Story 0.Y).

#### Story 0.Z5 - Graceful degradation and resilience

So that ErgodixDocs works (or fails gracefully and informatively) under partial outages: keyring locked, Anthropic API down, GitHub unavailable, Drive offline, Pandoc broken, XeLaTeX missing,

Value: trust. The tool should not become a catastrophic single point of failure when any one external dependency is degraded; users should not develop workaround habits that bypass the tool,

Risk if ignored: any single dependency outage blocks all work; users learn to circumvent the tool; the auto-sync flow becomes a liability when the network is intermittent,

Assumptions: most operations have viable fallback paths (cached results, deferred operations, read-only modes); failure mode classification is implementable; "degraded mode" can be communicated clearly via `ergodix status`,

Investigate when activated: failure-mode catalog per operation (already has a kernel in ADR 0003's auto-fix concept); circuit breakers on external API calls; explicit degraded-mode indicators surfaced in CLI output and the run-record; cached-result fallback for AI features when the API is unavailable.

### Story 0.Y - Publishing-house / enterprise scale (deferred — not a current target)

Documented for future architectural consideration. Not actively planned.

**What scales as-is:**
- Persona/floater registry — adding `line-editor`, `developmental-editor`, `proofreader`, etc. is the existing extension pattern
- Cantilever orchestrator — independent of user count; each machine runs its own
- Continuous polling — per-machine, each machine independent
- AI-prose boundary — applies uniformly regardless of org size
- Settings TOML structure — same registry shape works at any scale
- Importer registry — new sources added without touching core

**What doesn't scale and would need additions:**
- **Two-repo single-tenant model**: 500 authors = 500 corpus repos. Need org-level GitHub structure (sub-orgs per imprint), bulk-onboarding, repo templates.
- **Per-machine OS keyring credentials**: enterprise wants SSO (SAML/OIDC), centrally issued/revoked tokens, vault integration (Vault, AWS Secrets Manager). Current three-tier lookup extends cleanly — add a "Tier 0: SSO/vault" stage above env var.
- **Per-individual GitHub auth (`gh auth login`)**: enterprise wants GitHub Enterprise + SAML SSO. Same OAuth flow, different IdP.
- **Per-machine `local_config.py`**: managed devices need IT-pushed config. Add an `org_config.toml` URL or path that gets layered under `local_config.py`.
- **Per-machine cantilever / poller logs**: enterprise audit needs centralized log forwarding (Splunk, Datadog, S3). Add a "log destination" setting that supports remote sinks.
- **Individual Anthropic API keys**: enterprise wants centralized billing + per-author quotas. Add support for organization-issued keys with per-author allocation tracking.
- **GitHub branch protection per-repo**: enterprise wants policies enforced org-wide. GitHub provides this at org level; we'd document the recommended config but enforcement is GitHub's job, not ours.
- **Compliance** (SOC 2, ISO 27001, GDPR): out of scope for the tool itself; the surrounding deployment + ops practice carries the compliance burden.

**Architectural verdict:** the current design is single-author-centric and **doesn't preclude** enterprise scaling. Every gap above maps to an additive extension using patterns we already have (registries, settings layering, three-tier lookup). None require tearing anything out.

**Recommendation if/when this story activates:** treat it as Sprint 3+ work. Start by identifying the first real enterprise customer's actual needs rather than designing speculative abstractions. Most of the "enterprise readiness" list above is wrong until a specific buyer's procurement requirements clarify it.