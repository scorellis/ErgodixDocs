# ADR 0003: Cantilever bootstrap orchestrator

- **Status**: Partially Superseded by [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) and [ADR 0006](0006-editor-collaboration-sliced-repos.md)
- **Date**: 2026-05-03
- **Spike**: [Spike 0003 — Cantilever semantics, settings architecture, run-record](../spikes/0003-cantilever-semantics.md)

> **Note (2026-05-04 — corrections):** the operation count below was originally documented as "21" then incremented to "22" when D5 was added. Both numbers were wrong; the actual count of items in the table at the time of this ADR's authorship was **23** (A1–A7 + B1–B2 + C1–C6 + D1–D4 + E1–E2 + F1–F2). With D5 added by ADR 0004 and D6 added by ADR 0006's editor-signing-key work, **the current count is 25**.
>
> **Note (2026-05-07 — F1 reframed by [ADR 0012](0012-phase-2-patterns-configure-phase-and-five-phase-orchestrator.md)):** F1 ("Pre-run: detect connectivity + load settings from `settings/`") is **no longer a prereq module**. F1's responsibilities (network probe + settings load) are orchestrator-level concerns and live in `cantilever.py` and a new `ergodix/connectivity.py` / `ergodix/settings.py` rather than as `inspect()` / `apply()` per ADR 0010's per-op contract. The current count of **prereq operations** is therefore **24** (A1–A7 + B1–B2 + C1–C6 + D1–D6 + E1–E2 + F2). F1 stays in this ADR's narrative as a *responsibility* but is removed from the prereq-module count.
>
> **Note (2026-05-07 — B2 corpus-path wording):** the B2 row below reads "Detect Drive mount mode + Tapestry path." The "Tapestry" reference is a pre-pivot leftover from before [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) reframed the project as "tool for any author." When B2 is implemented, treat it as **generic corpus-path detection** — the user supplies their corpus folder name (or B2 surfaces a prompt for it via the configure phase from [ADR 0012](0012-phase-2-patterns-configure-phase-and-five-phase-orchestrator.md)). The literal "Tapestry of the Mind" string is the original author's specific corpus name, not a hardcoded default for any user.
>
> **Note (2026-05-03):** [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) consolidates `settings/personas/` + `settings/floaters/` into a single `settings/floaters/` folder. Body text below has been updated to drop the now-obsolete `settings/personas/` references. Idempotency rules, failure semantics, connectivity model, and run-record format are unchanged.

## Context

Per [ADR 0001](0001-click-cli-with-persona-floater-registries.md), `cantilever` is one of the planned subcommands and is the persona-aware bootstrap orchestrator. The original Story 0.8 framing was "all-encompassing setup / upgrade / deploy" — a vibe, not a specification. This ADR makes it concrete: the menu of operations, idempotency rules, settings architecture, failure semantics, and connectivity behavior.

## Decision

### Operation menu — 25 operations, six categories

Cantilever's complete catalog of operations. Each persona's settings file selects which operations apply to that persona.

**A — Environment bootstrap**

| # | Operation | Mutative? | Network? |
|---|---|---|---|
| A1 | Detect platform (macOS / Linux / Windows) | read-only | no |
| A2 | Install / verify Homebrew | mutative | yes |
| A3 | Install / verify Pandoc | mutative | yes |
| A4 | Install / verify XeLaTeX (MacTeX or BasicTeX) | mutative | yes |
| A5 | Install / verify Python 3 + create `.venv` | mutative | yes |
| A6 | Install / verify Python packages from `requirements.txt` | mutative | yes |
| A7 | Install / verify VS Code + extensions (Markdown Preview Enhanced, LTeX, CriticMarkup) | mutative | yes |

**B — Drive integration**

| # | Operation | Mutative? | Network? |
|---|---|---|---|
| B1 | Install / verify Google Drive for Desktop | mutative | yes |
| B2 | Detect Drive mount mode + Tapestry path | read-only | no |

**C — Repo + auth**

| # | Operation | Mutative? | Network? |
|---|---|---|---|
| C1 | `gh auth login` (browser-based, interactive) | mutative | yes |
| C2 | Clone the corpus repo (`tapestry-of-the-mind`) | mutative | yes |
| C3 | Configure `git user.name` / `user.email` if unset | mutative | no |
| C4 | Bootstrap `local_config.py` from `local_config.example.py` (preserve if present) | mutative | no |
| C5 | Create `~/.config/ergodix/` and `secrets.json` template | mutative | no |
| C6 | Prompt for credentials via keyring CLI (only those missing for chosen persona) | mutative | no |

