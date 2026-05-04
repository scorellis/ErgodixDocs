# Spike 0005: Integration of the editor-collaboration-sliced-repos proposal

- **Date range**: 2026-05-03
- **Sprint story**: [Story 0.8 — Architecture spike](../SprintLog.md#story-08---architecture-spike-orchestrator-pattern-role-based-cantilever-editor-collaboration-model-design-spike), Topics 5/6/8 (revisited)
- **ADRs produced**: [ADR 0006 — Editor collaboration via sliced git repositories with baseline-tracked resync](../adrs/0006-editor-collaboration-sliced-repos.md)

## Question

The author drafted a substantial design ADR offline (`ADR-editor-collaboration-sliced-repos.md`) proposing a sliced-repository architecture for editor collaboration. It conflicts with several already-locked decisions (notably ADR 0002's "all editors share one private corpus repo" model and the CriticMarkup-as-primary-review-surface decision). The question for this spike: what does it take to integrate this proposal cleanly with the existing ADR set?

## Discussion

### What the new ADR proposes

A master/slice topology:

- Author maintains a **master repository** containing the full corpus.
- Each editor gets a **dedicated slice repository** containing only their assigned files, with paths mirroring master.
- A **registry** in the master repo tracks each editor's slice URL, assigned files, baseline SHA, and policy.
- Two automation commands govern data flow: `publish` (master → slice) and `ingest` (slice → review branch on master).
- Editor commits must be **cryptographically signed**; ingest verifies signatures before accepting.
- File renames in master are **prohibited** while assigned to an editor; path stability is an interface contract.
- Encryption at rest handled at the disk/volume level, not at git-object level.

This is materially stronger than ADR 0002's "all editors push to per-day feature branches on a shared private corpus repo" in five distinct ways:

1. **Hard read access control** — editors literally cannot read what wasn't published to them.
2. **Bounded blast radius** — a compromised editor exposes only their slice.
3. **Clean revocation** — stop publishing + rotate slice credentials.
4. **Auditable history** — the registry's git history is itself the audit log.
5. **Native git mechanics** — signed commits, three-way merge, format-patch; no exotic dependencies.

### Conflicts with existing ADRs

| Existing decision | New ADR's position | Resolution |
|---|---|---|
| ADR 0002: all editors share one private corpus repo | Per-editor sliced repos provisioned from a master | ADR 0006 supersedes the repo-topology section of ADR 0002 |
| ADR 0002: editor's daily flow = Cmd+S → `ergodix sync` → PR review | Editor commits with signed commits to slice; author runs `ingest` | ADR 0006 supersedes the editor-workflow section of ADR 0002. Auto-sync hook still useful, but pushes to slice, not shared feature branch |
| Story 0.3 + ADR 0002: CriticMarkup as primary review surface | Editor edits prose directly; CriticMarkup not central | CriticMarkup becomes optional annotation; primary review is via three-way merge into review branch on master |
| ADR 0001: CLI named `ergodix` | New ADR drafted with `tapestry publish/ingest` | Naming reconciled — folded into `ergodix publish/ergodix ingest` |
| ADR 0001: importer registry for `migrate` | publish/ingest are continuous-operation, not import | Compatible — different concern |
| ADR 0003: cantilever's 22-operation menu | publish/ingest aren't bootstrap operations | Compatible — they are sibling CLI subcommands, not cantilever ops |
| ADR 0005: editor as floater | Compatible; editor floater's cantilever steps gain SSH-key-generation + GitHub-key-registration ops | Editor floater's `adds_operations` extended |
| (no prior ADR on signed commits) | Required | New requirement adopted |

### The four clarifying questions and their resolutions

**1. Naming.** Does `tapestry` in the draft refer to the CLI? Resolution: the CLI is `ergodix` (locked in ADR 0001). All `tapestry publish/ingest` references in the draft become `ergodix publish/ergodix ingest`.

**2. CriticMarkup vs. direct edits.** With slice repos, the natural editor flow is "edit prose, commit, push" — not "annotate with CriticMarkup, author accepts/rejects." Resolution: editor edits directly; CriticMarkup demoted to optional annotation. Story 0.3 updates accordingly.

**3. Cantilever integration vs. sibling subcommands.** publish and ingest could live inside cantilever's operation menu OR as sibling subcommands on the CLI. Resolution: sibling subcommands. They are operational (run continuously by the author), not bootstrap (run once at setup). Cantilever for the editor floater gains setup operations (SSH-keygen + GitHub-key-register) that *prepare* the editor for slice-repo work, but publish/ingest themselves are author-side commands run at any time.

**4. Signed commits requirement.** Adopting requires editor onboarding to include signing-key generation. Resolution: yes, adopted. Editor floater's cantilever steps automate SSH key generation (`ssh-keygen -t ed25519`) and registration with GitHub via the `gh` CLI as a signing key. Adds one step to the editor's one-time setup; doesn't break the zero-friction daily flow.

### Cost of integration

- Rename `ADR-editor-collaboration-sliced-repos.md` to `0006-editor-collaboration-sliced-repos.md` (numbering convention).
- Update internal "ADR-001" header to "ADR 0006".
- Replace `tapestry` CLI references with `ergodix`.
- Add Supersedes/Touches lines to the new ADR's frontmatter.
- Add a Note to ADR 0002 pointing to ADR 0006 for the superseded sections.
- Update SprintLog Story 0.8 Topic 6 / Topic 8 / Story 0.3 / Story 0.2 to reflect the new model.
- Add task lines for `ergodix publish` and `ergodix ingest` under Story 0.2.
- Note in Story 0.3 that CriticMarkup is now optional, not the primary mechanism.

Total: substantive but contained. No code changes (none of this is implemented yet).

### What this does NOT change

- Two-repo distinction at the org level still holds: `ErgodixDocs` (public, tooling) vs. corpus repos (private). Within each opus, the corpus repo gains the master/slice structure described in ADR 0006.
- Cantilever's 22-operation menu (ADR 0003) stays.
- Settings folder structure (ADR 0005) stays.
- All-floaters role model (ADR 0005) stays — editor floater just has more `adds_operations`.
- Multi-opus naming and CLI shape (Story 0.X) stays.

## Decisions reached

- **Adopt ADR 0006** as written (with the integration edits above) as the authoritative editor-collaboration model. → [ADR 0006](../adrs/0006-editor-collaboration-sliced-repos.md)
- **Supersede the repo-topology and editor-workflow sections of ADR 0002**; everything else in ADR 0002 (credentials, gh auth login, branch protection on master) stands. → ADR 0002 Note added
- **Demote CriticMarkup** from primary editorial review surface to optional annotation. → SprintLog Story 0.3 updated
- **Add `ergodix publish` and `ergodix ingest`** as planned subcommands. → SprintLog Story 0.2 updated
- **Editor floater's cantilever steps gain SSH-key-generation + GitHub-key-registration**. → SprintLog Story 0.8 Topic 4 noted; ADR 0005 reference

## Loose threads / deferred questions

These come straight from the ADR's own Open Questions section, kept here so the spike honors the author's own list:

- **Sub-chapter-granularity slicing** — current decision: chapter-level only; revisit if requirements change.
- **Editor edits to shared scaffolding** (`shared/macros.md` or LaTeX preamble files): default `policy.allow_macro_edits: false`; revisit per-editor if needed.
- **Sync header lifecycle** (strip on ingest vs. retain as provenance): tentatively strip and log to a sidecar audit file. Revisit when implementing.
- **Bindery integration** (narrative branches as first-class concepts): deferred to a future ADR on Bindery semantics.
- **Registry storage**: JSON for now; SQLite if concurrency or query needs grow.

## What's needed before implementation

ADR 0006 is now the design reference. Implementation work (Story 0.2 task lines for `ergodix publish/ingest`) needs:

1. Cantilever for the editor floater extended to generate + register the SSH signing key
2. Master-repo registry schema implementation (`slices/registry.json`)
3. `ergodix publish --editor <name>` implementation
4. `ergodix ingest --editor <name>` implementation
5. Tests covering all the abort cases the ADR enumerates

None of this is in v0.1.0; all of it lands at v0.2.0 or later, gated on real implementation activation of Story 0.2.
