# Spike 0009: Story 0.11 phase 2 — design decisions before cookie-cutting prereqs

- **Date range**: 2026-05-07
- **Sprint story**: [Story 0.11 — Installer redesign](../stories/SprintLog.md), phase 2 (next 21 prereqs after F1 reframed as orchestrator code).
- **ADRs produced**: ADR 0012 (codifies the four resolved patterns); plus Notes added to ADR 0010 (sudo-cache assumption, new "configure" 5th phase) and ADR 0006 (signing-key scope-refresh-on-demand).
- **Touches**: [ADR 0003](../adrs/0003-cantilever-bootstrap-orchestrator.md), [ADR 0006](../adrs/0006-editor-collaboration-sliced-repos.md), [ADR 0010](../adrs/0010-installer-preflight-consent-gate.md).
- **Status**: All six decisions resolved 2026-05-07. ADR 0012 implementation pending; lands as the first commit on the phase-2 branch after Story 0.11 phase-1 PR ([#6](https://github.com/scorellis/ErgodixDocs/pull/6)) merges.

## Question

Before scaling the prereq pattern from 3 ops to 25, the Plan subagent (run 2026-05-07 against the post-phase-1 codebase) flagged six unresolved design decisions. Cookie-cutting against an under-specified pattern multiplies any latent ambiguity 22 times. The question: resolve all six in one short spike, codify as a Note or new ADR, then proceed.

The six decisions:

1. **C3 — git config interactive.** Does `apply()` prompt mid-flow for `user.name` / `user.email`, or surface the manual `git config --global ...` command in `proposed_action` and let the user run it themselves?
2. **C6 — credential prompts.** Same shape as C3, scaled. Looping `getpass` prompts inside `apply()` for keyring credentials would violate ADR 0010's "consent gate already happened" model.
3. **A4 — MacTeX vs BasicTeX default.** 4GB vs 100MB. Which does the default Installer get? Is the choice a settings flag, a floater, or a per-install consent prompt?
4. **D6 — editor signing-key auth scope.** D6 generates an SSH key and registers it with GitHub via `gh ssh-key add --type signing`, which needs `admin:public_key`. Does C1's `gh auth login` request this scope upfront, or does D6 re-auth?
5. **F1 — prereq-vs-orchestrator framing.** F1 ("pre-run: detect connectivity + load settings") is *meta* — it runs before the prereq-loop and configures it. Does it satisfy the inspect/apply per-op contract from ADR 0010, or does it live in `cantilever.py` as orchestrator code that's not a prereq module?
6. **`needs_admin` escalation semantics.** `ApplyResult` has no admin field. Cantilever calls `request_admin_fn` once before the apply phase if any plan op has `needs_admin=True`. How does an individual `apply()` call invoke `sudo` after that?

## Discussion

### 1. C3 — git config interactive

**Options:**
- **(a) `apply()` prompts mid-flow** via `input()` for name/email when unset.
- **(b) `apply()` surfaces the manual command** in `remediation_hint` and returns `skipped`. Inspect's `proposed_action` shows the exact `git config --global` lines to run.
- **(c) `apply()` reads from `local_config.py`** (a new pair of fields like `GIT_USER_NAME` / `GIT_USER_EMAIL`) and runs `git config --global` non-interactively.

**Initial recommendation (later overridden): (b).** Cleaner phase model, but adds round-trips at first install.

**Resolution (2026-05-07): LOCKED — option (c′), a NEW post-apply "configure" phase shared with C6.** See decision #2 below; C3 and C6 collapse into one shared decision. C3's `apply()` becomes a no-op; the configure phase prompts for `user.name` / `user.email` (plain input) and shells out to `git config --global` to apply.

### 2. C6 — credential prompts

**Options:**
- **(a) Loop `getpass` prompts in `apply()`** — same problem as C3 option (a), worse because there are 1–3 keys to prompt for.
- **(b) Surface manual command in `remediation_hint`** for each missing key. Apply returns `skipped`. User runs `ergodix auth set-key <name>` themselves and re-runs cantilever.
- **(c) Post-apply "configure" phase** — a fifth phase between apply and verify, dedicated to interactive collection (git config + credentials + anything else that needs user input). Adds complexity to ADR 0010's four-phase model but yields single-run bootstrap.

**Initial recommendation (later overridden): (b)**, for ADR-0010-stays-pure reasons.

**Resolution (2026-05-07): LOCKED — option (c), shared post-apply "configure" phase.** Rationale (user-confirmed):

- The Plot-Planner story added 2026-05-07 explicitly named *"we need a hook to get authors using this tool"* — first-install friction kills adoption. Multi-round-trip bootstrap is exactly that friction.
- Solo-Author pacing makes (b) tolerable for the user's own machines, but locking (b) into the design now and refactoring to (c) when other authors arrive is *more* work than just doing (c) up front. The transition (b)→(c) means touching every interactive prereq again — the cookie-cutter scale issue we want to avoid.
- Inline-prompt option (a′ / "pre-disclosed inline") was considered but rejected: prompts interleave with apply progress lines, which is the same readability problem the consent-prompt newline fix on 2026-05-07 was about.

**Phase 5 (configure) shape:**

- Runs between apply (phase 3) and verify (phase 4). ADR 0010 four-phase model becomes a five-phase model; ADR 0012 codifies the new shape.
- New `InspectResult.status` value: `needs-interactive` — signals that an op produces no `apply()` work but needs configure-phase input.
- Configure phase iterates `inspect_results` filtering for `needs-interactive`, prompts the user (typed: plain string for git config, hidden input via `getpass` for credentials), stores via existing surfaces (`ergodix auth set-key` for keys, `git config --global` for git identity), and lets the user skip per-item ("press enter to skip this one for now").
- `--ci` floater skips the entire configure phase. CI environments must provide config via env vars (which `auth.py`'s tier-1 lookup already supports for credentials; git config can be set in CI's environment too).
- Configure phase is testable via the same `consent_fn`-style injection pattern that already exists in `cantilever.py` — tests pass a fake "answer-source" callable instead of reading real stdin.
- Decline / skip leaves the relevant verify check (`local_config_sane` etc.) failing, which produces a `verify-failed` outcome with clear remediation. This preserves the "soft fail" behavior — the user can complete setup later by re-running cantilever (or running the underlying command directly).

**Cost:** ~2–3 hours of focused design + implementation in the ADR 0012 follow-up. Lands before C3 or C6 prereq code begins.

### 3. A4 — MacTeX vs BasicTeX default

**Options:**
- **(a) `bootstrap.toml` flag** (`mactex.install_size: full|basic|skip`, default `full`) — committed setting, every contributor on this repo gets the same behavior. Per CLAUDE.md "settings/* drives behavior for all users."
- **(b) Floater** (`--mactex-basic` or `--mactex-skip`) — runtime choice, per-invocation.
- **(c) Per-install consent prompt** — bring back the mid-stream `[a/b/s]` prompt that the old installer had.

**Recommendation: (a) bootstrap.toml flag, default `full`.** The Author persona (the repo's primary user) wants full MacTeX for ergodic typesetting; that's the default. Settings flag lets per-machine override (a contributor without 4GB free can flip to `basic`). Option (b) is reasonable but adds CLI surface; option (c) revives the very anti-pattern ADR 0010 was designed to eliminate.

**Implication:** `settings/bootstrap.toml` doesn't exist yet — settings/ directory itself is unimplemented as of 2026-05-07. Either A4 implementation creates the settings infrastructure (scope creep) or A4 hard-codes `full` until settings/ lands. **Recommend hard-coding `full` in A4 v1, with a TODO comment + note in A4's docstring that the value will move to bootstrap.toml when the settings layer lands.**

**Resolution (2026-05-07): LOCKED — `full` (MacTeX) as default, hard-coded in A4 v1; bootstrap.toml flag deferred until settings/ lands.** Rationale (user-confirmed):

- Ergodic typesetting needs the full LaTeX surface — MacTeX bundles `fontspec`, `pdflscape`, `tikz`, `pandoc-crossref`, etc. that BasicTeX would require manual `tlmgr install` for. The first failed render is a worse experience than the 4GB up-front download.
- Per CLAUDE.md project pacing, ~1 year of solo Author use precedes inviting other authors; for that year the only Installer is the Author on machines they control on broadband. 4GB is a one-time cost.
- Disk-constrained machines exist but are addressed by **publishing minimum requirements** in the Install section of README, not by silently choosing a smaller install that surfaces failures later.
- "Authors might not render frequently" — but **some will**, and the first render they attempt has to work. Default-skip surfaces a frustrating failure right at the moment the Author wanted output.
- When other authors / collaborators arrive, the `bootstrap.toml` flag and per-floater overrides (`--mactex-basic` / `--mactex-skip` for editors who never render) become a small scope-isolated change, not a v1 concern.

### 4. D6 — editor signing-key auth scope

**Options:**
- **(a) C1 requests `admin:public_key` upfront.** Maximalist: every Installer who runs C1 grants the scope, even if they never use the editor floater.
- **(b) D6 re-auths.** D6 inspect detects insufficient scope, surfaces `gh auth refresh -s admin:public_key` as `proposed_action`, apply returns `skipped`.
- **(c) D6's apply runs `gh auth refresh` non-interactively if possible.** Probably not possible — refresh opens a browser for OAuth.

**Recommendation: (b).** D6 only runs when the `--editor` floater is active. Asking every Installer for `admin:public_key` violates least-privilege. The refresh-when-needed pattern (option b) keeps the principle and matches the C3/C6 "surface the manual command" model.

**Resolution (2026-05-07): LOCKED — option (b) re-auth on demand,** with one revision now that the configure phase is in scope: D6's interactive bit can move into the configure phase too (prompt: "Editor floater needs `admin:public_key` scope on your `gh` token; refresh now? [y/N]"), then `gh auth refresh -s admin:public_key` runs in-flow. Falls back to "skipped + remediation hint" if the user declines or `gh` isn't available. **Note added to ADR 0006** reflecting the actual workflow.

### 5. F1 — prereq-vs-orchestrator framing

**Options:**
- **(a) F1 is a prereq module.** Has `op_id="F1"`, inspect (probe network, return ok/failed), apply (no-op since it's read-only). Awkward fit for the inspect/apply contract — F1's "result" is a side effect (set `online` flag for downstream prereqs), not a state to apply.
- **(b) F1 is orchestrator code in `cantilever.py`.** Connectivity probe + settings load happen at the top of `run_cantilever()`, before the prereq loop. `is_online_fn` already exists in cantilever.py for this.
- **(c) F1 hybrid:** read-only prereq module that runs first, but its result mutates orchestrator state (the plan-building filter for network-required ops).

**Recommendation: (b).** ADR 0010 frames inspect/apply as per-op operations. F1 is *meta*-operational: it configures how the loop runs. The `is_online_fn` callable injection is already the right abstraction. Phase-2 work on F1 is just (1) replace the `_default_is_online_fn` stub with a real probe, (2) add settings/ loading. Both are orchestrator concerns, not prereq concerns.

**Implication:** F1 is removed from the "22 remaining prereqs" count — it's orchestrator work, not a prereq. The remaining count drops to 21.

**Resolution (2026-05-07): LOCKED — option (b),** F1 stays as orchestrator code in `cantilever.py`. Implementation is two small replacements (real connectivity probe, settings/ loader); not a prereq module. Remaining-prereq count: 21.

### 6. `needs_admin` escalation semantics

**Background:** Today's `ApplyResult` has no admin field. Cantilever's `_default_request_admin_fn` runs `sudo -v` once before the apply phase if any plan op has `needs_admin=True`. macOS sudo caches credentials for ~5 minutes by default, so subsequent `sudo` calls inside individual `apply()` functions inherit the cached auth without re-prompting.

**Question:** is this enough? What if A4 (MacTeX install) takes 6 minutes and the cache expires mid-apply? What if a user's sudoers config has a shorter timestamp_timeout?

**Options:**
- **(a) Trust the cache.** Document the 5-minute assumption. If it expires, sudo re-prompts inline (one-time, not blocking). Good enough for v1.
- **(b) Periodic re-validation.** Cantilever spawns a background `sudo -v` every 4 minutes during apply. Robust but adds complexity.
- **(c) Each `apply()` calls `sudo -n -v` first** (no-prompt cache check). If it fails, abort with a clear "credentials expired" message; user re-runs cantilever (idempotency handles the resume).

**Recommendation: (a) for v1.** The 5-minute cache window covers every plan we expect to assemble (A4 MacTeX is the worst case at ~3-5 min on broadband; everything else is sub-minute). If we hit the cache-expiry edge case in practice, escalate to (c) — option (b) is over-engineering for the v1 surface.

**Document in ADR 0010 as a Note** under the "Phase 3 — Apply" section: "Sudo-cache assumption: macOS default 5-minute timestamp_timeout. Plans whose total apply time exceeds this may surface a sudo re-prompt mid-apply; treated as one-time, non-blocking."

**Resolution (2026-05-07): LOCKED — option (a),** trust the macOS sudo cache for v1. Note added to ADR 0010. Escalation path (option c — `sudo -n -v` precheck inside each `apply()`) reserved for if the cache-expiry edge case shows up in real-world plans.

## Decision

All six decisions resolved 2026-05-07. ADR 0012 will codify them; Notes will be added to ADR 0006 and ADR 0010.

| # | Decision | Locked answer |
|---|---|---|
| 1 | C3 git config interactive | Subsumed by #2 — collected in the new configure phase. C3's `apply()` is a no-op; the configure phase prompts and shells out to `git config --global`. |
| 2 | C6 credential prompts | **Option (c) — new post-apply "configure" phase** (5th phase between apply and verify). Shared infrastructure with C3 and the interactive bit of D6. New `InspectResult.status = "needs-interactive"`; configure phase iterates and prompts; `--ci` skips. |
| 3 | A4 MacTeX default | **`full` (MacTeX) hard-coded in v1**, with TODO to move the value to `bootstrap.toml`'s `mactex.install_size: full|basic|skip` when the settings/ layer lands. Disk requirements published in README's Install section. |
| 4 | D6 signing-key auth scope | **Re-auth on demand** via the configure phase: prompts "Editor floater needs `admin:public_key` scope; refresh now? [y/N]" then runs `gh auth refresh -s admin:public_key`. Note added to ADR 0006. |
| 5 | F1 framing | **Orchestrator code in `cantilever.py`**, not a prereq module. Remaining-prereq count drops from 22 to 21. |
| 6 | `needs_admin` / sudo cache | **Trust macOS's 5-minute timestamp_timeout** for v1. Note added to ADR 0010 documenting the assumption; option (c) `sudo -n -v` precheck reserved for if real-world plans bust the cache. |

**Implementation gates (locked 2026-05-07):**

1. **ADR 0012** must merge before any phase-2 prereq code begins. Codifies #1–#6 above and the new five-phase orchestrator shape.
2. **Note appended to ADR 0010** — sudo-cache assumption documented; configure phase added between apply and verify.
3. **Note appended to ADR 0006** — editor signing-key flow uses scope-refresh-on-demand via the configure phase.
4. **Implementation order:** ADR 0012 + Notes → configure-phase orchestrator code (in `cantilever.py`, with `needs-interactive` status added to `InspectResult`) → then C1 → C2 → A2 per the Plan subagent's next-3 recommendation.

## Open questions for the user — RESOLVED 2026-05-07

- ~~A4 default `full` (4GB) vs `basic` (100MB)~~ — **`full`**, with rationale folded into decision #3 above.
- ~~C3/C6 manual-command pattern~~ — **option (c) configure phase**, see decision #2.
- ~~Anything the Plan subagent missed~~ — none; user noted future-marketing and planning skills (Plot-Planner, Sell-My-Book) and other architecture considerations have already been raised.
