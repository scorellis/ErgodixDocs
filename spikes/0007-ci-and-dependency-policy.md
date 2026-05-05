# Spike 0007: CI workflow design and dependency-pin policy

- **Date range**: 2026-05-04
- **Sprint story**: [Story 0.10 — TDD scaffolding](../SprintLog.md). The CI task in Story 0.10 was deferred until this spike answered the policy questions surfaced by the Copilot review of 2026-05-04.
- **ADRs produced**: [ADR 0009 — CI workflow and dependency-pin policy](../adrs/0009-ci-and-dependency-policy.md)

## Question

Six policy questions surfaced by the Copilot review:

1. CI workflow design — what the actual `.github/workflows/*.yml` file looks like.
2. What runs on each push — the order and parallelism of test/lint/typecheck/coverage steps.
3. What blocks merge — which checks earn the right to gray out the Merge button.
4. Multi-platform matrix — how many OS × Python combinations to cover.
5. Coverage ratchet — how to lift the coverage floor over time without it becoming busy-work.
6. Dependency-pin policy — Copilot flagged that `pyproject.toml` has lower-bound-only deps, fragile against fast-moving APIs (anthropic, google clients).

## Discussion

### Cost calibration

`ErgodixDocs` is a public repo. GitHub Actions runners are free and unmetered for public repos, including macOS and Windows. Multi-platform matrix carries no cost. The corpus repo (`tapestry-of-the-mind`) is private but holds prose, not code — no CI needed. The author confirmed this; corpus-side tooling, if it ever appears, would live in a public tooling repo with its own CI rather than on the prose repo.

### Dependency-pin policy — author's framing

The author asked: "I'd prefer to have local test deployments where we catch breaking changes and fix them before they make it to Main. Would it be possible to have an unbounded upper end on dependencies, and then when we break, we fix it and push to main with pinned versions?"

This is the well-known **"applications pin, libraries don't"** pattern (Donald Stufft, pypa). The shape:

- **`pyproject.toml`** keeps permissive `>=` bounds — the abstract contract.
- **A lockfile** (`uv.lock` or `requirements.lock`) pins exact versions — the concrete reproducible environment.

CI then runs two jobs:

- **Locked**: installs from the lockfile. Gating; blocks merge. Proves the known-good environment still works.
- **Latest**: installs from `pyproject.toml` with no constraints. Informational; does NOT block. Catches upstream breakage before it lands in the lock.

When the latest job fails: fix the code, regenerate the lock with the new versions, commit the fix + new lock together. Main is always green against pinned versions; the latest job is the tripwire.

### Tooling choice for the lock — uv

