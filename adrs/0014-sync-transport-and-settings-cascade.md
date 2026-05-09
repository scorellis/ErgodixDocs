# ADR 0014: Sync transport auto-detect + settings cascade

- **Status**: Accepted
- **Date**: 2026-05-09
- **Spike**: [Spike 0011 — Sync transport auto-detect + settings cascade](../spikes/0011-sync-transport-and-settings-cascade.md)
- **Touches**: [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) (B1 and B2 prereq definitions update), [ADR 0008](0008-cleanup-sync-rename-ownership-autofix-static-analysis.md) (settings/local_config split refined), [ADR 0010](0010-installer-preflight-consent-gate.md) (prereq conditionality semantics), `local_config.example.py`, `ergodix/settings.py`.

## Context

[Spike 0011](../spikes/0011-sync-transport-and-settings-cascade.md) resolved six design questions tangling sync-transport assumptions with the project's settings file layout. This ADR locks the resolutions before B2 implementation lands so the cookie-cutter pattern doesn't bake in Drive-only assumptions that don't survive the actual user base.

The decisions cluster into two themes:

**Sync transport.** Today's `local_config.example.py` exposes `SYNC_MODE = "mirror"` (or `"stream"`) as a manual config field. The user *also* specifies `CORPUS_FOLDER`. Two configs that have to agree, with no real user-base support for a third state ("no Drive at all"). Spike 0011 resolved this in favor of *auto-detect from `CORPUS_FOLDER` location*, with a first-class third state — **indy mode** — for users who don't sync via Drive at all.

**Settings cascade.** `settings/bootstrap.toml` is the only file `ergodix/settings.py` reads today (one consumer: A4 `mactex.install_size`). [CLAUDE.md](../CLAUDE.md) and [ADR 0008](0008-cleanup-sync-rename-ownership-autofix-static-analysis.md) mention `settings/floaters/<name>.toml` as a future per-floater layer, but no third "applies regardless of floater" layer exists. Spike 0011 resolved this in favor of a **three-tier cascade** with a new `settings/defaults.toml` ("SWAG" layer) at the base, narrowing `bootstrap.toml` to installer-only.

## Decision

### 1. Sync transport: auto-detect, not config

`SYNC_MODE` is **removed** from `local_config.example.py`. The user only specifies `CORPUS_FOLDER`. A new helper `detect_sync_transport(corpus_folder: Path) -> SyncMode` resolves the mode at run-start:

```python
SyncMode = Literal["drive-mirror", "drive-stream", "indy"]
```

- Path resolves under `~/My Drive/...` → `"drive-mirror"`.
- Path resolves under `~/Library/CloudStorage/GoogleDrive-*/...` → `"drive-stream"` (refused; B2 surfaces a `failed` with "switch to Mirror" remediation).
- Path resolves elsewhere on the local filesystem → `"indy"`.
- Path doesn't resolve → caller (B2) raises with a remediation pointing the user at `local_config.py`.

The detector is a small pure function; lives in `ergodix/sync_transport.py` (new module). Tested in isolation with `tmp_path` fixtures.

### 2. Indy mode is a first-class peer of drive-mirror in v1

Not a stretch goal, not a future story — supported from this ADR forward. The architectural cost (B1 conditionality, B2 dispatch) is cheaper to absorb at the foundation than to retrofit after additional Drive-coupled prereqs land.

