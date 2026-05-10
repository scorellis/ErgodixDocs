# AI Session Summary

## 2026-05-09 (Saturday — long-arc velocity day, late-evening checkpoint)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. AI as architectural co-author + continuity engine.
- AI's permitted on-corpus actions are a **closed list** per [ADR 0013](adrs/0013-ai-permitted-actions-boundary.md): mechanical correction, chapter scoring, interview-aligned structural analysis, suggestion-only craft advice. Everything else is barred. **The author is always at the keyboard for creative work.**

**Architecture phase complete.** ADRs 0001–0014 + Spikes 0001–0011 merged on `main`. Don't revisit unless explicitly asked.

**License:** PolyForm Strict 1.0.0 (source-available; commercial use requires separate license from scorellis@gmail.com). Repo public.

**Branch model:** trunk-based.

**Cadence rules (CLAUDE.md):**
- **Smaller-units-per-PR** — every coherent unit ships immediately for crash recovery.
- **Pause-after-each-PR** (added 2026-05-09 after a conflict cascade) — ship one PR, post the summary, stop. User merging or saying "next" is the continuation signal.
- **Session pacing** — user decides when to stop. AI never proposes stopping points.

**Author identity:** Scott R. Ellis. (`scorellis` is an abbreviated GitHub handle.)

### Today's arc — 2026-05-09 (18 PRs merged in one day)

By topic:
- **Architecture / docs**: Spike 0010 (UserWritingPreferencesInterview), Spike 0011 (sync transport + settings cascade), ADR 0013 (AI permitted-actions), ADR 0014 (sync transport + settings cascade), three new parking-lot stories (Devil's Toolbox, ergodix index, Skill factory-seal), CLAUDE.md additions (§Security review cadence, §Session pacing including pause-after-PR rule).
- **Implementation — sync transport arc**: settings cascade scaffolding (defaults.toml + bootstrap.toml + future floaters/), `ergodix/sync_transport.py`, B1 conditional on indy mode, B2 corpus-path validation.
- **Implementation — verify + status arc**: A5 (Python venv) + A6 (runtime packages) verify stubs, `ergodix status` real CLI command, E1 cantilever verify check (status exits 0), E2 persona-tailored "you're done" message.
- **Implementation — D-tier**: C6 credential prompts (configure phase), D3 dev dependencies, D4 branch tracking, D6 editor signing key (verify-only).
- **Security**: 0001 (TOCTOU+symlink) patched late last night; 0002 (parent-dir mode) + 0003 (migrate type validation) patched this morning. **Open security findings: 0.**
- **Settings**: `.claude/settings.json` cleanup — `git branch -d/-D *` allowed for routine cleanup.

### Story 0.11 status

**19 of 24 prereqs registered (79%).**

Done as prereq modules: A1 platform, A2 homebrew, A3 pandoc, A4 mactex, A5 venv, A6 packages, A7 vscode, B1 drive_desktop, B2 corpus_path, C1 gh_auth, C3 git_config, C4 local_config, C5 credential_store, C6 credential_prompts, D3 dev_dependencies, D4 branch_tracking, D6 editor_signing_key.

Done as orchestrator-level concerns: F1 connectivity + settings cascade, F2 run-record, E1 verify smoke, E2 done message.

**5 prereqs remaining:**
- **C2** (clone corpus repo) — design surface: needs CORPUS_REPO_URL field in local_config; per-opus considerations; existing-clone handling.
- **D1** (VS Code auto-sync task) — depends on `ergodix sync-in/-out` being real (currently stubs); editor-floater concern, persona-gating issue same as D6.
- **D2** (git hooks for prose linting) — depends on Phil-trained prose linter (parking-lot).
- **D5** (LaunchAgent polling) — depends on `ergodix sync-in` being real (currently stub).

### Cantilever phases A–F

- **Phase A (system tools)**: A1–A7 all done.
- **Phase B (Drive/corpus)**: B1 done conditional, B2 done.
- **Phase C (auth/repo scaffolding)**: C1, C3, C4, C5, C6 done. C2 remaining.
- **Phase D (persona extras)**: D3, D4, D6 done (verify-only). D1, D2, D5 pending (each has dependency blockers).
- **Phase E (verify + done)**: E1 + E2 both wired.
- **Phase F (orchestrator-level)**: F1 (connectivity + settings), F2 (run-record) both done.

### Open security findings

**0.** All three (0001, 0002, 0003) closed via the CLAUDE.md §3 security review cadence within 24 hours each.

### Permission system / settings state

`.claude/settings.json` allows `git branch -d/-D *` for routine cleanup. Other destructive variants (force push, reset --hard, filter-branch, etc.) remain denied.

### Next-session candidates

**Multi-session arcs (highest user-visible value):**
- **`ergodix migrate --from gdocs`** — Story 0.2's other big task. Walks corpus folder, exports `.gdoc` → `.md`, archives originals. Needs spike + ADR first (Drive/Docs API mapping, hierarchy detection, idempotency). Highest leverage but biggest scope.
- **`ergodix sync-in` / `sync-out`** — implements the polling cycle from ADR 0004. Unblocks D1 + D5. Sub-arc of editor collaboration.
- **`ergodix editor init`** — explicit command to drive the full D6 install flow (keygen + gh scope refresh + register + git config).
- **`ergodix opus init`** — command to bootstrap a new corpus folder + initialize the per-opus repo. Unblocks C2.

**Mechanical (~30-60 min each):**
- **C2** — clone corpus repo. Adds CORPUS_REPO_URL to local_config; clones if absent.
- **D1 / D2 / D5 stubs** — each as verify-only checks that detect state and stay informational. Same pattern as D4 / D6.

**Cleanup:**
- **`BootstrapSettings` / `load_bootstrap_settings` rename** — names are misleading post-ADR-0014. Sweeping diff but pure cleanup.

### Tomorrow's first move

Pick from "Next-session candidates." Most user-visible: migrate spike (sets up the next big arc). Most completion-driven: knock out C2 + D1/D2/D5 stubs to hit 24/24 prereq coverage. Cleanest pure-cleanup: BootstrapSettings rename.

### File state notes

- `ergodix status` is a real read-only health check. Run it any time to see the full operational picture.
- Settings cascade has 3 layers: code defaults → `settings/defaults.toml` → `settings/bootstrap.toml`. `floaters/<name>.toml` deferred until first per-floater consumer.
- Sync transport auto-detects from `CORPUS_FOLDER` location. `SYNC_MODE` field deleted from local_config per ADR 0014.
- `_finalize` closure in `run_cantilever` runs F2 (run-record) + E2 (done message) on every return path. F2 is fail-safe; E2 fires on success outcomes only.
- Cantilever's verify phase now runs `ergodix status` as the end-to-end smoke (E1).
