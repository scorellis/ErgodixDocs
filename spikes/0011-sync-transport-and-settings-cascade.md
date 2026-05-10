# Spike 0011: Sync transport auto-detect + settings cascade

- **Date**: 2026-05-09
- **Sprint story**: [Story 0.11 — Installer redesign](../stories/SprintLog.md#story-011---installer-redesign-per-adr-0010-elevated-to-highest-active-priority--blocks-remaining-story-010-work) — phase 2, B-tier prereqs.
- **ADRs to produce**: ADR 0014 (lock the resolutions below).
- **Touches**: [ADR 0003](../adrs/0003-cantilever-bootstrap-orchestrator.md) (B1 and B2 prereq definitions), [ADR 0008](../adrs/0008-cleanup-sync-rename-ownership-autofix-static-analysis.md) (`settings/` vs. `local_config.py` ownership split), `local_config.example.py` (the existing `SYNC_MODE` field), `ergodix/settings.py` (the existing single-file loader), future B1 and B2 prereq modules.
- **Status**: All six questions resolved in conversation 2026-05-09. ADR 0014 pending.

## Question

Before implementing B2 (Drive mount mode + corpus-path detection), six tangled design questions surfaced that — left unresolved — would have B2 hard-coded to assumptions that don't survive the project's actual user base.

The questions clustered into two themes:

**Sync transport** — does the user explicitly tell us how their corpus syncs (current state: `SYNC_MODE = "mirror"` in `local_config.example.py`), or do we infer it from where their corpus lives? And is "no sync at all" a real mode or just a future story?

**Settings cascade** — the project has `settings/bootstrap.toml` today (one consumer: A4 mactex install size) and `settings/floaters/<name>.toml` mentioned in CLAUDE.md but never written. There's no place for "settings that apply to every cantilever run regardless of which floaters are active" — the SWAG layer ("Stuff We All Get").

The six questions:

1. **Manual `SYNC_MODE` vs. auto-detect from `CORPUS_FOLDER` location?**
2. **Is "indy mode" (corpus on local disk, no Drive at all) a first-class peer of drive-mirror, or deferred?**
3. **Should drive-stream be supported in v1?**
4. **Does the existing single `bootstrap.toml` handle everything, or does the project need a layered cascade?**
5. **How does B1 (Drive Desktop install) behave when the user has no Drive at all?**
6. **How does B2 (mount detection) dispatch across the two transport modes?**

## Discussion

### 1. Manual `SYNC_MODE` vs. auto-detect

**Existing state**: `local_config.example.py` defines `SYNC_MODE = "mirror"` (with `"stream"` as the documented alternative). This was set up before the v1 user base was clarified — it asks the user to *both* point at their corpus *and* tell us how it syncs. Two configs that have to agree.

**Auto-detect framing** (the user proposed this): the user only specifies `CORPUS_FOLDER`. Cantilever inspects the path:

- Resolves under `~/My Drive/...` → drive-mirror mode.
- Resolves under `~/Library/CloudStorage/GoogleDrive-*/...` → drive-stream mode (refused in v1; see #3).
- Resolves elsewhere → indy mode (no sync).
- Doesn't resolve → hard fail with a clear remediation pointing the user at `local_config.py`.

**Options:**
- **(a)** Keep `SYNC_MODE` field; user picks. Two configs to keep in sync; users misconfigure.
- **(b)** Drop `SYNC_MODE` field; auto-detect from path location. One source of truth (`CORPUS_FOLDER`), no drift possible.

**Resolution**: **(b)**. Remove `SYNC_MODE` from `local_config.example.py`. The mode is a *function of where the corpus is*, not an independent setting. SOLID by reduction — fewer config fields, fewer ways for the system to be in an inconsistent state. The user's "we point at the path; we figure out the rest" instinct is correct.

### 2. Indy mode as first-class

**Existing state**: project documentation assumes Drive everywhere. B1 (install Drive Desktop) is a hard prereq. README's first-time-setup section walks through Drive setup. `local_config.example.py` says "Mirror is recommended."

**The local-only writer** (the user surfaced this): a writer who likes ergodic-text rendering + AI continuity tools but doesn't use Google Drive at all (or any cloud sync). Common case: privacy-conscious authors, authors with weak / metered connectivity, authors who already have their own sync setup (Dropbox, iCloud, Syncthing, plain local).

**Options:**
- **(a)** v1 supports Drive-mirror only. File "indy mode" as a future story. Pro: smaller v1 surface. Con: the indy use case is *simpler* than drive-mirror, and forcing those users to install Drive Desktop is gratuitous.
- **(b)** v1 supports drive-mirror AND indy as first-class peers. Pro: matches the natural shape of the user base; indy mode is genuinely simpler (no mount detection, no B1 prereq); architectural cost is small *now* but grows if retrofitted later.

**Resolution**: **(b)**. Indy mode is a first-class peer of drive-mirror in v1. Code structure assumes both from day one. The architectural cost is cheaper to absorb at the foundation than to retrofit after 5 more prereqs lock in Drive assumptions.

### 3. Drive-stream support in v1

**Pros of accepting drive-stream:**
- Doesn't lock out users with low local disk.
- Existing Stream-mode users don't need to migrate to Mirror just to use ErgodixDocs.

**Cons of accepting drive-stream:**
- Path is `~/Library/CloudStorage/GoogleDrive-<email>/` — email-dependent, fragile to detect (we'd have to enumerate the directory, find the GoogleDrive-* match, possibly with multiple accounts).
- Stream files are placeholders; opening triggers a download → flaky-network hangs hit users who think they're working offline.
- Render walks the corpus tree concatenating preambles; that's many file reads → many download triggers in stream mode → slow + unreliable.
- Future AI continuity reads many more files → same problem at higher scale.
- More code paths to maintain; more edge cases (auth flow, multiple accounts, sign-in state).

**Resolution**: **drive-stream not supported in v1.** Detection surfaces a clear `failed` status with remediation: "Switch Drive for Desktop to Mirror mode in Drive Preferences, then re-run cantilever." If a real user complains we revisit. The minimal docs we ship should say *what's needed* (Mirror mode, signed in), not *how to click through Google's settings menus that change every quarter*.

### 4. Settings cascade — does `bootstrap.toml` cover it?

**Existing state**: `settings/bootstrap.toml` exists with one field (`mactex.install_size`). `ergodix/settings.py` loads it. CLAUDE.md mentions `settings/floaters/<name>.toml` for per-floater settings, but no file has been written.

**The missing layer** (the user surfaced this): a settings layer that applies regardless of which floater is active. Not installer-specific. Not floater-specific. The SWAG layer ("Stuff We All Get").

The `bootstrap.toml` name is overloaded today — it currently holds settings that apply to every cantilever run, but its name suggests installer-only. The right structure is three tiers:

- **`settings/defaults.toml`** — applies to every cantilever run, every floater. The SWAG layer. Industry-standard term: "defaults" or "base settings."
- **`settings/bootstrap.toml`** — installer-specific overrides only (mactex install size, brew env, etc.). Narrowed scope.
- **`settings/floaters/<name>.toml`** — per-floater overrides (writer-specific, editor-specific).

**Load order** (most-general first, leaf-most wins):

```
defaults.toml → bootstrap.toml (during cantilever) → floaters/<active-floater>.toml (when that floater runs)
```

**Resolution**: introduce `settings/defaults.toml`. Migrate `mactex.install_size` from `bootstrap.toml` to `defaults.toml` (it's not installer-only — it's a project-wide preference). `bootstrap.toml` retains the installer-only fields it accumulates over time. `floaters/<name>.toml` lands when first per-floater override is needed. `ergodix/settings.py`'s loader extends to read all three with the documented load order.

### 5. B1 (Drive Desktop install) under indy mode

**B1's job today**: install Drive for Desktop via brew --cask, verify it's running.

**Under indy mode**: pointless. The user doesn't sync via Drive; installing Drive Desktop is gratuitous bloat.

**Resolution**: **B1 becomes conditional.** Cantilever's pre-flight detects sync transport from `CORPUS_FOLDER`. If indy mode, B1 is filtered out of the prereq list before inspect runs. The mechanism: B1's `inspect()` checks the detected mode and returns `status="ok"` with `current_state="indy mode; Drive Desktop not required"` when sync is indy. Drives the same plan-display semantics as any other "already satisfied" prereq.

### 6. B2 dispatches

**B2's job in the canonical (drive-mirror) case**: detect the Drive mount path, validate `CORPUS_FOLDER` exists under it, hand-fail on missing or stream-mode situations.

**B2's job under indy mode**: validate `CORPUS_FOLDER` resolves to a real directory. Nothing else. No mount detection. No Drive interaction.

**Resolution**: B2 dispatches on detected mode. The dispatch logic lives in a small helper (`detect_sync_transport(corpus_folder) -> SyncMode`) — testable, single-responsibility. The two code paths share their existence-check logic; only the mount-detection / stream-rejection logic is gated behind drive-mirror.

The `failed` cases B2 surfaces:
- `CORPUS_FOLDER` doesn't exist → `failed`, remediation: "Create the folder under `<detected mode>` and re-run, or update `CORPUS_FOLDER` in `local_config.py`."
- Drive mode detected but path is under Stream not Mirror → `failed`, remediation: "Switch Drive for Desktop to Mirror mode in Preferences."
- Drive mode detected but Drive Desktop isn't running → `failed`, remediation: "Start Drive for Desktop and sign in." (Cross-references B1's check.)

## Resolution summary

All six questions resolved as above. ADR 0014 will lock:

1. Auto-detect sync transport from `CORPUS_FOLDER` location; remove `SYNC_MODE` from `local_config.example.py`.
2. Indy mode is a first-class peer of drive-mirror in v1.
3. Drive-stream not supported in v1; clear remediation.
4. Three-tier settings cascade: `defaults.toml` (SWAG) + `bootstrap.toml` (installer-only) + `floaters/<name>.toml` (per-floater). Migrate `mactex.install_size` to `defaults.toml`.
5. B1 conditional on detected sync transport.
6. B2 dispatches via `detect_sync_transport(corpus_folder)`.

## Open considerations not blocking ADR 0014

- **What does `detect_sync_transport` use as its "known Drive mount paths" list?** macOS knows `~/My Drive` (Mirror) and `~/Library/CloudStorage/GoogleDrive-*/` (Stream); Linux and Windows differ. v1 is macOS-only per existing assumptions — a Linux/Windows port revisits this list. Cross-references the deferred `bootstrap.ps1`.
- **Does the user need a way to *force* a transport mode?** (e.g., "I have a Drive folder but I don't want to use Drive sync — treat it as indy.") Probably not in v1; auto-detect is the contract. If a real user surfaces a use case, an `OVERRIDE_SYNC_TRANSPORT = "indy"` field in `local_config.py` is the obvious escape hatch — file as parking-lot if the need arises.
- **Network-availability vs. sync-transport are independent axes.** Already correctly handled by the existing `ergodix/connectivity.py` (network probe at run-start). Cross-checked in the spike but no new architecture needed — just confirming the two stay independent.
- **`ErgodixDoc.map`** (the corpus index parking-lot story on `docs/parking-lot-interview-toolbox-map`, PR #34) lives at `_AI/ergodix.map` regardless of sync transport — both drive-mirror and indy mode write the index to the same relative location. No interaction with this spike.
