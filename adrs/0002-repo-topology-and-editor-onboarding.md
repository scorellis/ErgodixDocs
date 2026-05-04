# ADR 0002: Two-repo topology with auto-sync editor persona

- **Status**: Accepted
- **Date**: 2026-05-03
- **Spike**: [Spike 0002 — Repo topology, editor onboarding, and the bidirectional flow](../spikes/0002-repo-topology-editor-onboarding.md)

> **Note (2026-05-03):** [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) collapses personas and floaters into one registry. References to "editor persona" below should now be read as "editor floater." Behavior described is unchanged; only the noun differs.
>
> **Note (2026-05-03 — supersession):** [ADR 0006](0006-editor-collaboration-sliced-repos.md) supersedes the **repo topology** and **editor workflow** sections of this ADR. Specifically: the "all editors share one private corpus repo" topology is replaced by master + per-editor slice repos with publish/ingest commands; the auto-sync-on-save flow now targets the editor's slice repo rather than a shared feature branch; CriticMarkup is no longer the primary editorial review mechanism (it remains optional for annotations). The credentials-storage and `gh auth login` portions of this ADR stand unchanged.

## Context

ErgodixDocs needs to answer three intertwined questions:

1. Where do chapter prose files live, and at what visibility?
2. How do an editor's edits flow back to the author?
3. Is `--persona editor` a real `ergodix` mode, or just documentation over GitHub's existing review tools?

Constraints:

- **The "tool for any author" framing** (CHANGELOG `[0.1.0]`, README) requires the tooling to remain public.
- **Chapter prose is unpublished manuscript** and must remain private to the author and invited collaborators.
- **Editors are not necessarily git-savvy.** The current editor (Phil) is comfortable in VS Code but doesn't know git or GitHub; future editors and focus readers may have similar profiles.
- **Drive Mirror and git can't both be the source of truth** for the same corpus files without creating sync conflicts that bypass review.
- **Persona registry** (per [ADR 0001](0001-click-cli-with-persona-floater-registries.md)) is the agreed extension surface for role-aware behavior.

## Decision

### Two-repo topology

| Repo | Visibility | Holds | Branch model |
|---|---|---|---|
| `ErgodixDocs` | **Public** | Tooling, planning, ADRs, spikes, docs, installer, `auth.py` | `main` + `develop` + `feature/*` |
| `tapestry-of-the-mind` | **Private** | Chapter `.md` files + frontmatter, `_AI/` outputs, `_archive/` originals, render outputs | `main` + per-editor-per-day `feature/*`; no `develop` |

The corpus repo is **git-tracked, not Drive-synced**. Drive Mirror is no longer the source of truth for prose. Drive becomes a *render output* target — `ergodix render` can deposit PDFs into a Drive folder for passive readers (focus groups, publisher) who shouldn't be in git.

### Branch protection

`tapestry-of-the-mind/main`:

- Requires PR + author review (author listed in CODEOWNERS)
- Blocks direct push
- No required CI checks (corpus has no tests)

`ErgodixDocs` retains its existing `main` + `develop` model.

### Editor persona — real mode, real cantilever steps

`--persona editor` is a registered persona module (per ADR 0001) with concrete cantilever steps:

**One-time setup** (`ergodix --persona editor cantilever`):

1. Run `gh auth login` interactively — editor authenticates in their browser, one time.
2. Clone `tapestry-of-the-mind` to a sensible default location.
3. Configure `git user.name` and `git user.email`.
4. Install VS Code and the CriticMarkup extension.
5. Install a VS Code task that auto-runs `ergodix sync` on save, with debouncing (push at most every N seconds; default N = 30).

**Daily flow** (zero commands):

1. Editor opens the corpus folder in VS Code.
2. Edits chapters; uses CriticMarkup syntax for additions, deletions, and comments.
3. Cmd+S → the wired VS Code task fires `ergodix sync` in the background.
4. `ergodix sync` stages all changes, commits with an auto-message (`"Edits from <editor> — <date> <time>"`), pushes a per-editor-per-day feature branch, and opens (or updates) a PR via `gh pr create`.
5. Status-bar indicator confirms the sync. No commands typed.

