# AI Session Summary

## 2026-05-10 (Sunday — migrate arc complete; OAuth review backlog closed)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. AI as architectural co-author + continuity engine.
- AI's permitted on-corpus actions are a **closed list** per [ADR 0013](adrs/0013-ai-permitted-actions-boundary.md): mechanical correction, chapter scoring, interview-aligned structural analysis, suggestion-only craft advice. Everything else is barred. **The author is always at the keyboard for creative work.**

**Architecture phase complete.** ADRs 0001–0015 + Spikes 0001–0014 merged on `main`. Don't revisit unless explicitly asked.

**License:** PolyForm Strict 1.0.0 (source-available; commercial use requires separate license from scorellis@gmail.com). Repo public.

**Branch model:** trunk-based. **Stack PRs linearly** when working in sequence — branch off the previous feature branch (not main) so VERSION conflicts don't accumulate. Single-engineer workflow.

**Cadence rules (CLAUDE.md):**
- **Smaller-units-per-PR** — every coherent unit ships immediately.
- **Pause-after-each-PR** — ship one PR, post the summary, stop. User merging or saying "next" is the continuation signal.
- **Session pacing** — user decides when to stop. AI never proposes stopping points.

**Author identity:** Scott R. Ellis. (`scorellis` is an abbreviated GitHub handle.)

**Versioning policy** (locked 2026-05-10, see `CHANGELOG.md` header): **`1.MINOR.PATCH`** — MINOR = cumulative count of merged code PRs, PATCH = doc-only PRs since the most recent code PR. Not strict SemVer. Each PR includes its own bump in the same commit so drift doesn't recur.

**Reviews convention** (locked 2026-05-10): external PR reviews (Copilot, ChatGPT, human peer — reviewer-agnostic) live in `reviews/NNNN.external-review.md` (or `NNNN.X.external-review.md` for multiple reviews of the same ADR). Security reviews with open findings are held until fixes ship.

### Today's arc — 2026-05-10 (≈22 PRs across the day)

