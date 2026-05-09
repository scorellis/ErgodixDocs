# AI Session Summary

## 2026-05-08 (end-of-day — late session continued from 2026-05-07 marathon)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. AI as architectural co-author + continuity engine.
- AI's role is **Architectural Analysis only** — never edits prose chapters; tracks plotlines, flags plot holes, builds summaries/storyboards, supports worldbuilding.

**Architecture phase complete.** ADRs 0001–0012 + Spikes 0001–0009 merged on `main`. Don't revisit unless explicitly asked.

**Locked architectural decisions** (read in `adrs/` to fully load context):

- **ADR 0001** — Click subcommand groups, plugin registries (later collapsed by 0005).
- **ADR 0002** — Two-repo topology (later partly superseded by 0006).
- **ADR 0003** — Cantilever bootstrap orchestrator with 24 prereq ops (after F1 reframe).
- **ADR 0004** — Continuous polling job.
- **ADR 0005** — All roles as floaters; opus naming.
- **ADR 0006** — Editor collaboration via sliced git repositories.
- **ADR 0007** — Bootstrap scripts; prereqs as Python modules; console-script entry.
- **ADR 0008** — sync rename; local_config vs settings/* ownership; ruff + mypy.
- **ADR 0009** — CI workflow + dependency-pin policy.
- **ADR 0010** — 4-phase model, partly superseded by 0012.
- **ADR 0011** — ASVRAT story format for persona-driven stories; SVRAT OK for infrastructure.
- **ADR 0012** — 5-phase orchestrator (inspect → plan + consent → apply → **configure** → verify); `needs-interactive` InspectStatus; F1 reframed.

**License:** PolyForm Strict 1.0.0 (source-available, commercial use requires separate written license). Repo is public; non-commercial use OK; any commercial use requires a license from scorellis@gmail.com.

**Branch model**: trunk-based. Feature branches off main. Each PR independent unless explicitly stacked.

**Format decisions (Story 0.2, locked):**
- Pandoc Markdown + raw LaTeX passthrough; `.md` with mandatory YAML frontmatter (`format: pandoc-markdown`).
- One `.md` per Chapter.
- LaTeX preamble cascade: optional `_preamble.tex` at every folder level; render walks up most-general-first.
- Render pipeline: Pandoc → XeLaTeX → PDF.
- Showcase fixture lives at `examples/showcase/` — exercises footnotes, sidebar (tcolorbox), rotation, mirror, spiral, vector figure.

**Pacing**: ~1 year of solo `--writer --developer` use before inviting other authors.

**Working partnership norms** (in CLAUDE.md):
- Push back on principle violations.
- Late-arriving principles apply forward.
- Course corrections cost cycles but are healthy.
- Persistent record (CLAUDE.md, ADRs, spikes, WorkingContext, ai.summary) carries partnership across sessions.
- **Always ask before pushing to remote** in normal sessions; in auto-mode, push freely but explain the why.
- **Self-smoke as Installer persona** — when a smoke is needed, run it ourselves rather than delegating.

### Where work paused (end of 2026-05-08)

**Two PRs open and awaiting merge** (independent, mergeable in either order):

- **PR #28** — `feature/a7-check-vscode` — A7 prereq (VS Code + 3 extensions: markdown-preview-enhanced, ltex, criticmarkup). Cookie-cutter on the check_pandoc/check_mactex pattern, with an app-bundle fallback resolver so a fresh cask install works without PATH refresh. 14 new tests.
- **PR #29** — `feature/f2-run-record` — F2 from ADR 0003 §164: append one JSONL record per cantilever run to `~/.config/ergodix/cantilever.log`. Like F1, lives in orchestrator code (not a prereq module). Two-layer fail-safe so a write failure can never crash cantilever. 14 new tests.

Both branched off main, both have full quality gates green (296 tests pass, ruff + mypy clean).

**Tomorrow's first move:** merge #28 and #29 in either order. Then continue forward.

### Story 0.11 status

**~46% complete** after #28 + #29 merge: **11 of 24 prereqs registered.**

Done (registered as modules): A1 platform, A2 homebrew, A3 pandoc, A4 mactex, A7 vscode (#28), B1 drive_desktop, C1 gh_auth, C3 git_config, C4 local_config, C5 credential_store. Plus orchestrator-level: F1 (connectivity + settings), F2 (run-record, #29).

**13 prereqs remaining**: A5 / A6 (Python venv + packages — already done by bootstrap.sh, just need verify-only stubs), B2 (Drive mount detection + corpus path), C2 (clone corpus repo), C6 (credential prompts), D1–D6 (persona-gated extras), E1 (`ergodix status` verify — depends on `ergodix status` being built), E2 (persona-tailored "you're done" message — pure read-only).

### Other state on main

- `ergodix render` works end-to-end (Pandoc → XeLaTeX → PDF with preamble cascade).
- `examples/showcase/showcase.md` is the regression-lock fixture — render produces a 58KB PDF with sidebar, footnotes, rotated/mirrored text, spiral, vector hierarchy diagram.
- `bootstrap.sh` uses **non-editable install** (`pip install ".[dev]"`, no `-e`) to dodge a Python 3.13 + setuptools editable-install regression where the .pth-based finder silently fails. Devs who want editable mode can `pip install -e .` manually after bootstrap.
- `ergodix/version.py` uses three-tier resolution: `importlib.metadata.version("ergodix")` → VERSION file → `0.0.0+unknown`. Works for both editable and non-editable installs.
- `_verify_local_config_sane` rejects unedited `<…>` placeholder paths (PR #27, merged 2026-05-08) so first installs see a clear "edit local_config.py" remediation instead of misleading green.
- `*.pdf` is gitignored — render artifacts stay out of git.

### PRs merged in this session (2026-05-08)

- **#22** — A4 check_mactex (first settings consumer)
- **#23** — License switch to PolyForm Strict 1.0.0 + 3 parking-lot stories
- **#24** — bootstrap.sh editable_mode=compat (later superseded by #25)
- **#25** — bootstrap.sh non-editable install + version.py three-tier fix
- **#26** — examples/showcase/ render-pipeline smoke fixture
- **#27** — verify rejects local_config.py with `<…>` placeholder

### Next-session candidates (in rough value order)

1. **Merge #28 (A7) and #29 (F2)** — first move.
2. **E2** — print persona-tailored "you're done" message at end of cantilever run. Pure read-only output. Fastest win (~20 min).
3. **A5 / A6** — Python venv + packages verify-only stubs. Bootstrap already does the work; these just register an `inspect()` that reports `ok` so cantilever's coverage is complete. ~30 min each.
4. **B2** — Drive mount mode + corpus-path detection. Bigger design surface (Mirror vs Stream, prompt for corpus folder name via configure phase). Closes the loop on the local_config.py placeholder problem at the install level rather than just the verify level. ~60 min.
5. **`ergodix migrate --from gdocs`** — Story 0.2's other big task. Walks `local_config.CORPUS_FOLDER`, exports `.gdoc` → `.md` with frontmatter, archives originals to `_archive/`. Multi-session story; needs design first. **Highest user-visible value** but biggest scope.
6. **C6** — credential prompts via configure phase (similar pattern to C3 git_config). Mechanical.
7. **D-tier** — persona-gated extras. Lower priority until other authors arrive.

### Important context

- `.claude/settings.json` has broad allowlist + deny list. `git push *` stays in the prompt zone in normal sessions (auto-mode treats it as approved).
- `.claude/hooks/log-bash.sh` PreToolUse hook → `ai.bashcommands.log` (gitignored).
- `bootstrap.ps1` (Windows) deferred — no Windows users yet.
- E1 has a hidden dependency: it would verify `ergodix status` returns clean, but `ergodix status` doesn't exist yet. Build that subcommand first.
- Parking-lot stories (in SprintLog.md): Plot-Planner, Sell-My-Book, IP-strategy, Continuity-Engine, MCP-server-with-AI-user-persona, in-app editor with BYO-key.
- The local feature branches `feature/showcase-chapter`, `feature/bootstrap-non-editable`, `feature/verify-placeholder-detection`, `feature/a7-check-vscode`, `feature/f2-run-record` exist locally even after their PRs land — user denied a `git branch -d` cleanup. Leave them.