[`uv`](https://github.com/astral-sh/uv) is the modern choice in 2026 Python:

- `uv lock` generates the lockfile from `pyproject.toml`
- `uv sync` installs exactly what's locked
- 10–100× faster than pip-tools for dependency resolves
- Single binary, no Python bootstrap required (Rust)
- Reads `pyproject.toml` natively; doesn't fork our config

Alternative considered: `pip-tools` — same pattern, slower, ubiquitous. Picked `uv` for speed and modern alignment.

### What runs

In one parallel CI job per matrix cell:

1. Checkout code
2. Install Python (matrix-specified version)
3. Install `uv`
4. `uv sync --extra dev` (locked) OR `uv sync --extra dev --upgrade` (latest job)
5. `ruff check ergodix/ tests/`
6. `ruff format --check ergodix/ tests/`
7. `mypy ergodix/`
8. `pytest --cov=ergodix --cov-report=term-missing --cov-report=xml`
9. Upload coverage artifact

Steps 5–8 run sequentially within the job. Failure in any step fails the job. Multiple matrix cells run in parallel.

### What blocks merge

GitHub's "required checks" feature gates the Merge button. Decision:

| Check | Required? | Rationale |
|---|---|---|
| `pytest` (locked, all matrix cells) | **Yes** | Test failure = broken behavior |
| `ruff check` | **Yes** | Lint cheap; trivial to fix; no reason to let it slide |
| `ruff format --check` | **Yes** | Same |
| `mypy` (locked, all matrix cells) | **Yes** | Strict typing is a chosen discipline (ADR 0008); enforce it |
| Coverage gate | **Yes when ratchet floor exceeds 0** | See coverage section |
| `pytest` (latest, informational) | **No** | Catches upstream regressions; failure is a heads-up, not a blocker |
| `mypy` (latest, informational) | **No** | Same |

### Multi-platform matrix

Public repo + free Actions = no cost reason to skimp. v1 matrix:

- **OS**: macOS-latest, ubuntu-latest, windows-latest
- **Python**: 3.11, 3.12, 3.13

Cross-product = 9 cells per push. Each cell runs in parallel. Wall-clock time bounded by slowest cell (probably Windows installing dev deps).

The "latest" job doesn't matrix — single Linux + Python 3.13 cell is enough to detect upstream breakage; matrixing the tripwire is wasted compute.

### Coverage ratchet

`pytest-cov` writes coverage on every run. Two policy options:

- **Hard floor that ratchets up**: set `cov-fail-under=N`; bump N manually whenever real coverage exceeds the next milestone (50, 60, 70, 80%).
- **Diff coverage**: every PR's *new* lines must have coverage ≥ X%. Older code is grandfathered.

Decision: **hard floor that ratchets**, starting at 0% (current). Ratchet schedule:

- 0% until any module has tests landed beyond auth/version (current state).
- 50% once 5+ modules have test coverage.
- 70% once 15+ modules covered.
- 80% as the standing floor when most of `ergodix/` is implemented.

Diff-coverage is more disciplined but requires the `diff-cover` tool and more configuration. For a single-author project in pre-release, hard-floor ratcheting is enough discipline. Revisit if external contributors arrive.

### Workflow file shape

One file: `.github/workflows/ci.yml`. Two jobs declared:

- `test-locked` (matrixed 3 OS × 3 Python = 9 cells, gating)
- `test-latest` (single cell, informational)

`continue-on-error: true` on the latest job so its failure shows as yellow rather than red and doesn't block PRs.

Push triggers: every push to `main`, every PR opened against `main`. Branch protection on `main` requires the gating jobs.

### Dependency upper-bound exception list

Even with the locked/latest split, some dependencies have a track record of breaking minor releases. For those, additionally cap upper bounds in `pyproject.toml` so end users installing without the lock don't get burned:

- `anthropic ~= 0.40` (cap at major version)
- `google-api-python-client ~= 2.100` (same)

Other deps (`click`, `keyring`) have stable APIs — leave at lower-bound only.

## Decisions reached

- **CI runs only on `ErgodixDocs` (public repo)**. Corpus repos get no CI. → [ADR 0009](../adrs/0009-ci-and-dependency-policy.md)
- **Two-job CI design**: locked (gating) + latest (informational tripwire). → ADR 0009
- **uv as the lockfile tool**. `uv.lock` committed to the repo. `uv sync` installs locked; `uv sync --upgrade` for the latest job. → ADR 0009
- **Multi-platform matrix**: macOS + Linux + Windows × Python 3.11/3.12/3.13 = 9 cells. Free on public repo. → ADR 0009
- **Required checks**: pytest, ruff check, ruff format --check, mypy. Latest-job equivalents are informational. → ADR 0009
- **Coverage ratchet**: hard floor; bump manually at 50/70/80% milestones. → ADR 0009
- **Dependency caps for fast-moving APIs**: `anthropic ~= 0.40`, `google-api-python-client ~= 2.100`. Others remain `>=`. → ADR 0009

## Loose threads

- Diff-coverage migration if external contributors arrive — revisit at that point.
- A nightly cron run of the latest job could provide earlier signal than push-triggered runs. Worth adding once the project has any real velocity.
- Codeownership-driven required reviewers (CODEOWNERS file) — not part of CI proper but related; defer to a future spike if needed.
- Pre-commit hooks running ruff + mypy locally so developers don't push obvious failures — designed during developer-floater cantilever implementation.
