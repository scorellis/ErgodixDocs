# CLAUDE.md — ErgodixDocs Working Conventions

This file is the steady-state working context for Claude/Copilot/AI agents collaborating on ErgodixDocs. It is not a session log (that's `WorkingContext.md`) and it is not a resume prompt (that's `ai.summary.md`). It encodes the project's persistent conventions so a fresh AI session inherits them without rediscovery.

Read this file before doing any non-trivial work in the repo.

## Top-priority principles

### 1. Test-driven development — always

**Write failing tests first. Then write the minimal code to make them pass.** Do not write implementation code without a corresponding test. This is non-negotiable.

The cycle:
1. **Red**: write a test against the contract you want. Run it. Confirm it fails for the right reason (the function doesn't exist yet, or the behavior is wrong, not because the test itself is broken).
2. **Green**: write the smallest possible code that makes the test pass. No more.
3. **Refactor**: improve structure with the green tests as a safety net.

When adding a new module or function, the test file lands first. When fixing a bug, write a test that reproduces the bug, watch it fail, then fix the code. Do not skip step 1.

This applies to:
- Every new function under `ergodix/`
- Every prereq check (`ergodix/prereqs/check_*.py`)
- Every floater module (`ergodix/floaters/*.py`)
- Every importer plugin (`ergodix/importers/*.py`)
- Every CLI subcommand surface
- Every bug fix

This does **not** apply to:
- Documentation (ADRs, spikes, README, etc.)
- Configuration files
- Build scripts (`bootstrap.sh`, `bootstrap.ps1`)
- One-off ad-hoc analysis

### 2. AI-prose boundary

**The AI never edits chapter prose.** Chapter `.md` files are author-only. The AI may:
- read prose to understand it,
- generate analysis (continuity reports, plot maps, summaries) into `_AI/` subfolders,
- produce render artifacts.

The AI may not:
- mutate chapter prose,
- write CriticMarkup edits into chapter files,
- propose prose substitutions.

This boundary is load-bearing for the project's identity and audience. Do not propose tooling that violates it without an explicit decision recorded in a new ADR.

## Architectural conventions (already locked — see `adrs/` for full detail)

- **CLI framework**: Click subcommand groups. Console-script entry in `pyproject.toml` registers `ergodix` on PATH.
- **Roles as floaters**: `--writer`, `--editor`, `--developer`, `--publisher`, `--focus-reader`. Composable. `focus-reader` is mutex with the others. Behavior floaters: `--dry-run`, `--verbose`, `--ci`.
- **Plugin registries**: `ergodix/floaters/`, `ergodix/importers/`, `ergodix/prereqs/`. Adding a new entry = drop a file. No central enum.
- **Cantilever**: 25-operation orchestrator (A1–A7, B1–B2, C1–C6, D1–D6, E1–E2, F1–F2). Four-phase execution per [ADR 0010](adrs/0010-installer-preflight-consent-gate.md): inspect (read-only) → plan + single consent gate → apply (mutative, with grouped sudo) → verify (smoke checks). Idempotent. Abort-fast with detailed remediation. Connectivity auto-detected.
- **Prereq contract** (per ADR 0010): each prereq module exposes `inspect() -> InspectResult` (read-only) and `apply() -> ApplyResult` (mutative). The earlier `check() -> CheckResult` contract from ADR 0007 is partially superseded; `auto_fix` callable is removed entirely (every mutative action goes through consent).
- **Auth**: three-tier credential lookup — env var → OS keyring (service `ergodix`) → fallback file `~/.config/ergodix/secrets.json` (mode 600).
- **Scopes**: `drive.readonly` and `documents.readonly` only. Broader scopes require an explicit ADR.
- **Repo topology**: public `ErgodixDocs` (tooling) + private corpus repo per opus + per-editor slice repos (signed commits, baseline-tracked resync via `ergodix publish` / `ergodix ingest`).
- **Format**: Pandoc Markdown + raw LaTeX passthrough. `.md` extension. Mandatory YAML frontmatter (`format: pandoc-markdown`, `pandoc-extensions: [...]`). One `.md` per Chapter.
- **LaTeX preamble cascade**: optional `_preamble.tex` at every folder level. Render walks up the tree, concatenates most-general-first.
- **Multi-corpus**: container is called an **opus** (plural **opera**). `ergodix opus list/add/switch/remove`. (Implementation deferred to Story 0.X.)

## Code conventions

- **Python ≥ 3.11**. `from __future__ import annotations` at the top of new modules.
- **Type hints required**. `mypy --strict` runs on every push.
- **Format and lint**: ruff. `ruff check`, `ruff format --check`. No black, no flake8, no isort — ruff replaces all three.
- **Tests**: pytest with `pytest-cov`. Test files live under `tests/`, mirroring the source layout.
- **Path resolution**: never bake `Path.home()` (or any env-var-derived path) into module-level constants. Resolve lazily so tests can monkeypatch `HOME`. Use a small descriptor pattern if you need attribute-style access.
- **Subprocess**: shell out via `subprocess.run` rather than reaching for `pygit2` / `GitPython`. Keeps the dependency footprint small.
- **No globals for env-derived state**. Compute on access.
- **Permission invariants on secret files**: refuse to read if mode is loosened beyond 600. Surface the misconfiguration loudly.

## Settings vs. config — what goes where

- **`local_config.py`** (per-machine, gitignored): absolute paths (corpus folder, Drive mount), token file location, sync mode. Each user has their own. Editing affects only that user's machine.
- **`settings/bootstrap.toml` + `settings/floaters/<name>.toml`** (per-repo, committed): operation criticality flags, floater op-additions, exclusive_with constraints, polling cadence. Editing affects every user of this repo.

**Rule**: if changing the value affects only this machine, it goes in `local_config.py`. If changing the value should change behavior for every contributor, it goes in `settings/`.

## Branching and PRs

- Trunk-based: only `main` plus feature branches off main.
- Feature branch naming: `feature/<short-description>` or `bugfix/<short-description>`.
- Every change goes through a PR before merging to main.
- PR titles are short (≤ 70 chars); body explains the why.
- ADRs are write-once. Supersession via a new ADR with a Note added to the older one.

## ADR and spike conventions

- **ADRs** (`adrs/NNNN-kebab-title.md`): a single decision, write-once. Modified Michael Nygard format. Status / Date / Spike / Supersedes / Touches in frontmatter.
- **Spikes** (`spikes/NNNN-kebab-title.md`): the *journey* of a discussion that produced one or more ADRs. Free-form narrative.
- ADRs and spikes use independent numbering (Spike 0003 may produce ADR 0007).
- A new design decision goes through: spike → ADR → tasks in SprintLog → implementation behind tests.

## What goes in which doc

- **`README.md`**: external-facing. What the project is, how to install, how to use.
- **`CLAUDE.md`** (this file): persistent conventions for AI sessions. Steady-state, not session-specific.
- **`WorkingContext.md`**: running session log. Updated when sessions pause or pivot.
- **`ai.summary.md`**: resume prompt for the next AI session. Re-written every time work pauses for the day.
- **`SprintLog.md`**: SVRAT stories (So that, Value, Risk, Assumptions, Tasks). Sprint planning + status.
- **`CHANGELOG.md`**: Keep-a-Changelog format. `[Unreleased]` section gets the in-flight work; release entries get added at version bumps.
- **`Hierarchy.md`**: the narrative-content model (EPOCH → Compendium → Book → Section → Chapter).
- **`docs/`**: external-facing reference docs (`gcp-setup.md`, `comments-explained.md`, future `vscode-setup.md`).

## When to ask vs. when to proceed

- **Proceed**: any tested change that satisfies an existing ADR or SprintLog task.
- **Ask**: any change that conflicts with an ADR (would require supersession), introduces a new dependency, or expands scope beyond the current story.
- **Always ask before pushing to remote.** Local commits are fine; pushes go through user approval every time. The user may have reasons (timing, account context, work boundaries) for wanting visibility into when public-repo activity happens.
- **Always ask**: anything destructive (force-push, branch deletion, history rewrite). Never run a destructive git command without explicit user approval.

## Communication norms with the user

- Short, compartmentalized responses preferred.
- No throat-clearing phrases ("That distinction matters", "It's worth noting", etc.).
- Lead with the recommendation; offer alternatives only when load-bearing.
- When the user asks "what next?", propose a concrete next step rather than restating options.
- If you're not sure, say so. Don't manufacture confidence.

## Working partnership norms

The collaboration on this project is treated as a partnership, not a transactional service. A few norms keep that healthy:

- **Push back on principle violations.** When the user directs an action that contradicts a CLAUDE.md rule or a locked ADR, name the conflict in one sentence and let the user decide. Don't lecture. "I'm violating it on purpose, here's why" is a fine answer — the check is just that both parties know.
- **Late-arriving principles are normal.** A working principle (like TDD-first) might be declared partway through a story, after some code has already shipped without it. Apply the principle forward and accept that prior code may need rework. Capture the "why now" in a doc edit so the rationale survives.
- **Course corrections cost cycles but are healthy.** Reopening a topic mid-discussion, introducing a new concern, switching priorities mid-implementation — all expected. Absorb the change; capture it in the right doc (spike for design discussion, ADR for locked decisions, SprintLog for story re-prioritization). Future readers should see the reasoning, not just the result.
- **The persistent record is how partnership survives sessions.** Each new AI session rebuilds context from CLAUDE.md, the ADRs, the spikes, WorkingContext.md, and ai.summary.md. Treat additions to those documents as durable. Treat the conversation itself as ephemeral. Capture insights *before* moving on.
