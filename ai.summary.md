# AI Session Summary

## 2026-05-09 (Saturday — long-arc velocity day, mid-session refresh)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. AI as architectural co-author + continuity engine.
- AI's permitted on-corpus actions are a **closed list** per [ADR 0013](adrs/0013-ai-permitted-actions-boundary.md): mechanical correction, chapter scoring, interview-aligned structural analysis, suggestion-only craft advice. Everything else is barred. **The author is always at the keyboard for creative work.**

**Architecture phase complete.** ADRs 0001–0014 + Spikes 0001–0011 merged on `main`. Don't revisit unless explicitly asked.

**License:** PolyForm Strict 1.0.0 (source-available; commercial use requires separate license from scorellis@gmail.com). Repo public.

**Branch model:** trunk-based. **Smaller-units-per-PR cadence** — every coherent unit of work commits + pushes immediately. Crash recovery has cost cycles before; this pattern is the primary defense.

**Session pacing (per CLAUDE.md):** user decides when to stop. AI does NOT propose stopping points. Pick the next coherent unit and start.

**Author identity:** Scott R. Ellis. (`scorellis` is an abbreviated GitHub handle.)

### Today's arc — 2026-05-09 (8 PRs merged + 8 PRs in flight)

**Already merged earlier today** (#34, #35, #36, #37, #38, #39, #40 + #32, #33 from late last night):
- Spike 0010 (UserWritingPreferencesInterview), Spike 0011 (sync transport + settings cascade), ADR 0013 (AI permitted-actions), ADR 0014 (sync transport + settings cascade)
- Devil's Toolbox / ergodix index / Skill factory-seal parking-lot stories
- Settings cascade scaffolding (defaults.toml + bootstrap.toml + future floaters/)
- `ergodix/sync_transport.py` + B1 conditionality + B2 (`check_corpus_path`)
- Security/0001 (TOCTOU+symlink) + security/0002 (parent-dir mode) patches; CLAUDE.md §3 security cadence

**In-flight PRs from this session** (open, awaiting merge):
- **#41** — CLAUDE.md §Session pacing + ai.summary refresh
- **#42** — C6 `check_credential_prompts` (Anthropic / Google OAuth keyring prompts via configure phase)
- **#43** — E2 persona-tailored "you're done" message (writer / editor / developer / publisher / focus-reader, plus generic)
- **#44** — A5 (Python venv) + A6 (runtime packages) verify-only stubs
- **#45** — `ergodix status` real read-only health check (replaces stub) — surfaces version, sync transport, prereqs, settings, credentials, network
- **#46** — D4 `check_branch_tracking` (verify local main → origin/main, reframed for trunk-based since `develop` was deleted)
- **#47** — D3 `check_dev_dependencies` (verify [dev] extras importable: pytest, ruff, mypy, pytest-cov)
- **#48** — E1 cantilever verify check: `ergodix status` exits 0

### Story 0.11 status (after all 8 in-flight PRs merge)

**16 of 24 prereqs registered (67%).**

Done as prereq modules: A1 platform, A2 homebrew, A3 pandoc, A4 mactex, A5 venv, A6 packages, A7 vscode, B1 drive_desktop, B2 corpus_path, C1 gh_auth, C3 git_config, C4 local_config, C5 credential_store, C6 credential_prompts, D3 dev_dependencies, D4 branch_tracking.

Done as orchestrator-level concerns: F1 connectivity + settings cascade, F2 run-record, E1 verify smoke, E2 done message.

**8 prereqs remaining:** C2 (clone corpus repo), D1 (VS Code auto-sync task), D2 (git hooks for prose linting), D5 (LaunchAgent polling), D6 (editor signing key).

### Permission system note (cleaned up today)

`.claude/settings.json` now allows `git branch -d *` and `git branch -D *` (the latter via explicit user authorization for cleanup). Originally both were in deny; lowercase `-d` is safe (refuses to delete unmerged), uppercase `-D` is force-delete.

Local branches are clean — only `main` remains after today's batch deletion. Remote branches: in-flight PRs preserve theirs; merged ones are mostly cleaned via GitHub UI by the user.

### Next-session candidates

**Quick wins remaining:**
- **D2 stub** — install a no-op pre-commit hook script. Becomes meaningful when the Phil-trained linter lands (Sprint 1+).
- **D1 stub** — install `.vscode/tasks.json` defining `sync-in` / `sync-out` tasks. The CLI commands are stubs today; the tasks file is the persistent setup.

**Mechanical (~60-90 min each):**
- **D6** — editor signing key generation + gh scope refresh + git config for signing. Persona-gated (editor floater) but the orchestrator doesn't yet do persona-aware filtering, so D6's inspect needs a soft "skip if no editor mode" branch.
- **C2** — clone corpus repo. Real design surface (per-opus, existing folder handling).
- **D5** — LaunchAgent polling. Needs `ergodix sync-in` to be real, OR install with a stub program for now.

**Multi-session arcs:**
- **`ergodix migrate --from gdocs`** — Story 0.2's other big task. Highest user-visible value but biggest scope. Spike + ADR first.
- **`ergodix sync-in` / `sync-out`** — unblocks D1, D5; sub-arc of editor collaboration (ADR 0006).

### Open security findings

- [security/0003](security/0003-migrate-skips-type-validation.md) — `cmd_migrate_to_keyring` doesn't validate value types. Low severity, one-line fix queued.

### Important conventions

- **CLAUDE.md §3 — Security review cadence**: event-driven, severity-based remediation.
- **CLAUDE.md — Session pacing**: user decides when to stop.
- **CLAUDE.md principle #2 (refined)** — AI permitted-actions boundary per ADR 0013.

### Tomorrow's first move

Pick from "Next-session candidates." If most of #41–#48 has merged, the registered prereq count is 16 (67%) and cantilever phases A–E + F are functionally complete. Best next arc is probably the migrate spike (sets up the next big user-visible feature) or D6 (completes the editor-floater install path). Quick wins (D2 stub, D1 stub) are also there if a low-energy session calls for momentum.

### File state notes

- `ergodix status` is now a real read-only health check (PR #45) that exposes the full operational picture in one command. E1 (PR #48) ties it to cantilever's verify phase.
- Settings cascade has 3 layers: code defaults → `settings/defaults.toml` → `settings/bootstrap.toml`. `floaters/<name>.toml` deferred until first per-floater consumer.
- Sync transport auto-detects from `CORPUS_FOLDER` location: under `~/My Drive` → drive-mirror; under `~/Library/CloudStorage/GoogleDrive-*` → drive-stream (rejected v1); else → indy. `SYNC_MODE` field deleted from local_config per ADR 0014.
- `_finalize` closure in `run_cantilever` runs F2 (run-record) + E2 (done message) on every return path. F2 is fail-safe; E2 fires on success outcomes only.
