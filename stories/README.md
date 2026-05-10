# Stories

One file per story. Mirrors the `adrs/` and `spikes/` conventions.

## Layout

```
stories/
  README.md                          ← this file (index)
  SprintLog.md                       ← the monolith, frozen as a geological layer (2026-05-10)
  active/                            ← stories actively being worked on
    <slug>.md
  parking-lot/                       ← deferred stories (activated when their time comes)
    <slug>.md
```

## Convention

- **One story per file.** Easier to link to, easier to PR-review (one story changes = one file changes), aligns with `adrs/NNNN-*.md` and `spikes/NNNN-*.md`.
- **Filename**: kebab-case slug. No number prefix (numbers in the monolith were sprint-keyed; the per-file convention is by-slug). If you need ordering, the `Origin` frontmatter line records it.
- **Format**: ASVRAT (As / So that / Value / Risk / Assumptions / Tasks) per [ADR 0011](../adrs/0011-asvrat-story-format-for-persona-stories.md) for persona-driven stories. Infrastructure / chore stories may use a lighter shape — the spirit is "capture the rationale, not just the to-do list."
- **Status header**: every story file leads with a Status / Origin / cross-ref block so readers can place the story in context without scanning the body.
- **Cross-refs use full repo-relative paths** (e.g. `../../adrs/0015-...md` not `../SprintLog.md`).

## Why a folder, not the monolith

`stories/SprintLog.md` was a single ~700-line file covering every story across Sprint 0, Sprint 1 placeholders, and the parking lot. Pros of that shape: one page, easy to grep, single source of truth. Cons that pushed the change: every story edit produced merge-conflict surface on the same file; cross-linking from spikes / ADRs / external review files required anchor-following; no clean way to mark a story "active" vs. "parking-lot" vs. "done" except by inline status badges.

The folder structure trades the single-page property for per-file linkability, conflict-free per-story edits, and a clean active/parking-lot/done partition by directory.

## The monolith stays as history

[`stories/SprintLog.md`](SprintLog.md) is preserved as a frozen geological layer (2026-05-10). It contains the full history of Sprint 0's run — including DONE stories with detailed task lists, design discussions inlined per story, and the parking-lot section the new per-file structure replaces. Don't edit it; reach for it as a historical reference. New stories go in this folder's `active/` or `parking-lot/` subdirectories.

## Current state (2026-05-10)

### Active

- [ergodix-index](active/ergodix-index.md) — `ergodix index` + `_AI/ergodix.map`. Sprint 1 starter. Spike 0015 landed.

### Parking lot (this folder)

- [uv-migration](parking-lot/uv-migration.md) — adopt uv per ADR 0009's locked design (close the deviation noted in PR #86).

### Parking lot (still in the monolith, pending migration to per-file)

The following stories live in `SprintLog.md`'s parking-lot section and have not yet been extracted to per-file form. They will land in a follow-up PR:

- CriticMarkup dual-mode review (spike)
- Continuity-Engine: AI-assisted story-logic analysis suite
- Plot-Planner: AI-assisted authoring-analysis tool suite
- Sell-My-Book: book-marketing assistance suite
- IP strategy: trademark + patent decision
- Licensing + monetization framework
- Skill factory-seal protection
- MCP server + AI-user persona
- In-app AI editor with BYO-key + Drive sync
- Phil-trained custom prose linter
- Devil's Toolbox: foundational rhetoric reference Skill
- `form-analyzer` ergodite: grade-level + rhetorical eloquence + Fibonacci arc
- Story 0.X — Multi-opus support
- Scale concerns (broader bucket)
- Story 0.Y — Publishing-house / enterprise scale

Until they're extracted, the canonical place to read those stories is the monolith.
