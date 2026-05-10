# ADR 0008: Sync rename, config ownership, auto-fix bound, static-analysis stance

- **Status**: Accepted
- **Date**: 2026-05-03
- **Spike**: (none — bundle of small decisions surfaced during the Story 0.8 self-audit)
- **Touches**: [ADR 0001](0001-click-cli-with-persona-floater-registries.md), [ADR 0002](0002-repo-topology-and-editor-onboarding.md), [ADR 0004](0004-continuous-repo-polling.md), [ADR 0007](0007-bootstrap-prereqs-cli-entry.md)

## Context

Self-audit at the close of Story 0.8 surfaced several small misalignments and gaps that don't individually warrant a spike but together would create real friction during implementation. Bundling them here keeps the ADR set tidy.

## Decisions

### 1. Rename `ergodix sync` to disambiguate

The single subcommand `sync` was implicitly doing three different jobs:

- Editor's outbound push after Cmd+S (per ADR 0002 / 0006)
- Polling job's periodic invocation (per ADR 0004)
- Cantilever-time slice-repo setup (already separate as cantilever op `D5` per ADR 0003)

Renaming:

- **`ergodix sync-out`** — editor's outbound push to their slice repo. What the auto-sync VS Code task fires on save. Replaces `sync` references in ADR 0002 and ADR 0006.
- **`ergodix sync-in`** — polling-job invocation. Fetches remote changes; persona-specific behavior (writer pulls main; editor checks PR review comments; etc.). Replaces `sync --background` references in ADR 0004.
- **Cantilever's slice-repo setup** stays as cantilever operation `D5` (poller install) and gains companion ops for slice clone where needed. No subcommand rename.

The two existing ADRs that reference `ergodix sync` keep their text; this ADR is the canonical reference for the renames going forward. README and docs updated to match.

### 2. `local_config.py` vs. `settings/*.toml` ownership rule

Both hold configuration. Different scopes:

- **`local_config.py`** lives in the repo root and is **gitignored**. It's **per-machine** state: absolute paths (Drive mount, corpus folder), tokens file path, sync mode. Each user has their own. Editing it changes only that user's environment.
- **`settings/bootstrap.toml`** and **`settings/floaters/<name>.toml`** are **committed to the repo**. They're **per-repo** behavior config: which operations cantilever runs, criticality flags, floater op-additions, exclusive_with constraints. Changes affect every user of this repo.

**Rule of thumb**: if changing the value affects only this machine, it goes in `local_config.py`. If changing the value should change behavior for every contributor, it goes in `settings/`.

This rule is documented in `local_config.example.py` (header comment) and in `settings/README.md` (new file, written when settings/ is created).

### 3. Auto-fix iterative bound

ADR 0007's `CheckResult.auto_fix` callable returns a new `CheckResult`. Without a bound, repeated `failed → auto_fix → CheckResult(failed, auto_fix=...)` could loop forever.

**Decision**: cantilever invokes `auto_fix` at most **once per operation**. If the retried `check()` still fails, cantilever treats it as terminal (abort-fast per ADR 0003). The retry is iterative, not recursive — implemented as a single conditional, not as a recursive call.

Implementation sketch:

```python
result = check()
if result.status == "failed" and result.auto_fix:
    fixed_result = result.auto_fix()
    result = check()  # re-evaluate, no further retry
if result.status == "failed":
    abort_with_remediation(result)
```

### 4. Static-analysis stance — ruff + mypy

Adopted from day one in `pyproject.toml`:

- **`ruff`** (formatter + linter, rust-fast). Replaces black + flake8 + isort. Default config plus a small project ruleset.
- **`mypy`** (static type checking). Strict mode for `ergodix/`; relaxed for `tests/`.

Added to dev deps:

```toml
[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "ruff",
    "mypy",
]
```

CI runs `ruff check`, `ruff format --check`, and `mypy ergodix/` on every push as gating checks.

Rationale: `ruff` is the modern Python convention as of 2026 — it's faster and has fewer config files than the black + flake8 + isort stack it replaces. `mypy` strictness for the package catches contract drift early. Cost of adoption is one config block in `pyproject.toml`; cost of *not* adopting compounds with every new module.

## Consequences

**Easier:**

- Three-meaning `sync` becomes self-explanatory at the CLI surface.
- New contributors have a one-paragraph rule for where config goes.
- Cantilever cannot accidentally infinite-loop on a bad auto-fix.
- Style drift doesn't accumulate over the ~50-module implementation phase.

**Harder:**

- Existing ADR text mentions `ergodix sync` and refers readers here for the current names. Mild navigational cost.
- `mypy --strict` will catch things during refactors that would otherwise have been silent. That's the point, but expect occasional implementation-time friction.

**Accepted tradeoffs:**

- The auto-fix bound is "exactly one retry, no more." More sophisticated retry policies (exponential backoff, classified-failure-aware retry) are deferred until they're actually needed.
- `ruff format` replaces `black`. If the project ever has contributors with strong black preferences, ruff's black-compatible formatter satisfies them.

## Alternatives considered

- **Keep `sync` overloaded; document the three meanings**: rejected. Naming is cheap; confusion compounds.
- **Auto-fix recursion with a depth limit (3? 5?)**: rejected. Auto-fix should be a single deterministic correction. If one pass doesn't fix it, the operation needs human attention, not more automated retries.
- **Black + flake8 + isort + mypy**: rejected. Modern Python tooling has consolidated; ruff is the right choice in 2026.
- **No static analysis (defer until later)**: rejected. Cost grows with codebase size; landing it now is cheap.

## References

- [Story 0.8 self-audit](../stories/SprintLog.md) — origin of the items in this ADR.
- [ADR 0007](0007-bootstrap-prereqs-cli-entry.md) — `CheckResult` dataclass that this ADR bounds.
- [ADR 0001](0001-click-cli-with-persona-floater-registries.md), [ADR 0002](0002-repo-topology-and-editor-onboarding.md), [ADR 0004](0004-continuous-repo-polling.md), [ADR 0006](0006-editor-collaboration-sliced-repos.md) — touched by the `sync` rename.
