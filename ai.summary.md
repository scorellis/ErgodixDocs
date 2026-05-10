# AI Session Summary

## 2026-05-09 (Saturday — Story 0.11 closed at 100%)

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

### Story 0.11 status — **CLOSED at 100% on 2026-05-09**

**24 of 24 prereqs registered.** All ADR 0003 prereq ops (A1–A7, B1–B2, C1–C6, D1–D6, E1–E2, F1–F2) have homes in the codebase. Cantilever's five phases per ADR 0012 (inspect → plan + consent → apply → configure → verify) are functionally complete.

**Real install actions** (mutative apply): A1 platform, A2 homebrew, A3 pandoc, A4 mactex, A7 vscode, B1 drive_desktop, C1 gh_auth, C3 git_config (configure phase), C4 local_config, C5 credential_store, C6 credential_prompts (configure phase).

**Verify-only stubs** (apply is no-op; full install defers to follow-on commands): A5 venv, A6 packages, B2 corpus_path, C2 corpus_clone, D1 vscode_task, D2 prose_linter_hook, D3 dev_dependencies, D4 branch_tracking, D5 launchagent_poller, D6 editor_signing_key.

**Orchestrator-level concerns**: F1 connectivity + settings cascade, F2 run-record (JSONL append), E1 verify smoke (`ergodix status` exits 0), E2 persona-tailored done message.

**Follow-on commands implied by stub deferrals** (for future stories):
- `ergodix opus clone` (drives C2's full install)
- `ergodix opus init` (creates a fresh corpus folder + repo)
- `ergodix vscode init` (drives D1)
- `ergodix lint init` (drives D2 once Phil-trained linter ships)
- `ergodix poller init` (drives D5 once `ergodix sync-in` is real)
- `ergodix editor init` (drives D6's full keygen + gh scope refresh + git config flow)
- `ergodix sync-in` / `ergodix sync-out` (real implementations; currently CLI stubs)

### Cantilever phases A–F (all complete)

- **Phase A (system tools)**: A1–A7 all registered.
- **Phase B (Drive/corpus)**: B1 conditional on indy mode, B2 dispatches on detected sync transport.
- **Phase C (auth/repo scaffolding)**: C1–C6 all registered.
- **Phase D (persona extras)**: D1–D6 all registered (D3 has real apply; rest are verify-only stubs deferring to follow-on commands).
- **Phase E (verify + done)**: E1 (verify smoke = `ergodix status` exits 0) + E2 (persona-tailored done message).
- **Phase F (orchestrator-level)**: F1 connectivity + settings, F2 run-record.

### Open security findings

**0.** All three (0001, 0002, 0003) closed via the CLAUDE.md §3 security review cadence within 24 hours each.

### Permission system / settings state

`.claude/settings.json` allows `git branch -d/-D *` for routine cleanup. Other destructive variants (force push, reset --hard, filter-branch, etc.) remain denied.

### Next-session candidates

Story 0.11 is closed. The next arcs are the user-facing features that turn cantilever into a working tool.

**Highest user-visible leverage:**
- **`ergodix migrate --from gdocs`** — Story 0.2's other big task. Walks corpus folder, exports `.gdoc` → `.md`, archives originals. Needs spike + ADR first (Drive/Docs API mapping, hierarchy detection, idempotency). Without migrate, the user can't get their actual prose into the system.
- **`ergodix sync-in` / `sync-out`** — implements the polling cycle from ADR 0004 + the editor-collaboration round-trip from ADR 0006. Unblocks D1 + D5's full install flows.

**Stub-driven follow-on commands** (one per stub deferral — each turns a verify-only stub into a real install action):
- `ergodix opus clone` (drives C2)
- `ergodix opus init` (creates a fresh corpus folder + repo)
- `ergodix vscode init` (drives D1)
- `ergodix poller init` (drives D5; depends on `sync-in` real)
- `ergodix editor init` (drives D6)
- `ergodix lint init` (drives D2; depends on Phil-trained linter)

**Cleanup:**
- **`BootstrapSettings` / `load_bootstrap_settings` rename** — names are misleading post-ADR-0014. Sweeping diff but pure cleanup.
- **ADR 0003 D4 wording fix** — "develop branch tracking" predates the trunk-based decision; D4 is now main-branch-tracking. Already documented in the prereq module's docstring; could land as a Note on the ADR.

### Tomorrow's first move

Story 0.11's close-out is the natural punctuation mark. The next big arc is **`ergodix migrate --from gdocs`** — set up the spike + ADR first since the design surface is real (which Drive/Docs APIs to use, which auth flow, how to handle the .gdoc → markdown conversion, idempotency, archive layout). Implementation follows in subsequent PRs.

### File state notes

- `ergodix status` is a real read-only health check. Run it any time to see the full operational picture.
- Settings cascade has 3 layers: code defaults → `settings/defaults.toml` → `settings/bootstrap.toml`. `floaters/<name>.toml` deferred until first per-floater consumer.
- Sync transport auto-detects from `CORPUS_FOLDER` location. `SYNC_MODE` field deleted from local_config per ADR 0014.
- `_finalize` closure in `run_cantilever` runs F2 (run-record) + E2 (done message) on every return path. F2 is fail-safe; E2 fires on success outcomes only.
- Cantilever's verify phase now runs `ergodix status` as the end-to-end smoke (E1).
