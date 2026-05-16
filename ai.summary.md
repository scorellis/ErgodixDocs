# AI Session Summary

## 2026-05-11 (v1.0 milestone closed — ergodix-index arc end-to-end on main; craft methodology captured)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. AI as architectural co-author + continuity engine.
- AI's permitted on-corpus actions are a **closed list** per [ADR 0013](adrs/0013-ai-permitted-actions-boundary.md): mechanical correction, chapter scoring, interview-aligned structural analysis, suggestion-only craft advice. Everything else is barred. **The author is always at the keyboard for creative work.**

**Architecture phase complete.** ADRs 0001–0016 + Spikes 0001–0015 merged on `main`. Don't revisit unless explicitly asked.

**License:** PolyForm Strict 1.0.0 (source-available; commercial use requires separate license from scorellis@gmail.com). Repo public.

**Branch model:** trunk-based. **Lessons learned the hard way (twice each):** GitHub's stacked-PR base auto-retarget is unreliable — when shipping multiple PRs in sequence, branch each off `main` directly (accept that the 2nd+ to merge will need a quick VERSION/CHANGELOG rebase). For PRs that strictly depend on each other's content, branch off the prior feature branch but still target `main` so the diff reduces correctly when the parent merges.

**Cadence rules (CLAUDE.md):**
- **Smaller-units-per-PR** — every coherent unit ships immediately.
- **Pause-after-each-PR** — ship one PR, post the summary, stop. User merging or saying "next" is the continuation signal.
- **Session pacing** — user decides when to stop. AI never proposes stopping points.

**Author identity:** Scott R. Ellis. (`scorellis` is an abbreviated GitHub handle.) Fictional `"Stephen Corellis"` is fine as test-fixture metadata only.

**Versioning policy** (locked 2026-05-10, see `CHANGELOG.md` header): **`1.MINOR.PATCH`** — MINOR = cumulative count of merged code PRs, PATCH = doc-only PRs since the most recent code PR. Not strict SemVer. Each PR includes its own bump in the same commit.

**Reviews convention** (locked 2026-05-10): external PR reviews (Copilot, ChatGPT, human peer — reviewer-agnostic) live in `reviews/NNNN.external-review.md` (or `NNNN.X.external-review.md` for multiple reviews against the same ADR). Security reviews with open findings are held until fixes ship.

---

### v1.0 milestone — **CLOSED** (2026-05-11)

Per the original CLAUDE.md bar (migrate + render + at least one Sprint 1 story end-to-end), v1.0 is now feature-complete on `main`:

| Pillar | Status | Where |
|---|---|---|
| **Migrate** | ✅ feature-complete | ADR 0015, `ergodix migrate --from gdocs/docx` |
| **Render** | ✅ working | Pandoc → XeLaTeX → PDF, preamble cascade |
| **Sprint 1 story (`ergodix index`)** | ✅ end-to-end | ADR 0016, 6 chunks merged: PRs #95, #96, #97, #98, #99, #101 |

VERSION on main is **1.68.2**. Tests: **761 passing, 1 skipped** (forward-looking PEP 440 gate). `ruff` + `format` + `mypy --strict` clean.

The v1.0 milestone is a tagged feature line per the policy, not a major version bump. No git tag has been pushed yet — that's a separate decision when ready.

### Today's arc — 2026-05-11

