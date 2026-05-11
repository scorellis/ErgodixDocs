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

Infra / tooling:

- [uv-migration](parking-lot/uv-migration.md) — adopt uv per ADR 0009's locked design (close the deviation noted in PR #86).

Spike (not yet ASVRAT-shape story):

- [criticmarkup-dual-mode-review](parking-lot/criticmarkup-dual-mode-review.md) — diff-level + CriticMarkup review UX precedence.

Sprint 1+ when activated:

- [continuity-engine](parking-lot/continuity-engine.md) — AI-assisted story-logic analysis suite. Project's raison d'être.
- [phil-trained-prose-linter](parking-lot/phil-trained-prose-linter.md) — custom linter trained on the human editor's repeated corrections.

Sprint 2+ when activated:

- [plot-planner](parking-lot/plot-planner.md) — AI-assisted authoring-analysis tool suite (craft, not story logic).
- [wordsmith-toolbox](parking-lot/wordsmith-toolbox.md) — foundational rhetoric reference Skill (dependency of Plot-Planner tools).
- [form-analyzer-ergodite](parking-lot/form-analyzer-ergodite.md) — grade-level + rhetorical eloquence + Fibonacci arc; first concrete ergodite.
- [skill-factory-seal-protection](parking-lot/skill-factory-seal-protection.md) — signed Skill manifests; activates with first proprietary Skill.
- [mcp-server-ai-user-persona](parking-lot/mcp-server-ai-user-persona.md) — MCP server exposing a curated ergodix tool surface; new AI-user persona.

Way later (post-distribution / pre-commercial):

- [ip-strategy](parking-lot/ip-strategy.md) — trademark "ErgodixDocs" + patent decision (hard deadline ~2027-05-02 for US grace-period filing).
- [licensing-monetization](parking-lot/licensing-monetization.md) — license keys, payment, distribution channels.
- [sell-my-book](parking-lot/sell-my-book.md) — book-marketing assistance suite (activates after the author's own book ships).
- [in-app-ai-editor](parking-lot/in-app-ai-editor.md) — polished consumer app, BYO-key + Drive sync (after Plot-Planner + licensing ship).

Scale / multi-tenancy (deferred until real signal):

- [multi-opus-support](parking-lot/multi-opus-support.md) — Story 0.X. Named bundles of (corpus + floater set) on one machine.
- [scale-concerns](parking-lot/scale-concerns.md) — Stories 0.Z1–0.Z5: concurrency, AI cost, retention, resilience.
- [publishing-house-enterprise-scale](parking-lot/publishing-house-enterprise-scale.md) — Story 0.Y. Enterprise tenancy (SSO, central billing, etc.).

The monolith [SprintLog.md](SprintLog.md) is no longer the canonical source for any active or parking-lot story — it remains as historical record only.