**Author reviews** the resulting PRs in GitHub (or via `gh pr view` from the CLI), comments inline using GitHub review tools, accepts or requests changes, merges to `main`.

### AI artifacts

AI runs locally on the author's machine and writes its outputs to `_AI/` in the working copy. **Author commits and pushes manually** when satisfied with the output. The AI has no git push credentials. This preserves the human-in-the-loop principle and avoids any auth-rotation or audit-trail complexity for AI commits.

If the volume of AI artifacts later justifies an automated AI → branch → PR workflow, it becomes a separate ADR with its own spike. Not in v1.

### What this is *not*

- **Not** a Drive-synced corpus. We rejected that explicitly because of the Drive-vs-git source-of-truth conflict.
- **Not** a GitHub-API-driven account onboarding. GitHub deliberately doesn't expose account creation; editors create their own accounts manually (one-time, ~5 min).
- **Not** a Claude-wrapped editor experience. Adds an Anthropic subscription dependency to a role that doesn't otherwise need AI.
- **Not** a VS Code extension yet. Right north star, real engineering cost; parked for Sprint 2+.

## Consequences

**Easier:**

- Public tooling, private prose — clean audience separation.
- Standard developer review workflow for chapter edits — well-trodden, no invention.
- Editors get a zero-command daily flow once cantilever has run.
- AI stays out of credential management.
- The `--persona editor` design plugs directly into ADR 0001's persona registry — no new architectural surface.
- Future personas (focus reader, publisher, line editor) follow the same pattern: define their cantilever steps and sync behavior in their persona module.

**Harder:**

- Two repos to maintain rather than one. Author has two `git remote`s, two CHANGELOGs, two release cadences. Manageable but real.
- The author still has to do the editor's one-time setup (or screen-share through it). One-time cost; explicitly accepted.
- The auto-sync debounce mechanism needs careful design — Cmd+S on every keystroke must not stomp git operations.
- `tapestry-of-the-mind` is a living manuscript in git; bad merges or force-pushes could lose prose. Branch protection + author-review-required mitigates but doesn't eliminate the risk. Backups (Drive Mirror of the rendered PDFs, and GitHub's own retention) provide redundancy.

**Accepted tradeoffs:**

- Editors can never commit directly to `main` — every edit goes through PR review even for trivial typos. Acceptable cost for the safety and the audit trail.
- AI artifacts manually committed = some friction for the author. Worth it for the credential/auth simplicity.
- VS Code extension as the long-term zero-friction path is deferred. The CLI flow is intermediate; if it proves friction-y in practice, we revisit.

## Alternatives considered

- **Single public repo with prose mixed in**: rejected. Conflicts with privacy of unpublished manuscript.
- **Single private repo with tooling and prose**: rejected. Conflicts with the "tool for any author" framing — tooling should be public.
- **Drive Mirror as primary corpus storage**: rejected. Drive-vs-git source-of-truth conflict bypasses the review workflow.
- **Hybrid Drive + git** (Topic 5 option C from the spike): rejected. Same conflict as Drive-only, plus added complexity.
- **Private review repo separate from main private repo** (Topic 5 option D): rejected. Two-repo split already separates public/private; adding a third for review is overhead without clear benefit.
- **Editor mode as just a doc label** (Topic 8 option A): rejected. Without persona-aware automation, the editor has to learn git + GitHub manually, which contradicts the zero-friction goal.
- **Claude as editor wrapper**: rejected. Adds Anthropic subscription dependency for a role that doesn't need AI.
- **GitHub API-based account creation**: not possible; GitHub doesn't expose this.
- **VS Code extension**: deferred to Sprint 2+; right long-term, expensive in the near term.

## References

- [Spike 0002](../spikes/0002-repo-topology-editor-onboarding.md) — full discussion record.
- [ADR 0001](0001-click-cli-with-persona-floater-registries.md) — persona registry that this ADR plugs into.
- [Hierarchy.md](../Hierarchy.md) — narrative model the corpus repo mirrors in folder structure.
- [SprintLog.md](../SprintLog.md) Story 0.8 — parent design spike.
