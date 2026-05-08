# ADR 0006: Editor Collaboration via Sliced Git Repositories with Baseline-Tracked Resync

- **Status**: Accepted
- **Date**: 2026-05-03
- **Author**: Scott Ellis (original draft); integrated into the ErgodixDocs ADR set 2026-05-03
- **Spike**: [Spike 0005 — Integration of the editor-collaboration-sliced-repos proposal](../spikes/0005-editor-collaboration-integration.md)
- **Supersedes (in part)**: [ADR 0002](0002-repo-topology-and-editor-onboarding.md) — corpus repo topology section and editor workflow section. The credentials-storage and `gh auth login` portions of ADR 0002 stand unchanged.
- **Touches**: [ADR 0001](0001-click-cli-with-persona-floater-registries.md) — `publish` and `ingest` added as new top-level subcommands. [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) — editor-floater cantilever operations gain SSH-key generation + GitHub-key registration steps. [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) — editor floater's `adds_operations` extended.

> **Note (2026-05-07 — added by [ADR 0012](0012-phase-2-patterns-configure-phase-and-five-phase-orchestrator.md)):** the editor signing-key registration flow described below assumes the user's `gh` token has `admin:public_key` scope. Per ADR 0012's least-privilege resolution, C1 (`gh auth login`) does **not** request this scope upfront — it would burden every Installer (writer / developer / publisher / focus-reader) with a scope only the editor floater needs. Instead, D6 (editor signing key) detects insufficient scope at inspect time, marks itself `needs-interactive`, and the configure phase (new in ADR 0012) prompts: "Editor floater needs `admin:public_key` scope on your `gh` token; refresh now? [y/N]" before running `gh auth refresh -s admin:public_key`. The downstream `gh ssh-key add --type signing` step then works against the refreshed token. If the user declines the refresh, D6's verify check fails with a clear remediation pointing at the manual `gh auth refresh` command.

---

## Context

The Tapestry of the Mind corpus (including *The Overmorrow Cycle*) is being migrated to LaTeX to enable AI oversight, structured review, and durable long-form management. The corpus comprises ~600,000 words across multiple books, chapters, glossaries, and companion reference documents.

A subset of editors will be granted access to portions of the corpus for editorial review. Requirements:

1. Editors must only have access to the specific chapters/files assigned to them.
2. Editor changes must round-trip back to the author's master corpus with full fidelity.
3. The system must support offline work by both author and editors.
4. The author must retain authoritative control: every editor change is reviewable before integration.
5. The blast radius of any single editor (compromised machine, leaked credentials, broken trust) must be bounded to their assigned slice.
6. The system must compose with existing converter pipelines (Item 3 of the migration plan) and a future encryption layer (Item 4).

Git is the obvious version-control substrate but does not natively support per-file access control within a single repository. Encrypted-at-rest approaches (`git-crypt`, `git-agecrypt`) handle confidentiality but not access revocation, and they expose the full ciphertext history to every cloner.

## Decision

Adopt a **sliced-repository architecture with baseline-tracked resync**:

1. The author maintains a **master repository** containing the full corpus.
2. Each editor is provisioned a **dedicated slice repository** containing only their assigned files, with file paths mirroring the master.
3. A **registry** (committed to the master repo) tracks each editor's slice repo URL, assigned file list, and the master commit SHA from which their current slice was derived (the *baseline*).
4. Two automation commands govern the data flow:
   - `publish` — copies authorized files from master to the slice repo, commits, pushes, and updates the registry baseline.
   - `ingest` — fetches the slice repo, generates patches scoped to authorized files, applies them to a review branch on master using three-way merge against the baseline, and surfaces the branch for author review.
5. All editor commits are **cryptographically signed** (GPG or SSH); ingest verifies signatures before accepting.
6. Encryption at rest is handled at the **disk/volume level** on the author's machine, not at the git-object level.

## Architecture

