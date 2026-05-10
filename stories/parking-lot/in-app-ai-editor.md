# In-app AI editor with BYO-key + Drive sync

- **Status**: parking-lot (way later — after distribution + Plot-Planner)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

## As / So that

As a writer using the polished consumer ErgodixDocs app (DMG / App Store), so that the writing experience itself happens *inside* ergodix rather than VS Code — on-the-fly AI assistance the user pays for via their own API key (BYO-AI), with chapter content auto-syncing to Google Drive as plain `.md` files in the background.

## Value

Lowers the barrier for non-developer authors who don't want VS Code; user-pays-AI keeps the cost model honest (we don't markup AI calls and the user's privacy stance with their AI provider stays their own); plain-`.md`-in-Drive preserves the "tool for any author, no lock-in" principle from [ADR 0005](../../adrs/0005-roles-as-floaters-and-opus-naming.md) — the user can walk away with their corpus as portable Markdown anytime.

## Risk

Building a custom editor is a huge surface (rich text + Markdown rendering, syntax highlighting, find/replace, version history, conflict resolution, accessibility); user-pays-AI requires good key management UX (already half-solved by `auth.py`'s three-tier credential lookup but the editor adds new prompts); "background sync" is the same hard concurrency problem as [scale-concerns](scale-concerns.md) §Z1; investing in a custom editor before the writer audience exists may be premature; competing against entrenched editors (Scrivener, Ulysses, Obsidian) needs a real differentiator.

## Assumptions

Users will accept BYO-API-key (anthropic / openai / etc.); Drive's filesystem-mirror remains a reliable sync surface; the editor can ship as an Electron / Tauri / native app once monetization is sorted; the existing CLI surface keeps working in parallel for power users (the editor and CLI are not mutually exclusive — the CLI is the engine, the editor is the front end).

## Tasks (when activated — way after the licensing framework + Plot-Planner have shipped)

- [ ] Decide editor framework — Tauri (smaller / faster, Rust+web), Electron (heavier / familiar), web-only (no install but offline-fragile), native macOS (best UX, single-platform).
- [ ] BYO-API-key flow — store via OS keychain (already wired in `auth.py`'s tier-2); UI for entering / rotating / removing keys.
- [ ] Markdown editor experience — mode + extensions + preview + render; CriticMarkup-aware comment surface.
- [ ] Background Drive sync — leverages existing Mirror infrastructure; debounce; conflict UI (extends [scale-concerns](scale-concerns.md) §Z1's solution).
- [ ] On-the-fly AI assistance hooks — which Plot-Planner tools surface inline as the author writes? (writing-score, duplicate-smasher in real-time as a side panel?).
- [ ] Distribution as a separate package from the CLI, OR unified app that bundles both — decide.
- [ ] Privacy story for the BYO-key + Drive sync stack documented in the App Store listing.
- [ ] Accessibility audit — screen reader support, keyboard navigation, contrast.

## Cross-references

- [licensing-monetization](licensing-monetization.md): commercial distribution prerequisite.
- [plot-planner](plot-planner.md): inline tool integration surface.
- [scale-concerns](scale-concerns.md) §Z1: concurrency + conflict handling.
