# ADR 0012: Phase-2 patterns — configure phase, F1 reframing, and the new five-phase orchestrator

- **Status**: Accepted
- **Date**: 2026-05-07
- **Spike**: [Spike 0009 — Phase-2 design decisions before cookie-cutting prereqs](../spikes/0009-phase-2-design-decisions.md)
- **Touches**: [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) — F1 reframed as orchestrator code rather than a prereq. [ADR 0006](0006-editor-collaboration-sliced-repos.md) — editor signing-key flow uses scope-refresh-on-demand. [ADR 0010](0010-installer-preflight-consent-gate.md) — partially superseded: extends the four-phase model to five phases.

## Context

Phase 1 of Story 0.11 (cantilever orchestrator + first three prereqs A1/C4/C5) shipped on 2026-05-07 via PR #6. Before scaling the prereq pattern from 3 to 24 ops, the Plan subagent flagged six design decisions that, if left unresolved, would either (a) get re-litigated per prereq during phase 2 or (b) lead to inconsistent shapes across the cookie-cutter prereq set. Spike 0009 captured the decisions and resolutions; this ADR locks them.

The decisions cluster into three themes:

1. **Interactive input collection.** Several prereqs (C3 git config, C6 credentials, the interactive bit of D6 signing-key) need user input that ADR 0010's four-phase model (inspect → plan + consent → apply → verify) doesn't naturally accommodate. Mid-flow `input()` calls inside `apply()` violate ADR 0010's "one decision (Y/n on a clearly-laid-out plan)" intent. The "manual round-trip" alternative (apply emits remediation hints, user pastes commands, re-runs cantilever) creates first-install friction — exactly the friction that defeats the adoption hook the project needs.
2. **Op-vs-orchestrator framing.** F1 ("pre-run: detect connectivity + load settings") was specified as a prereq in ADR 0003, but its result mutates orchestrator state rather than producing a per-op apply. The inspect/apply contract from ADR 0010 doesn't fit.
3. **Default values + defer-to-settings tension.** A4 (MacTeX vs BasicTeX) is the first prereq where the "right" default depends on `settings/bootstrap.toml`, but settings/ doesn't exist yet. Hard-code in v1 vs. introduce settings infrastructure as scope-creep.

## Decision

### 1. Five-phase orchestrator (extends ADR 0010)

ADR 0010's four phases become five:

```
┌─────────┐   ┌────────────────┐   ┌────────┐   ┌───────────────┐   ┌─────────┐
│ INSPECT │ → │ PLAN + CONSENT │ → │ APPLY  │ → │   CONFIGURE   │ → │ VERIFY  │
│ (read)  │   │ (single Y/n)   │   │ (mut.) │   │ (interactive) │   │ (smoke) │
└─────────┘   └────────────────┘   └────────┘   └───────────────┘   └─────────┘
```

**Phase 4 — Configure** is new. It runs after `apply` and before `verify`. Its contract:

