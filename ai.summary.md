# AI Session Summary

## 2026-05-06 (end-of-late-night-session)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. AI as architectural co-author + continuity engine.
- AI's role is **Architectural Analysis only** — never edits prose chapters; tracks plotlines, flags plot holes, builds summaries/storyboards, supports worldbuilding.

**Architecture phase complete.** ADRs 0001–0010 and Spikes 0001–0008 are merged on `main`. Don't revisit unless explicitly asked.

**Locked architectural decisions (read these in `adrs/` to fully load context):**

- **ADR 0001** — Click subcommand groups, plugin registries (later collapsed by 0005).
- **ADR 0002** — Two-repo topology (later partly superseded by 0006).
- **ADR 0003** — Cantilever bootstrap orchestrator with 25 operations (later refined by 0010).
- **ADR 0004** — Continuous polling job (every 5 min, persona-aware, no-op when offline).
- **ADR 0005** — All roles as floaters in single registry. `--writer`, `--editor`, `--developer`, `--publisher`, `--focus-reader`. Multi-corpus container named "opus" (plural "opera").
- **ADR 0006** — Editor collaboration via sliced git repositories with baseline-tracked resync.
- **ADR 0007** — Bootstrap scripts (sh + ps1), prereqs as importable Python modules, console-script entry in pyproject.toml.
- **ADR 0008** — `ergodix sync` rename to `sync-out`/`sync-in`; local_config vs settings/* ownership rule; ruff + mypy adopted.
- **ADR 0009** — CI workflow + dependency-pin policy. Locked vs latest two-job CI; uv as lockfile tool; reactive capping pre-Story-0.7, proactive capping post-Story-0.7.
- **ADR 0010** — Pre-flight scan + consent gate + apply + verify four-phase installer model. Replaces `check() -> CheckResult` from ADR 0007 with separate `inspect()` and `apply()` per prereq.

**Branch model**: trunk-based. Only `main` plus feature branches.

**Format decisions (Story 0.2, locked):**
- Pandoc Markdown + raw LaTeX passthrough; `.md` extension with mandatory YAML frontmatter (`format: pandoc-markdown`).
- One `.md` file per Chapter.
- LaTeX preamble cascade: optional `_preamble.tex` at every folder level; render walks up the tree, concatenates most-general-first.
- Render pipeline: Pandoc → XeLaTeX → PDF.

**Pacing**: ~1 year of private development by author (`--writer --developer` floater combination) before inviting other authors.

**Working partnership norms** (now in CLAUDE.md):
- Push back on principle violations in one sentence; let user decide.
- Late-arriving principles are normal — apply forward, accept rework.
- Course corrections cost cycles but are healthy; capture in the right doc.
- The persistent record (CLAUDE.md, ADRs, spikes, WorkingContext, ai.summary) is how partnership survives sessions. Capture insights before moving on.
- **Always ask before pushing to remote.**

**Where work paused (2026-05-06 early morning):**

- On branch `feature/installer-redesign`. **Story 0.11 (installer redesign per ADR 0010) in flight.**
- **7 commits pushed to origin.** Should be reviewed by Copilot before adding more code on top.
- Implementation completed: prereq types (`InspectResult`, `ApplyResult`), cantilever phases 1–4 with sudo grouping, abort-fast, verify-on-no-changes, op_id uniqueness, PATH-derived ergodix smoke, local_config sanity check.
- Two Copilot reviews already absorbed and addressed in-branch.
- **Tests: 110 passing, 1 skipped. Coverage 75%. ruff + mypy strict clean.**

**Story 0.11 remaining steps:**

- **Step 3** (next): First real prereq — `ergodix/prereqs/check_platform.py` (A1, simplest of the 25 ops). Validates inspect/apply contract against real code. Smallest piece next.
- **Step 4**: Wire `ergodix cantilever` Click subcommand to `run_cantilever()`.
- **Step 5**: Thin `bootstrap.sh` (and `bootstrap.ps1` later) + integration smoke test in fresh deploy directory.
- **Step 6**: Remaining 24 prereqs — cookie-cutter against the established pattern.

**Tomorrow's first move:**

1. Open PR for `feature/installer-redesign` against `main` (7 commits).
2. Ask Copilot for a third review of this branch — prior two each caught real bugs; marginal value of another review remains high.
3. Absorb findings, then begin Story 0.11 step 3 (`check_platform.py`).

Please start by asking the user whether they want to (a) wait for Copilot's review of the now-pushed branch before continuing, or (b) start step 3 in parallel. Then proceed accordingly.

Important context:
- `.claude/settings.json` was added with read-only auto-allows for `pytest`, `ruff check`, `ruff format --check`, `mypy` to reduce permission prompts during long Bash-heavy sessions.
- `.claude/settings.local.json` has a stale `chmod +x deploy.sh` entry (deploy.sh was deleted weeks ago); harmless but worth cleaning up.
