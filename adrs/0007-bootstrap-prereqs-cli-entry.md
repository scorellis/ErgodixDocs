# ADR 0007: Bootstrap scripts, prereqs module layout, console-script CLI entry

- **Status**: Accepted
- **Date**: 2026-05-03
- **Spike**: [Spike 0006 — Bootstrap, prereqs layout, CLI entry point](../spikes/0006-bootstrap-prereqs-cli-entry.md)
- **Closes**: Story 0.8 Topics 2, 9, 10.

## Context

ADR 0003 specified that cantilever runs a 22-operation menu. ADR 0001 specified Click subcommand groups for the CLI. Today's `install_dependencies.sh` is a monolithic Bash script that does most of what cantilever should do, but in one file. Three implementation questions needed answers before any of it can be built:

- How does the existing monolith get broken apart?
- What's the contract for each piece?
- How does the resulting `ergodix` command end up on the user's PATH?

## Decision

### Bootstrap scripts (Topic 10)

`install_dependencies.sh` is renamed to `bootstrap.sh` (macOS/Linux). A sibling `bootstrap.ps1` (Windows) is added when v1 implementation begins. Both scripts are minimal:

1. Verify Python 3 present (install via brew/apt/winget if absent — platform-specific).
2. Create `.venv` at repo root.
3. Activate `.venv`.
4. Run `pip install -e .` (reads `pyproject.toml`, registers the `ergodix` console-script).
5. Run `ergodix cantilever` (which dispatches to the prereqs modules below).

Everything cantilever does today via Bash is moved into Python. Bootstrap is just enough to get Python and the `ergodix` command working; cantilever does the rest.

### Prereqs layout (Topic 2)

Every operation from ADR 0003's 22-operation menu becomes a Python module under `ergodix/prereqs/`. Each module exposes:

```python
def check() -> CheckResult:
    """Idempotent. Returns CheckResult with status, message, optional remediation."""
```

`CheckResult` is a small dataclass:

```python
@dataclass
class CheckResult:
    status: Literal["ok", "skipped", "deferred-offline", "failed"]
    message: str
    remediation_hint: str | None = None
    auto_fix: Callable[[], CheckResult] | None = None
```

Cantilever loads each module (driven by the union of universal ops + enabled floater `adds_operations` per ADR 0005), calls `check()`, and acts on the result:

- `ok` / `skipped`: continue.
- `deferred-offline`: log to run-record (per ADR 0003 F2), continue.
- `failed` with `auto_fix`: invoke auto-fix, re-evaluate.
- `failed` without auto-fix: print step-X-of-Y messaging and remediation_hint, exit non-zero.

The connectivity check (F1 from ADR 0003) is the first prereq run; offline outcome short-circuits subsequent network-dependent prereqs to `deferred-offline`.

### CLI entry point (Topic 9)

`pyproject.toml` declares a console-script entry:

```toml
[project.scripts]
ergodix = "ergodix.cli:main"
```

`pip install -e .` (run by bootstrap) registers a small executable in the venv's `bin/` (macOS/Linux) or `Scripts/` (Windows) directory. As long as the venv is active, `ergodix` is on PATH. No shell wrappers, no manual PATH editing.

### Folder layout after refactor

```
ErgodixDocs/
  bootstrap.sh                    # macOS/Linux entrypoint
  bootstrap.ps1                   # Windows entrypoint (added during implementation)
  pyproject.toml                  # registers ergodix console-script
  ergodix/                        # the Python package
    __init__.py
    cli.py                        # Click groups (per ADR 0001)
    cantilever.py                 # orchestrator (per ADR 0003)
    auth.py                       # moved from repo root
    version.py                    # moved from repo root
    prereqs/                      # extracted from install_dependencies.sh
      __init__.py
      types.py                    # CheckResult dataclass
      check_<op>.py               # one per ADR 0003 operation
    importers/                    # per ADR 0001
    floaters/                     # per ADR 0005
  settings/                       # per ADR 0005
    bootstrap.toml
    floaters/
  adrs/  spikes/  docs/
```

`auth.py` and `version.py` move from repo root into `ergodix/` so they can be imported as `from ergodix.auth import ...` etc. Backwards-compat is fine to ignore — nothing depends on them externally.

### What stays the same

- ADR 0001's Click subcommand groups: unchanged.
- ADR 0003's 22-operation menu and idempotency rules: unchanged. Operations now live in `prereqs/`.
- ADR 0005's all-floaters model: unchanged.
- `auth.py` three-tier credential lookup: unchanged.
- `bootstrap.toml` + `settings/floaters/<name>.toml`: same shape, settled location.

### What goes away

- `install_dependencies.sh` (renamed to `bootstrap.sh`, gutted to ~5 lines of Python-bootstrap logic).
- The monolithic Python heredoc inside the current installer (operations now live as separate Python modules).
- Repo-root `auth.py` and `version.py` (move into the package).

## Consequences

**Easier:**
- Each operation is a small, independently testable Python module.
- Adding a new operation: create `prereqs/check_<op>.py` with a `check()` function; reference it from settings.
- Cross-platform parity: bootstrap scripts are platform-specific bridges; everything else is portable Python.
- The `ergodix` command works the same way on every platform once `pip install -e .` runs.
- Standard Python tooling (pytest, mypy, ruff) Just Works against the package layout.

**Harder:**
- Refactor work is real — extracting ~22 operations from Bash to Python, plus moving `auth.py` and `version.py`. One implementation session.
- Bootstrap scripts must handle Python-not-installed gracefully (install Python via OS package manager). Per-platform code.
- Console-script entries require `pip install -e .` to have run; users who skip bootstrap and manually `python -m ergodix` will work, but the documented happy path is bootstrap → `ergodix cantilever`.

**Accepted tradeoffs:**
- Bootstrap scripts duplicate Python-install logic across `.sh` and `.ps1`. Acceptable; both scripts are small.
- Console-script entry requires an active venv. Documented as the standard pattern; activation is one line.
- Story 0.7 covers the "non-technical user with no terminal experience" case via app-store-style installers; v1 assumes the user can clone a repo and run a script.

## Alternatives considered

- **Keep `install_dependencies.sh` monolithic, add `cantilever.py` alongside**: rejected. Defeats the registry-based extension pattern from ADR 0001/0003/0005.
- **CLI tools per prereq (subprocess shells out)**: rejected. Slower, harder to test, weaker error reporting; subprocess overhead per op adds up.
- **Registered class implementing a base interface**: rejected as over-engineered for the current size; the `check() -> CheckResult` function contract is enough.
- **`python -m ergodix` only, no console-script**: rejected. Forces users to remember the `-m` form; non-standard against typical Python CLI tooling.
- **Shell wrappers in `bin/`**: rejected. Console-script entry is the standard mechanism and integrates with future packaging (Story 0.7).

## References

- [Spike 0006](../spikes/0006-bootstrap-prereqs-cli-entry.md) — discussion record.
- [ADR 0001](0001-click-cli-with-persona-floater-registries.md) — Click subcommand groups.
- [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) — 22-operation menu now mapped to prereqs modules.
- [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) — floater registry that drives which prereqs run.