The user-facing framing: ErgodixDocs supports two sync transports in v1 — **drive-mirror** (corpus lives under Google Drive's Mirror mount) and **indy** (corpus lives anywhere on local disk; no sync). Both are equally legitimate; neither is the "fallback."

### 3. Drive-stream not supported in v1

Detection surfaces a `failed` status with a clear remediation: "Switch Drive for Desktop to Mirror mode in Drive Preferences, then re-run cantilever." If a real user complains, revisit; v1 keeps the surface tight.

The README's first-time-setup section gets minimal Drive instructions — *what's needed* (Mirror mode, signed in), not *how to click through Google's UI*. We don't end up supporting Google.

### 4. Settings cascade: three tiers

```
settings/defaults.toml   ← applies to every cantilever run, every floater (SWAG layer)
        ↓
settings/bootstrap.toml  ← installer-specific overrides only (narrowed scope)
        ↓
settings/floaters/<active-floater>.toml  ← per-floater overrides (when that floater runs)
```

Load order is most-general-first; later layers override earlier. `ergodix/settings.py`'s loader reads all three. Defaults are baked in code (current behavior preserved); each layer's file is optional.

**Migration**: `mactex.install_size` moves from `bootstrap.toml` to `defaults.toml`. It's not installer-specific — it's a project-wide preference that happens to be consumed during install. `bootstrap.toml` retains the slot for future installer-only fields.

**Naming**: industry-standard "defaults" beats "base," "common," or the playful "SWAG." Self-documenting; matches user expectations from other tools.

### 5. B1 (Drive Desktop install) becomes conditional

B1's `inspect()` consults `detect_sync_transport(CORPUS_FOLDER)`:

- `drive-mirror` or `drive-stream` → original B1 behavior (verify Drive Desktop installed, return `needs-install` if absent).
- `indy` → return `status="ok"` with `current_state="indy mode; Drive Desktop not required"`. No mutation; no plan entry.

The conditionality lives in B1 itself, not in the orchestrator. Cantilever doesn't need to know about sync transport — B1 reports the right status given the detected mode, and the rest of the four-phase model proceeds normally.

### 6. B2 dispatches via `detect_sync_transport`

B2's `inspect()` flow:

```
mode = detect_sync_transport(CORPUS_FOLDER)
if not CORPUS_FOLDER.exists():
    return failed("CORPUS_FOLDER does not resolve...")
if mode == "drive-stream":
    return failed("Drive-stream not supported in v1; switch to Mirror...")
if mode == "drive-mirror":
    return ok(current_state="corpus at <path> under Drive Mirror mount")
# mode == "indy"
return ok(current_state="corpus at <path>; indy mode (no Drive sync)")
```

Existence check is shared. Mount-detection / stream-rejection logic only runs in the drive-mirror path. B2's `apply()` is essentially a no-op for v1 — the path either exists or it doesn't; we don't create the folder on the user's behalf (corpus folder creation is a precondition; future `ergodix opus init` story handles bootstrap).

### Consequences

- **`local_config.example.py`** loses `SYNC_MODE`. Comments updated to reflect that the user only specifies `CORPUS_FOLDER`. C4 (`check_local_config`) generation flow inherits the simpler template.
- **`ergodix/settings.py`** extends to read three files in cascade order. Defaults remain baked in code; each TOML file is optional. `BootstrapSettings` dataclass stays the typed snapshot the rest of the project consumes — readers don't see the cascade, just the resolved values.
- **`settings/defaults.toml`** lands as a real (initially small) file shipped with the repo. First field migrated in: `mactex.install_size`.
- **B1** gains a sync-transport check at the top of `inspect()`. Existing Drive-installed-and-running tests continue to pass; new tests cover the indy short-circuit path.
- **B2** is implementable against this locked architecture. Story 0.11 phase-2 picks back up.
- **Future Linux / Windows ports** revisit `detect_sync_transport`'s known-mount-paths list. v1 is macOS-only; the helper is cleanly testable so a future port adds platform branches without restructuring.
- **Existing CHANGELOG `[Unreleased]` entry** for the migrate of mactex.install_size from bootstrap.toml to defaults.toml lands when the cascade scaffolding ships.

### Alternatives considered

- **Keep `SYNC_MODE` as a manual field** with values `"mirror" | "stream" | "indy"`. Rejected: two-config drift; inconsistent with the project's "infer where you reasonably can" instinct (cf. connectivity auto-detect, mode-mode autodetection in render preamble cascade).
- **Defer indy mode to a future story.** Rejected: cheaper to absorb at the foundation. Architectural retrofit costs grow with each Drive-coupled prereq that ships under the old assumption.
- **Single settings file (no cascade).** Rejected: the cascade's value isn't visible until the second consumer of "applies-everywhere" settings shows up, but the cost of adding the cascade *now* (one new file, ~15 lines of loader extension) is much lower than retrofitting once `bootstrap.toml` is overloaded with non-installer fields.
- **Two-tier cascade (defaults.toml + floaters/, drop bootstrap.toml).** Rejected: the installer phase has its own concerns (mactex install size mid-cantilever, brew env quirks, sudo cache assumption from ADR 0010) that don't apply outside cantilever. Keeping `bootstrap.toml` as a narrow installer-scoped layer is the right separation.
- **Support drive-stream by enumerating `~/Library/CloudStorage/GoogleDrive-*` directories.** Rejected: email-dependent path detection is fragile; Stream files are placeholders that trigger downloads on read, which interacts badly with render's many-file scan and the future continuity engine's even-more-files scan. Re-evaluate if a real Stream-mode user surfaces.

### Open considerations not blocking

- **Optional `OVERRIDE_SYNC_TRANSPORT` escape hatch** in `local_config.py` ("I have a Drive folder but I want it treated as indy") — file as parking-lot if a real use case appears. Auto-detect is the contract for v1.
- **Linux + Windows known-mount-paths** for `detect_sync_transport`. v1 is macOS-only; cross-references the deferred `bootstrap.ps1`.
- **`OVERRIDE_*` field naming** if escape hatches accumulate — establish a convention then.
