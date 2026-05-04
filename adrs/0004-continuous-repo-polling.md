# ADR 0004: Continuous repo polling

- **Status**: Accepted
- **Date**: 2026-05-03
- **Spike**: [Spike 0003 — Cantilever semantics, settings architecture, run-record](../spikes/0003-cantilever-semantics.md) (decision pulled out of the cantilever spike to keep [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) focused on bootstrap.)

## Context

Cantilever (ADR 0003) is a one-shot bootstrap orchestrator. Once it's installed the environment, the system needs an ongoing mechanism for each persona's machine to stay in sync with the corpus repo:

- **Writer** wants to see editor PRs landing on `main` quickly (without needing to manually `git fetch`).
- **Editor** wants to know if the author has merged their work or pushed conflicting changes (so they can rebase before adding more edits).
- **Future personas** (focus reader, publisher) want their local view to update without command-line interaction.

The author specified: a job running every 5 minutes that looks for changes to the repo, downloads the persona's working set, and silently no-ops when offline.

## Decision

ErgodixDocs installs a **continuous polling job** as part of cantilever. It runs every 5 minutes, checks the corpus repo for changes, performs persona-specific update behavior, and is offline-safe.

### Mechanism (per platform)

| Platform | Mechanism | v1? |
|---|---|---|
| **macOS** | LaunchAgent plist in `~/Library/LaunchAgents/com.ergodix.poller.plist`, loaded via `launchctl bootstrap` | yes |
| Linux | systemd timer + service unit (user-scoped: `~/.config/systemd/user/`) | future |
| Windows | Task Scheduler entry | future |

The cantilever operation that installs the poller (call it operation `D5` — added to ADR 0003's catalog as a follow-up edit) generates the platform-appropriate scheduler entry from a template.

### Cadence

**Default: 5 minutes.** Configurable per persona in `settings/personas/<name>.toml`:

```toml
[poller]
interval_seconds = 300
```

Editors might want shorter (60 sec — they're actively editing); focus readers might want longer (3600 sec — they read at human cadence). Persona-tunable.

### What the poller actually runs

The poller invokes `ergodix sync --background` (a flag indicating non-interactive, auto-mode behavior). Behavior is persona-aware via the persona registry from [ADR 0001](0001-click-cli-with-persona-floater-registries.md):

**Pre-action: connectivity check.**
- If offline: write a single-line marker to `~/.config/ergodix/poller.log` and exit 0. **No-op, no user disruption.**
- If online: continue.

**Writer persona behavior:**
- `git fetch origin`
- If `main` has new commits, `git pull --ff-only origin main` (only when the local branch is `main`; otherwise just fetch and notify via system notification).
- Check for new PRs via `gh pr list`; if there are unreviewed PRs, surface a notification.

**Editor persona behavior:**
- `git fetch origin`
- `git push` any pending local edits on the editor's working branch (the auto-sync flow from ADR 0002 normally handles this on Cmd+S; the poller is a safety net for when the editor closes VS Code mid-edit).
- Check for review comments on the editor's open PR; surface a notification if any.
- **Never auto-merges or auto-pulls into the editor's working branch** — protects in-progress edits from being clobbered.

**Future personas** declare their own poller behavior in their persona module.

### Offline = no-op, not "mode"

Offline is not a mode — it's the absence of network. The poller checks at the top of every run and silently skips network-dependent work when there is none. There is no `--offline` flag; there is no user-visible offline indicator. The user only notices the poller when it surfaces a notification (new PR, review comment, conflict).

This is consistent with cantilever's connectivity model from ADR 0003.

### Installation and removal

- **Install** is operation `D5` of cantilever, gated on persona settings (`settings/personas/<name>.toml` declares `poller.enabled = true`).
- **Removal** happens via `ergodix poller --uninstall` or by re-running cantilever with a persona whose settings have `poller.enabled = false`.
- Both operations are idempotent.

### Logging

Poller runs append to `~/.config/ergodix/poller.log` (separate from `cantilever.log`). One line per run:

```
2026-05-03T14:30:00Z OK fetched=2 pulled=0 notifications=1
2026-05-03T14:35:00Z OFFLINE
2026-05-03T14:40:00Z OK fetched=0 pulled=0 notifications=0
```

Log rotation: the poller truncates entries older than 30 days on each run.

## Consequences

**Easier:**

- Editors and writers stay in near-real-time sync without thinking about git.
- Offline laptops behave gracefully (cron-friendly, plane-friendly).
- The architecture extends to new personas: drop a new `personas/<name>.toml` with poller behavior + a function in the persona module.
- Decoupled from cantilever — the poller is a separate process, can fail independently, and can be unloaded for debugging without touching the bootstrap orchestrator.

**Harder:**

- launchd is the macOS-only mechanism for v1; Linux and Windows ports are future work, gated on actual demand.
- A misbehaving poller could spam notifications or cause unexpected git operations. Mitigation: the poller's behavior per persona is small, audit-able, and unit-testable.
- Notifications need a cross-platform abstraction eventually (`osascript` on Mac, `notify-send` on Linux, `BurntToast`-style on Windows); v1 is `osascript` only.

**Accepted tradeoffs:**

- 5-minute default cadence may feel slow during active collaboration; personas can shorten. Acceptable to start conservative.
- The poller deliberately doesn't auto-merge or auto-pull editor working branches. Safety > speed for prose editing.
- Per-machine poller log is parallel to per-machine cantilever log; team coordination not in scope (consistent with ADR 0003).

## Alternatives considered

- **Inotify / FSEvents file-watching** instead of polling: rejected. Watches local filesystem changes, not remote repo changes; doesn't solve "did Phil push something on his machine" without polling something anyway.
- **Webhook-driven push notifications**: rejected. Requires an always-on receiver process or a server endpoint we don't want to operate. Polling is frugal.
- **Manual `git pull` only**: rejected. Editors aren't git-savvy; defeats the zero-friction principle from ADR 0002.
- **Cantilever's bootstrap step doing this rather than a separate process**: rejected. Cantilever is one-shot; polling is continuous. Different lifecycles, different concerns.
- **A single shared poller for all personas**: rejected. Persona-specific behavior would force the shared poller to know about every persona; per-persona modules are the agreed extension surface (ADR 0001).

## References

- [Spike 0003](../spikes/0003-cantilever-semantics.md) — origin of this decision.
- [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) — cantilever installs the poller as one of its operations.
- [ADR 0001](0001-click-cli-with-persona-floater-registries.md) — persona registry the poller plugs into.
- [ADR 0002](0002-repo-topology-and-editor-onboarding.md) — editor persona that the poller serves as a safety net for.
