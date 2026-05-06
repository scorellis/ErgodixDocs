# ADR 0010: Installer pre-flight scan, single consent gate, atomic execute

- **Status**: Accepted
- **Date**: 2026-05-05
- **Spike**: [Spike 0008 — Installer redesign: pre-flight scan + consent gate](../spikes/0008-installer-redesign-preflight-consent.md)
- **Touches**: [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) — refines failure / consent semantics. [ADR 0007](0007-bootstrap-prereqs-cli-entry.md) — partially supersedes the prereq contract.

## Context

ADR 0007 specified `def check() -> CheckResult` as the prereq module contract, with an optional `auto_fix` callable. In practice, this conflates **inspecting** the system (which should be read-only) with **modifying** it (which should require user consent and may need admin rights). Today's installer (`install_dependencies.sh` plus the Python heredoc inside it) reflects the same conflation: it charges through inspect-and-fix steps in sequence with mid-stream prompts (MacTeX a/b/s, Drive launch y/N), no upfront plan, no final verification.

A test run on 2026-05-05 in a fresh deploy directory at `~/Documents/Scorellient/Applications/ErgodixDocs/` exposed concrete gaps:

- No `pip install -e .` step → `ergodix` console-script never registered.
- Python 3.9.6 venv created despite `pyproject.toml` requiring `>=3.11` (worked by luck of upstream backwards-compat).
- Final summary message tells the user to run `python auth.py set-key …`; auth.py moved to `ergodix/auth.py`.
- "Installation Complete" printed without any verification that the install actually works.
- LTeX VS Code extension install failed silently with no diagnostic.
- Mid-stream interactive prompts interrupt flow.

Spike 0008 captured the full inventory and the author's preferred UX: pre-flight scan → single consent → execute (one admin escalation if needed) → verify.

## Decision

### Four-phase installer execution

```
┌──────────────────┐   ┌────────────────────────┐   ┌──────────────┐   ┌─────────────────┐
│ 1. INSPECT       │ → │ 2. PLAN + CONSENT GATE │ → │ 3. APPLY      │ → │ 4. VERIFY        │
│   (read-only)    │   │   (single Y/n prompt)  │   │  (mutative)  │   │  (smoke checks) │
└──────────────────┘   └────────────────────────┘   └──────────────┘   └─────────────────┘
```

**Phase 1 — Inspect.** Every prereq module's `inspect()` runs in dependency order. Each returns an `InspectResult`. No mutations. Connectivity is detected once at the start (per ADR 0003); offline-capable inspections still run, network-dependent ones return a `deferred-offline` status.

**Phase 2 — Plan + consent.** Cantilever assembles the ordered list of `apply()` calls that would bring the system to the desired state. The plan is shown to the user as a numbered list with each entry indicating: what changes, whether it requires admin, expected duration if known. A single `Y/n` prompt governs the whole plan. Decline → exit cleanly with "no changes made."

**Phase 3 — Apply.** Cantilever runs each consented `apply()` in order. Operations that require admin are grouped so the user is prompted for their password **once**, not per-op. Progress is shown as `[k/n] description...`. Abort-fast on the first failure, with detailed remediation per ADR 0003.

**Phase 4 — Verify.** A required final phase. Cantilever runs:

- Import the package: `python -c "import ergodix"` succeeds.
- Console-script smoke: `ergodix --version` exits 0 and prints a version.
- Test suite (when dev deps were part of the apply): `pytest -q --no-cov` exits 0.
- Config sanity: `local_config.py` exists, mode 600, contains a non-empty `CORPUS_FOLDER`.

A failed verify is loud and specific: tell the user what passed, what failed, and what to do.

### Prereq contract — separate `inspect()` and `apply()`

This ADR partially supersedes ADR 0007's `check() -> CheckResult` shape:

```python
# ergodix/prereqs/types.py

@dataclass(frozen=True)
class InspectResult:
    op_id: str                  # e.g. "A1", "C2"
    status: Literal["ok", "needs-install", "needs-update", "deferred-offline", "failed"]
    description: str            # what this op is responsible for
    current_state: str          # human-readable: "Pandoc 3.9.0 installed" or "Pandoc not found"
    proposed_action: str | None # human-readable: "Install Pandoc 3.9 via brew" or None if no change
    needs_admin: bool = False
    estimated_seconds: int | None = None
    network_required: bool = False


@dataclass
class ApplyResult:
    op_id: str
    status: Literal["ok", "skipped", "failed"]
    message: str                # what was done, or what failed
    remediation_hint: str | None = None
```

```python
# ergodix/prereqs/check_pandoc.py  (one example)

def inspect() -> InspectResult: ...
def apply() -> ApplyResult: ...
```

Cantilever calls `inspect()` for every op during phase 1. It only calls `apply()` for ops where `inspect().status` is `needs-install` / `needs-update`, AND the user consented in phase 2.

### Where ADR 0007's `auto_fix` callable goes

The `auto_fix` callable from ADR 0007's `CheckResult` is **removed**. Reason: under the new model, every mutative action goes through the consent gate. There is no separate "auto-fix" path. The closest equivalent is the `apply()` function, which is consented-to before being called.

Ramifications: ADR 0008's "auto-fix iterative bound" decision (max one retry) is simplified — there is no retry. If `apply()` fails, cantilever surfaces it in the verify phase and asks the user to address it manually. Re-running cantilever picks up where the system actually is now (idempotency).