### Repository Topology

```
                    ┌──────────────────────────┐
                    │   Master Repository      │
                    │   (author-only, local +  │
                    │    private remote)       │
                    │                          │
                    │   chapters/              │
                    │   glossary/              │
                    │   companion/             │
                    │   slices/registry.json   │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │ publish          │ publish          │ publish
              ▼                  ▼                  ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │ slice-editor-A  │ │ slice-editor-B  │ │ slice-editor-C  │
    │ (chapters 1-3)  │ │ (chapters 4-7)  │ │ (glossary only) │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │ ingest            │ ingest            │ ingest
             └──────────────────┬┴───────────────────┘
                                ▼
                   review branches on master
```

### Registry Schema

The registry lives at `slices/registry.json` in the master repo and is the single source of truth for editor permissions and sync state.

```json
{
  "version": 1,
  "editors": {
    "ethan": {
      "slice_repo_url": "git@github.com:scorellis/tapestry-slice-ethan.git",
      "public_key_fingerprint": "SHA256:...",
      "assigned_files": [
        "chapters/ch005.tex",
        "chapters/ch006.tex",
        "shared/macros.tex"
      ],
      "baseline_sha": "a1b2c3d4...",
      "last_published": "2026-05-03T14:22:00-05:00",
      "last_ingested": "2026-05-02T09:14:00-05:00",
      "policy": {
        "allow_macro_edits": false,
        "lock_assigned_files_on_master": true
      }
    }
  }
}
```

### Publish Command

`ergodix publish --editor <name>`

1. Read the registry entry for the editor.
2. Verify master is clean (no uncommitted changes).
3. Clone or update a working copy of the slice repo into a scratch directory.
4. Compute the diff between `assigned_files` and the slice repo's current contents:
   - Copy/overwrite authorized files from master.
   - Remove any files in the slice repo no longer in `assigned_files`.
5. Inject a sync header comment into each chapter file (LaTeX-comment-safe inside `.md` files containing raw LaTeX, or HTML-comment-safe in pure Markdown blocks):
   ```
   % ergodix-sync: baseline=<master-sha> editor=<name> published=<iso8601>
   ```
6. Commit to the slice repo with message:
   ```
   sync from master @ <master-sha>
   ```
7. Push to the slice repo's remote.
8. Update `baseline_sha` and `last_published` in the registry; commit the registry update to master.

### Ingest Command

`ergodix ingest --editor <name>`