- Iterates `inspect_results` filtering for `status == "needs-interactive"` (new value, see #2 below).
- For each, prompts the user using a typed input function: plain `input()` for non-secret strings (git user.name, user.email), `getpass.getpass()` for credentials. Prompt is the prereq's `proposed_action` field (e.g., `"Enter your git user.name:"`), and the user can press Enter alone to skip per item.
- Applies the collected value via the prereq's existing CLI surface — `git config --global` for git identity, `ergodix auth set-key` for credentials, `gh auth refresh -s <scope>` for D6's signing-key scope refresh.
- The `--ci` floater skips the entire configure phase. CI environments must provide config via env vars (which `auth.py`'s tier-1 lookup already supports for credentials; git config goes via `GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL` or `git config --global` set in CI's prep).
- Decline / skip leaves the relevant verify check failing, producing a `verify-failed` outcome with clear remediation. The user can complete setup later by re-running cantilever or running the underlying command directly.

The configure phase is testable via the same callable-injection pattern that already exists in `cantilever.py` for `consent_fn` and `is_online_fn`. Tests pass a fake "answer-source" callable instead of reading real stdin.

### 2. New `InspectResult.status` value: `needs-interactive`

`InspectStatus` adds `"needs-interactive"` to its Literal:

```python
InspectStatus = Literal[
    "ok",
    "needs-install",
    "needs-update",
    "needs-interactive",     # new — apply() is no-op; configure phase handles
    "deferred-offline",
    "failed",
]
```

`InspectResult.needs_action` returns True for `needs-interactive` so the op appears in the plan and the user is informed of it during the consent gate. The plan-display rendering should mark these ops differently (e.g., `[interactive]` tag) so the user knows they will be prompted later.

The op's `apply()` is a no-op for `needs-interactive` ops — it returns `ApplyResult(status="skipped", message="awaiting configure phase")` or similar.

### 3. F1 is orchestrator code, not a prereq

F1 ("pre-run: detect connectivity + load settings/") is removed from the 25-op menu in ADR 0003 and lives in `cantilever.py` as orchestrator-level concerns:

- The `is_online_fn` callable currently in `cantilever.py` (with a `_default_is_online_fn` stub that always returns True) becomes a real TCP probe. Implementation lives in a new module `ergodix/connectivity.py` per ADR 0003's earlier note.
- A new `ergodix/settings.py` module loads `settings/bootstrap.toml` + the per-floater `settings/floaters/<name>.toml` files (per ADR 0005), with sensible defaults when files are absent.

The remaining-prereq count goes from 22 to 21.

### 4. A4 MacTeX default

A4 v1 hard-codes `full` (MacTeX) as the install choice. The `settings/bootstrap.toml` flag `mactex.install_size: full|basic|skip` is documented as the future override path; A4's docstring carries a TODO referring to the settings layer's eventual landing. README's Install section publishes the disk requirement (~4GB) as a minimum prerequisite so disk-constrained users see it before they run `bootstrap.sh`.

Rationale: ergodic typesetting requires the full LaTeX surface (`fontspec`, `pdflscape`, `tikz`, `pandoc-crossref`); BasicTeX would require manual `tlmgr install` cycles that surface mid-render failures. The first failed render is a worse user experience than a one-time 4GB download. CLAUDE.md's "~1 year of solo Author use precedes inviting other authors" pacing means the only Installer for the foreseeable future is the Author on machines they control on broadband.

### 5. D6 signing-key auth scope: re-auth on demand

D6 (editor signing key) requires `admin:public_key` scope on the user's `gh` token. C1 (`gh auth login`) does NOT request this scope upfront — it would violate least-privilege for users who never enable the `--editor` floater. Instead, D6's inspect detects insufficient scope, marks the op `needs-interactive`, and the configure phase prompts: "Editor floater needs `admin:public_key` scope on your `gh` token; refresh now? [y/N]" before running `gh auth refresh -s admin:public_key`.

A Note is appended to ADR 0006 documenting this flow.

### 6. `needs_admin` / sudo-cache assumption

Cantilever's existing `request_admin_fn` runs `sudo -v` once before the apply phase if any plan op has `needs_admin=True`. macOS's default `timestamp_timeout` of 5 minutes covers every plan we currently expect to assemble (A4 MacTeX is the worst case at ~3-5 minutes on broadband; everything else is sub-minute). For v1 we trust this cache. If real-world plans bust the cache (longer A4 install, multi-op plan with cumulative sudo), we escalate to a `sudo -n -v` precheck inside each `apply()` that does mutative system work.

A Note is appended to ADR 0010 documenting this assumption.

## Consequences

**Easier:**
- Single-run bootstrap from a fresh clone produces a fully-configured install — no re-run cycles, no "paste these 5 commands" lists.
- The configure phase is a single, well-scoped surface for all interactive collection — adding a new interactive op is "set status=needs-interactive in inspect, set proposed_action to the prompt text, write a small completion handler." No phase-model rework per op.
- F1 reframe removes contract impedance: orchestrator concerns live in orchestrator code; per-op concerns stay in prereq modules.
- Hard-coding A4's `full` choice unblocks A4 implementation without dragging settings/ infrastructure into phase 2.

**Harder:**
- Five phases is more than four. Plan-display UX and run-record schemas must accommodate the new phase. Tests cover one more cross-cutting code path.
- Configure-phase prompts need careful UX design: skip semantics, item labels, hidden vs plain input, accessibility (screen readers).
- The `--ci` flag now has more semantic weight: it disables consent AND configure. Documentation must make this clear so CI authors don't get surprised.

**Accepted tradeoffs:**
- A4 hard-coded `full` means disk-constrained users discover the requirement at the README level rather than during install. Acceptable; this is a documented minimum requirement, not silent behavior.
- The configure phase runs even for `--ci` (though it's a no-op skip in that mode); we accept the minor extra code path.
- D6's "re-auth on demand" means the editor floater's first activation has a sub-prompt the writer floater never sees. Acceptable; the alternative (upfront max-scope grant) violates least-privilege.

## Alternatives considered

- **Manual round-trip for C3/C6** (Spike 0009 option b): apply emits remediation hints, user pastes commands, re-runs cantilever. Rejected: friction is hostile to adoption. Solo-Author pacing makes it tolerable for v1, but locking it into the design now and refactoring to the configure phase later is more work than just doing the configure phase up front.
- **Inline pre-disclosed prompts** (Spike 0009 option a′): apply prompts mid-flow but the consent gate pre-discloses what's coming. Rejected: prompts interleave with apply progress lines, which is the same readability problem the consent-prompt newline fix on 2026-05-07 was about. UX-wise not as clean as a dedicated phase.
- **F1 as a prereq with a special `meta` flag**: rejected. Adds contract complexity for a single edge case. Cleaner to acknowledge that not every cantilever responsibility is a per-op concern.
- **A4 introduces settings/ in v1**: rejected as scope creep. Settings/ has its own design surface (TOML schema, loader, validation, override semantics) that deserves its own ADR — pulling it into A4 would conflate two unrelated concerns.

## References

- [Spike 0009](../spikes/0009-phase-2-design-decisions.md) — discussion record + decision log.
- [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) — 25-operation menu (now 24 after F1 reframe).
- [ADR 0006](0006-editor-collaboration-sliced-repos.md) — editor signing-key flow (Note added).
- [ADR 0010](0010-installer-preflight-consent-gate.md) — pre-flight consent gate (Note added: configure phase + sudo-cache assumption).
- [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) — floater registry; `--ci` floater behavior extends here.
