"""
Settings loader used at cantilever pre-flight (per ADR 0012's F1 reframe).

Returns a typed snapshot of ``settings/bootstrap.toml`` (and, when
implemented, the per-floater files under ``settings/floaters/``) with
sensible defaults when files are absent or malformed. Cantilever calls
this once at the top of ``run_cantilever()``; downstream prereqs read
fields off the snapshot.

**Defaults are the production behavior today.** The repo ships with no
committed ``settings/`` directory yet — landing settings infrastructure
without a concrete consumer would be premature. The first consumer is
ADR 0012's A4 (MacTeX install size); when A4 lands its prereq, it reads
``settings.mactex_install_size`` and respects the value.

**Malformed-TOML handling** is deliberately permissive: a corrupt or
typo'd bootstrap.toml falls back to defaults and records a human-readable
warning on the snapshot, rather than aborting cantilever pre-flight.
The orchestrator surfaces ``snapshot.warnings`` to the user before the
plan-display phase so configuration mistakes don't get silently ignored.

Path resolution uses ``Path.cwd()`` per CLAUDE.md (no module-level
``Path.home()`` baking) and matches cantilever's other ``cwd``-relative
file lookups (``local_config.py`` verify check, C4's bootstrap target).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

MactexInstallSize = Literal["full", "basic", "skip"]
_VALID_MACTEX_VALUES: frozenset[str] = frozenset({"full", "basic", "skip"})

_DEFAULT_MACTEX_INSTALL_SIZE: MactexInstallSize = "full"


@dataclass(frozen=True)
class BootstrapSettings:
    """Typed snapshot of ``settings/bootstrap.toml``.

    Frozen — the loader produces it once at pre-flight; orchestrator code
    reads but doesn't mutate. Future settings fields land here as new
    keyword-only attributes with their own documented default.
    """

    mactex_install_size: MactexInstallSize = _DEFAULT_MACTEX_INSTALL_SIZE
    """Per ADR 0012: 'full' (~4GB MacTeX) is the documented default; can
    be overridden to 'basic' (BasicTeX, ~100MB) or 'skip' (no LaTeX).
    Disk requirements are published in README's Install section."""

    warnings: list[str] = field(default_factory=list)
    """Human-readable strings describing parse / validation issues
    discovered during load. The orchestrator surfaces these to the user;
    cantilever does not abort on them — defaults take over so the run
    can continue."""


def _bootstrap_toml_path() -> Path:
    """Resolve ``settings/bootstrap.toml`` from cwd at call time."""
    return Path.cwd() / "settings" / "bootstrap.toml"


def load_bootstrap_settings() -> BootstrapSettings:
    """Load ``settings/bootstrap.toml`` and return a typed snapshot.

    Layered fallbacks:

    1. File missing → return defaults, no warning (the project ships
       with no settings/ directory; this is the normal case until a
       consumer needs an override).
    2. File present but unreadable / malformed → return defaults,
       record a warning, do NOT abort.
    3. File present + valid TOML, but a documented field has an
       unknown value → return default for that field, record a warning.
    """
    path = _bootstrap_toml_path()
    warnings: list[str] = []

    if not path.exists():
        return BootstrapSettings(warnings=warnings)

    try:
        raw = path.read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        warnings.append(
            f"settings/bootstrap.toml could not be parsed ({exc.__class__.__name__}: {exc}); "
            "using defaults."
        )
        return BootstrapSettings(warnings=warnings)

    mactex_size: MactexInstallSize = _DEFAULT_MACTEX_INSTALL_SIZE
    mactex_table = data.get("mactex", {})
    if isinstance(mactex_table, dict):
        configured = mactex_table.get("install_size")
        if isinstance(configured, str):
            if configured in _VALID_MACTEX_VALUES:
                # Cast is safe: we just verified membership in the literal set.
                mactex_size = configured  # type: ignore[assignment]
            else:
                warnings.append(
                    f"settings/bootstrap.toml: mactex.install_size={configured!r} "
                    f"is not one of {sorted(_VALID_MACTEX_VALUES)}; "
                    f"using default {_DEFAULT_MACTEX_INSTALL_SIZE!r}."
                )

    return BootstrapSettings(
        mactex_install_size=mactex_size,
        warnings=warnings,
    )
