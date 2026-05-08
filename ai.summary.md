# AI Session Summary

## 2026-05-07 (mid-morning checkpoint, pre-PR)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. AI as architectural co-author + continuity engine.
- AI's role is **Architectural Analysis only** — never edits prose chapters; tracks plotlines, flags plot holes, builds summaries/storyboards, supports worldbuilding.

**Architecture phase complete.** ADRs 0001–0011 and Spikes 0001–0008 are merged on `main` (or in flight on `feature/installer-redesign`). Don't revisit unless explicitly asked.

**Locked architectural decisions (read in `adrs/` to fully load context):**

- **ADR 0001** — Click subcommand groups, plugin registries (later collapsed by 0005).
- **ADR 0002** — Two-repo topology (later partly superseded by 0006).
- **ADR 0003** — Cantilever bootstrap orchestrator with 25 operations (later refined by 0010). **Note:** ADR 0003's B2 description still contains a "Tapestry path" pre-pivot leftover; treat the implementation as generic "corpus path" detection. Worth a one-line Note added to ADR 0003 when B2 lands.
- **ADR 0004** — Continuous polling job (every 5 min, persona-aware, no-op when offline).
- **ADR 0005** — All roles as floaters in single registry. `--writer`, `--editor`, `--developer`, `--publisher`, `--focus-reader`. Multi-corpus container named "opus" (plural "opera").
- **ADR 0006** — Editor collaboration via sliced git repositories with baseline-tracked resync.
- **ADR 0007** — Bootstrap scripts (sh + ps1), prereqs as importable Python modules, console-script entry in pyproject.toml.
- **ADR 0008** — `ergodix sync` rename to `sync-out`/`sync-in`; local_config vs settings/* ownership rule; ruff + mypy adopted.
- **ADR 0009** — CI workflow + dependency-pin policy. Locked vs latest two-job CI; uv as lockfile tool; reactive capping pre-Story-0.7, proactive capping post-Story-0.7.
- **ADR 0010** — Pre-flight scan + consent gate + apply + verify four-phase installer model. Replaces `check() -> CheckResult` from ADR 0007 with separate `inspect()` and `apply()` per prereq.
- **ADR 0011** — ASVRAT story format required for persona-driven sprint stories; infrastructure stories may keep SVRAT. Forward-only convention; existing stories not migrated.

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
- **Always ask before pushing to remote** AND **always pair the ask with a brief one- or two-sentence reason** so the user can decide quickly.
- **Self-smoke as Installer persona:** when validating bootstrap/cantilever changes, the AI runs `./bootstrap.sh` directly at `/Users/scorellis/Documents/Scorellient/Applications/ErgodixDocs/` (re-cloning fresh) and reads the output, instead of asking the user to run-and-paste.

**Where work paused (2026-05-07 mid-morning, pre-PR):**

- On branch `feature/installer-redesign`. **Story 0.11 phase 1 complete and Copilot-reviewed clean — recommended for PR + merge.**
- **17 commits pushed to origin** (yesterday's 11 + today's 6).
- Today's commits:
  - **ADR 0011 + CLAUDE.md** — ASVRAT story-format convention.
  - **C4 prereq** (`check_local_config`) — bootstraps `local_config.py` from `local_config.example.py`, mode 0o600, preserves existing.
  - **Cantilever inspect-failed UX** — emits which prereqs failed before halting; previously silent.
  - **Cantilever consent-prompt UX** — `print()` after `input()` so consent prompt is visible when stdin is piped (user-reported "I never saw the consent prompt").
  - **`local_config.example.py` genericized** — removed pre-pivot "Tapestry of the Mind" hardcode; placeholder is now `<YOUR-CORPUS-FOLDER>` with a "REQUIRED EDIT" comment block.
  - **Permissions overhaul** — `.claude/settings.json` now uses category-level allowlist (venv tooling, routine git, file ops, bootstrap, pip install) + explicit deny list (sudo, force-push, hard-reset, branch -D, system installs, pipe-to-shell, raw-disk ops). PreToolUse hook (`.claude/hooks/log-bash.sh`) appends every Bash command to `ai.bashcommands.log` (gitignored) for local backtrack.
  - **C5 prereq** (`check_credential_store`) — ensures `~/.config/ergodix/` exists at mode 0o700; three inspect outcomes (ok / needs-update / needs-install). Idempotent.
- **Tests: 158 passing, 1 skipped. Coverage 80%. ruff + mypy strict clean.**
- **Self-smoke at `/Users/scorellis/Documents/Scorellient/Applications/ErgodixDocs/` (re-cloned fresh, 3 times today):** all green. Plan correctly contains C4 only; C5 reports `ok` since `~/.config/ergodix/` already lives at 0o700 from prior dev work — validates idempotency end-to-end on a real machine.
- **Copilot review of `feature/installer-redesign` (Haiku 4.5):** zero blockers, recommends PR. The one specific finding (check_platform coverage gap, lines 30–38) was a stale read; current state is 100% / 0 misses. Pattern is locked for cookie-cutting more prereqs.

**Story 0.11 status:**
- Phase 1 (cantilever foundation + first 3 prereqs + UX + permissions): **DONE**, awaiting PR.
- Phase 2 (next 22 prereqs): pending. A `Plan` subagent ran 2026-05-07 to group remaining ops by complexity tier and propose a next-3 ordering — see [SprintLog Story 0.11](SprintLog.md) for the Plan output, when copied in.

**Parking lot accumulated 2026-05-07 (no fix-now action):**
- `_verify_local_config_sane` silently passes the `<YOUR-CORPUS-FOLDER>` placeholder — should detect bracket-style placeholders and flag.
- ADR 0003's B2 description has stale "Tapestry path" wording — fix when implementing B2.
- Cantilever output is silent on `ok` inspect results — could show "N ops checked, K need action" summary line.
- Tool rename idea: "Tapestry" or "Tapiz" — long-term parking lot.
- `bootstrap.ps1` (Windows sibling of bootstrap.sh) — deferred per Story 0.11 task list.

**Next-session opening move:**

1. If the PR has not been opened: open it. Branch is fully validated and reviewed. Description should reference (a) what phase 1 delivers, (b) the parking-lot items above, (c) the Plan-subagent's phase-2 ordering.
2. If the PR has been opened and reviewed: absorb findings, merge, then start phase 2 from a fresh branch off `main`.
3. If phase 2 is already in flight: skip resume prompt and continue from the current todo list.

Important context:
- `.claude/settings.json` now permissive for routine commands; deny list catches the dangerous shapes; `git push *` stays in the prompt zone per "always ask before pushing."
- `.claude/hooks/log-bash.sh` is active — every Bash command Claude runs lands in `ai.bashcommands.log` (gitignored) with a UTC timestamp.
- `.claude/settings.local.json` still has a stale `chmod +x deploy.sh` entry (deploy.sh was deleted weeks ago); harmless but worth cleaning up at some idle moment.
- Test deploy directory backups (`ErgodixDocs.bak-2026-05-06`, `ErgodixDocs.bak-2026-05-07-pre-fixes`, `ErgodixDocs.bak-2026-05-07-pre-c5`) live alongside the active install at `/Users/scorellis/Documents/Scorellient/Applications/`. User can clean up when ready.