ADR 0008 stands except for that one specific clause.

### `--ci` and `--dry-run` floater behavior

Per ADR 0005, both are top-level floaters.

- **`--ci`**: bypasses the consent prompt. Uses defaults from `settings/floaters/ci.toml`. Fails fast (exits non-zero) on any operation that would have requested interactive input, including admin escalation that requires `sudo`. CI runs use `--ci` to verify cantilever succeeds against a fresh image without any human in the loop.
- **`--dry-run`**: runs phase 1 (inspect) + phase 2 (plan display), then exits without applying. Useful for "show me what cantilever would do."

### Specific gaps from today's intel — explicit fixes

Story 0.11 implementation must address each:

| Gap | Fix in implementation |
|---|---|
| No `pip install -e .` step | Phase 3 explicitly invokes it after the venv exists |
| Python 3.9.6 chosen automatically | Inspect phase enforces Python `>=3.11`; if not found, plan includes installing Homebrew Python 3.13 |
| Stale `python auth.py …` reference in final message | Final message uses `ergodix` console-script commands only |
| No final verification | Phase 4 explicitly runs the smoke checks listed above |
| LTeX silent failure | If a VS Code extension install fails, surface the underlying `code --install-extension` exit code and stderr |
| Mid-stream prompts | All choices (MacTeX option, Drive launch) move into Phase 2's plan, not mid-execute |
| Brew auto-update spam | `HOMEBREW_NO_AUTO_UPDATE=1` set for the duration of cantilever's brew calls |
| Final next-steps message stale | Generated dynamically from the run record, not hard-coded |

### Settings layering for the consent gate

`settings/bootstrap.toml` gains a section:

```toml
[consent]
# Operations that always require explicit user consent in the plan,
# even if they're marked critical = true elsewhere. Useful for things
# the user might genuinely want to skip on a given install (e.g.
# MacTeX on a writer-only machine that delegates rendering elsewhere).
always_prompt = ["A4"]   # XeLaTeX install
```

`settings/floaters/ci.toml` gains a section:

```toml
[ci_defaults]
# When --ci is active, these are the answers used in lieu of prompts.
A4 = "skip"     # don't install MacTeX in CI
B1 = "skip"     # don't install Drive Desktop in CI
```

## Consequences

**Easier:**
- The author's described UX is achievable with one round of implementation work, not a series of refinements.
- Verify phase catches install regressions immediately, not when the user tries to run `ergodix migrate` next week.
- `--dry-run` becomes a genuinely useful "what would happen?" tool.
- CI runs are deterministic — no hung prompts, no missing-input failures.
- Adding a new prereq is still drop-a-file, just with two functions instead of one.

**Harder:**
- Every existing prereq concept needs to be split into `inspect()` and `apply()`. Mostly mechanical, but it's two functions where there was one.
- The plan-display UX has to be designed (table format, color, terminal width handling). Implementation detail; not architectural.
- Sudo grouping requires careful sequencing so all admin-needing ops come before or after non-admin ops. Solved by sorting the plan during phase 2.

**Accepted tradeoffs:**
- Phase 1 inspect adds ~2–5 seconds to every cantilever run (every op runs inspect before any mutative work). Worth it.
- Removing `auto_fix` means we can't silently fix small things; everything goes through consent. This is by design — the user wanted explicit control.

## Alternatives considered

- **Keep ADR 0007's `check() -> CheckResult` with auto_fix**: rejected. Conflates inspect and apply; today's installer run proves the model is friction-prone in practice.
- **Three-phase model (inspect → apply → verify, no consent gate)**: rejected. The author explicitly wants the consent step; it's the difference between a tool the user controls and one that just charges through.
- **Per-op consent prompts**: rejected. The author's exact request was a single consent for the whole plan, not a forest of prompts. UX gain is real.
- **Implicit consent for non-admin ops**: rejected. If we ever broaden the audience to less-technical users, "I didn't agree to that" becomes a reasonable complaint about silent installs. Always show the plan; always ask once.

## Implementation notes

- Story 0.11 (newly created in SprintLog) tracks the implementation work.
- Estimated scope: rewrite `install_dependencies.sh` to a 5-line `bootstrap.sh` (per ADR 0007), implement the four phases in `ergodix/cantilever.py`, define `InspectResult` and `ApplyResult` in `ergodix/prereqs/types.py`, write inspect/apply for each of the 25 ops from ADR 0003.
- Tests come first per CLAUDE.md TDD norm: red tests for cantilever's phase orchestration, then for each inspect/apply pair.
- Story 0.10 (TDD scaffolding for the rest of the modules) resumes after Story 0.11 lands, since the prereq contract change here invalidates any test stubs written against ADR 0007's old `check()` shape.

## References

- [Spike 0008](../spikes/0008-installer-redesign-preflight-consent.md) — discussion record + concrete intel from today's installer run.
- [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) — failure semantics this ADR refines.
- [ADR 0007](0007-bootstrap-prereqs-cli-entry.md) — prereq contract this ADR partially supersedes.
- [ADR 0008](0008-cleanup-sync-rename-ownership-autofix-static-analysis.md) — auto-fix bound is mostly moot under the new model; one specific clause superseded.