1. Read the registry entry; record the current `baseline_sha`.
2. Fetch the slice repo into a scratch directory.
3. Identify all commits in the slice repo authored after the baseline.
4. Verify every commit is signed by a key matching `public_key_fingerprint`. Abort if any commit is unsigned or signed by an unrecognized key.
5. Verify every changed file is within `assigned_files`. Abort if the editor modified or added files outside their permitted scope; surface the offending paths.
6. Generate patches via `git format-patch` from baseline to the slice repo's HEAD.
7. Create a review branch on master: `editor/<name>/ingest-<YYYY-MM-DD>-<short-sha>`.
8. Apply patches with `git am --3way`. The baseline commit is the common ancestor for three-way merge; conflicts are surfaced for manual resolution.
9. Strip sync header comments before final commit (or leave them; decide per Open Question #3).
10. Leave the branch unmerged for the author's review. Do **not** auto-merge to main.

### Conflict Handling

Three-way merge handles the case where the author has also edited a chapter since the last publish. The baseline serves as the common ancestor. If `policy.lock_assigned_files_on_master` is `true`, the publish command will refuse to push if the author has touched any of `assigned_files` since the previous baseline — forcing the author to either ingest first, revert local changes, or explicitly override.

### File Path Stability

File renames in master are **prohibited** for any file currently assigned to an editor. The publish command verifies path stability against the registry's recorded `assigned_files` list. To rename, the author must (a) ingest all outstanding editor work, (b) rename in master, (c) update the registry, (d) republish (which the editor will see as a delete + add).

### Signed Commits

Editors generate a signing key (GPG or SSH-based git signing) and provide the public key fingerprint at onboarding. The fingerprint is stored in the registry. Ingest verifies every commit's signature against this fingerprint. Unsigned or mis-signed commits cause ingest to abort cleanly without modifying master.

### Encryption Posture

- **Master repo at rest:** full-disk encryption (FileVault / LUKS / BitLocker) on the author's machine; encrypted backups.
- **Slice repos in transit:** TLS via the git remote (HTTPS or SSH).
- **Slice repos at rest on hosting provider:** if the hosting provider is not fully trusted, layer per-editor encryption (e.g., `age` with the editor's public key) on the published files. Deferred to a follow-up ADR.
- **Slice repos at rest on editor machine:** the editor's responsibility, governed by onboarding agreement.

## Consequences

### Positive

- **Hard access control:** editors literally cannot read what was never pushed to them. No reliance on key-management discipline for confidentiality of unassigned material.
- **Bounded blast radius:** a compromised editor machine exposes only that editor's slice.
- **Clean revocation:** revoking an editor is "stop publishing + rotate slice repo credentials." No need to re-encrypt the corpus.
- **Native git workflow:** signed commits, three-way merges, patches, and review branches all use standard git mechanics. No exotic dependencies.
- **Composable with offline mode:** patch-file exchange (Option 2 from prior discussion) is a trivial extension — `format-patch` to a `.mbox` bundle, transmit out-of-band, `git am` on receipt.
- **Auditable:** the registry's history in the master repo is itself a complete audit log of who had access to what, and when.
- **Aligns with project philosophy:** keeps failure signals (editor disagreement, leaks, machine compromise) in the system without letting any single failure run the system.

### Negative

- **Tooling burden:** `publish` and `ingest` must be built and maintained. Estimate: a few hundred lines of Python wrapping `git` CLI, plus tests.
- **Path-rename rigidity:** the no-rename-while-assigned rule constrains author refactoring. Mitigated by treating chapter file paths as stable interfaces.
- **Author-side merge work:** when the author and editor both touch a chapter, three-way merges fall to the author. Mitigated by `lock_assigned_files_on_master` policy.
- **Per-editor repo proliferation:** each editor needs a provisioned remote. Manageable at small editor counts (≤10); revisit if scale grows.
- **No real-time collaboration:** if simultaneous editing of the same chapter is ever needed, this architecture does not support it. Out of scope; revisit with a CRDT-based ADR if requirements change.

### Neutral

- Editors must learn to use signed commits. One-time onboarding cost.
- The registry becomes a critical artifact — its loss or corruption breaks sync. Mitigated by living in the master repo's git history.

## Alternatives Considered

**A. `git-crypt` / `git-agecrypt` (single repo, encrypted files, per-file keys).** Rejected: revocation requires full key rotation and re-encryption; cloners retain ciphertext history indefinitely; doesn't prevent metadata leakage (file names, commit messages, structure).

**B. Single repo with branch-level permissions (e.g., GitLab protected branches).** Rejected: editors with clone access can read all branches regardless of push permissions. Doesn't actually enforce read access.

**C. Document-management systems (SharePoint, Google Drive, Notion).** Rejected: poor LaTeX support, weak version control, vendor lock-in, no offline-first story, AI-oversight tooling would have to be retrofitted.

**D. CRDT-based real-time collaborative editor (Yjs, Automerge).** Rejected as primary architecture: overkill for async editorial review, adds operational complexity, no clear access-control story. May revisit as a layer for specific use cases.

**E. Patch-file exchange only (no shared remotes).** Rejected as primary architecture but **retained as an offline fallback** — the publish/ingest commands should support a `--bundle` mode that produces and consumes git bundles for air-gapped exchange.

## Open Questions

1. **Chapter-level granularity sufficient?** Or are sub-chapter slices (scenes, glossary entries) ever needed? Current decision: chapter-level only; revisit if requirements change.
2. **Editor edits to shared scaffolding (macros, preamble).** Should `shared/macros.tex` be assignable, read-only-shipped, or fully excluded? Current default: read-only-shipped, with `policy.allow_macro_edits: false` rejecting any patches that touch it.
3. **Sync header lifecycle.** Strip on ingest, or retain as provenance? Tentatively: strip, but log to a sidecar audit file in the master repo.
4. **Bindery integration.** Should the sync model be aware of narrative branches (alternate timelines, deprecated chapters) as first-class concepts, or treat them as ordinary git branches? Deferred to a future ADR on Bindery semantics.
5. **Registry as JSON vs. SQLite.** JSON is git-friendly and human-readable; SQLite is more robust for concurrent operations and richer queries. Starting with JSON; migrate if needed.

## Implementation Notes

When implementing this ADR:

- Build `publish` and `ingest` as subcommands of the existing `ergodix` CLI (Click subcommand groups per [ADR 0001](0001-click-cli-with-persona-floater-registries.md)). They are sibling subcommands, not cantilever operations — they run continuously, not at bootstrap.
- Wrap `git` via `subprocess` rather than reaching for `pygit2` or `GitPython`; the CLI surface is small and shelling out keeps the dependency footprint minimal.
- The editor floater's cantilever steps (per [ADR 0005](0005-roles-as-floaters-and-opus-naming.md)) gain a step to generate an SSH signing key (`ssh-keygen -t ed25519`) and register it with GitHub via the `gh` CLI as a signing key. The fingerprint is captured by the author when adding the editor to the registry.
- File operations on `.md` files (the canonical chapter format per [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) and the Story 0.2 format decisions) — note: this ADR's references to `.tex` reflect the original draft; the canonical extension is `.md` containing Pandoc Markdown with raw LaTeX passthrough. The slicing, signing, and ingest mechanics are identical regardless of extension.
- Tests should cover: clean publish, publish with file removal, ingest with no conflicts, ingest with three-way merge, ingest with unauthorized file modification (must abort), ingest with unsigned commits (must abort), path-rename rejection, registry round-trip.
- The `--bundle` mode for offline exchange is a stretch goal for v1 but should not be designed out — keep the publish/ingest internals factored so that the transport (push/pull vs. bundle file) is swappable.
- Surface every abort condition with a clear, actionable error message naming the offending editor, file, or commit. Failures must be loud and specific.

## Reconciliation with prior ADRs

This ADR settles questions earlier ADRs left ambiguous and overrides earlier ADRs in specific ways:

- **CriticMarkup is no longer the primary editorial review surface** ([ADR 0002](0002-repo-topology-and-editor-onboarding.md), [Story 0.3](../SprintLog.md)). With slice repos, the editor edits prose directly via signed git commits; the author reviews via three-way merge in a review branch. CriticMarkup remains useful for the editor's own annotations or the author's self-notes, but is no longer the central mechanism.
- **The "editor pushes to a per-day feature branch on the shared corpus repo" workflow** ([ADR 0002](0002-repo-topology-and-editor-onboarding.md)) is replaced by "editor pushes to their slice repo; author runs `ergodix ingest`."
- **The "all editors share one private corpus repo" topology** ([ADR 0002](0002-repo-topology-and-editor-onboarding.md)) is replaced by "master repo + per-editor slice repos."
- **Auto-sync via Cmd+S** ([ADR 0002](0002-repo-topology-and-editor-onboarding.md)) — the editor's slice repo can still use a Cmd+S → debounced sync hook; it just pushes to the slice repo, not to a feature branch on a shared repo.
- **Story 0.X (multi-opus)** is unaffected: each opus has its own master repo, and slicing happens within each opus's master.

---

*End of ADR 0006.*
