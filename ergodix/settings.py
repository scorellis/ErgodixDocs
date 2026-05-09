"""
Settings loader used at cantilever pre-flight (per ADR 0012's F1 reframe).

Returns a typed snapshot of the project's settings cascade — the layered
TOML files under ``settings/`` — with sensible defaults when files are
absent or malformed. Cantilever calls this once at the top of
``run_cantilever()``; downstream prereqs read fields off the snapshot.

**Cascade (per ADR 0014).** Three layers, most-general first:

1. ``settings/defaults.toml`` — applies to every cantilever run, every
   floater. The "SWAG" layer (Stuff We All Get): project-wide
   preferences that aren't installer-specific. Optional file.
2. ``settings/bootstrap.toml`` — installer-specific overrides only.
   Optional file. Wins over defaults.toml when both set the same field.
3. ``settings/floaters/<active-floater>.toml`` — per-floater overrides.
   **Deferred until the first per-floater consumer activates** (per
   ADR 0014 §4); the layer is documented here but not yet read by the
   loader. When it lands, the load order extends naturally: floater files
   override bootstrap.toml.

**Code defaults are the floor.** When no file sets a value, the
hard-coded constants in this module win. Production behavior with no
``settings/`` directory is unchanged from the pre-cascade era.

**Malformed-TOML handling** is deliberately permissive: a corrupt or
typo'd file in any layer falls back to the layer below (and ultimately
to defaults), records a human-readable warning on the snapshot, and does
NOT abort cantilever pre-flight. The orchestrator surfaces
``snapshot.warnings`` to the user before the plan-display phase so
configuration mistakes don't get silently ignored.

Path resolution uses ``Path.cwd()`` per CLAUDE.md (no module-level
``Path.home()`` baking). Tests use ``monkeypatch.chdir`` to point the
loader at a controlled fake repo root.

NOTE: the dataclass name ``BootstrapSettings`` and the loader name
``load_bootstrap_settings`` predate ADR 0014 and are now mild
misnomers (the cascade is no longer just "bootstrap"). A rename is
deferred to a follow-up cleanup PR to keep this PR's diff focused on
the cascade extension; callers across cantilever and tests reference
the names today.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

MactexInstallSize = Literal["full", "basic", "skip"]
_VALID_MACTEX_VALUES: frozenset[str] = frozenset({"full", "basic", "skip"})

_DEFAULT_MACTEX_INSTALL_SIZE: MactexInstallSize = "full"


@dataclass(frozen=True)
class BootstrapSettings:
    """Typed snapshot of the resolved settings cascade.

    Frozen — the loader produces it once at pre-flight; orchestrator code
    reads but doesn't mutate. Future settings fields land here as new
    keyword-only attributes with their own documented default.
    """

    mactex_install_size: MactexInstallSize = _DEFAULT_MACTEX_INSTALL_SIZE
    """Per ADR 0012: 'full' (~4GB MacTeX) is the documented default; can
    be overridden to 'basic' (BasicTeX, ~100MB) or 'skip' (no LaTeX).
    Disk requirements are published in README's Install section. Per
    ADR 0014, the documented home for this value is
    ``settings/defaults.toml``; ``bootstrap.toml`` overrides it for
    installer-specific cases."""

    warnings: list[str] = field(default_factory=list)
    """Human-readable strings describing parse / validation issues
    discovered during load. The orchestrator surfaces these to the user;
    cantilever does not abort on them — defaults take over so the run
    can continue."""


def _defaults_toml_path() -> Path:
    """Resolve ``settings/defaults.toml`` from cwd at call time."""
    return Path.cwd() / "settings" / "defaults.toml"


def _bootstrap_toml_path() -> Path:
    """Resolve ``settings/bootstrap.toml`` from cwd at call time."""
    return Path.cwd() / "settings" / "bootstrap.toml"


def _load_toml_file(path: Path, label: str) -> tuple[dict[str, Any], list[str]]:
    """Read a TOML file from ``path``. Return the parsed dict + any
    warnings.

    - Missing file → ({}, []) — silent; both files are optional.
    - Unreadable / malformed → ({}, [<warning>]) — record but don't abort.

    ``label`` is the filename used in warning messages (e.g.
    ``"defaults.toml"``) so the user can tell which layer broke.
    """
    if not path.exists():
        return {}, []

    try:
        raw = path.read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return {}, [
            f"settings/{label} could not be parsed "
            f"({exc.__class__.__name__}: {exc}); using defaults."
        ]
    return data, []


def _parse_mactex_install_size(
    data: dict[str, Any], label: str
) -> tuple[MactexInstallSize | None, list[str]]:
    """Pull mactex.install_size out of one layer's parsed TOML.

    Returns ``(value, warnings)``:
    - ``(None, [])`` — layer didn't set this field at all.
    - ``(value, [])`` — layer set a valid value.
    - ``(None, [<warning>])`` — layer set an unknown value; caller
      proceeds with whatever the layer below produced.
    """
    mactex_table = data.get("mactex", {})
    if not isinstance(mactex_table, dict):
        return None, []
    configured = mactex_table.get("install_size")
    if configured is None:
        return None, []
    if not isinstance(configured, str):
        return None, [
            f"settings/{label}: mactex.install_size has non-string value "
            f"{configured!r}; using default."
        ]
    if configured in _VALID_MACTEX_VALUES:
        return configured, []  # type: ignore[return-value]
    return None, [
        f"settings/{label}: mactex.install_size={configured!r} "
        f"is not one of {sorted(_VALID_MACTEX_VALUES)}; "
        f"using default {_DEFAULT_MACTEX_INSTALL_SIZE!r}."
    ]


def load_bootstrap_settings() -> BootstrapSettings:
    """Load the settings cascade and return a typed snapshot.

    Cascade order (most-general first; later layers override earlier):

    1. Code defaults (the constants in this module).
    2. ``settings/defaults.toml`` — SWAG layer.
    3. ``settings/bootstrap.toml`` — installer-only overrides.

    Floater layer (``settings/floaters/<name>.toml``) is documented in
    ADR 0014 but not read here yet; lands when the first per-floater
    consumer activates.
    """
    warnings: list[str] = []

    # Layer 2: defaults.toml.
    defaults_data, defaults_warnings = _load_toml_file(_defaults_toml_path(), "defaults.toml")
    warnings.extend(defaults_warnings)

    # Layer 3: bootstrap.toml.
    bootstrap_data, bootstrap_warnings = _load_toml_file(_bootstrap_toml_path(), "bootstrap.toml")
    warnings.extend(bootstrap_warnings)

    # Resolve mactex_install_size: bootstrap > defaults > code default.
    mactex_size: MactexInstallSize = _DEFAULT_MACTEX_INSTALL_SIZE

    defaults_value, defaults_field_warnings = _parse_mactex_install_size(
        defaults_data, "defaults.toml"
    )
    warnings.extend(defaults_field_warnings)
    if defaults_value is not None:
        mactex_size = defaults_value

    bootstrap_value, bootstrap_field_warnings = _parse_mactex_install_size(
        bootstrap_data, "bootstrap.toml"
    )
    warnings.extend(bootstrap_field_warnings)
    if bootstrap_value is not None:
        mactex_size = bootstrap_value

    return BootstrapSettings(
        mactex_install_size=mactex_size,
        warnings=warnings,
    )
