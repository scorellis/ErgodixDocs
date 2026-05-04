# Spike 0002: Repo topology, editor onboarding, and the bidirectional flow

- **Date range**: 2026-05-03
- **Sprint story**: [Story 0.8 — Architecture spike](../SprintLog.md#story-08---architecture-spike-orchestrator-pattern-role-based-cantilever-editor-collaboration-model-design-spike), Topics 5, 6, 8
- **ADRs produced**: [ADR 0002 — Two-repo topology with auto-sync editor persona](../adrs/0002-repo-topology-and-editor-onboarding.md)

## Question

Three intertwined questions resolved together:

- **Topic 5**: How do an editor's edits flow back to the author? GitHub PR? Drive Mirror? Hybrid? Private review repo?
- **Topic 6**: Where do chapters live? Same repo as tooling? Separate repo? Public or private?
- **Topic 8**: Is `--persona editor` a real mode that runs different tooling, or just a documentation label over GitHub's existing review tools?

## Discussion

### The collision: Drive Mirror vs. git for the corpus

Initial thinking had chapters living in `~/My Drive/Tapestry of the Mind/` (Drive Mirror provides automatic cross-device sync). But chapters also need the version-control + review benefits of git. Putting them in *both* creates a real conflict: Drive Mirror and git both want to be the truth about file content. If Phil edits on his machine and saves, Drive Mirror pushes the change up; the author's machine sees it as an uncommitted working-tree change without ever going through PR review. The git review workflow gets bypassed by the file system.

Resolution: pick one source of truth. **Git wins for the corpus**. Drive becomes a *render output* target (PDF deployments to passive readers) rather than the corpus storage.

### Author's three proposals for Phil's UX

The author asked about three specific alternatives:

1. **Use Claude as a wrapper** — Phil tells local Claude "I'm done" and Claude pushes for him.
2. **Use the GitHub API to create his account** — fully programmatic onboarding.
3. **Build a VS Code extension with a button** — one-click UX in his editor.

Honest assessments:

- **GitHub API to create an account**: not possible. GitHub deliberately doesn't expose account creation — interactive signup is required (email verification, captcha, ToS). Account creation must be manual; everything else after is automatable.
- **Claude wrapper**: technically works but adds an Anthropic subscription dependency for an editor who doesn't otherwise need AI features. Adds Claude needing git+GitHub creds. Net: more weight, no real win over a CLI command.
- **VS Code extension**: right long-term north star. Best UX for non-technical editors. Real engineering cost (TypeScript, extension API, packaging, marketplace). Sprint 2+ scope. Not v1.

### The lighter answer that already fits ADR 0001

ErgodixDocs already has `ergodix sync` planned as a subcommand and personas as a registry. The editor persona's `cantilever` steps and `sync` behavior, defined in the persona module, give us:

**One-time setup** (`ergodix --persona editor cantilever`):
- Run `gh auth login` (browser-based, Phil's credentials, one time)
- Clone `tapestry-of-the-mind` to a sensible location
- Configure `git user.name` and `git user.email`
- Install VS Code and the CriticMarkup extension
- Wire a VS Code task that auto-runs `ergodix sync` on save (with debouncing)

**Daily flow** (zero commands):
- Phil opens the corpus folder in VS Code
- Edits chapters with CriticMarkup
- Cmd+S saves → debounced VS Code task fires `ergodix sync` in the background
- `ergodix sync` stages everything, commits with an auto-message, pushes a per-day feature branch, and opens or updates a PR via `gh pr create`
- Phil sees a small "synced" indicator in VS Code's status bar; otherwise nothing

**Auto-sync debounce**: Cmd+S on every keystroke would stomp git operations. The wired task uses a debounce — push at most every N seconds (e.g. 30) or on explicit `ergodix sync --now`. Implementation detail; surfaced as a design constraint, not a blocker.

The author explicitly chose "absolute zero-friction" for the daily flow and accepted helping Phil through the one-time setup via screen-share.

### Public/private split

Two repos:

- **`ErgodixDocs`** (public): tooling, planning, ADRs, spikes, docs. Anyone reads; only collaborators write. The "tool for any author" framing demands this stay public.
- **`tapestry-of-the-mind`** (private): `.md` chapter files, frontmatter, `_AI/` outputs, `_archive/` of original `.gdoc` files post-migration. Author + editor + future collaborators only. World has no access.

The original "public repo" decision (Story 0.4) was made when the repo was tooling-only. With chapter prose now in scope, that calculus changes — chapters move to the private repo; tooling stays public. Re-examined and resolved in this spike.

### AI artifacts and git auth

AI runs locally on the author's machine, generates files in `_AI/` of the working copy. **Author commits them manually** when satisfied. AI never has git push credentials. Preserves the human-in-the-loop principle and avoids any AI-auth complexity for git itself.

If at some point the AI's output volume justifies an "AI commits to its own branch + opens a PR" workflow, that becomes a future story with its own spike. Not v1.

### Branch model for the corpus repo

Simpler than the tooling repo. The corpus has a different cadence (daily prose edits) and a different review profile (one author, one or a few editors, no CI gating prose merges).

- `main` — current canonical state of the manuscript
- `feature/<editor>-<date>` — work-in-progress feature branches per editor per day
- No `develop` branch — corpus is simpler than tooling; PR straight to `main` with required author review

Branch protection on `tapestry-of-the-mind/main`:
- Require PR review from author (a CODEOWNER) before merge
- Block direct push to `main`
- No CI required (corpus has no tests)

## Decisions reached

- **Two-repo topology**: `ErgodixDocs` public for tooling; `tapestry-of-the-mind` private for the corpus. → [ADR 0002](../adrs/0002-repo-topology-and-editor-onboarding.md)
- **Corpus is git-tracked, not Drive-synced**. Drive becomes a render-output target only. → ADR 0002
- **AI artifacts** go to `_AI/` in the working copy; author commits manually; AI has no git credentials. → ADR 0002
- **Editor persona** is real, with `cantilever` steps installing `gh` auth, the corpus clone, VS Code + CriticMarkup, and an auto-sync VS Code task. → ADR 0002
- **Daily editor flow** is zero-command via Cmd+S → debounced `ergodix sync` task. → ADR 0002
- **Branch model for corpus**: `main` + per-editor-per-day feature branches; no `develop`; PR + author-review-required to `main`. → ADR 0002

## Loose threads / deferred questions

- **VS Code extension** as a button-driven UX: parked as a future story (Sprint 2+). The CLI is the work; the extension would be a button face on top.
- **Other personas** (focus reader, publisher, beta reader, line editor) — out of scope for this spike. Topic 4 will expand the role matrix when needed.
- **Auto-sync debounce mechanism** — implementation detail (probably a `lastSync` timestamp file + N-second cooldown); designed when the editor cantilever is built.
- **Sync conflict resolution** — what if Phil and the author both push edits on overlapping branches? Standard git conflict resolution; may need a `--persona editor` UX wrapper that explains conflicts in non-git language. Filed as a Story 0.2 sub-task to revisit when sync is implemented.
- **Future review-tool integrations** (e.g. Phil prefers reading PDFs to Markdown — `ergodix render` could auto-produce a CriticMarkup-rendered PDF on every PR push). Worth considering when we get to render implementation.
