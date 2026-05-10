# Spike 0008: Installer redesign — pre-flight scan + consent gate

- **Date range**: 2026-05-05
- **Sprint story**: [Story 0.11 — Installer redesign](../stories/SprintLog.md) (new; elevated above remaining Story 0.10 implementation work)
- **ADRs produced**: [ADR 0010 — Pre-flight scan, single consent gate, atomic execute](../adrs/0010-installer-preflight-consent-gate.md)
- **Touches**: [ADR 0003](../adrs/0003-cantilever-bootstrap-orchestrator.md) — refines the failure / consent semantics. [ADR 0007](../adrs/0007-bootstrap-prereqs-cli-entry.md) — partially supersedes the `check() -> CheckResult` contract (now distinguishes read-only inspect from mutative apply).

## Question

Today's installer (`install_dependencies.sh` + the Python heredoc inside it) charges through a sequence of mid-stream prompts and writes. Even with the planned ADR 0007 refactor into `bootstrap.sh` + `ergodix/prereqs/check_*.py`, the contract remained one-shot: each `check()` could be both "is it OK?" and "go fix it." This conflates two phases that should be separate:

- **Inspect (read-only)** — what's the current state? What needs to change? Does any of it require admin?
- **Apply (mutative)** — actually do the install/upgrade work, with one admin prompt at the right moment.

The author asked: shouldn't the installer be able to detect dependencies that aren't met, present the user with a single plan, ask for one consent, then proceed (escalating to admin once if needed)? Today's experience proved the current design doesn't do this.

## Discussion

### Today's installer-run intel (gathered 2026-05-05)

Ran `install_dependencies.sh` against a fresh clone in `~/Documents/Scorellient/Applications/ErgodixDocs/`. Observations grouped by severity:

**High-severity gaps:**

