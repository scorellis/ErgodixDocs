# Spike 0003: Cantilever semantics, settings architecture, run-record

- **Date range**: 2026-05-03
- **Sprint story**: [Story 0.8 — Architecture spike](../stories/SprintLog.md#story-08---architecture-spike-orchestrator-pattern-role-based-cantilever-editor-collaboration-model-design-spike), Topic 3
- **ADRs produced**: [ADR 0003 — Cantilever bootstrap orchestrator](../adrs/0003-cantilever-bootstrap-orchestrator.md), [ADR 0004 — Continuous repo polling](../adrs/0004-continuous-repo-polling.md)

## Question

What does `ergodix cantilever` actually *do*, mechanically? The author's earlier framing was "all-encompassing setup / upgrade / deploy" — a vibe, not a spec. Concretely:

1. The menu of operations cantilever can run.
2. Whether each is read-only, mutative, or destructive.
3. Whether cantilever is idempotent.
4. Network requirements.
5. Failure semantics (abort fast vs. continue and report).
6. Where settings live and how they're structured.

## Discussion

### The 19→21 operation menu

Strawman drawn from the existing `install_dependencies.sh` content, ADR 0001 (CLI structure), and ADR 0002 (editor persona steps). Six categories:

- **A — Environment bootstrap** (Homebrew, Pandoc, XeLaTeX, Python venv, Python deps, VS Code + extensions)
- **B — Drive integration** (install Drive for Desktop, detect mount mode + Tapestry path)
- **C — Repo + auth** (gh login, clone corpus, configure git identity, bootstrap `local_config.py`, `~/.config/ergodix/`, prompt for missing credentials)
- **D — Persona-specific tooling** (auto-sync VS Code task for editor, prose-linting hooks for writer/dev, dev deps + branch tracking for developer floater)
- **E — Verification & exit** (run `ergodix status`, print "you're done" message)

Author additions during discussion:

- **F1 — Pre-run: connectivity detection + load settings** so cantilever knows up-front what's available.
- **F2 — Post-run: write run-record** to `~/.config/ergodix/cantilever.log` so re-runs can detect upgrades.

Final count: 21 operations, A–F.

### Idempotency + upgrade detection

Author's emphasis: cantilever must be silently idempotent. Re-running detects upgrades, deploys them, never duplicates installs, never clobbers configs.

The hard sub-problem: detecting **breaking changes**. v1 strategy — log every run with versions and operations executed; flag major-version dependency bumps as "potentially breaking" warnings post-run. v1 doesn't try to *prevent* breaking changes automatically; it surfaces them.

Forward/backward compatibility observation from author: "Multiple machines should be able to run different versions. The only caveat would be some sort of major, breaking change — like, we decide to change the file format. That would be a major version change and would force an upgrade."

This aligns with the project's existing semver policy (CHANGELOG header). Recorded as a constraint on ADR 0003: cantilever's upgrade detection respects semver — minor/patch upgrades silent, major bumps surface a "breaking change — read the CHANGELOG before continuing" prompt.

### Skippable operations per persona

Author observation: not all personas need every operation. A writer may not need Drive integration; an editor doesn't need the developer-floater dev deps. The persona registry (ADR 0001) was already structured to support per-persona operation selection — this becomes more concrete: each persona's settings file declares which operations from the global menu it requires, which it requests but allows skipping, and which it ignores entirely.

### Prose linting concern

Author flagged: prose linting (smart quotes, double spaces, bad tabs) is appealing but ergodic-text artistry might be at odds with naive linting. Decision: prose linting is opt-in via the writer persona settings, default off, override-able per file (probably via a frontmatter flag or a `lint: skip` marker in CriticMarkup). Implementation deferred; recorded as a Story 0.2 sub-task.

### Failure semantics — abort fast with great messaging

Author landed on: abort-fast (option A from the strawman) but with very detailed remediation instructions and auto-fix attempts where safe. Sample failure messaging:

```
✗ Failed at step 17 of 21: A4 — Install XeLaTeX
  Reason: brew install --cask mactex failed (exit 1)
  Diagnosis: looks like there's not enough free disk space (~4 GB needed)
  Suggested fix:
    1. Free up at least 4 GB of disk space, OR
    2. Re-run with: ergodix --persona writer cantilever --basictex-instead
  After fixing, re-run cantilever — it will skip the 16 steps that already succeeded.
```

The "step X of Y" framing is a hard requirement: the author wanted users to know exactly how far cantilever progressed.

Auto-fix where possible (e.g. "Drive process not running — opening it for you... done. Re-running step.") avoids easy-to-fix failures becoming user-visible aborts.

### Settings architecture — `settings/` folder, per-concept files

Author's significant architectural addition: instance settings should live in compartmentalized files under a `settings/` folder, mirroring the registry concepts. This supports later flipping criticality, defaults, etc., without code changes.

Initial proposal had `cantilever-writer-settings.toml`, which read as if `cantilever > writer` was the order — contradicting the locked CLI shape from ADR 0001 (`ergodix --persona writer cantilever`, persona owns the invocation). Renamed to mirror runtime order:

```
settings/
  bootstrap.toml              # global cantilever settings: criticality flags, defaults
  personas/
    writer.toml
    editor.toml
    publisher.toml             # future
    focus-reader.toml          # future
  floaters/
    developer.toml
    dry-run.toml
    verbose.toml
    ci.toml
```

TOML chosen for human-readability + comments + Python stdlib support (`tomllib` since 3.11).

For v1: every operation marked `critical = true` in `bootstrap.toml`. Persona / floater settings can override later. Format:

```toml
[operations.A1]
description = "Detect platform"
critical = true

[operations.A4]
description = "Install XeLaTeX"
critical = true   # later: set false if user wants render to be optional
```

### Run-record location: per-machine

Considered: should the run-record live in the repo (committed) so multiple machines share a coordinated history? Resolution: **per-machine sufficient for v1**. Path: `~/.config/ergodix/cantilever.log`. The "team coordination" use case doesn't apply to a single-author + single-editor model. Easy to add later if it becomes needed.

### Connectivity = automatic detection, no `--offline` flag

Author refined: there's no `--offline` mode, just automatic detection at the start of every run (cantilever, sync, polling job). If offline, network operations no-op silently with a deferred-action marker; the user sees nothing if they didn't ask for anything network-dependent. Cron-friendly.

### What's NOT cantilever's job

Out of scope, kept as separate subcommands:

- `ergodix migrate` — explicit one-time corpus import.
- `ergodix render` — Pandoc → PDF, on demand.
- `ergodix sync` — outbound edit push, runs constantly via auto-sync hooks.
- OS-level updates — out of scope entirely.
- GCP project setup — manual one-time per `docs/gcp-setup.md`.

### Polling job — separate decision (becomes ADR 0004)

Toward end of discussion the author landed: there should be a job running every 5 minutes that polls the repo for changes, downloads the persona's working set, and silently no-ops when offline. This is a continuous-operation concern, not a bootstrap concern. Cantilever *installs* the poller as one of its operations; the poller itself runs independently.

Pulled out as ADR 0004 to keep ADR 0003 focused on bootstrap semantics.

## Decisions reached

- **21-operation menu** (A1 through F2), all idempotent. → [ADR 0003](../adrs/0003-cantilever-bootstrap-orchestrator.md)
- **Settings architecture** in `settings/` folder, per-concept TOML files mirroring the registries. → ADR 0003
- **Failure mode**: abort-fast with "step X of Y" progress messaging, detailed remediation, and auto-fix where safe. → ADR 0003
- **Connectivity**: automatic detection at run-start, offline = silent no-op for network operations. → ADR 0003
- **Run-record**: per-machine at `~/.config/ergodix/cantilever.log`. → ADR 0003
- **Upgrade detection**: silent for compat upgrades; major-version dependency bumps surface a "potentially breaking" warning. Honors semver. → ADR 0003
- **Continuous polling job**: separate concern; runs every 5 min via launchd (macOS), no-op when offline, persona-aware fetch behavior. → [ADR 0004](../adrs/0004-continuous-repo-polling.md)

## Loose threads / deferred questions

- **Prose linting design** — opt-in per writer persona; conservative defaults; override-able per file. Filed under Story 0.2.
- **Auto-fix catalog** — which failure modes have safe auto-fixes vs. require user action. Cataloged operation-by-operation during cantilever implementation.
- **Cross-platform poller** (Linux cron / systemd, Windows Task Scheduler) — v1 is macOS launchd only. Other platforms tracked as future port work.
- **Major-version upgrade UX** — the "you're on 0.x, this version is 1.x" prompt's exact wording and behavior decided when we ship 1.0.0. For now, the policy is locked.
