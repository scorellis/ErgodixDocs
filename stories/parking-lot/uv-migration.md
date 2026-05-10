# uv migration — adopt uv as the lockfile + dep-management tool (per ADR 0009 locked design)

- **Status**: parking-lot (deferred; activate when ready to do the migration)
- **Origin**: introduced by the "Note — pragmatic v1 (2026-05-10)" section of [ADR 0009](../../adrs/0009-ci-and-dependency-policy.md), which acknowledges the deviation from the locked uv-based design.
- **Lifts a dependency from**: PRs #86 (`.github/workflows/ci.yml`) + #87 (`.github/workflows/integration.yml`) — both currently pip-based.

## Why this is parked

ADR 0009's locked design specifies `uv` (via `astral-sh/setup-uv@v3`) + a committed `uv.lock` + a 9-cell matrix (macOS / Ubuntu / Windows × 3.11 / 3.12 / 3.13) + a `test-latest` informational tripwire. The CI workflow that shipped in PR #86 is a **pragmatic v1**: single Ubuntu + 3.13 cell, `pip install -e ".[dev]"`, no `uv.lock`.

The pragmatic version exists because `uv` was not yet installed on the project's dev machine when CI shipped. Migrating now requires a coordinated set of changes that's bigger than a single PR; deferring kept the CI launch unblocked.

## As / So that

As a developer (and a future CI maintainer), so that the CI workflow matches ADR 0009's locked design — reproducible across the 9-cell matrix, locked against a committed `uv.lock` for our internal environment, with the `test-latest` tripwire catching upstream churn before it breaks main — instead of the pragmatic single-cell pip-based v1 that closed the "no CI" gap but doesn't catch macOS / Windows / older-Python regressions.

## Value

- Matrix coverage catches platform-specific regressions (path separators, venv layout, brew vs apt cantilever paths) before they reach the user.
- `uv.lock` makes our internal environment bit-for-bit reproducible — every CI run, every developer's local dev loop, every Claude session sees the same dep versions.
- `test-latest` informational tripwire surfaces upstream API churn (`anthropic`, `google-api-python-client`, others) as a yellow warning on the PR before the locked job goes red on main.
- The uv-based dev loop is meaningfully faster than pip — improves iteration speed on every PR.

## Risk

- Migration touches `bootstrap.sh` (currently `pip install -e ".[dev]"`), `.github/workflows/ci.yml`, the README install instructions, CLAUDE.md, and any test or doc that names `pip`. Coordination cost is real.
- `uv` is newer than `pip`; if there's a `uv` bug we don't have, we'd be the ones discovering it. Mitigation: uv has been stable through 2026; bus factor risk is low.
- A bad `uv.lock` regeneration could pin a known-bad version of a transitive dep. Mitigation: regenerate from a known-good environment and verify CI passes against the new lock before merging.

## Assumptions

- `uv` is installable cross-platform via `brew install uv` (macOS), `pipx install uv` (Linux/Windows), or `astral-sh/setup-uv@v3` (CI).
- `pyproject.toml`'s existing `[project.optional-dependencies] dev = [...]` shape is compatible with `uv sync --extra dev` out of the box.
- The user is willing to install `uv` on their dev machine (one-time setup).

## Tasks (when activated)

- [ ] Install `uv` on the dev machine (`brew install uv` on macOS).
- [ ] Generate the initial `uv.lock` from the current `pyproject.toml`: `uv lock`.
- [ ] Commit `uv.lock` to the repo. Verify it's NOT in `.gitignore`.
- [ ] Update `bootstrap.sh`: replace `pip install -e ".[dev]"` with `uv sync --extra dev`. Keep `pip` as a fallback if `uv` isn't on PATH? Lean: yes, with a clear error message recommending `brew install uv`.
- [ ] Update `.github/workflows/ci.yml` to match ADR 0009's full design: `astral-sh/setup-uv@v3`, `uv sync --extra dev`, all `uv run` invocations for ruff / mypy / pytest, full 9-cell matrix.
- [ ] Add the `test-latest` informational job: `uv sync --extra dev --upgrade --resolution=highest`, `continue-on-error: true`, single Ubuntu + 3.13 cell.
- [ ] Update `.github/workflows/integration.yml` to use uv-based install too (for consistency, though the smoke is mostly CLI-level).
- [ ] Update `scripts/integration-smoke.sh` to call `uv sync --extra dev` instead of `pip install -e ".[dev]"` (or leave pip-based as a portable fallback — decide).
- [ ] Update README install instructions (mention `brew install uv` as a recommended pre-bootstrap step).
- [ ] Update CLAUDE.md: replace any `pip install` references in code conventions with `uv sync`, add a working-norm note that `uv.lock` is committed and regenerated together with any `pyproject.toml` change.
- [ ] Update ADR 0009: remove or supersede the "Note — pragmatic v1 (2026-05-10)" section (leave it as a record per the Note's own guidance, but add a follow-up Note pointing at the migration PR that landed the full design).
- [ ] Smoke the migration locally: clear `.venv`, run `bootstrap.sh`, verify everything still works.
- [ ] Run `scripts/integration-smoke.sh` against the migrated setup.
- [ ] Set up GitHub branch protection on `main` to require all 9 cells of `test-locked` per ADR 0009's "Required checks for merge" section.

## Cross-references

- [ADR 0009 §"Note — pragmatic v1 (2026-05-10)"](../../adrs/0009-ci-and-dependency-policy.md): the deviation this story exists to close.
- [ADR 0009 §"Decision"](../../adrs/0009-ci-and-dependency-policy.md): the locked target.
- [Spike 0007](../../spikes/0007-ci-and-dependency-policy.md): original discussion record.
