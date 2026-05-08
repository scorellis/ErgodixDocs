# AI Session Summary

## 2026-05-07 (end-of-day-marathon — long crazy night)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. AI as architectural co-author + continuity engine.
- AI's role is **Architectural Analysis only** — never edits prose chapters; tracks plotlines, flags plot holes, builds summaries/storyboards, supports worldbuilding.

**Architecture phase complete.** ADRs 0001–0012 + Spikes 0001–0009 merged on `main`. Don't revisit unless explicitly asked.

**Locked architectural decisions** (read in `adrs/` to fully load context):

- **ADR 0001** — Click subcommand groups, plugin registries (later collapsed by 0005).
- **ADR 0002** — Two-repo topology (later partly superseded by 0006).
- **ADR 0003** — Cantilever bootstrap orchestrator with 25 ops (later refined by 0010 + 0012).
- **ADR 0004** — Continuous polling job.
- **ADR 0005** — All roles as floaters; opus naming.
- **ADR 0006** — Editor collaboration via sliced git repositories.
- **ADR 0007** — Bootstrap scripts; prereqs as Python modules; console-script entry.
- **ADR 0008** — sync rename; local_config vs settings/* ownership; ruff + mypy.
- **ADR 0009** — CI workflow + dependency-pin policy.
- **ADR 0010** — Pre-flight scan + consent gate + apply + verify (4-phase, partially superseded by 0012's 5-phase).
- **ADR 0011** — ASVRAT story format for persona-driven stories; SVRAT OK for infrastructure.
- **ADR 0012** — Phase-2 patterns: **5-phase orchestrator** (inspect → plan + consent → apply → **configure** → verify); `needs-interactive` InspectStatus; F1 reframed as orchestrator code (not a prereq); A4 MacTeX hard-coded `full` for v1; D6 signing-key scope refresh on demand; sudo-cache trust assumption.

**Branch model**: trunk-based.

**Format decisions (Story 0.2, locked):**
- Pandoc Markdown + raw LaTeX passthrough; `.md` with mandatory YAML frontmatter (`format: pandoc-markdown`).
- One `.md` per Chapter.
- LaTeX preamble cascade: optional `_preamble.tex` at every folder level; **render walks up most-general-first** and concatenates via `--include-in-header` flags.
- Render pipeline: Pandoc → XeLaTeX → PDF.

**Pacing**: ~1 year of solo `--writer --developer` use before inviting other authors.

**Working partnership norms** (in CLAUDE.md):
- Push back on principle violations.
- Late-arriving principles apply forward.
- Course corrections cost cycles but are healthy.
- Persistent record (CLAUDE.md, ADRs, spikes, WorkingContext, ai.summary) carries partnership across sessions.
- **Always ask before pushing to remote**, paired with a brief reason.
- **Self-smoke as Installer persona** — run `./bootstrap.sh` directly at `~/Documents/Scorellient/Applications/ErgodixDocs/`, don't delegate.

**Where work paused (2026-05-07 end of marathon):**

Today's session shipped a *lot*. Twelve PRs merged (or about to merge). On `main` now:

- **Cantilever orchestrator (5-phase)** with sudo grouping, abort-fast, op_id-uniqueness, inspect-failed UX, configure phase, verify-on-no-changes.
- **8 prereqs landed on main**: A1 (platform), C3 (git config — first interactive), C4 (local_config), C5 (credential dir), C1 (gh auth). **Plus** A2 (Homebrew), A3 (Pandoc), B1 (Drive Desktop) — but those three are sitting in **PR #21 awaiting merge** (rescue PR; see below).
- **F1 reframed** as orchestrator code: `ergodix/connectivity.py` (real TCP probe), `ergodix/settings.py` (BootstrapSettings loader from `settings/bootstrap.toml`).
- **`ergodix render`** — first user-facing feature command (Story 0.2's render pipeline).
- **`bootstrap.sh`** — minimal Python-detect / venv / `pip install -e ".[dev]"` / `ergodix cantilever`.
- **Permissions/hooks overhaul** — broad allowlist + targeted deny + PreToolUse bash audit (`ai.bashcommands.log`).
- **ADR 0011 + 0012**, **Spike 0009**.
- **Plot-Planner + Sell-My-Book** parking-lot stories (future feature suites).
- **Tests: 265 passing on the rescue branch (PR #21)** — will be 265 on main once #21 merges. ruff + mypy strict clean.

**🚨 IMPORTANT — open at session end:**

- **PR #21 — "Rescue: A2 + A3 + B1 prereqs"** is open and MERGEABLE. Stacked-PR cascade didn't auto-retarget after #11 merged; PRs #17/#18/#19 ended up merging into their stale feature-branch bases instead of main. Cherry-picked the three commits onto `feature/rescue-a2-a3-b1` from current main. Tests/lint/mypy clean. **Tomorrow's first move: merge PR #21**. After that, main has the full 8-prereq + render + orchestrator state.
- **Lesson learned for stacked PRs**: merge bottom-up, *one at a time*, waiting for each to land on main before merging the next. GitHub auto-retargets the next-up PR's base when its predecessor lands. Doing them all at once with stacked bases skips main and lands them in stale branches.

**Story 0.11 status:**
- 8 prereqs done (A1, A2, A3, B1, C1, C3, C4, C5) once #21 merges.
- F1 reframed.
- **16 prereqs remaining**: A4 (MacTeX), A5 (Python verify), A6 (pip dev deps), A7 (VS Code + extensions), B2 (Drive mount detect), C2 (clone corpus), C6 (credential prompts), D1–D6 (persona-gated), E1 / E2 (verify exit), F2 (run-record).

**Next-session candidates** (in rough value order):

1. **Merge PR #21** (rescue) — first thing.
2. **A4 (MacTeX)** — installs XeLaTeX. First consumer of `settings.mactex_install_size` (default `"full"`). The moment A4 + render are both on main, `ergodix render <chapter>` produces a real PDF on a fresh machine.
3. **`ergodix migrate --from gdocs`** — Story 0.2's other big task. Walks `~/My Drive/Tapestry of the Mind/` (or whatever `local_config.CORPUS_FOLDER` points to), exports `.gdoc` → `.md` with frontmatter prepended, archives the originals to `_archive/`. Turns the existing corpus editable in VS Code.
4. **More installer prereqs** — A5/A6 (verify-only, quick), A7 (VS Code + extensions), B2 (Drive mount detection — closes the configure-loop with `local_config.py` placeholder substitution), C2 (clone corpus), C6 (credential prompts via configure phase like C3), D-tier (persona-gated, lower priority until other authors arrive).

**Important context:**

- `.claude/settings.json` has broad allowlist + deny list (force-push, hard-reset, branch -D, sudo, system installs, pipe-to-shell, raw-disk ops). `git push *` stays in the prompt zone per CLAUDE.md.
- `.claude/hooks/log-bash.sh` PreToolUse hook → `ai.bashcommands.log` (gitignored).
- `local_config.example.py` was genericized today (Tapestry leak removed, `<YOUR-CORPUS-FOLDER>` placeholder).
- ADR 0003 has Notes added: F1 reframed (24 prereqs not 25); B2's "Tapestry path" wording flagged.
- ADR 0006 has a Note: editor signing-key scope refresh on demand via configure phase.
- ADR 0010 has a Note: 5-phase via ADR 0012; sudo-cache assumption.
- `local_config_sane` verify check still passes the `<YOUR-CORPUS-FOLDER>` placeholder silently — should detect bracket-style placeholders and flag (parking lot).
- `bootstrap.ps1` (Windows) deferred.
- The dev venv has a known editable-install quirk where `import ergodix` fails from outside the repo root (the .pth file isn't always processed). `pip install -e ".[dev]"` rerun fixes it. Doesn't affect production users (their venv is fresh).

**Tomorrow's first move:**

1. Merge PR #21 (rescue A2/A3/B1).
2. Pull latest main locally.
3. Pick from "Next-session candidates" — A4 likely highest value (unlocks `ergodix render` end-to-end on fresh machines).
4. Branch off the previous PR going forward (stacking) **but merge bottom-up one at a time** to avoid the trap PR #21 just rescued.
