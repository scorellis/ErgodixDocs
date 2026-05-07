# AI Session Summary

## 2026-05-06 (end-of-day)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. AI as architectural co-author + continuity engine.
- AI's role is **Architectural Analysis only** — never edits prose chapters; tracks plotlines, flags plot holes, builds summaries/storyboards, supports worldbuilding.

**Architecture phase complete.** ADRs 0001–0011 and Spikes 0001–0008 are merged on `main` (or in flight on `feature/installer-redesign`). Don't revisit unless explicitly asked.

**Locked architectural decisions (read in `adrs/` to fully load context):**

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
- **ADR 0011** — ASVRAT story format required for persona-driven sprint stories; infrastructure stories may keep SVRAT. Forward-only convention; existing stories not migrated. Added 2026-05-06.

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

**Where work paused (2026-05-06 end of day):**

- On branch `feature/installer-redesign`. **Story 0.11 (installer redesign per ADR 0010) advanced through step 5.**
- **11 commits pushed to origin** (prior 7 + today's 4: ADR 0011, step 3 check_platform, step 4 CLI wired, step 5 bootstrap.sh).
- Implementation completed today:
  - **ADR 0011** — ASVRAT story-format convention codified.
  - **Step 3** — `ergodix/prereqs/check_platform.py` (op A1, the simplest of the 25). Validates the inspect/apply contract against real code.
  - **Step 4** — `ergodix cantilever` Click subcommand wired to `run_cantilever()`; success-outcome ladder maps `applied` / `no-changes-needed` / `dry-run` / `consent-declined` → exit 0, everything else → exit 1.
  - **Step 5** — `install_dependencies.sh` deleted; replaced by minimal `bootstrap.sh` per ADR 0007: detect Python ≥3.11, create `.venv`, `pip install -e ".[dev]"`, hand off to `ergodix cantilever`. Re-runnable. Forwards user args (`--dry-run`, `--ci`) through to the CLI. README + CHANGELOG updated.
- **Tests: 129 passing, 1 skipped. Coverage 78%. ruff + mypy strict clean.**

**Story 0.11 remaining:**

- **Manual smoke test (NEXT — tomorrow's first move):** the user runs `./bootstrap.sh` in a fresh checkout at `~/Documents/Scorellient/Applications/ErgodixDocs/` to validate the end-to-end cold-start path. The branch is pushed; recommended sequence is to `mv` the prior 2026-05-05 test install aside, `git clone -b feature/installer-redesign` fresh, then `./bootstrap.sh`. Expected behavior: A1 platform check passes on macOS, plan is empty (no other prereqs implemented), verify phase reports `local_config_sane` as failed because no `local_config.py` exists yet (correct outcome — that's a "verify-failed" exit, not a silent green).
- **Step 6** (after smoke validates the pattern): remaining 24 prereqs from ADR 0003 — cookie-cutter against the `check_platform.py` pattern. TDD-first per CLAUDE.md.
- **`bootstrap.ps1`** — Windows sibling of bootstrap.sh, deferred.
- **Spike-0008-driven gap items** still open: `pip install -e .` as explicit phase-3 step (currently lives in bootstrap.sh; ADR 0010 wants it as a prereq), Python ≥3.11 enforcement in inspect, final-message generation from run record, etc. — bundle these into step 6 work.

**Tomorrow's first move:**

1. **Wait for the user's smoke-test report** from `~/Documents/Scorellient/Applications/ErgodixDocs/`. Likely outcomes:
   - **Green-ish** (A1 passes, verify reports the missing local_config.py): proceed to step 6 by picking the next-simplest prereq (probably A2 or B1) and writing its tests first.
   - **Red** (any phase crashes, bootstrap.sh fails to find Python, pip install fails, ergodix not on PATH after install, verify panics): triage with the user, fix the root cause, re-run. Do NOT cookie-cut step 6 against a broken pattern.
2. After smoke passes, propose step 6 ordering: do prereqs in ADR 0003 order (A1 done; A2 next), or in dependency order (Python prereq before brew prereq before Pandoc prereq).

Important context:
- `.claude/settings.json` was added 2026-05-05 with read-only auto-allows for `pytest`, `ruff check`, `ruff format --check`, `mypy` to reduce permission prompts during long Bash-heavy sessions.
- `.claude/settings.local.json` has a stale `chmod +x deploy.sh` entry (deploy.sh was deleted weeks ago); harmless but worth cleaning up.
- Branch is pushed; PR not yet opened. User may want a third Copilot review of the now-larger branch (4 new commits since the last review absorption) before scaling to step 6.