- **ergodix-index arc (chunks 1–6)** all merged: pure helpers (#95), orchestrator + atomic write (#96), drift + read_map (#97), CLI wiring (#98), fixture + hermetic e2e (#99), first-consumer doc (#101). `ergodix index` is now a real command with `--check` / `--corpus` / `--quiet`; map lives at `<corpus>/_AI/ergodix.map`.
- **ADR 0016** locks all 9 open questions from Spike 0015 (schema v1 with strict refusal; no `kind` field; `mtime` advisory; map tracked-in-git; walker factoring deferred; `--check` exits 1 on drift; consumers read via `read_map()` only; sliced editor repos regenerate locally; `_AI/` is the project-wide AI-artifact namespace).
- **Author craft methodology landed in tree (#102)**: `docs/wordsmith-toolbox-reference.md` (~30 rhetorical devices, stable ids, classifier hints) + `docs/scoring-methodology.md` (Overmorrow Writing Analysis Guide + Ten Measures of Literary Quality, 1–10 tabular contract with Eloquence watchpoints). Future Plot-Planner / writing-score / form-analyzer Skill lifts directly into a TOML data file.
- **"Devil's Toolbox" → "Wordsmith Toolbox" rename** (#102) across the entire tree. Rationale: avoids friction in K-12 / education-mode and commercial deploys; matches the methodology's "Eloquence is intentionality" directive. `grep -rln '[Dd]evil'` returns zero matches.
- **System-flow diagram landed (#91)**: `diagrams/ergodix-system-flow.md` — Mermaid flowchart + node-reference table with ADR cross-refs. First architectural diagram in the repo.
- **Stories folder convention** (#89, #92): monolithic `SprintLog.md` → per-file `stories/active/` and `stories/parking-lot/`. 15 parking-lot stories extracted. Monolith retained as frozen geological history.
- **Smoke script hardening (#90)**: closes Review 0015.3 findings (version-source false-negative; bootstrap blocking on consent gate). Smoke now reads `$DEPLOY_DIR/VERSION` and invokes `--dry-run cantilever`.
- **GitHub Actions CI shipped (#86, #87)**: pragmatic v1 of ADR 0009 — single Ubuntu + Python 3.13 cell, ruff + format + mypy + pytest on every PR, integration smoke on every push. Full uv + 9-cell matrix deferred to the `uv-migration` parking-lot story.

---

### Status — where the project is now

**Migrate, render, ergodix-index**: feature-complete (see milestone table above).

**Auth**: OAuth flow real, token persistence secure (mode 0o600, parent dir 0o700, O_NOFOLLOW, fstat, atomic tmp+rename, paste-the-code dance). Refresh-token age tracking with 90-day staleness warning. All 7 OAuth review findings closed.

**Tests**: 761 passing, 1 skipped, 89% coverage.

**CI/CD**: GitHub Actions running ruff + format + mypy + pytest + integration smoke. Both `ci.yml` and `integration.yml` workflows live; integration smoke uses the same `scripts/integration-smoke.sh` that runs locally.

**Author craft input data captured in tree**: the moat under future Plot-Planner / writing-score / form-analyzer tooling is now sitting in `docs/`.

### Open security findings

**0.** All review findings closed (OAuth review backlog + Review 0015.2 + Review 0015.3).

---

### Next-session candidates

v1.0 is closed. Sprint 2 is the next major arc. Highest-leverage starting moves:

1. **Spike 0010 resolution** — author preferences interview design. Unblocks `writing-score`'s per-author tics/tropisms watchpoint data per the Wordsmith Toolbox / scoring-methodology contract. Spike 0010 has 6 open questions; resolving them produces an ADR.
2. **Spike 0013 ADR** — ergodite registry contract (the analysis plugin model). Unblocks `form-analyzer` (Spike 0014) and every future analysis ergodite. Numbered as ADR 0017+.
3. **First Continuity-Engine tool** — `timeline-continuity-analyzer` is the easiest starter (pure date/season anchor extraction with prompt-cached cross-chapter analysis). Demonstrates the Plot-Planner / Continuity-Engine vision end-to-end with the smallest possible scope.
4. **Tag v1.0 milestone** — push a git tag like `milestone-v1` against the current `main` HEAD to formally mark the feature line. The user has not requested this yet.

**Smaller follow-ups still on the table:**
- Author's Fibonacci writing prompt → `docs/fibonacci-writing-prompt.md` (Spike 0014's blocker; precondition for the form-analyzer's structural-arc sub-check).
- Sweep ADR Notes for hidden follow-ups (mentioned in passing earlier).
- Footnote handling polish in gdocs/docx importers.
- Inline image positioning (currently emits refs as a trailing block).
- The `uv-migration` parking-lot story whenever the dev wants to commit to it (closes the deviation from ADR 0009's locked CI design).

---

### Gotchas worth remembering across sessions

- **GitHub stacked-PR base auto-retarget is NOT reliable.** When a parent PR merges, GitHub does NOT always retarget the dependent PR's base to main. Burned us twice this session (PRs #78→#79 with chunk 6; PR #94 leaking content into the wrong base). **Default to branching each PR off main directly** even if the content depends on a prior unmerged branch — accept the VERSION/CHANGELOG rebase on the 2nd+ merge.
- **Force-push is sandbox-blocked** in this environment. When a rebased branch needs pushing, push under a fresh `-v2` branch name and close/reopen the PR. Or have the user run `git push --force-with-lease` from their terminal.
- **zsh `interactivecomments` defaults to OFF.** Multi-line shell-paste blocks for the user must NOT include `#` comment lines — apostrophes inside what would be a "comment" trigger an unclosed-quote prompt the user can't easily escape. Memory rule recorded.
- **Finder/iCloud spawns ` 2.md`/` 3.md` dedup copies** under `stories/`, `reviews/`, `spikes/` occasionally. Always byte-identical to canonical siblings — safe to `rm` in a housekeeping pass.

### File state notes

- `ergodix migrate`, `ergodix index`, `ergodix status`, `ergodix render` are all real CLI commands.
- `ergodix.index` module exposes the read API future tools use: `read_map`, `compare_to_map`, `DriftReport`, `IndexEntry`, `Map`, `MAP_SCHEMA_VERSION`.
- Settings cascade has 3 layers: code defaults → `settings/defaults.toml` → `settings/bootstrap.toml`. `floaters/<name>.toml` deferred until first per-floater consumer.
- Sync transport auto-detects from `CORPUS_FOLDER` location.
- `_media/` directories under the corpus are intentionally created at umask default (not 0o700 like OAuth dirs) — they hold chapter images, not credentials.
- `_AI/` is the project-wide canonical namespace for AI-emitted artifacts (per ADR 0016 §9): `_AI/ergodix.map` from `ergodix index`; future `_AI/continuity-engine/`, `_AI/plot-planner/`, etc.
- `examples/migrate-fixture/` and `examples/index-fixture/` are the canonical hermetic e2e fixtures (copy to `tmp_path` in tests; never mutate the tracked content).
- `reviews/` holds ADR-scoped external review files: `0013.external-review.md`, `0015.external-review.md`, `0015.1.external-review.md`, `0015.2.external-review.md`, `0015.3.external-review.md`.
- `docs/` craft references: `wordsmith-toolbox-reference.md` (rhetoric catalog), `scoring-methodology.md` (chapter-eval rubric), `ergodix-map-consumers.md` (read-API doc for downstream tools), `gcp-setup.md`, `comments-explained.md`.
- `diagrams/ergodix-system-flow.md`: Mermaid system-flow + node-reference table.