**D — Persona-specific tooling**

| # | Operation | Mutative? | Network? |
|---|---|---|---|
| D1 | Install VS Code task for auto-sync (editor only) | mutative | no |
| D2 | Configure git hooks for prose linting (writer / writer+developer) | mutative | no |
| D3 | Install dev dependencies (developer floater) | mutative | yes |
| D4 | Set up `develop` branch tracking + branch protection notice (developer floater) | read-only | no |
| D5 | Install continuous polling job (LaunchAgent on macOS) — see [ADR 0004](0004-continuous-repo-polling.md) | mutative | no |
| D6 | Set up editor signing key — generate `ed25519` SSH key + register with GitHub as a signing key + configure local git to sign commits (editor floater only) — see [ADR 0006](0006-editor-collaboration-sliced-repos.md) | mutative | yes |

**E — Verification & exit**

| # | Operation | Mutative? | Network? |
|---|---|---|---|
| E1 | Run `ergodix status` to verify the resulting environment | read-only | partial |
| E2 | Print persona-tailored "you're done" message + next steps | read-only | no |

**F — Pre/post**

| # | Operation | Mutative? | Network? |
|---|---|---|---|
| F1 | Pre-run: detect connectivity + load settings from `settings/` | read-only | partial |
| F2 | Post-run: write run-record to `~/.config/ergodix/cantilever.log` | mutative | no |

### Idempotency

**Every operation is idempotent.** Running cantilever twice in a row produces the same end state. Each operation has a "is this already done?" check before mutating anything. This is non-negotiable — it's the property that lets users "just re-run cantilever" when something goes wrong.

### Upgrade detection

Cantilever silently applies dependency upgrades on re-run. The post-run record (F2) captures versions of all dependencies after each run; the pre-run check (F1) compares against the previous record and:

- **Compatible upgrades** (patch/minor): apply silently.
- **Major-version dependency upgrades**: display a "potentially breaking — review CHANGELOG" warning before continuing.
- **Major-version of `ergodix` itself** (e.g. 0.x → 1.x with file-format changes): block until user explicitly confirms with a dedicated `ergodix upgrade --confirm-breaking` flag. Honors semver.

This addresses the multiple-machines-different-versions case: minor mismatches are silent and forward/backward compatible; only file-format-breaking changes force coordination.

### Failure semantics — abort-fast with great messaging

When an operation fails:

1. Print: `✗ Failed at step X of Y: <operation_id> — <description>`
2. Print: structured remediation block — exact reason, diagnosis, suggested fix(es), and a reminder that re-running cantilever skips successful steps.
3. **Attempt safe auto-fix** when one exists (e.g., open Drive if not running, then re-try the step).
4. Exit non-zero only if auto-fix fails or no auto-fix is defined.

The "step X of Y" framing is required — users must always know how far cantilever progressed.

### Connectivity — automatic detection

No `--offline` flag. F1 detects connectivity at run-start. If offline:

- Network operations (any row marked `Network? yes`) silently no-op with a "deferred — will retry when online" marker in the run-record.
- Offline-capable operations run normally.
- Cantilever exits cleanly without user-visible disruption.

This makes cantilever (and `sync`, and the continuous polling job per [ADR 0004](0004-continuous-repo-polling.md)) cron-safe and travel-friendly.

### Settings architecture

Compartmentalized TOML files under `settings/`, mirroring the persona/floater registries from ADR 0001:

```
settings/
  bootstrap.toml              # global cantilever settings: criticality flags, defaults
  personas/
    writer.toml               # writer persona settings + operation overrides
    editor.toml               # editor persona settings + operation overrides
    publisher.toml             # future
    focus-reader.toml          # future
  floaters/
    developer.toml             # developer floater settings
    dry-run.toml
    verbose.toml
    ci.toml
```

`bootstrap.toml` declares each operation's default criticality. Persona and floater files override per-persona and per-floater. v1 default: every operation `critical = true`. Concrete schema:

```toml
# settings/bootstrap.toml
[operations.A1]
description = "Detect platform"
critical = true

[operations.A4]
description = "Install XeLaTeX (MacTeX or BasicTeX)"
critical = true   # set to false if the persona doesn't need PDF rendering
```

