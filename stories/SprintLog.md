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
- **One `.md` file per Chapter** — chapters are the smallest creative unit. **[LOCKED 2026-05-03]**
- AI-generated artifacts live in a parallel `_AI/` subfolder
- Optional `_archive/` holds the original `.gdoc` files post-migration as a safety net

**LaTeX preamble cascade** **[LOCKED 2026-05-03]**:

A `_preamble.tex` file is **optional at every folder level** of the hierarchy (Epoch / Compendium / Book / Section). When `ergodix render` builds a chapter, it walks up the folder tree from the chapter's directory to the corpus root, collects every `_preamble.tex` it finds, concatenates them most-general-first, and passes the result to Pandoc via `--include-in-header`.

LaTeX naturally honors override-by-redefinition (later-loaded definition wins), so:
- the epoch preamble sets project-wide defaults (fonts, page geometry, custom commands),
- a compendium / book / section preamble can override anything for that branch,
- siblings unaffected.

**Three scopes for font / style changes:**

| Scope | Mechanism | Example |
|---|---|---|
| Single passage | Inline `{\fontfamily{cmtt}\selectfont ...}` in chapter prose | One paragraph in monospace inside an otherwise-Garamond chapter |
| Single chapter | YAML frontmatter `extra-preamble:` block with raw LaTeX | This chapter only in Times New Roman |
| Entire book / section | Drop `_preamble.tex` in that folder | All of Book Two in Crimson Pro |

The render command is ~15 lines: walk up the directory tree, collect `_preamble.tex` files in order, concatenate. No plugin system, no settings file — file presence at folder boundaries does the work.

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

### Story 0.8 - Architecture spike: orchestrator pattern, role-based cantilever, editor collaboration model **[DESIGN SPIKE — DONE 2026-05-03]**

**All 10 topics resolved.** ADRs 0001–0008 cover the locked decisions; spikes 0001–0006 capture the discussions. Story 0.8 closes here; implementation work continues under Story 0.2 (and follow-on stories) against the locked architecture.

**Closing notes:**
- All 22 cantilever prereq operations stay as separate modules under `ergodix/prereqs/` regardless of size. Consistency over file-count savings.
- Author works in `--writer --developer` floater combination during the project's pre-release year. No external authors invited until the tool stabilizes.

This story produces decisions, not code. Each task is a discussion topic. Discussion outcomes get recorded as updates to this story (and follow-up stories where appropriate) before any related implementation begins.

So that ErgodixDocs has one coherent operational pattern (single orchestrator + manifest-driven prereqs + small single-purpose modules) modeled on UpFlick conventions, with role-aware modes (`--writer`, `--editor`, `--developer`) and a defensible editor-collaboration + permissions model — all locked in *before* Story 0.2 / 0.3 / 0.6 implementation begins,

Value: prevents the bolt-on tooling sprawl that comes from writing standalone commands one at a time; aligns this codebase with UpFlick conventions for cross-tool consistency; surfaces editor-workflow + permissions decisions early enough that they can shape the migration script's output structure and the repo's public/private split,

Risk: design-by-committee; the chosen pattern may not survive contact with real implementation; over-specifying roles up front creates flag complexity we never use,

Assumptions: UpFlick's orchestrator + manifest pattern is well-considered enough to be a starting point; a single `ergodix` CLI with role flags is more discoverable than N separate commands; GitHub's existing access controls are sufficient for editor permissions without inventing new infrastructure,

#### Discussion Topics (each yields a decision; mark `[DECIDED: ...]` inline as we go)

