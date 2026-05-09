# AI Session Summary

## 2026-05-09 (Saturday — long-arc velocity day)

### Prompt To Resume Conversation

You are an AI in the ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- ErgodixDocs is a tool for any author who writes Ergodic-text fiction. AI as architectural co-author + continuity engine.
- AI's permitted on-corpus actions are now a **closed list** per [ADR 0013](adrs/0013-ai-permitted-actions-boundary.md): mechanical correction (punctuation/spelling), chapter scoring, interview-aligned structural analysis, suggestion-only craft advice. Everything else is barred. **The author is always at the keyboard for creative work.**

**Architecture phase complete.** ADRs 0001–0014 + Spikes 0001–0011 merged on `main`. Don't revisit unless explicitly asked.

**License:** PolyForm Strict 1.0.0 (source-available; commercial use requires separate license from scorellis@gmail.com). Repo public.

**Branch model:** trunk-based. Smaller-units-per-PR cadence — every coherent unit of work commits + pushes immediately, before drafting the next thing. Crash recovery has cost cycles before, this pattern is the primary defense.

**Author identity:** Scott R. Ellis. (`scorellis` is an abbreviated GitHub handle, not a contraction of his surname.)

### Today's arc — 2026-05-09

**10 PRs merged today.** Massive sync-transport + AI-boundary + security arc.

Architecture / docs:
- **Spike 0010** — UserWritingPreferencesInterview: design surface for the onboarding interview (six open questions; resolution deferred until first consumer activates).
- **Spike 0011** — sync transport auto-detect + settings cascade.
- **ADR 0013** — AI permitted-actions boundary. Locks the closed list of four on-corpus AI actions; replaces the older blanket "AI never edits prose" rule. CLAUDE.md principle #2 now points at this ADR.
- **ADR 0014** — sync transport auto-detect + settings cascade. Drops `SYNC_MODE` field from `local_config.example.py` in favor of auto-detection. Indy mode = first-class peer of drive-mirror in v1. Drive-stream rejected with "switch to Mirror" remediation. Three-tier settings cascade: `defaults.toml` (SWAG layer) + `bootstrap.toml` (installer-only) + `floaters/<name>.toml` (deferred).
- **Three new parking-lot stories**:
  - **Devil's Toolbox** — foundational rhetoric reference Skill (rhetorical devices, fallacies, narrative primitives) that informs Plot-Planner stylistic-feedback tools by id reference.
  - **`ergodix index` + `_AI/ergodix.map`** — corpus content index (per-file SHA-256 + size + mtime) for incremental analysis. Lands soon, after enough prereqs to support it.
  - **Skill factory-seal protection** — cryptographic protection for proprietary Skills (signed manifests, monthly key rotation, runtime tamper detection, change-via-repo-comment workflow).
- **Security #0001 patched** (PR #32, last night) — TOCTOU + symlink protection in `_read_file_data_checked` via `O_NOFOLLOW + fstat`. `SECURITY.md` + `security/` records folder + cadence in CLAUDE.md §3 established.
- **Security #0002 patched** (PR #33) — parent-dir mode 0700 enforced at read time on `~/.config/ergodix/`.

Implementation:
- **Settings cascade scaffolding** (PR #38) — loader extension reading `defaults.toml` then `bootstrap.toml` cascade-style.
- **`ergodix/sync_transport.py`** (PR #39) — `detect_sync_transport(path)`, `read_corpus_folder_from_local_config()`, `detect_current_sync_transport()`. Path-structure based, no existence requirement.
- **B1 conditionality** (PR #39) — `check_drive_desktop` short-circuits to `ok` under indy mode. User-visible: indy users no longer see Drive Desktop in their cantilever plan.
- **B2 implementation** (PR #40) — new `check_corpus_path` prereq. Validates corpus folder + dispatches on detected mode. Refines ADR 0014 §6: missing config → ok-deferred (so C4 can run on fresh install) instead of failed.

### Story 0.11 status

**12 of 24 prereqs registered (50%).** A1, A2, A3, A4, A7, B1, B2, C1, C3, C4, C5 + orchestrator-level F1, F2.

**12 prereqs remaining**: A5 (Python venv verify), A6 (Python packages verify), C2 (clone corpus repo), C6 (credential prompts via configure phase), D1–D6 (persona-gated extras), E1 (`ergodix status` smoke), E2 (persona-tailored "you're done" message).

### Next-session candidates

**Quick wins (~30 min each):**
- **A5/A6** — Python venv + packages verify-only stubs. Bootstrap already does the work; these just register inspect() returning `ok`.
- **E2** — persona-tailored "you're done" message at end of cantilever run.

**Mechanical (~60 min each):**
- **C6** — credential prompts via configure phase. Same pattern as C3 git_config. Multi-step keyring prompts for missing API keys.

**Substantive (multi-hour):**
- **C2** — clone corpus repo. Real design surface (per-opus, signed clones, edge cases for existing folders).
- **`ergodix migrate --from gdocs`** — Story 0.2's other big task. Highest user-visible value but biggest scope. Spike + ADR first.

### Open security findings

- [security/0003](security/0003-migrate-skips-type-validation.md) — `cmd_migrate_to_keyring` doesn't validate value types. Low severity, one-line fix queued.

### Important conventions (ratified today)

- **CLAUDE.md §3 — Security review cadence**: event-driven reviews triggered by story completions in security-sensitive code, new external surfaces, version bumps. Severity-based remediation: critical/high patched immediately, medium queued in SprintLog, low/info filed.
- **CLAUDE.md — Session pacing**: user decides when to stop. AI does NOT propose stopping points, wrap-ups, or breaks. Pick the next coherent unit and start. Crash recovery via per-unit commits + pushes + ai.summary.md updates at meaningful checkpoints.
- **CLAUDE.md principle #2 (refined)** — AI permitted-actions boundary per ADR 0013, replacing the older blanket "AI never edits prose."

### Permission system note

`.claude/settings.json` cleaned up today: `Bash(git branch -d *)` and `Bash(git branch -D *)` are now in allow (was blocked by deny). Lowercase `-d` is safe (refuses to delete unmerged work); uppercase `-D` is force-delete (permitted but used carefully).

### Tomorrow's first move

Pick from "Next-session candidates" — C6 has the most user-visible value of the mechanical options; A5/A6 are the fastest wins; B-tier work is done. The migrate spike is the next big arc and worth scheduling for a dedicated session.
