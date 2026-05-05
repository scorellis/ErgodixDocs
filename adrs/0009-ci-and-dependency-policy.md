# ADR 0009: CI workflow and dependency-pin policy

- **Status**: Accepted
- **Date**: 2026-05-04
- **Spike**: [Spike 0007 — CI workflow design and dependency-pin policy](../spikes/0007-ci-and-dependency-policy.md)
- **Touches**: [ADR 0008](0008-cleanup-sync-rename-ownership-autofix-static-analysis.md) — adds the actual CI workflow file that ADR 0008 referenced as paper-only.

## Context

ADR 0008 declared "CI runs `ruff check`, `ruff format --check`, and `mypy` on every push as gating checks" without committing the actual workflow file. The Copilot review of 2026-05-04 flagged this as paper policy and additionally surfaced two adjacent concerns: a lack of dependency upper bounds (especially on fast-moving APIs like `anthropic` and `google-api-python-client`), and a coverage gate set to `cov-fail-under=0` with no schedule for tightening it.

The author's preferred dependency workflow (recorded in Spike 0007 and refined 2026-05-05): main has to be **locked across the board** because end users installing via `pip install ergodix` only see `pyproject.toml`, not our internal `uv.lock`. So locks must live in both places — `pyproject.toml` for the public contract end users consume, `uv.lock` for our own reproducible environment. Feature branches push the threshold via the `test-latest` tripwire job; main runs the locked job. Caps are added reactively (when something breaks) during pre-release; proactively (across all known-fast-moving deps) once Story 0.7 ships pip-installability.

## Decision

### Scope

CI runs on the **public `ErgodixDocs` repo only**. Corpus repos (private, prose-only) get no CI. If future tooling lands and needs CI, that tooling lives in a public repo with its own CI.

### Workflow file

A single file at `.github/workflows/ci.yml`. Two top-level jobs:

- **`test-locked`** (gating) — runs against the committed lockfile. Matrix: macOS, Ubuntu, Windows × Python 3.11, 3.12, 3.13 = 9 cells. All cells must pass for merge.
- **`test-latest`** (informational tripwire) — runs against unbounded dependency resolution from `pyproject.toml`. Single cell: Ubuntu + Python 3.13. `continue-on-error: true` so its failure shows yellow, doesn't block.

Triggers: every push to `main`, every PR opened against `main`.

### What runs in each job

In order, sequentially within a cell, failure stops further steps:

1. `actions/checkout@v4`
2. `actions/setup-python@v5` with the matrix Python version
3. Install `uv` (from `astral-sh/setup-uv@v3`)
4. **Locked**: `uv sync --extra dev`
   **Latest**: `uv sync --extra dev --upgrade --resolution=highest`
5. `uv run ruff check ergodix/ tests/`
6. `uv run ruff format --check ergodix/ tests/`
7. `uv run mypy ergodix/`
8. `uv run pytest --cov=ergodix --cov-report=term-missing --cov-report=xml`
9. (Locked job only) Upload coverage XML as a workflow artifact

### Required checks for merge

GitHub branch protection on `main` requires:

- All 9 cells of `test-locked` (steps 5–8 within each cell)
- That's it.

The `test-latest` job is **not** required for merge. Its failures appear in the PR view as warnings the author can address proactively.

### Dependency-pin policy

Two separate locks, two different jobs, depending on whether you're protecting **us** (reproducible internal environment) or **end users** (whoever does `pip install ergodix` once Story 0.7 ships).

#### The two lock locations

- **`pyproject.toml`** — ships with the package. End users installing via `pip install ergodix` see only this. The bounds here are the public contract.
- **`uv.lock`** — committed to the repo, used by our CI and our local dev environment. End users **never see this file**. It pins exact versions for every transitive dependency so our environment is reproducible bit-for-bit.

#### Where each lock lives, by branch and context

| Context | `pyproject.toml` bounds | `uv.lock` | Net effect |
|---|---|---|---|
| **`main` (the published product)** | Tight: `>=` floors plus `~=` upper caps on any dep that has shown breaking changes within minor releases | Committed; pinned exact versions | Both locks active. End users installing from `pip install ergodix` get a known-good range; our CI on main is reproducible exactly. **Main is locked across the board.** |
| **Feature branch — `test-locked` job (gating)** | Same `pyproject.toml` as main | Same `uv.lock` as main | Mirrors main's environment exactly. PRs prove they pass on the locked environment before merge. |
| **Feature branch — `test-latest` job (informational tripwire)** | Same `pyproject.toml` (the caps still apply by default) | **Ignored** | `uv sync --upgrade` resolves to the newest versions allowed by `pyproject.toml`. To deliberately probe past a cap, use `uv sync --upgrade-package <name>=>X.Y` for that specific package — used when we want to test "would removing this cap work?" |
| **Local dev — reproduce CI** | Read | Read | `uv sync` — exact mirror of CI's locked job. |
| **Local dev — push the threshold** | Read | Ignored | `uv sync --upgrade` — installs the latest within `pyproject.toml` caps. Catches what the CI tripwire would catch, locally and faster. |

#### Reactive capping (Phase 1, pre-Story-0.7)

While the project is pre-release and not yet pip-installable for outside users:

- `pyproject.toml` starts with `>=` floors only — no preemptive caps.
- `uv.lock` carries the reproducibility burden alone.
- When `test-latest` catches breakage:
  - **Fix is simple**: update code, regenerate `uv.lock`, commit fix + new lock together. No cap needed.
  - **Fix is complex or undesirable**: add a `~=` (or `<X.0`) cap to `pyproject.toml` for that dep. Regenerate `uv.lock`. Commit the cap + lock. Document in `CHANGELOG.md`.