- [x] **Topic 1 — Orchestrator pattern review.** **[DECIDED 2026-05-03]** Adopt **Click subcommand groups** with three plugin registries (personas, floaters, importers) for Open/Closed extensibility. See [Spike 0001](spikes/0001-orchestrator-pattern.md) for the discussion and [ADR 0001](adrs/0001-click-cli-with-persona-floater-registries.md) for the locked decision.
- [x] **Topic 2 — Prereqs layout.** **[DECIDED 2026-05-03]** Closed by [ADR 0007](adrs/0007-bootstrap-prereqs-cli-entry.md). One Python module per operation under `ergodix/prereqs/`, each exposing `def check() -> CheckResult`. Cantilever loads, dispatches, acts on result.
- [x] **Topic 3 — `--cantilever` semantics.** **[DECIDED 2026-05-03]** Closed by [ADR 0003](adrs/0003-cantilever-bootstrap-orchestrator.md). 25-operation menu (A1–A7, B1–B2, C1–C6, D1–D6, E1–E2, F1–F2; D5 added by ADR 0004 for the poller, D6 added by ADR 0006 for editor signing-key setup). All idempotent, abort-fast with detailed remediation messaging, auto-detected connectivity, settings in `settings/` (TOML), per-machine run-record at `~/.config/ergodix/cantilever.log`. Continuous polling job spun out as [ADR 0004](adrs/0004-continuous-repo-polling.md).
- [x] **Topic 4 — Role flag matrix.** **[DECIDED 2026-05-03]** Closed by [ADR 0005](adrs/0005-roles-as-floaters-and-opus-naming.md). Personas and floaters collapsed into a single registry; every role is a floater. Each role's TOML declares `adds_operations` and (for focus-reader only) `exclusive_with`. CLI surface: `ergodix --writer --developer cantilever`, etc. Empty-flag invocations fail fast. Multi-corpus container named **opus** (locked into Story 0.X for future implementation).
- [x] **Topic 5 — Bidirectional flow architecture.** **[DECIDED 2026-05-03]** Closed by [ADR 0002](adrs/0002-repo-topology-and-editor-onboarding.md), updated by [ADR 0006](adrs/0006-editor-collaboration-sliced-repos.md). Editor's edits flow via signed commits to a per-editor slice repo; author runs `ergodix ingest` to surface a review branch on master. AI artifacts go to `_AI/` and are author-committed manually.
- [x] **Topic 6 — Permissions + public/private split.** **[DECIDED 2026-05-03]** Closed by [ADR 0002](adrs/0002-repo-topology-and-editor-onboarding.md), updated by [ADR 0006](adrs/0006-editor-collaboration-sliced-repos.md). `ErgodixDocs` (public, tooling) + per-opus master corpus repo (private) + per-editor slice repos (private, file-scoped). Hard read access control via slicing; per-editor blast radius bounded; clean revocation by ceasing to publish + rotating slice credentials.
- [x] **Topic 7 — Pandoc / LaTeX comment representation explainer.** **[DONE 2026-05-03]** Educational doc shipped at [docs/comments-explained.md](docs/comments-explained.md). Covers CriticMarkup, HTML comments, LaTeX comments, and Pandoc spans/divs — with worked examples, render outcomes, VS Code extension list, and tooling cheat sheet.
- [x] **Topic 8 — Editor mode vs. plain GitHub.** **[DECIDED 2026-05-03]** Closed by [ADR 0002](adrs/0002-repo-topology-and-editor-onboarding.md), updated by [ADR 0006](adrs/0006-editor-collaboration-sliced-repos.md), [ADR 0005](adrs/0005-roles-as-floaters-and-opus-naming.md), and [ADR 0008](adrs/0008-cleanup-sync-rename-ownership-autofix-static-analysis.md). Editor is a real floater with concrete cantilever steps (gh auth, slice repo clone, SSH signing key generation + GitHub registration, VS Code + CriticMarkup install for optional annotations, auto-sync VS Code task targeting the slice repo). Daily flow remains zero-command via Cmd+S → debounced `ergodix sync-out` (renamed from `sync` per ADR 0008; pushes to the editor's slice).
- [x] **Topic 9 — CLI entry point & installation.** **[DECIDED 2026-05-03]** Closed by [ADR 0007](adrs/0007-bootstrap-prereqs-cli-entry.md). Console-script entry in `pyproject.toml` (`ergodix = "ergodix.cli:main"`); registered by `pip install -e .` during bootstrap; works on PATH whenever the venv is active. No shell wrappers.
- [x] **Topic 10 — Migration plan from current `install_dependencies.sh`.** **[DECIDED 2026-05-03]** Closed by [ADR 0007](adrs/0007-bootstrap-prereqs-cli-entry.md). Rename to `bootstrap.sh` + add `bootstrap.ps1`; extract every operation into `ergodix/prereqs/check_*.py`; move `auth.py` and `version.py` into the `ergodix/` package. Bootstrap is ~5 lines (Python install + venv + `pip install -e .` + `ergodix cantilever`).

#### How this story closes

Spike closes when Topics 1–10 are all `[DECIDED]` with their resolutions inlined or linked to follow-up implementation stories (which may be created during the spike). At that point, Story 0.2's implementation tasks (`ergodix migrate`, `ergodix render`) and Story 0.3's editor workflow can proceed against a coherent design.

### Story 0.9 - macOS Keychain integration testing + credential-store abstraction **[NEXT after 0.10 if real]**

So that we know whether macOS Keychain access from a non-codesigned Python interpreter actually behaves the way Story 0.5 assumed (first-read prompt, "Always Allow" makes subsequent reads silent), and so the credential-store layer is compartmentalized enough to swap if Keychain proves friction-y,

Value: Story 0.5's claim is currently untested. If macOS re-prompts on every Python interpreter restart (plausible for non-codesigned binaries), the daily UX breaks. Discovering that during real use is much worse than discovering it during integration testing now,

Risk: Keychain prompts behaving badly forces a rapid swap to a different credential store; if `auth.py` is tightly coupled to `keyring.set_password`/`get_password` calls scattered through code, the swap is painful,

Assumptions: integration tests can simulate or capture real Keychain interactions; abstracting the credential store behind a small interface is cheap; alternative stores (encrypted file, 1Password CLI, etc.) are pluggable behind the same interface,

Tasks:
- [ ] Write integration test that drives `auth.py set-key`, then opens a fresh Python interpreter and reads it back. Repeat across interpreter restarts. Document actual behavior observed.
- [ ] If Keychain re-prompts: extract a `CredentialStore` interface in `auth.py` with concrete `KeyringStore` and at least a stub `EncryptedFileStore` implementation. Make the active store selection a setting.
- [ ] If Keychain behaves: keep current shape; document the test result in the credential-store comment block in `auth.py`.
- [ ] Either way: ensure all credential reads/writes in the codebase go through a single abstraction (currently `auth.py`'s helpers); no direct `keyring.*` calls from anywhere else.

### Story 0.11 - Installer redesign per ADR 0010 **[DONE 2026-05-09 — 24/24 prereqs registered]**

**Closed 2026-05-09 with PR #58 (C2 verify-only stub).** All 24 prereq ops from ADR 0003 (A1–A7, B1–B2, C1–C6, D1–D6, E1–E2, F1–F2) have homes in the codebase. Cantilever's five phases per ADR 0012 (inspect → plan + consent → apply → configure → verify) are functionally complete. Some prereqs are verify-only stubs that defer their full install flow to follow-on stories — see "Implementation status by op" below.

So that running cantilever feels like one decision (a single Y/n on a clearly-laid-out plan) rather than a forest of mid-stream prompts; so that the system is inspected before anything is mutated; so that admin escalation happens once at the right moment; and so that a final verification step proves the install actually works,

Value: today's installer (`install_dependencies.sh`) was test-run on 2026-05-05 and surfaced concrete gaps (no `pip install -e .`, Python version not enforced, stale `auth.py` reference in final message, LTeX silent failure, no verification step, mid-stream prompts). All evidence is in [Spike 0008](spikes/0008-installer-redesign-preflight-consent.md). Fixing them piecemeal would be cheaper short-term but would not fix the underlying UX (charge-through-with-prompts) or the contract conflation in `check() -> CheckResult` from ADR 0007.

Risk: implementation touches every prereq module that exists or is planned (25 from ADR 0003); the `inspect()` / `apply()` split is mechanical but voluminous; if we get the verify-phase contract wrong we'll catch install regressions late.

Assumptions: the four-phase model (inspect → plan + consent → apply → verify) from [ADR 0010](adrs/0010-installer-preflight-consent-gate.md) is workable; the `--ci` floater can faithfully bypass consent using `settings/floaters/ci.toml` defaults; the user is OK with re-running cantilever from the top after a failed apply (no resumability in v1).

**Why elevated above remaining Story 0.10 work:** the prereq-module contract changes from `check() -> CheckResult` (ADR 0007) to separate `inspect()` and `apply()` (ADR 0010). Test stubs written against the old contract would have to be rewritten. Doing Story 0.11 first means Story 0.10's remaining stub work targets the correct contract.

Tasks:
- [x] Rewrite `install_dependencies.sh` to a minimal `bootstrap.sh` that does only: detect Python ≥3.11, create `.venv` with it, `pip install -e ".[dev]"`, run `ergodix cantilever`. Per ADR 0007. **[DONE 2026-05-06]** `bootstrap.ps1` deferred to a follow-up step.
- [ ] Define `InspectResult` and `ApplyResult` dataclasses in `ergodix/prereqs/types.py` per ADR 0010.
- [x] Implement `ergodix/cantilever.py` with the four-phase orchestrator: inspect → plan + consent → apply (with grouped sudo) → verify. **[DONE 2026-05-06]**
- [x] Implement the verify-phase smoke checks: import package, `ergodix --version` (interpreter-dir-derived path), `local_config.py` sanity (mode 600 + non-empty CORPUS_FOLDER). pytest verify check is conditional on `--developer` floater and lands when that floater's adds_operations are wired. **[DONE 2026-05-06]**
- [x] **Inspect-failed first-class outcome** (Copilot review 2026-05-05 finding #2) — failed inspects no longer disappear into no-changes-needed or get rewritten to deferred-offline. **[DONE 2026-05-06]**
- [x] **op_id uniqueness validation** at run_cantilever entry (Copilot finding #3) — duplicate op_ids raise ValueError before any work happens. **[DONE 2026-05-06]**
- [x] **Verify runs on no-changes-needed path** (Copilot finding #5) — catches false greens from a too-permissive inspect. **[DONE 2026-05-06]**
- [ ] For each of the 25 cantilever operations from ADR 0003, write the corresponding `ergodix/prereqs/check_<op>.py` with split `inspect()` / `apply()` functions. Tests come first per CLAUDE.md TDD norm. **Progress: A1 (platform) + C4 (local_config bootstrap) + C5 (credential-store dir) + C3 (git config — first interactive prereq) + C1 (gh auth login) landed; F1 reframed as orchestrator code per ADR 0012 (real connectivity probe in `ergodix/connectivity.py`, settings loader in `ergodix/settings.py`); 19 remaining as of 2026-05-07.**
- [ ] Address every gap from Spike 0008's intel:
  - [ ] `pip install -e .` is an explicit phase-3 step
  - [ ] Python ≥3.11 enforced in inspect; plan adds Homebrew python@3.13 install if missing
  - [ ] Final next-steps message uses `ergodix` console-script commands only (no stale `python auth.py` reference)
  - [ ] Phase 4 verification is required, fails loud
  - [ ] VS Code extension install failures surface the underlying `code --install-extension` exit code + stderr
  - [ ] All choices (MacTeX option, Drive launch) move into the phase 2 plan, not mid-execute
  - [ ] `HOMEBREW_NO_AUTO_UPDATE=1` set for cantilever's brew calls
  - [ ] Final next-steps message generated from the run record, not hardcoded
- [x] Re-run cantilever in `~/Documents/Scorellient/Applications/ErgodixDocs/` to validate. Should produce a working install with `ergodix` on PATH and `pytest` passing — without manual intervention. **[DONE 2026-05-07]** — three self-smokes after C4 / consent fix / C5 commits, all green; placeholder `<YOUR-CORPUS-FOLDER>` correctly substitutes for the original "Tapestry of the Mind" hardcode.
- [x] Update CHANGELOG `[Unreleased]` with the contract change and refer to ADR 0010. **[DONE 2026-05-07]** — running entries kept in sync per commit.

#### Story 0.11 phase 2 — implementation plan (2026-05-07, from `Plan` subagent)

**Recommended next 3 (in order):**

1. **C1 — `gh auth login`** — highest value to the Installer persona: clone (C2) and editor signing (D6) both block on it. Idempotency cheap (`gh auth status` exit code). Network-only, no admin. The interactive `gh auth login` itself is a subprocess hand-off, not a mid-flow prompt — fits the apply contract cleanly.
2. **C2 — clone corpus repo** — direct successor to C1; together they unblock the entire C-tier. Trivial idempotency (`.git` dir present). Pure subprocess + path check, no admin. Ships momentum.
3. **A2 — install / verify Homebrew** — gateway dependency for A3, A4, A7, B1. Well-known idempotent check (`brew --version`). First Tier-2 op; landing it proves the network/admin pattern that the next four installers will copy.

Rationale: C1+C2 are short and high-leverage and unblock the most downstream ops. A2 then opens the entire A-tier without yet committing to MacTeX (the gnarliest install).

**Complexity tiers (22 remaining ops):**

- **Tier 1 — trivial / cookie-cutter (C4/C5 shape):** C2, C3, D1, D2, D4, F2.
- **Tier 2 — network / package-install:** A2, A3, A4, A5, A6, A7, B1, D3.
- **Tier 3 — interactive / cross-cutting:** C1, C6, D6, C3.
- **Tier 4 — persona-gated / orchestration:** D5, B2, E1, E2, F1.

**Key dependencies:**

- A2 → A3, A4, A7, B1 (brew is the installer)
- A5 → A6 (venv before pip)
- C1 → C2, D6 (auth before clone, before pushing signing key to GitHub)
- C5 → C6 (dir before secrets file)
- C4 → B2 (B2 patches the generated `local_config.py`)

**Design decisions to resolve before phase-2 implementation:**

- **C3 (git config interactive)** — does `apply()` prompt mid-flow for name/email, or surface `git config --global ...` as `proposed_action` for the user to run manually? ADR 0010 consent gate suggests the latter.
- **C6 (credential prompts)** — same question scaled: looping `getpass` prompts inside `apply()` violates the "consent gate already happened" model. Likely needs a sub-contract or moves to a post-apply interactive phase.
- **A4 (MacTeX vs BasicTeX)** — which does default Installer get? 4GB vs 100MB. Settings flag in `bootstrap.toml`?
- **D6 (editor signing key)** — needs `gh api` write scope; does C1's auth flow request it, or does D6 re-auth?
- **F1** — is this a prereq module at all, or orchestrator code in `cantilever.py`? ADR 0010 frames inspect/apply as per-op; F1 is meta.
- **`needs_admin` escalation semantics** — `ApplyResult` has no admin-escalation field. How does A4/B1 surface a sudo prompt mid-apply?

These should be addressed in a short spike or ADR before phase-2 work begins, NOT discovered ad-hoc per prereq.

### Story 0.10 - Test-driven development scaffolding **[IN FLIGHT — branch `feature/test-scaffolding`; PAUSED until Story 0.11 lands]**

**Progress as of 2026-05-03 end of session:**

Done:
- [x] `pyproject.toml` created with dynamic version (reads `VERSION`), Python >=3.11, console-script entry `ergodix = "ergodix.cli:main"`, dev deps (pytest, pytest-cov, ruff, mypy per ADR 0008), pytest config (`--strict-markers`, coverage), ruff lint+format config, mypy strict.
- [x] `ergodix/` package skeleton with `__init__.py`. `auth.py` and `version.py` moved into the package from repo root.
- [x] `tests/` directory with `conftest.py` providing `fake_home`, `clean_env`, `fake_keyring` fixtures.
- [x] `tests/test_version.py` — 6 tests covering version string, VERSION-file matching, fallback, importability, no side effects, PEP 440 (skipped until 1.0).
- [x] `tests/test_auth.py` — 16 tests covering all three credential tiers, permission-mode invariant, missing-credential error, keyring error narrowing per ADR 0008, CLI smoke, migration-to-keyring.
- [x] **Bug found and fixed during TDD red phase**: `auth.py` was resolving `Path.home()` at import time, baking the path into module constants. Tests that monkeypatched HOME got stale values. Fixed via `_LazyPath` descriptor that evaluates `Path.home()` on every attribute access.
- [x] `.gitignore` extended for `*.egg-info`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `htmlcov`.
- [x] `.venv` recreated with Python 3.13.12 (system Python 3.9.6 was too old for `>=3.11` requirement).
- [x] **Test result: 22 passed, 1 skipped.**

Remaining (next session):
- [ ] Stub failing tests for every planned module — one `test_<module>.py` per planned source module:
  - [ ] `test_cli.py` (Click root group + subcommand routing per ADR 0001)
  - [ ] `test_cantilever.py` (orchestrator, idempotency, abort-fast, auto-fix bound per ADR 0003 + ADR 0008)
  - [ ] 22 × `test_prereqs_<op>.py` (each tests the `check() -> CheckResult` contract per ADR 0007)
  - [ ] 8 × `test_floaters_<name>.py` (writer / editor / developer / publisher / focus_reader / dry_run / verbose / ci per ADR 0005)
  - [ ] 2 × `test_importers_<name>.py` (gdocs + scrivener)
  - [ ] `test_publish.py` + `test_ingest.py` (ADR 0006 abort cases: signed-commit verification, unauthorized-file rejection, path-rename rejection, three-way merge)
  - [ ] `test_connectivity.py`, `test_runrecord.py`
- [x] **ADR 0009 (CI workflow + dependency-pin policy) [DECIDED 2026-05-04]**: two-job CI design (locked = gating, latest = informational tripwire), `uv` lockfile, multi-platform 3 OS × 3 Python matrix on public repo (free), hard-floor coverage ratchet, `~=` caps on fast-moving APIs only. See [Spike 0007](spikes/0007-ci-and-dependency-policy.md) and [ADR 0009](adrs/0009-ci-and-dependency-policy.md).
- [ ] CI workflow file under `.github/workflows/ci.yml` per ADR 0009 (locked job matrix + latest tripwire job).
- [ ] `uv.lock` generated and committed; `pyproject.toml` updated with `~=` caps on `anthropic` and `google-api-python-client`.
- [ ] Confirm all new tests are RED (failing for the right reasons) before any implementation begins
- [ ] Coverage gate flipped on once green-phase implementation begins


So that every function we're about to write has a failing test waiting for it before we implement it,

Value: red-green-refactor cycle keeps implementation honest; tests document the contract before code drifts; coverage is built up from day one rather than bolted on later; cantilever's prereq modules in particular benefit because each one is small and individually testable,

Risk: writing too many tests up front against speculative APIs that change during implementation; the tests themselves becoming a maintenance burden if not run continuously,

Assumptions: pytest + pytest-cov are the framework choice (per Story 0.5 + ADR 0007's dev deps); test layout follows pytest conventions (`tests/` at repo root, `test_<module>.py` per source module); contracts are stable enough from ADRs 0001–0007 that tests can be written against them,

Tasks:
- [ ] Create `tests/` directory at repo root with `conftest.py` for shared fixtures (tmp_path, fake home dir, mocked keyring backend, etc.)
- [ ] Add pytest config to `pyproject.toml` (test paths, markers, coverage thresholds)
- [ ] Write failing test stubs for each existing module:
  - [ ] `tests/test_version.py` — version reads VERSION file; falls back to `0.0.0+unknown`
  - [ ] `tests/test_auth.py` — three-tier credential lookup; permission-mode invariant; CLI subcommands; keyring error handling
- [ ] Write failing test stubs for each planned `prereqs/check_*.py` (per ADR 0003's 25-op menu + ADR 0007's layout)
- [ ] Write failing test stubs for each planned `floaters/<name>.py` registry entry (per ADR 0005)
- [ ] Write failing test stubs for each planned `importers/<name>.py` (per ADR 0001 — gdocs + scrivener for v1)
- [ ] Write failing test stubs for `ergodix.cli` Click command groups
- [ ] Write failing test stubs for `ergodix.cantilever` orchestrator
- [ ] Write failing test stubs for `ergodix.publish` and `ergodix.ingest` (per ADR 0006 — including the abort-cases the ADR enumerates)
- [ ] Set up CI to run `pytest --cov` on every push (GitHub Actions; gate via developer floater)
- [ ] Confirm all tests are RED (failing for the right reasons) before any implementation begins

After this story closes, every subsequent implementation commit has a measurable "made N tests pass" outcome.

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

- **Story 0.7 — Distribution prep** (deferred until Sprint 1+): make install accessible to non-technical users who don't know git or terminals. Candidates: PyPI publish (`pip install ergodix`), Homebrew formula (`brew install ergodix`), Mac App Store / signed `.pkg` installer, Windows MSI / Microsoft Store, curl|bash stub at a stable URL, GUI installer wrapping the bootstrap scripts. Decide *after* the tool is working end-to-end and a real "completely ignorant" user is identified to validate against.
- **AI commenting on chapter docs** (deferred indefinitely): if the AI ever wants to write CriticMarkup directly into chapter `.md` files (rather than just emitting a flag report), revisit the AI-prose boundary policy. Currently the AI writes only into `_AI/` files, never into chapter prose.

### Spike — CriticMarkup dual-mode review (deferred — not blocking v1)

So that the author has a coherent UX for reviewing two parallel review surfaces — diff-level prose changes (per ADR 0006) and CriticMarkup `{>> <<}` annotations *inside* the changed prose — without confusion about precedence, render output, or "is this a comment about the old text or the new text?",

Value: prevents the editor's annotations from being lost or mis-applied during diff review; clarifies the rendered-output shape when a chapter has both an editor's prose edit AND an editor's comment about something else in the same paragraph,

Risk: not addressing this means the author has to mentally context-switch every review session; ad-hoc workflow forms before the spike can settle the convention,

Tasks (when activated):
- [ ] document the two surfaces and their interaction patterns
- [ ] decide rendering precedence in `--track-changes=all` mode when both diff and CriticMarkup are present
- [ ] decide whether `ergodix ingest` should auto-extract CriticMarkup `{>> <<}` blocks into review-comment metadata vs. leave them in-prose
- [ ] update [docs/comments-explained.md](docs/comments-explained.md) with the resolved convention

### Story — Continuity-Engine: AI-assisted story-logic analysis suite (Sprint 1+ when activated)

As a writer, so that the author can ask focused, named questions about whether the *story* holds together (not whether the *prose* is good — that's Plot-Planner's job) — Does this timeline make sense? Where did this character disappear from chapter 4? What promise did chapter 1 make that I haven't paid off? — and get grounded, evidence-backed answers from an AI that has read the whole corpus, without that AI ever writing a word of prose,

Value: this is the project's stated raison d'être ("AI as architectural co-author and continuity engine"); concretely-named tools turn vague "the AI helps you" into "I just ran timeline-continuity-analyzer on Compendium 2 and it flagged three conflicting season references"; respects the AI-prose boundary (every tool *flags* and *cites*, never edits); the named-tool surface makes the value teachable to other authors during distribution,

Risk: scope explosion — there are infinite "story-logic checks" you could imagine; the methodology behind each tool needs to be defensible (an AI saying "this is a plot hole" without grounded evidence is worse than no tool); cross-chapter context windows are expensive without smart retrieval; tool overlap with Plot-Planner needs clear boundaries (Plot-Planner = *prose mechanics*; Continuity-Engine = *story logic*); some tools depend on hierarchy decisions still in flux (multi-opus, sliced-repo collaboration),

Assumptions: per-chapter analysis with cross-chapter retrieval is tractable using the prompt-caching strategy from Story 0.Z2; tools are best invoked via Claude Code's skill / slash-command surface (`.claude/skills/<name>/`) so they live close to the corpus repo, with `ergodix` subcommand mirrors for CI / scripting; an umbrella `continuity-engine` namespace separates these from `plot-planner` (craft) and from `sell-my-book` (marketing); evidence-citation is non-negotiable — every flag must point at the chapter / line that triggered it,

Tools known so far (per the author's framing — list grows when activated):

- **`timeline-continuity-analyzer`** — extracts every temporal anchor (dates, seasons, "three weeks later", character ages) and flags conflicts across the corpus.
- **`plot-hole-finder`** — surfaces internal logical contradictions (character knows X in ch.3 but acts surprised by X in ch.7; an event is described as "unprecedented" when ch.2 shows precedent).
- **`character-arc-tracker`** — extracts each character's appearances + decisions + emotional state; flags inconsistencies, abrupt shifts without setup, and disappearances.
- **`worldbuilding-consistency-checker`** — checks magic-system rules, geography, technology level, currency, languages — every named worldbuilding fact tracked across chapters.
- **`foreshadowing-tracker`** — pairs planted seeds (chekov's guns) with their payoffs; flags unresolved seeds and unsetup payoffs.
- **`promise-and-payoff-tracker`** — chapter-level: what did this chapter promise the reader, was it paid off later, by whom, and how cleanly?
- **`POV-leak-detector`** — tags POV per scene; flags information leaks (third-person-limited POV reveals knowledge the POV character couldn't have).
- **`name-disambiguator`** — flags same-named or near-same-named characters / places / objects that may confuse readers.
- **`relationship-graph-walker`** — who knows what about whom? Who has met whom? Tracks secrets, disclosures, alliances, betrayals, and surfaces "this character shouldn't know that yet" violations.
- **`death-and-resurrection-ledger`** — who died, who came back, intentional or continuity error?
- **`question-the-corpus`** — open-ended Q&A: "Why does Aria distrust the council?" — AI grounds the answer in citations; the answer is a *summary of evidence*, never a creative interpretation that wasn't in the prose.
- **+ more** when the story activates.

Tasks (when activated):

- [ ] Decide implementation surface: Claude Code skills (`.claude/skills/<name>/`) vs `ergodix` subcommands vs both. Likely both — slash-commands for in-editor use, `ergodix` subcommand mirrors for CI/scripting/headless.
- [ ] Lock the namespace: `continuity-engine` (working name) — distinguishes from `plot-planner` (craft) and `sell-my-book` (marketing). Could collapse if architecturally cleaner.
- [ ] Settle on per-chapter analysis index + cross-chapter retrieval pattern — cross-references Story 0.Z2; prompt-caching strategy is load-bearing.
- [ ] **Evidence-citation contract**: every flag points at chapter / paragraph / line. Non-negotiable. No "trust me, AI says so."
- [ ] Build the first three tools (`timeline-continuity-analyzer`, `plot-hole-finder`, `character-arc-tracker`) end-to-end — establish the cookie-cutter pattern, then enumerate the rest.
- [ ] AI-prose boundary enforcement: every tool emits flags / citations / artifacts in `_AI/` subfolders, *never* mutates chapter prose. The MCP server (parking-lot) inherits this constraint.
- [ ] Documentation page mapping each tool's question / inputs / outputs / methodology. The methodology is the moat — vague "I asked the AI" beats nothing, but a defensible methodology is what makes Continuity-Engine valuable.

This story partially supersedes / consolidates Sprint 1 stories 1.1 (plotline tracking), 1.2 (plot-hole detection), and 1.5 (worldbuilding support) — those are conceptually subsumed under specific Continuity-Engine tools. Decide at activation time whether to retire Sprint 1.1/1.2/1.5 or keep them as sub-stories.

### Story — Plot-Planner: AI-assisted authoring-analysis tool suite (Sprint 2+ when activated)

As a writer, so that the author has a cadre of focused, narrow-purpose AI tools that surface specific craft issues across a chapter or the whole corpus — pacing, originality, repetition, tone — without conflating them into one monolithic "review" that's hard to act on,

Value: each tool answers a single, named question and produces a focused report; the author iterates against one craft dimension at a time rather than drowning in a generic "make this better" pass; "hook to get authors using this tool" — a memorable, action-named tool surface (writing-score, copyright-quest, duplicate-smasher, PC-placator) is the thing that builds adoption habits; respects the AI-prose boundary because every tool *flags* / *scores*, never edits prose,

Risk: scope creep — 20+ tools is a lot of surface to design, document, and maintain; without a strong umbrella concept the suite fragments; tool overlap (e.g. duplicate-smasher vs. writing-score's repetition signal) creates user confusion; tool quality drops if each tool is a thin LLM wrapper without a real scoring methodology behind it,

Assumptions: the author has a defined scoring methodology (Fibonacci peaks, dynamics, show-vs-tell, etc.) that can be encoded; per-chapter analysis with cross-chapter context is tractable using the prompt-caching strategy from Story 0.Z2; tools are best invoked via Claude Code's skill/slash-command surface (`.claude/skills/` or `.claude/commands/`) so they live close to the corpus repo, with the option of also surfacing them as `ergodix` subcommands; an umbrella "plot-planner" name is the right grouping primitive,

Tools known so far (more TBD):

- **`writing-score`** — scores a chapter (or the whole corpus) using the author's methodology; flags pacing, dynamics, show-vs-tell, Fibonacci peaks, weak verbs, dialogue-vs-narration ratio, etc.
- **`copyright-quest`** — searches across known works (corpus + author's prior drafts + a curated public-domain index?) to flag accidental copy/paste, residual placeholder text, or inadvertent close-paraphrase that could read as infringement.
- **`duplicate-smasher`** — finds repeated patterns: copy-paste duplicates, excessive same-word/same-phrase clusters, structural repetition across chapters.
- **`PC-placator`** — detects the full tone spectrum, from hate-speech / triggering / incendiary / rage-baiting at one end through edgy / raw / extreme, past kind / saccharine / boring / explainery, to raunchy / sensual / heart-pounding-action / page-turning / re-read-inducing at the other. Reports where each chapter sits and where the author may want to push or pull.
- **+ ~16 more** to be enumerated when the story activates.

Tasks (when activated):

- [ ] Decide implementation surface: Claude Code skills/commands (`.claude/skills/<name>/`) vs. `ergodix` subcommands vs. both. Likely both — slash-commands for in-editor use, `ergodix` subcommand mirrors for CI/scripts.
- [ ] Name the umbrella concept (`plot-planner` is the working name; could be `authoring-suite`, `craft-tools`, etc.).
- [ ] **Dependency: [Wordsmith Toolbox story](#story--wordsmith-toolbox-foundational-rhetoric-reference-skill-sprint-2-when-activated).** `writing-score`, `PC-placator`, and most stylistic-feedback tools reference rhetoric primitives by id; the Wordsmith Toolbox Skill provides the canonical reference. Sequence: ship Wordsmith Toolbox before (or alongside) the first stylistic-feedback tool.
- [ ] **Dependency: [Spike 0010 — UserWritingPreferencesInterview](../spikes/0010-user-writing-preferences-interview.md).** Tool output is shaped by author preferences (scoring weights, anti-patterns, AI-boundary refinements) — the interview captures these once and tools reference them every run.
- [ ] Encode the author's scoring methodology in a stable, testable form (probably a TOML/YAML rubric).
- [ ] Settle on per-chapter analysis index + cross-chapter retrieval pattern — cross-references Story 0.Z2.
- [ ] Build the first three tools (`writing-score`, `duplicate-smasher`, `PC-placator`) end-to-end — establish the cookie-cutter pattern, then enumerate the remaining ~16.
- [ ] Decide adoption hook: which tool is the "first one a new author tries" that demonstrates value in <5 minutes?
- [ ] Documentation page mapping each tool's question / inputs / outputs / scoring methodology.

### Story — Sell-My-Book: book-marketing assistance suite (way later, after the corpus is finished)

As a publisher (and as the author wearing the publisher floater), so that there is a tool surface for the post-writing phase — turning a finished corpus into something readers actually find and buy — without bolting marketing concerns onto the authoring tools,

Value: the tool's value continues past "draft is done" into the part of writing that most authors find hardest (selling); creates a complete pipeline from blank page to launched book; tools live in their own namespace so they don't pollute the writing workflow,

Risk: huge surface (audience research, blurb generation, cover design feedback, price-point analysis, launch-platform comparison, ad copy, review-funnel design, social media seeding, etc.); easy to wander into commodity ad-tech territory; ethical concerns about AI-generated promotional content need their own handling; doing this *before* the author's own book launch validates the approach risks building features that don't survive contact with real publication realities,

Assumptions: the author's own book ships first and surfaces concrete needs; lessons from that launch flow back into the tooling rather than the tooling being designed in the abstract; a clean separation between authoring tools (Plot-Planner) and marketing tools (Sell-My-Book) is maintained; some tools may share infrastructure with Plot-Planner (corpus indexing, character extraction) without sharing tool surface,

Tasks (when activated — *after the author's own book has shipped*):

- [ ] Run the author's own launch and harvest "what tools would have made this 10x easier" intel.
- [ ] Decide the Sell-My-Book tool surface (likely separate slash-command/skill namespace from Plot-Planner).
- [ ] Enumerate concrete tools based on the launch retrospective.
- [ ] Address ethical guardrails on AI-generated marketing content (transparency, disclosure norms).
- [ ] Decide whether Sell-My-Book ships with Plot-Planner or as a separate phase / package.

### Story — IP strategy: trademark "ErgodixDocs" + patent decision (talk to attorney)

As a publisher, so that the name, brand, and any patentable architecture decisions are protected before commercial launch — without over-spending on IP before the product has a real audience,

Value: trademarks protect the user-facing brand cheaply and durably; patents protect novel architecture but cost real money and have hard deadlines that started ticking when the repo went public; doing both right before commercialization is the difference between a defensible launch and a launch that gets copied by someone with a bigger budget,

Risk: NOT consulting a real IP attorney is the biggest risk — software patent strategy in particular is non-DIY territory; the US 12-month grace period on first public disclosure (started ~2026-05-02 when this repo was first made public) caps when you can still file a US utility application that claims novelty; most non-US jurisdictions require absolute novelty so the public-disclosure window has likely already foreclosed those countries; spending $5K–$25K on a patent that gets rejected for prior art (decades of installer / configuration tools — Chef, Puppet, Ansible, Nix, Homebrew formulae, MacPorts, dpkg, etc. — set a high prior-art bar for "multi-phase orchestrator with consent gate") is real money wasted,

Assumptions: the author has the financial position to pursue real IP protection; an IP attorney is the right next step; trademark protection is high-value-low-cost (good ROI) regardless of whether patents make sense; the architecture-level concepts (cantilever orchestrator, configure phase, preamble cascade) are novel-feeling but face real prior-art questions that a search would surface,

Tasks (when activated — talk to an IP attorney first):

- [ ] **Trademark "ErgodixDocs"** (and potentially "Ergodix" and any related marks) at USPTO via TEAS — ~$350 filing fee + attorney costs; protects the brand which is what users actually associate with the product. High value, low cost, fast.
- [ ] **Provisional patent application** if patenting is pursued — ~$65 USPTO fee + ~$1.5K attorney for drafting. Locks in priority for 12 months while deciding whether to commit to a full non-provisional application. **Hard deadline: ~2027-05-02 to file in the US** (12-month grace period from first public disclosure ~2026-05-02; outside US is likely already too late).
- [ ] **Prior-art search** before any non-provisional commitment — patent attorney runs this. Architecture-level patents face decades of installer / configuration / build-tool prior art. Likely candidates: cantilever's 5-phase orchestrator + needs-interactive configure phase; ergodic-typesetting preamble cascade; AI-prose-boundary enforcement model.
- [ ] **Non-provisional patent application** if the prior-art search clears it and the business case justifies $5K–$25K + 18–36 months of prosecution. Otherwise drop the patent path.
- [ ] **Domain name protection** — register `ergodix.com` / `ergodix.app` / `ergodixdocs.com` / etc. before someone else does (cheap, ~$15/yr each).
- [ ] **Copyright** — already automatic on every commit; nothing to file. The PolyForm Strict license already establishes copyright posture.

**Key dates:**
- ~2026-05-02 — first public disclosure (repo went public). US patent grace period clock started.
- ~2027-05-02 — US patent application deadline if pursuing the grace-period filing.

**Key counsel question:** "Given decades of installer / configuration-management prior art, is there a defensible novel claim worth filing on the multi-phase orchestrator + configure-phase pattern, or should we focus on trademark + brand + the actual product instead?"

### Story — Licensing + monetization framework (way later — pre-distribution)

As a publisher (and the author wearing the publisher floater), so that ErgodixDocs can be sold as a commercial product when it ships out of the ~1-year solo-dev window — license-key validation, expiry handling, "trial / expired" UX, payment integration, and distribution channels (DMG, App Store, brew tap, web download) need a coherent design before anyone pays for it,

Value: a defensible monetization path that survives common piracy patterns, integrates with whatever payment platform we pick, and degrades gracefully when payment lapses (read-only? grace period? hard block?); also blocks the obvious "anyone can run it for free forever" failure mode that would foreclose the publisher persona's reason to exist,

Risk: getting this wrong creates support load, alienates legitimate users, or leaves obvious workarounds; over-engineering it before any users exist is also waste; license-validation that phones home creates a privacy story that needs to match the rest of the project's "local and frugal" stance,

Assumptions: ~1 year of pre-commercial dev gives time to learn how the tool is actually used; the licensing layer will be a separate concern from cantilever (a wrapper / decorator pattern rather than a hard cantilever dep); the eventual distribution mode (DMG, App Store, web download, brew tap, etc.) shapes how the license-check integrates,

Tasks (when activated):
- [ ] Choose license-validation model — server-validated keys vs offline-signed certs vs hybrid; decide phone-home cadence (session-start? daily? never?)
- [ ] Decide grace-period / hard-cutoff behavior on expiry (read-only mode? N-day grace? feature-gating?)
- [ ] Pick payment platform (Stripe, App Store, Paddle, Lemon Squeezy, etc.) and wire it
- [ ] Decide trial mechanics (free for X days, free with N chapters, free forever for personal non-commercial, etc.)
- [ ] Build the licensing layer as an opt-in wrapper around the CLI — not a hard dep that breaks the existing dev workflow
- [ ] Distribution: DMG signing + notarization (macOS), App Store packaging, brew tap, possibly Microsoft Store + apt repo
- [ ] Privacy: no telemetry beyond license-validation pings; document clearly; respect the "local and frugal" posture from README
- [ ] Decide whether existing open-source-licensed bits (any third-party deps) constrain commercial distribution; license-compatibility audit

### Story — Skill factory-seal protection (Sprint 2+ when activated; activates with first proprietary Skill)

As a publisher (and the author wearing the publisher floater), so that the proprietary Skills that constitute the project's actual moat — the author's scoring methodology, the Wordsmith Toolbox rhetoric reference, the Plot-Planner tool suite, future Continuity-Engine analyzers — cannot be silently modified, forked, or ratioed-into-meaninglessness by a downstream user; if a user wants to change a Skill, they file a comment / PR on the upstream repo and we decide whether to accept it,

Value: protects the IP that distinguishes ErgodixDocs from "Claude with a markdown folder"; ensures the Skills a user runs are the Skills the project author signed off on (no silent local modification that produces *worse* output the author then attributes to ErgodixDocs); creates a clean upstream-feedback channel (repo comments) that improves Skills over time without fragmenting them; pairs naturally with the [Licensing + monetization framework](#story--licensing--monetization-framework-way-later--pre-distribution) story since both want signed certs and a phone-home channel — share the infrastructure,

Risk: signing infrastructure is real engineering (key generation, secure storage of the signing key, signature verification at runtime, key rotation, revocation) and easy to get subtly wrong; "tampered Skill refuses to load" UX must be excellent or legitimate users will be locked out by file-mode glitches; monthly key rotation creates a hard online-once-a-month dependency that conflicts with the indy-mode design — needs a graceful-degrade story; a determined attacker can always strip signatures and run modified code (the seal is a *trust signal*, not a DRM shield) — the value is "honest users can verify they're running unmodified Skills," not "no one can modify Skills,"

Assumptions: Skills live at `.claude/skills/<name>/` (per [Plot-Planner](#story--plot-planner-ai-assisted-authoring-analysis-tool-suite-sprint-2-when-activated) story); Ed25519 or RSA-PSS signatures are sufficient (no need for hardware-token signing in v1); the project author holds the signing key offline; monthly key rotation is achievable (issue a new validity-window certificate; old signatures stay valid until they expire from the trust window); the user accepts a once-monthly online check as part of the "local and frugal" stance because the alternative — perpetual offline trust — undermines revocation,

Mechanism (rough sketch — to be refined when activated):

- Each Skill ships with a `manifest.toml` declaring its permitted-actions category per [ADR 0013](../adrs/0013-ai-permitted-actions-boundary.md) and a detached signature file (`manifest.sig`).
- ErgodixDocs ships with a bundled public key + a *validity-window* certificate (e.g., "this signing key is trusted for the 60 days starting 2026-MM-DD").
- At Skill-load: verify the signature against the pubkey; verify the cert is within its validity window. Both must pass or the Skill refuses to load with a clear error (`Skill <name> failed signature check; the factory seal is broken. To request changes, comment on the upstream repo at <url>`).
- A scheduled check (cantilever follow-on or a small `ergodix refresh-keys` command) fetches the current validity-window cert from a known endpoint when the local cert is within 14 days of expiry. Network required at most once / 30 days.
- Offline grace: cert expired within last 30 days → load with a soft warning. Cert expired > 30 days → refuse to load with clear remediation ("connect to the network and run `ergodix refresh-keys`"). Tunable via the future `settings/defaults.toml` once the settings cascade lands.
- Indy-mode users can still run with cached certs as long as they've refreshed at least once; first-time install requires a network roundtrip to fetch the initial cert.

Tasks (when activated):
- [ ] Cross-reference [the Licensing + monetization framework story](#story--licensing--monetization-framework-way-later--pre-distribution) and consolidate where the infrastructure overlaps (signed certs + phone-home cadence + privacy story).
- [ ] Choose signing algorithm — Ed25519 (fast verify, small signatures, modern) is the default unless there's a good reason to pick RSA-PSS.
- [ ] Build `ergodix refresh-keys` subcommand — fetches the current validity-window cert from a known HTTPS endpoint and writes to `~/.config/ergodix/skill-keys/`.
- [ ] Build the Skill-loader's signature-verification path — runs at every Skill invocation; cached after first verify per process.
- [ ] Decide validity-window cadence (30 days is a starting point; 60 or 90 may be friendlier for long-offline users; shorter than 30 starts to feel hostile).
- [ ] Decide what gets signed: just the manifest (cheap, but doesn't catch code modification), the entire Skill directory tarball (heavier, but real tamper detection), or both layers (defense in depth).
- [ ] Document the change-via-comment workflow: a user wants to modify a Skill → they comment on the upstream repo / file a PR / propose the change; if the project author accepts, the modified Skill is signed and shipped in the next release.
- [ ] Decide the network-required-once-monthly UX — calendar-driven cantilever prereq that runs `refresh-keys` if last-refresh > N days, with a clear warning before any refusal.
- [ ] Document loudly that the seal is a *trust signal*, not anti-piracy: a determined attacker can strip signatures and modify code; the seal protects honest users from drift, not against active subversion.
- [ ] Cross-reference [SECURITY.md](../SECURITY.md) — add a section explaining the threat model for Skill integrity (in-scope: silent local modification by tools/agents; out-of-scope: a determined local attacker with the user's account).

### Story — MCP server + AI-user persona (Sprint 2+ when activated)

As an **AI-user** (a Claude or other LLM instance acting on behalf of a human author), so that an AI assistant can read this repo's documentation (ADRs, spikes, README, CLAUDE.md), understand the tool's architecture, and run ergodix commands on the user's behalf — turning "Claude, render chapter 3" or "Claude, what plotlines are unresolved?" into actual ergodix invocations,

Value: amplifies the "AI as architectural co-author" thesis that drives the project; lets users who don't want a CLI experience still benefit from ergodix; centralizes documentation as the AI's context source rather than scattered prompt engineering; opens a distribution channel where the user's existing AI subscription (Claude, ChatGPT, etc.) drives the experience; introduces a new persona (AI-user) as a proper floater alongside writer / editor / developer / publisher / focus-reader,

Risk: AI-user must NOT cross the AI-prose boundary (per CLAUDE.md and ADR 0006 — the AI never edits chapter prose, never acts as the writer); the tool's existing safeguards need an MCP-layer enforcement so an AI-user can't bypass them via the MCP surface; expanding the floater set introduces another persona that needs careful scoping; MCP itself is a relatively new spec, so betting on it has stability risk; users may expect the AI-user to write chapters and we have to enforce "no" gracefully,

Assumptions: MCP (Model Context Protocol) is a stable enough surface to build against; the existing ADRs / spikes / README provide enough context for an AI to operate ergodix without runtime training; an AI-user is a real persona (per ADR 0011 the story leads with "As an AI-user"); the ethical stance "AI flags, human decides" extends cleanly to "AI invokes the analysis tools, never the prose-mutating ones,"

Tasks (when activated):
- [ ] New ADR locking the AI-user persona + floater + scope (alongside writer/editor/developer/publisher/focus-reader from ADR 0005)
- [ ] Add `--ai-user` floater (or `--mcp` server-mode) to the CLI
- [ ] Build `ergodix-mcp` (or similar) MCP server exposing a curated tool surface to a Claude/AI client — render, status, plotline-tracking, summaries, etc.
- [ ] Lock the AI-user out of any operation that would edit prose chapters (extends ADR 0006's AI-prose boundary; explicit deny list in the MCP surface)
- [ ] Decide whether the MCP server reads the live filesystem or a snapshot — Drive sync + concurrency interactions
- [ ] Documentation surface for the MCP tools (so the AI knows what's available); auto-generate from CLI?
- [ ] User flow for pointing Claude (or other) at the MCP server; auth model for the MCP

### Story — In-app AI editor with BYO-key + Drive sync (way later — after distribution + Plot-Planner)

As a writer using the polished consumer ErgodixDocs app (DMG / App Store), so that the writing experience itself happens *inside* ergodix rather than VS Code — on-the-fly AI assistance the user pays for via their own API key (BYO-AI), with chapter content auto-syncing to Google Drive as plain `.md` files in the background,

Value: lowers the barrier for non-developer authors who don't want VS Code; user-pays-AI keeps the cost model honest (we don't markup AI calls and the user's privacy stance with their AI provider stays their own); plain-`.md`-in-Drive preserves the "tool for any author, no lock-in" principle from ADR 0005 — the user can walk away with their corpus as portable Markdown anytime,

Risk: building a custom editor is a huge surface (rich text + Markdown rendering, syntax highlighting, find/replace, version history, conflict resolution, accessibility); user-pays-AI requires good key management UX (already half-solved by `auth.py`'s three-tier credential lookup but the editor adds new prompts); "background sync" is the same hard concurrency problem as Story 0.Z1; investing in a custom editor before the writer audience exists may be premature; competing against entrenched editors (Scrivener, Ulysses, Obsidian) needs a real differentiator,

Assumptions: users will accept BYO-API-key (anthropic / openai / etc.); Drive's filesystem-mirror remains a reliable sync surface; the editor can ship as an Electron / Tauri / native app once monetization is sorted; the existing CLI surface keeps working in parallel for power users (the editor and CLI are not mutually exclusive — the CLI is the engine, the editor is the front end),

Tasks (when activated — way after the licensing framework + Plot-Planner have shipped):
- [ ] Decide editor framework — Tauri (smaller / faster, Rust+web), Electron (heavier / familiar), web-only (no install but offline-fragile), native macOS (best UX, single-platform)
- [ ] BYO-API-key flow — store via OS keychain (already wired in `auth.py`'s tier-2); UI for entering / rotating / removing keys
- [ ] Markdown editor experience — mode + extensions + preview + render; CriticMarkup-aware comment surface
- [ ] Background Drive sync — leverages existing Mirror infrastructure; debounce; conflict UI (extends Story 0.Z1's solution)
- [ ] On-the-fly AI assistance hooks — which Plot-Planner tools surface inline as the author writes? (writing-score, duplicate-smasher in real-time as a side panel?)
- [ ] Distribution as a separate package from the CLI, OR unified app that bundles both — decide
- [ ] Privacy story for the BYO-key + Drive sync stack documented in the App Store listing
- [ ] Accessibility audit — screen reader support, keyboard navigation, contrast

### Story — Phil-trained custom prose linter (Sprint 1+ when activated)

So that a custom linter trained on the human editor's repeated corrections becomes a first-pass automatic editor — catching the things the editor consistently fixes (specific verb-tense patterns, comma habits, clichés the author falls into) so the human editor can focus on higher-level work,

Value: amortizes the editor's expertise into reusable tooling; reduces the editor's repetitive workload; demonstrates the AI-as-architectural-analyst principle in a concrete way that respects the AI-prose boundary (the linter *flags*; the human *decides*),

Risk: linter false-positives become noise that the author learns to ignore, defeating the purpose; over-fitting to one editor's idiosyncrasies may reduce portability when adding a second editor,

Assumptions: the editor's review history (post-merge diffs over time) is sufficient training signal; flagging-not-fixing preserves the AI-prose boundary; per-editor and per-author training is feasible at the corpus scale,

Tasks (when activated):
- [ ] Mine accepted editor patches from `git log` to extract recurring corrections
- [ ] Build a rule-based first pass (regex / token-pattern matching) for high-confidence patterns
- [ ] Layer ML or LLM-driven detection for fuzzier patterns (style consistency, tone drift)
- [ ] Wire as `ergodix lint` subcommand; integrate with `--developer` floater's pre-commit hooks
- [ ] Per-author + per-editor training profiles in `settings/`

### Story — Wordsmith Toolbox: foundational rhetoric reference Skill (Sprint 2+ when activated)

As a writer, so that the AI tools that score and critique prose have a stable, comprehensive reference for rhetorical devices, logical fallacies, persuasion techniques, and narrative structures — instead of each tool re-deriving "what counts as a metaphor" or "what counts as a strawman" from the model's free-floating knowledge — and the author can trust that two tools using the same primitive (e.g. `writing-score` and `PC-placator` both reasoning about *ethos*) reach consistent verdicts,

Value: a structured rhetoric knowledge base is the *moat* under Plot-Planner's tool suite; without it, every tool is a thin LLM wrapper that may classify the same passage differently across runs; with it, tools become deterministic enough to be testable; second-order: enables adversarial-style review tools that intentionally apply hostile rhetorical analysis to expose weaknesses,

Risk: scope explosion (rhetoric is a *huge* field — Aristotelian appeals, classical figures, modern persuasion taxonomies, narrative theory, prosody, etc. — picking a curriculum boundary is hard); reference drift (the canonical taxonomy changes between editions of textbooks; pinning a *version* matters); over-engineering — if no Plot-Planner tool actually consumes the toolbox, it's documentation no one reads,

Assumptions: a single foundational reference is more valuable than per-tool inline definitions; the reference is consulted by tools, not directly by humans (humans get *output* from the tools, not raw rhetoric lookups); a TOML/YAML rubric is rich enough to encode each device (name, definition, exemplars, classifier hints) without prose; the umbrella "Wordsmith Toolbox" name lands the right tone — analytical, slightly adversarial, useful for both critique and stylistic advice,

Tasks (when activated):
- [ ] Decide curriculum scope — what does "rhetoric" cover here? Likely union of: Aristotelian appeals (ethos / pathos / logos / kairos), classical figures (anaphora, chiasmus, polysyndeton, etc.), logical fallacies (formal + informal), persuasion patterns (Cialdini's six + variants), narrative-structural primitives (hero's journey beats, kishōtenketsu, etc.), prosody-adjacent devices (sentence rhythm, paragraph cadence). Probably *not* covered: pure literary theory (deconstruction, reader-response), academic rhetoric (debate-style argumentation).
- [ ] Encode each entry in a stable TOML/YAML schema with id, name, category, definition, exemplars, classifier-hint (a few examples the AI can match against).
- [ ] Land as a Skill at `.claude/skills/wordsmith-toolbox/` with reference data in the skill's data files; tools reference by id.
- [ ] First consumer: `writing-score` references device-ids when flagging strengths/weaknesses ("strong anaphora in §3.2" / "logos appeal undermined by post hoc fallacy in §4.1").
- [ ] Decide version pinning + amendment process — when a new device is added or a definition changes, do existing scored chapters re-score? Probably not; record the version-of-record in `_AI/scoring-runs/<run>.toml`.
- [ ] Cross-reference: [Spike 0010 — UserWritingPreferencesInterview](spikes/0010-user-writing-preferences-interview.md) (author may opt out of certain rhetoric categories — "don't flag classical figures unless explicitly asked").
- [ ] Cross-reference: [Plot-Planner story](#story--plot-planner-ai-assisted-authoring-analysis-tool-suite-sprint-2-when-activated) (Wordsmith Toolbox is a dependency of `writing-score`, `PC-placator`, and any future stylistic-feedback tool).

### Story — `form-analyzer` ergodite: grade-level + rhetorical eloquence + Fibonacci arc (Sprint 2+ when activated)

As a writer (and a teacher in education-mode), so that one ergodite produces a single readout grading a chapter's *form* on three orthogonal axes — readability/grade-level (publicly-defined formulas: Flesch-Kincaid, Gunning Fog, SMOG, Coleman-Liau, ARI, Dale-Chall), rhetorical eloquence (density of detected figures per paragraph, drawing on Wordsmith Toolbox primitives), and Fibonacci/golden-mean structural arc (per the author's Fibonacci writing prompt) — instead of needing to run three separate analyses to diagnose whether the prose is pitched at the right grade level, rich enough rhetorically, and following the author's preferred narrative shape,

Value: this is the first concrete instance of the ergodite plugin contract from [Spike 0013](spikes/0013-style-sentinel-and-certificate.md) — proves the plumbing works end-to-end with a useful output that the writer / editor / publisher floaters can all consume; bundling three sub-checks under one ergodite gives a unified per-chapter readout (one report to read, not three to merge); grade-level analysis directly enables the education-mode target audience match (school deploys with a target band like "middle school - upper" and the ergodite flags drift); the eloquence axis becomes the first concrete consumer of Wordsmith Toolbox rhetoric primitives, validating that abstraction; the Fibonacci axis lets the author check whether their structural intuition matches the prose actually written,

Risk: the Fibonacci sub-check is blocked on capturing the author's prompt artifact in-tree (`docs/fibonacci-writing-prompt.md` — flagged in Spike 0013 cross-references); the eloquence sub-check is fully useful only after Wordsmith Toolbox ships its rhetoric reference (we can ship a minimal inline list for v1 and refactor later); grade-level scope creep (Lexile and ATOS are widely deployed in K-12 but proprietary — pulling those in needs a license + commercial discussion, not in scope for v1); reports without an interview-supplied target band only show "the prose is at grade 9.5" without flagging "off-target" — handles cleanly via null fields,

Assumptions: `textstat` (or equivalent) bundles the public formulas so we don't reimplement; LLM-classified rhetoric is a setting-gated optional (default off for determinism); single ergodite with toggleable sub-checks is the right grain rather than three separate ergodites,

Tasks (when activated):
- [ ] Implement after the ergodite registry from Spike 0013 / ADR-X1 ships — this story instantiates the contract, doesn't define it.
- [ ] Decide `textstat` vs. inline formulas. Lean: pull in `textstat` (small dep, well-tested, public-domain math).
- [ ] Build the grade-level sub-check: portfolio (FK / Flesch-Ease / Gunning Fog / SMOG / Coleman-Liau / ARI / Dale-Chall), consensus grade, band classification, target-band comparison from Spike 0010 interview.
- [ ] Build the rhetorical-eloquence sub-check: 7 v1 figures (anaphora, epistrophe, polysyndeton, asyndeton, tricolon, alliteration, anastrophe) via regex; per-paragraph density; LLM classifier behind setting.
- [ ] Build the Fibonacci sub-check (after `docs/fibonacci-writing-prompt.md` lands): per-paragraph intensity score, target curve, deviation flagging.
- [ ] Pull rhetoric primitives from Wordsmith Toolbox once that ships; until then, inline a minimal definition table inside the form-analyzer module.
- [ ] Cross-reference: [Spike 0014 — form-analyzer ergodite](spikes/0014-form-analyzer-ergodite.md) (design).
- [ ] Cross-reference: [Spike 0013](spikes/0013-style-sentinel-and-certificate.md) (registry contract); [Spike 0010](spikes/0010-user-writing-preferences-interview.md) (target band + Fibonacci preferences); [Wordsmith Toolbox story](#story--wordsmith-toolbox-foundational-rhetoric-reference-skill-sprint-2-when-activated) (rhetoric primitives).

### Story — `ergodix index` + `_AI/ergodix.map`: corpus content index (near-term — after B2)

As the AI continuity engine and any incremental-analysis tool, so that we don't reconsume the entire corpus every session — the map records per-file SHA-256 hashes, sizes, and mtimes so a downstream tool can diff current state against the last-indexed state and only send *changed* chapters to the AI,

Value: massive cost savings on Anthropic API once Plot-Planner / Continuity-Engine tools start running over the corpus — without an index, every continuity-check pass re-tokenizes the whole opus; with an index, only the deltas; second-order: the map becomes the foundation for the future "multidimensional mind map" of plotlines, conversations, character arcs, etc. that lets the AI build incremental knowledge across sessions,

Risk: stale-map handling (user edits a file outside ErgodixDocs, the map doesn't refresh; tools work from outdated assumptions); merge-conflict noise if the map is git-tracked in a shared corpus repo; over-engineering the format too early — better to ship a simple v1 than design for the future N+1 tool,

Assumptions: SHA-256 of file content is sufficient for change-detection (collisions are not a threat model concern); the map is regenerated on demand via a `ergodix index` subcommand and re-runs cheaply; lives at `_AI/ergodix.map` next to the corpus per the existing `_AI/` convention; TOML keeps it human-readable so the user can open and inspect without tooling,

Tasks (when activated):
- [ ] `ergodix index` CLI subcommand — walks `CORPUS_FOLDER`, hashes every `.md` and `_preamble.tex`, writes `_AI/ergodix.map`. Idempotent.
- [ ] Map schema (TOML): `[meta]` block (version, generated_at, generator, corpus_root); `[[files]]` array with path, sha256, size, mtime.
- [ ] `ergodix index --check` mode — reports drift (which files changed since last index) without rewriting.
- [ ] Decide gitignored vs tracked. Likely *tracked* in shared corpus repos so collaborators see the same baseline; conflicts auto-resolve by re-running `ergodix index`.
- [ ] First consumer: future Continuity-Engine tools read the map to decide which chapters to re-scan.
- [ ] Cross-reference: [Continuity-Engine story](#story--continuity-engine-ai-assisted-story-logic-analysis-suite-sprint-1-when-activated) (the map enables incremental continuity passes).

### Story 0.X - Multi-opus support (deferred to Sprint 1+ or first real use case)

**Terminology:** an **opus** is a named bundle of (corpus path + default floater set + last-used context). Plural: **opera**. Term chosen to fit the project's classical/Latin voice without colliding with Compendium (a level in the narrative Hierarchy).

So that one machine and one identity can address multiple opera with different role-sets per opus (you on Tapestry as writer/dev/publisher; you on a friend's manuscript as focus-reader; an editor working two authors' books in parallel),

Value: makes ErgodixDocs viable as the underlying tool when adoption broadens past one author; lets a single user split work across opera without re-installing per project,

Risk: introducing the dimension prematurely costs more than waiting; conflating this with enterprise tenancy concerns that aren't actually adjacent,

Assumptions: forward-compatible architectural pieces already in place (registries, settings folder, three-tier credential lookup); `local_config.py`'s `CORPUS_FOLDER` becoming a dict keyed by opus name is non-breaking,

CLI shape (locked at story-open time):

```bash
ergodix opus list
ergodix opus add tapestry --corpus tapestry-of-the-mind --writer --developer --publisher
ergodix opus add friend-novel --corpus their-book --focus-reader
ergodix opus switch tapestry
ergodix cantilever                  # uses current opus
ergodix sync-out                    # uses current opus (per ADR 0008 rename)
```

Each opus is stateful — `opus switch <name>` sets a current-opus pointer (probably in `local_config.py`); subsequent commands inherit its corpus + floater config.

Tasks (filled out when story moves out of parking lot):
- [ ] confirm stateful (`switch`) vs. per-invocation (`--opus <name>`) — likely support both, with `switch` writing the current pointer used as default for subsequent invocations
- [ ] extend `local_config.py` schema: `OPERA = { "tapestry": {...}, "friend-novel": {...} }` plus `CURRENT_OPUS` pointer
- [ ] update cantilever to take opus context as input (which floaters apply to which opus)
- [ ] update `ergodix sync-out`, `sync-in`, `migrate`, `render`, `status` to be opus-aware
- [ ] migration path for existing single-opus installs (the existing `CORPUS_FOLDER` becomes the first entry under `OPERA["default"]`)

### Scale concerns (deferred; activate per real signal)

The dimensions below are real architectural considerations even though they don't have urgency yet. Forward-compatibility decisions made now should not foreclose any of them. Each becomes its own story when activated.

#### Story 0.Z1 - Concurrency and write-collision handling

So that multiple editors can work on the corpus simultaneously without losing edits or producing broken merges,

Value: real-world co-editing (writer + editor + future line editor) needs to be safe; auto-sync racing against itself across machines is the failure mode this prevents,

Risk if ignored: silent data loss when two auto-syncs land in overlapping windows; surprising conflicts that bypass the editor persona's "zero-friction" promise,

Assumptions: each editor's machine works on independent feature branches by default; sync conflicts on shared branches surface as standard git conflicts; debouncing in the auto-sync VS Code task is part of the solution but not the whole solution,

Investigate when activated: per-machine sync queues; conflict detection in `ergodix sync-out` before push (warn user when remote has new commits on the same branch); fast-forward-only sync as default; explicit `ergodix sync-out --force` for the rare overrule case.

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