By topic:
- **Migrate arc — feature-complete.** Chunks 1-7 plus chunk 6b (gdocs image extraction) per ADR 0015 all merged on main. `ergodix migrate --from gdocs` works end-to-end with: OAuth paste-the-code flow + token persistence (chunks 1a/1b/1c), importer registry (chunk 2), corpus walker + manifest TOML + archive (chunks 3a/3b/3c), CLI wiring (chunk 4), `.docx` importer (chunk 5), embedded image extraction for both gdocs and docx (chunk 6 + 6b), and `examples/migrate-fixture/` for hermetic e2e tests (chunk 7).
- **OAuth security review — backlog at 0 open findings.** All 7 findings from `reviews/0015.external-review.md` closed: #1 RefreshError messaging, #2 client_id consistency, #3 token-age tracking + staleness warning, #4 rate-limit / token-exchange messaging, #5 parent-dir mode safety net, #6 broken-local_config warning, #7 deserialization validation.
- **Architecture — designed but parking-lot:** Spike 0012 (migrate-from-gdocs design), Spike 0013 (style sentinel + authorship certificate + ergodites + education-mode extension), Spike 0013 amendment (ergodites naming locked + integrity sub-section), Spike 0014 (form-analyzer ergodite). ADR 0015 (migrate locked).
- **Two external reviews completed:** `reviews/0015.external-review.md` (chunks 1a-1c OAuth security) and `reviews/0015.2.external-review.md` (PRs #73-#77 + chunk 6/6b/oauth-backlog). All medium and low findings addressed; **0 critical, 0 open**.
- **Versioning + reviews conventions** established mid-day: 1.MINOR.PATCH PR-cadence-based, reviews in `reviews/NNNN.external-review.md`.
- **Branch-stacking discipline established:** linear chain (`main → branch-A → branch-B → branch-C`) is the default for sequential work. Sibling branches off main caused VERSION-conflict cascades earlier in the day.

### Status — where the project is now

**Story 0.2 (canonical repo format + migrate):**
- Format locked (Pandoc Markdown + raw LaTeX, YAML frontmatter) in earlier ADRs.
- Migrate **feature-complete** end-to-end. `ergodix migrate --from gdocs --check --corpus <path>` is callable.

**Story 0.3 (auth):** OAuth flow real, token persistence secure (mode 0o600, parent dir 0o700, O_NOFOLLOW, fstat, atomic tmp+rename, paste-the-code dance). Refresh-token age tracking with staleness warning at 90 days.

**Story 0.11 (cantilever installer):** Closed at 100% on 2026-05-09. All A1-F2 prereqs registered.

**Render:** Already working (Pandoc → XeLaTeX → PDF).

**Sprint 1 features (Plot-Planner, Continuity-Engine, ergodix index, scoring):** Not started. **Next major arc.** All depend on migrate landing — which it now has.

**Tests:** 667 passing, 1 skipped (forward-looking PEP 440 gate). 88% coverage. ruff + format + `mypy --strict` clean.

### Open security findings

**0.** All 7 OAuth review findings closed; security/0001-0005 from earlier closed.

### Next-session candidates

The migrate arc is feature-complete. Render is working. The natural next big arc is **Sprint 1**.

**Highest user-visible leverage:**
- **`ergodix index` + `_AI/ergodix.map`** (parking-lot story, "near-term — after B2"): per-file SHA-256 hash map of the corpus so incremental AI tools (Plot-Planner, Continuity-Engine) only re-analyze changed chapters. Foundational for every Sprint 1 tool that runs over the corpus. Likely starting move.
- **Plot-Planner** (Sprint 1+ parking-lot): AI-assisted authoring-analysis tool suite. Spike 0010's interview gates structural analysis preferences.
- **Continuity-Engine** (Sprint 1+ parking-lot): plot-hole and continuity detection across chapters.

**Migrate polish (smaller follow-ups):**
- The author's Fibonacci writing prompt → `docs/fibonacci-writing-prompt.md` (Spike 0014's blocker).
- Footnote handling in gdocs/docx importers (parking-lot).
- Inline image positioning (current v1 emits refs as a trailing block; polish pass can position inline).
- Tables — not in scope for v1.

**v1.0.0 milestone (per the original CLAUDE.md bar — migrate + render + at least one Sprint 1 story working e2e on real Tapestry content):** ~85% there. Migrate ✅, render ✅, Sprint 1 story remains.

### Today's gotchas worth remembering

- **GitHub stacked-PR base auto-retarget is NOT reliable.** PR #78 (chunk 6) merged into its stacked base branch instead of main when the parent merged; chunk 6's content had to be cherry-picked onto main as PR #79. When stacking, verify each PR's base after upstream merges.
- **Force-push is sandbox-blocked** in the current environment. The user runs `git push --force-with-lease origin <branch>` from their terminal when a rebased/amended branch needs pushing.
- **zsh's `interactivecomments` defaults to OFF.** Multi-line shell-paste blocks for the user must NOT include `#` comment lines — apostrophes inside what would be a "comment" trigger an unclosed-quote prompt the user can't easily escape from. Memory rule recorded.

### File state notes

- `ergodix migrate` is real. `ergodix status` is real. `ergodix render` is real.
- Settings cascade has 3 layers: code defaults → `settings/defaults.toml` → `settings/bootstrap.toml`. `floaters/<name>.toml` deferred until first per-floater consumer.
- Sync transport auto-detects from `CORPUS_FOLDER` location.
- `_media/` directories under the corpus are intentionally created at umask default (not 0o700 like OAuth dirs) — they hold chapter images, not credentials. Documented in code comments per review 0015.2.
- `examples/migrate-fixture/` is the canonical hermetic e2e fixture (Chapter 1.gdoc placeholder + Chapter 2.docx real binary + Notes.gsheet skip-test). Build script at `tests/build_migrate_docx_fixture.py` (lives outside the fixture so the migrate walker doesn't pick it up).
- `reviews/` holds the ADR-scoped external review files: `0013.external-review.md`, `0015.external-review.md`, `0015.1.external-review.md`, `0015.2.external-review.md`.