```toml
# settings/floaters/editor.toml  (per ADR 0005 — single floater registry)
adds_operations = ["A7", "C3", "D1", "D5", "D6"]
exclusive_with = ["focus-reader"]
# editor doesn't need: A3 (Pandoc), A4 (XeLaTeX), B2 (Drive Tapestry path),
#                       C4 (local_config — author-side concern), C5/C6 (no API keys),
#                       D2/D3/D4 (no dev tooling unless --developer is added).
# D6 was added 2026-05-04 per ADR 0006 (SSH signing-key setup).
```

Adding a new floater = drop a new file in `settings/floaters/`. Adding a new operation = add it to `settings/bootstrap.toml`. No code changes.

### Run-record

Per-machine, at `~/.config/ergodix/cantilever.log`. Structured (JSON-lines). Each cantilever run appends one record:

```json
{"ts": "2026-05-03T14:32:00Z", "persona": "writer", "floaters": ["developer"], "operations": [{"id": "A1", "status": "ok"}, {"id": "A4", "status": "deferred-offline"}, ...], "exit": 0, "duration_seconds": 47}
```

The polling job (ADR 0004) and future `ergodix status` consume this to know what was last done and when.

### What's NOT cantilever's job

- `ergodix migrate` — explicit one-time corpus import; sibling subcommand.
- `ergodix render` — Pandoc → PDF; sibling subcommand.
- `ergodix sync-out` (editor save → slice push) and `ergodix sync-in` (poller fetch); sibling subcommands. See [ADR 0008](0008-cleanup-sync-rename-ownership-autofix-static-analysis.md) for the rename rationale.
- `ergodix publish` / `ergodix ingest` — author-side editor-collaboration commands; sibling subcommands. See [ADR 0006](0006-editor-collaboration-sliced-repos.md).
- OS updates, GCP project setup — out of scope.

## Consequences

**Easier:**

- Re-running cantilever is always safe.
- Adding personas, floaters, or operations is a settings/registry change; no code edits.
- Failure messaging tells users *exactly* what went wrong and what to do.
- Cron/launchd-friendly — connectivity-aware operations no-op cleanly.
- Per-machine run-records mean each install can evolve at its own pace; semver gates breaking changes.
- The 21-operation menu becomes the source-of-truth for what cantilever can do; Topic 4 (role matrix) becomes a fill-in-the-table exercise against this list.

**Harder:**

- Each operation must be implemented with idempotency in mind from day one — no quick-and-dirty mutations.
- The auto-fix catalog needs to be carefully curated; bad auto-fixes that "succeed" but leave a broken state are worse than failures.
- Settings file proliferation — five+ files for v1 (bootstrap + a couple of personas + a couple of floaters). Acceptable; the parallel structure with the registries makes it discoverable.
- Run-record format is JSON-lines; if we ever want to ship a "show me cantilever history" UI, we have to write the parser.

**Accepted tradeoffs:**

- v1 marks everything critical. Granular criticality is expressible but unset for now. Acceptable; later flips don't require code changes.
- Prose linting (D2) is opt-in per persona settings, not default — ergodic-text artistry takes precedence over linting. Acceptable.
- Run-record is per-machine, not shared. Team coordination deferred to later when the use case is real.

## Alternatives considered

- **Continue-and-report failure mode**: rejected. The "we got 60% of the way there" twilight zone is harder to reason about than fail-fast + idempotent re-run.
- **Hardcoded operation list in code**: rejected. Settings-file-driven menu honors Open/Closed.
- **`--offline` flag**: rejected. Auto-detection is friendlier; cron-safe; never disrupts the user.
- **Single global `settings.toml`**: rejected. Compartmentalized files mirror the registry pattern (ADR 0001) and let persona / floater settings live alongside their concept.
- **YAML or JSON for settings**: rejected. TOML has comments + native Python stdlib parsing; cleaner for human-edited config.
- **Run-record committed to repo for team coordination**: rejected for v1. No multi-collaborator use case yet; per-machine is sufficient.
- **Auto-applied major-version upgrades**: rejected. Forced confirmation for breaking changes is the right safety posture.

## References

- [Spike 0003](../spikes/0003-cantilever-semantics.md) — full discussion record.
- [ADR 0001](0001-click-cli-with-persona-floater-registries.md) — CLI structure + persona/floater registries.
- [ADR 0002](0002-repo-topology-and-editor-onboarding.md) — repo topology + editor persona.
- [ADR 0004](0004-continuous-repo-polling.md) — continuous polling job (sibling concern).
- [CHANGELOG.md](../CHANGELOG.md) — semver policy this ADR honors.
