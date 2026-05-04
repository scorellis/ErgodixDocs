# Spike 0006: Bootstrap, prereqs layout, CLI entry point

- **Date range**: 2026-05-03
- **Sprint story**: [Story 0.8 — Architecture spike](../SprintLog.md#story-08---architecture-spike-orchestrator-pattern-role-based-cantilever-editor-collaboration-model-design-spike), Topics 2, 9, 10
- **ADRs produced**: [ADR 0007 — Bootstrap scripts, prereqs module layout, console-script CLI entry](../adrs/0007-bootstrap-prereqs-cli-entry.md)

## Question

Three implementation-flavored questions closing Story 0.8:

- **Topic 10**: How does today's monolithic `install_dependencies.sh` evolve into the cantilever orchestrator from ADR 0003?
- **Topic 2**: What's the contract for prereq check scripts — CLI tools, importable functions, or registered classes?
- **Topic 9**: How does the `ergodix` command end up runnable on the user's PATH?

## Discussion

### Topic 10 — `install_dependencies.sh` → `bootstrap.sh` + `prereqs/`

Two approaches considered:

- **Monolithic**: keep `install_dependencies.sh` as the bootstrap; add a sibling `cantilever.py` for orchestration.
- **Extracted**: rename to `bootstrap.sh`, extract every operation into `prereqs/check_<x>.py` modules; `bootstrap.sh` is small (just the Python install bootstrap); `ergodix cantilever` does the rest by calling each `prereqs/` module in turn.

Author confirmed: **extract**. No monolith. Matches the registry pattern from ADRs 0001/0003/0005.

### Topic 2 — Each prereq is an importable function

Three options for the prereq contract:

- **CLI script**: each `prereqs/check_pandoc.py` is invokable as `python prereqs/check_pandoc.py`; cantilever shells out and inspects exit codes.
- **Importable function**: each module exposes `def check() -> Result`; cantilever imports and calls.
- **Registered class**: each module defines a class implementing a base `Prereq` interface; cantilever discovers via the registry.

Author confirmed: **importable function**. Lightweight, testable, no subprocess overhead. Each `prereqs/check_<x>.py` exposes:

```python
def check() -> CheckResult:
    """Idempotent. Returns CheckResult with status, message, and remediation."""
```

`CheckResult` is a small dataclass: `status` (ok/skipped/deferred-offline/failed), `message`, optional `remediation_hint`, optional `auto_fix` callable.

### Topic 9 — Console-script entry in `pyproject.toml` + bootstrap scripts

Three options:

- `python -m ergodix` only (no PATH install)
- Shell wrappers in `bin/ergodix` and `bin/ergodix.ps1`
- Console-script entry in `pyproject.toml`

Author preference: "whatever is most likely to work; a simple bash and powershell that bootstrap everything is ideal."

Resolution: **console-script entry** as the standard mechanism, with **`bootstrap.sh` (macOS/Linux) and `bootstrap.ps1` (Windows)** as the user-facing one-shot scripts.

Bootstrap script flow:

1. Verify Python 3 present (or install via brew/apt/winget if absent — platform-specific)
2. Create `.venv` in repo root
3. Activate venv
4. `pip install -e .` (reads `pyproject.toml`, registers `ergodix` console-script in venv's bin)
5. Run `ergodix cantilever` (which loads prereqs/ modules and runs them)

Result: user clones the repo, runs `bootstrap.sh` (or `.ps1`), and from then on `ergodix` is a command in their venv.

### What gets clarified about the install model

User asked plainly how this works (unfamiliar with the package side). The answer: there is no remote stub installer. The repo *is* the install. `pip install -e .` reads the local `pyproject.toml` and registers the `ergodix` command pointing at the local source.

For non-technical users (the "completely ignorant" case the user named), Story 0.7 (Distribution prep) covers app-store-style intuitive installers — PyPI, Homebrew, signed installers, curl|bash stubs. Deferred.

### Folder layout after the refactor

```
ErgodixDocs/
  bootstrap.sh                    # macOS/Linux entrypoint
  bootstrap.ps1                   # Windows entrypoint
  pyproject.toml                  # registers `ergodix` console-script
  ergodix/                        # the Python package
    __init__.py
    cli.py                        # Click command groups (per ADR 0001)
    cantilever.py                 # cantilever orchestrator (per ADR 0003)
    auth.py                       # already exists
    version.py                    # already exists
    prereqs/                      # NEW: extracted from install_dependencies.sh
      __init__.py
      types.py                    # CheckResult dataclass
      check_platform.py           # A1
      check_homebrew.py           # A2
      check_pandoc.py             # A3
      check_xelatex.py            # A4
      check_python_venv.py        # A5
      check_python_packages.py    # A6
      check_vscode.py             # A7
      check_drive_app.py          # B1
      check_drive_mount.py        # B2
      check_gh_auth.py            # C1
      check_corpus_clone.py       # C2
      check_git_identity.py       # C3
      check_local_config.py       # C4
      check_central_config.py     # C5
      check_credentials.py        # C6
      check_autosync_task.py      # D1
      check_lint_hooks.py         # D2
      check_dev_deps.py           # D3
      check_branch_tracking.py    # D4
      check_poller.py             # D5
      check_status.py             # E1
      check_done_message.py       # E2
      check_connectivity.py       # F1
      record_run.py               # F2
    importers/                    # per ADR 0001
      __init__.py
      gdocs.py                    # migrate --from gdocs
      scrivener.py                # migrate --from scrivener
    floaters/                     # per ADR 0005 (settings counterpart in settings/floaters/)
      __init__.py
      writer.py
      editor.py
      developer.py
      publisher.py
      focus_reader.py
  settings/
    bootstrap.toml
    floaters/
      writer.toml
      editor.toml
      developer.toml
      publisher.toml
      focus-reader.toml
      dry-run.toml
      verbose.toml
      ci.toml
  adrs/  spikes/  docs/
  README.md  CHANGELOG.md  VERSION
  local_config.example.py
```

`auth.py` and `version.py` move from repo root into the `ergodix/` package as part of the refactor.

### Migration path

The refactor is mechanical. `install_dependencies.sh` operations map 1:1 to `prereqs/check_<x>.py` modules. The user's existing `local_config.py` (if any) is preserved by `check_local_config.py`'s idempotency logic — same as today.

A future commit performs the actual refactor under Story 0.2 implementation work. This ADR locks the *target shape*; the move happens when implementation begins.

## Decisions reached

- **Topic 10**: extract `install_dependencies.sh` operations into `prereqs/check_*.py` modules; rename the entry script to `bootstrap.sh`. → [ADR 0007](../adrs/0007-bootstrap-prereqs-cli-entry.md)
- **Topic 2**: each `prereqs/check_*.py` exposes an importable `check() -> CheckResult` function. → ADR 0007
- **Topic 9**: console-script entry in `pyproject.toml`; `bootstrap.sh` + `bootstrap.ps1` as the cross-platform user-facing entrypoints. → ADR 0007

## Loose threads / deferred questions

- **Auto-fix function shape** — `CheckResult.auto_fix` callable contract (when invoked, what it can mutate, how it reports back). Designed during implementation.
- **Connectivity check (`check_connectivity.py`)** — what URLs to probe, what timeout. Implementation-time decision.
- **Windows-specific prereqs** — winget for Homebrew-equivalent? PowerShell-only checks? Documented as a future port concern; v1 is macOS-first.
- **Story 0.7 (intuitive installers)** — extended in the parking lot to cover the "completely ignorant user" case; activated when distribution work begins.