- **No `pip install -e .` step.** The installer never registers the `ergodix` console-script entry. After "successful" install, `ergodix` is not on PATH; user must know to invoke `python -m ergodix.cli` instead. Documentation says `ergodix migrate`. Mismatch.
- **Python 3.9.6 venv created** despite `pyproject.toml` requiring `>=3.11`. The installer takes whatever `python3` resolves to first (Xcode's). Anthropic and Google client packages happen to support 3.9 today; it's luck, not policy.
- **Stale `auth.py` reference.** Final summary message tells user to run `python auth.py set-key …`. File moved into `ergodix/auth.py` weeks ago. Command fails.

**Medium-severity gaps:**

- **No final verification step.** Installer prints "Installation Complete" without testing anything. No `ergodix --version` smoke check, no `pytest` run, no import check.
- **LTeX VS Code extension install failed silently.** Just printed "Could not install LTeX." No diagnostic to help the user understand why. Extension may have been renamed/discontinued.
- **No pre-flight scan + consent gate.** Mid-stream interactive prompts (MacTeX a/b/s, Drive launch y/N) interrupt flow.
- **XeLaTeX silently skipped** in non-interactive mode. Single warning line easy to miss; no surfacing in a final summary.

**Low-severity gaps:**

- **Brew auto-update spam.** Several minutes of unrelated formula/cask listings pollute output. Brew's default behavior, not something we control directly, but we can suppress it via `HOMEBREW_NO_AUTO_UPDATE=1` for the duration of the install.
- **Final next-steps message stale.** "We will build ergodix migrate/render next" — those stubs already exist in `ergodix/cli.py`.

**Observations that worked:**

- Drive Mirror detected, corpus folder identified at `/Users/scorellis/My Drive/Tapestry of the Mind` correctly.
- `local_config.py` generation worked (mode 600).
- `~/.config/ergodix/` directory created cleanly (mode 700).
- Markdown Preview Enhanced VS Code extension installed.
- Tests pass after manual `pip install -e ".[dev]"`: 22 passed, 1 skipped.

### The author's proposed UX

> "We do a scan, and make a list: 'The following dependencies have not been met. Would you like to run the following script to update them?' then show them the script followed with a prompt that will trip off a request for admin rights to run the install script."

Concretely, four phases:

1. **Pre-flight inspect** — every prereq's `inspect()` runs read-only; each returns a `CheckResult` describing current state and what action would bring it to OK.
2. **Plan display + consent** — installer assembles the plan (ordered list of mutative operations), shows it to the user, asks once: "Apply N changes? [Y/n]". Operations needing admin are flagged.
3. **Apply (mutative)** — runs each `apply()` in order. Operations requiring sudo are batched so the user is prompted for their password once.
4. **Verify** — smoke checks: import the package, run `ergodix --version`, run pytest, confirm `local_config.py` is sane. Report final state.

### How this refines ADR 0007's `CheckResult`

ADR 0007 specifies:

```python
def check() -> CheckResult: ...
```

Where `CheckResult` may carry an `auto_fix` callable. In practice this conflates inspect and fix.

ADR 0010 separates them:

```python
def inspect() -> InspectResult:
    """Read-only. Reports current state and what apply() would do."""

def apply(plan_step: PlanStep) -> ApplyResult:
    """Mutative. Performs the change inspect() said was needed."""
```

`InspectResult.needs_action` is True when something would change. `apply()` is only called on items where the user consented. The `auto_fix` concept from ADR 0007 collapses naturally: there's no auto-fix vs. apply distinction; everything goes through the consent gate.

### Code signing — out of scope for this ADR

The author noted: "Of course we will need to (later on) get some sort of certificate that signs us as being on the up and up." This is genuine — Apple Developer ID enrollment ($99/year) + notarization is necessary before non-technical Mac users will install ergodix without security warnings. It belongs in Story 0.7 (Distribution prep), already parked. ADR 0010 doesn't address it.

### `--ci` mode behavior

Per ADR 0005's `--ci` floater, non-interactive mode bypasses the consent prompt and uses defaults from `settings/`. This is essential for CI runs (the gating job from ADR 0009 runs cantilever in `--ci` mode to verify the install works on a fresh image). Defaults should be conservative: skip MacTeX (large download), skip optional VS Code extensions, but install everything mandatory.

### `--dry-run` mode behavior

Per ADR 0005's `--dry-run` floater, dry-run does inspect + plan display, then exits without applying. Useful for users who want to know what cantilever would do without committing.

### Why this elevates above remaining Story 0.10 work

The user said: "move it up in the sprint plan to be done first." Reasoning: the test stubs we'd write next under Story 0.10 will exercise the new `inspect()` / `apply()` contract. Writing tests against the old `check()` contract and then having to rewrite them is wasted work. The contract change has to land first.

## Decisions reached

- **Two-phase contract**: `inspect()` (read-only) and `apply()` (mutative) replace the conflated `check() -> CheckResult` from ADR 0007. → [ADR 0010](../adrs/0010-installer-preflight-consent-gate.md)
- **Four-phase installer UX**: pre-flight inspect → plan display + single consent → apply (with grouped sudo) → verify. → ADR 0010
- **Final verification step is required**: import package, run `ergodix --version`, run pytest, surface failures clearly. → ADR 0010
- **`--ci` mode bypasses consent**, uses settings-file defaults, fails fast on anything that would prompt interactively. → ADR 0010
- **`--dry-run` shows the plan and exits** without applying. → ADR 0010
- **All gaps captured above** (no `pip install -e .`, Python version not enforced, stale auth.py reference, LTeX failure, brew spam, missing verification) are explicit fixes in the implementation work for Story 0.11. → ADR 0010
- **Code signing / notarization deferred** to Story 0.7. Out of scope here.
- **Story 0.11 created and elevated above remaining Story 0.10 test-stub work**. → SprintLog update.

## Loose threads

- **Detection of breaking changes mid-run.** ADR 0003 already handles this via the run-record format; ADR 0010 inherits.
- **Persistence of plan state if user aborts mid-apply.** If apply step 5 of 12 fails and the user fixes the underlying issue, can re-running cantilever resume from step 6? Decision: no, just re-run from the top — idempotency handles it. Resumability is a future enhancement.
- **Network detection at inspect-phase boundaries.** ADR 0003's connectivity auto-detection runs once at start; ADR 0010 inherits.
- **Plan display format** — table vs. checkbox list vs. progress bar — implementation detail, decided when the new bootstrap.sh + cantilever orchestrator land. Not blocking.