This matches the author's preference: don't preemptively cap; cap reactively when forced.

#### Proactive capping (Phase 2, when Story 0.7 ships pip install)

When end users start consuming `ergodix` via `pip install`:

- Audit `pyproject.toml` and add `~=` caps to every dep with a known history of breaking-change minor releases (in 2026, that's at least `anthropic` and `google-api-python-client`).
- Reason: `uv.lock` doesn't ship with the package install; only `pyproject.toml` constraints reach end users. Without caps, end users get whatever PyPI has, which can break their install at any time outside our control.
- `test-latest` job continues as a tripwire, now testing past the caps via `--upgrade-package` to detect when caps could be safely lifted.
- This phase boundary is documented in CHANGELOG when it crosses.

#### Workflow when `test-latest` fails

1. Author sees a yellow tripwire on a PR (or a nightly cron run on main once we add one).
2. Reproduces locally: `uv sync --upgrade && pytest`.
3. Decides:
   - Fix the code → update, regenerate `uv.lock`, commit fix + lock.
   - Cap the dep → add `~=` (or `<X.0`) in `pyproject.toml`, regenerate `uv.lock`, commit cap + lock + CHANGELOG note.
4. PR lands; locked job (gating) passes against the new lock; main stays green.

### Coverage policy

Hard-floor ratchet, schedule below. `cov-fail-under` lives in `pyproject.toml`'s pytest config:

- **Now (auth + version only)**: `cov-fail-under=0`. No gate.
- **5+ modules covered**: bump to 50%.
- **15+ modules covered**: bump to 70%.
- **Most of `ergodix/` implemented**: bump to 80% as the standing floor.

Each ratchet bump is a deliberate one-line PR after observing real coverage exceeds the next milestone. No automatic ratchet — explicit human decision keeps the project honest.

Diff-coverage tooling (per-PR coverage on new lines only) is rejected for v1: requires `diff-cover`, more config, and the project has one author. Revisit when external contributors arrive.

### What this is not

- Not a release pipeline. Pushing to PyPI / Homebrew / Mac App Store is Story 0.7 (Distribution prep) work.
- Not a docs-build pipeline. README + ADRs + spikes are read-as-source on GitHub; no rendering.
- Not a security scanner. `pip-audit` / GitHub Dependabot can layer on later if needed.
- Not a release-tagging automation. Manual tagging until the project has a real release cadence.

## Consequences

**Easier:**

- Every PR runs the full quality gate without manual effort.
- Forward-compatibility regressions (a dep ships a breaking change) surface within hours, not when a user installs.
- Locking with `uv` is fast (typically under a second for resolves) and the lockfile is small.
- Multi-platform coverage from day one ensures the cross-platform claim from ADR 0007 (macOS + Linux + Windows) is validated, not aspirational.
- Coverage ratchet is opt-in discipline: the project can move fast in early days without a coverage gate making every PR painful.

**Harder:**

- Three OSes × three Python versions = 9 cells per push. Wall-clock time bounded by slowest cell (~3–5 minutes typically). Acceptable; free on public repo.
- The author has to keep `uv.lock` current. `uv lock` is a one-line command but easy to forget. Mitigate by adding a CI step that fails if `uv lock --check` shows the lockfile is stale relative to `pyproject.toml`.
- Two CI jobs means two reads of all the same setup output. Minor noise in the GitHub UI.
- Coverage ratchet is manual; we have to remember to bump it. Acceptable for v1.

**Accepted tradeoffs:**

- `test-latest` is informational, not gating. A truly catastrophic upstream change that breaks everything still merges if the author isn't paying attention. Counter: the gating `test-locked` job won't break, and the user sees the yellow tripwire on every push so it's hard to miss.
- We pick `uv` over `pip-tools` despite `pip-tools` being older and more ubiquitous. `uv` is the modern choice in 2026 Python; the speed difference matters in the dev loop.

## Alternatives considered

- **Single CI job with no lock/latest split**: rejected. Either the build is fragile against upstream churn (no lockfile) or it never catches upstream breakage (lockfile only).
- **Pin exact versions in `pyproject.toml`**: rejected. Pollutes the abstract dependency contract; makes the package painful to install alongside other tools that have overlapping deps.
- **`pip-tools` instead of `uv`**: rejected. Same pattern, slower, requires Python bootstrap. `uv` wins on speed and modernness.
- **Diff coverage instead of hard floor**: rejected for v1. More tooling, more config, no contributors yet to benefit.
- **Multi-platform matrix only on release branches**: rejected. Catches platform issues too late. With free public-repo runners, may as well always run.
- **Marking the latest job as required**: rejected. Upstream breakage shouldn't block author velocity; the latest job is a tripwire, not a gate.

## Implementation notes

- The actual `.github/workflows/ci.yml` file lands as part of Story 0.10 implementation work (a follow-up commit on `feature/test-scaffolding`).
- `uv.lock` is generated by `uv lock` and committed; do not edit by hand.
- `pyproject.toml` `[project]` table gets `~=` pins added for `anthropic` and `google-api-python-client` in the same commit.
- Branch protection settings on `main` need to be updated in GitHub's web UI to require the `test-locked (...)` matrix checks. This is operational, not code; documented in CLAUDE.md once the workflow lands.

## References

- [Spike 0007](../spikes/0007-ci-and-dependency-policy.md) — discussion record.
- [ADR 0008](0008-cleanup-sync-rename-ownership-autofix-static-analysis.md) — the policy this ADR makes real.
- [uv documentation](https://docs.astral.sh/uv/) — lockfile tooling chosen.
- ["Applications pin, libraries don't"](https://caremad.io/posts/2013/07/setup-vs-requirement/) — Donald Stufft's canonical writeup of the pattern this ADR adopts.
