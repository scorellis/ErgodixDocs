"""
Tests for ergodix.settings — the bootstrap-settings loader used at
cantilever pre-flight. Per ADR 0012's F1 reframe, settings/ loading is
orchestrator-level concern, not a prereq module.

The loader returns a typed snapshot of ``settings/bootstrap.toml`` (and
later ``settings/floaters/<name>.toml`` per ADR 0005) with sensible
defaults when files are absent. Defaults must let cantilever run on a
machine that has no ``settings/`` directory at all — the project ships
with no committed settings yet, and per CLAUDE.md, settings/ is for
behavior that should differ between contributors, not a hard prereq.

Tests use ``tmp_path`` + ``monkeypatch.chdir`` to point the loader at a
controlled fake repo root. No production settings are touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ─── load_bootstrap_settings — defaults when no file ──────────────────────


def test_returns_defaults_when_settings_dir_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repo with no ``settings/`` folder at all should still produce a
    valid settings snapshot — every callsite reads from the snapshot
    via attribute / key access without checking 'does this file exist?'"""
    from ergodix.settings import load_bootstrap_settings

    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s is not None
    # Documented default for A4 (per ADR 0012): "full" MacTeX install.
    assert s.mactex_install_size == "full"


def test_returns_defaults_when_bootstrap_toml_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """settings/ exists but bootstrap.toml doesn't → still get defaults."""
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == "full"


# ─── load_bootstrap_settings — explicit values from bootstrap.toml ────────


def test_reads_mactex_install_size_from_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit value in bootstrap.toml overrides the default."""
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "bootstrap.toml").write_text('[mactex]\ninstall_size = "basic"\n')
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == "basic"


@pytest.mark.parametrize("value", ["full", "basic", "skip"])
def test_mactex_install_size_accepts_documented_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "bootstrap.toml").write_text(f'[mactex]\ninstall_size = "{value}"\n')
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == value


def test_mactex_install_size_unknown_value_falls_back_to_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    A typo or invalid value in bootstrap.toml should NOT crash cantilever
    nor silently propagate — fall back to the default ('full') and emit
    a warning marker on the snapshot so the orchestrator can surface it
    to the user.
    """
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "bootstrap.toml").write_text('[mactex]\ninstall_size = "everything"\n')
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == "full"
    assert s.warnings  # non-empty
    assert any("mactex" in w.lower() for w in s.warnings)


# ─── Malformed TOML — graceful failure ─────────────────────────────────────


def test_malformed_toml_falls_back_to_defaults_with_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bootstrap.toml that's not valid TOML must not crash cantilever
    at orchestrator pre-flight. Defaults + warning marker."""
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "bootstrap.toml").write_text("this is not [valid] = TOML at all")
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == "full"
    assert s.warnings
    assert any("toml" in w.lower() or "parse" in w.lower() for w in s.warnings)


# ─── Snapshot type contract ────────────────────────────────────────────────


def test_snapshot_is_a_dataclass_with_documented_fields() -> None:
    """
    Pin the snapshot's public surface so future additions are deliberate
    and not retro-fitted via dict access.
    """
    from dataclasses import fields

    from ergodix.settings import BootstrapSettings

    field_names = {f.name for f in fields(BootstrapSettings)}
    assert "mactex_install_size" in field_names
    assert "warnings" in field_names


# ─── ADR 0014 — settings cascade (defaults.toml + bootstrap.toml) ─────────
#
# Per ADR 0014 §4: three-tier cascade — `settings/defaults.toml` (SWAG
# layer, applies to every cantilever run) → `settings/bootstrap.toml`
# (installer-only overrides) → `settings/floaters/<name>.toml` (per-
# floater overrides, deferred until first consumer). Load order is
# most-general first; later layers override earlier.


def test_reads_mactex_install_size_from_defaults_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A value in `settings/defaults.toml` (and no bootstrap.toml override)
    must drive the resolved snapshot. Pins that defaults.toml is read
    when bootstrap.toml is absent."""
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "defaults.toml").write_text('[mactex]\ninstall_size = "basic"\n')
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == "basic"


def test_bootstrap_toml_overrides_defaults_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When both files set the same field, bootstrap.toml wins —
    bootstrap.toml is the installer-only override layer applied AFTER
    defaults. Pins the cascade direction."""
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "defaults.toml").write_text('[mactex]\ninstall_size = "basic"\n')
    (tmp_path / "settings" / "bootstrap.toml").write_text('[mactex]\ninstall_size = "skip"\n')
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == "skip"


def test_defaults_toml_alone_works_when_bootstrap_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """defaults.toml present, bootstrap.toml absent → defaults' value
    survives. Pins that bootstrap.toml's absence doesn't reset to the
    code default."""
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "defaults.toml").write_text('[mactex]\ninstall_size = "skip"\n')
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == "skip"


def test_malformed_defaults_toml_falls_back_to_code_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A malformed defaults.toml gets the same loud-not-fatal treatment
    bootstrap.toml does: defaults + warning, no abort."""
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "defaults.toml").write_text("garbage [not = toml")
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == "full"
    assert any("defaults.toml" in w for w in s.warnings)


def test_unknown_value_in_defaults_toml_falls_back_with_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unknown enum value in defaults.toml falls back to code default
    AND warns — same shape as bootstrap.toml's typo handling."""
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "defaults.toml").write_text('[mactex]\ninstall_size = "everything"\n')
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == "full"
    assert any("mactex" in w.lower() for w in s.warnings)


def test_warnings_from_both_files_accumulate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If both files have problems, the snapshot surfaces warnings from
    both. Tests that the cascade doesn't swallow one file's diagnostics
    when the other also fails."""
    from ergodix.settings import load_bootstrap_settings

    (tmp_path / "settings").mkdir()
    (tmp_path / "settings" / "defaults.toml").write_text("not [valid toml")
    (tmp_path / "settings" / "bootstrap.toml").write_text('[mactex]\ninstall_size = "weird"\n')
    monkeypatch.chdir(tmp_path)

    s = load_bootstrap_settings()

    assert s.mactex_install_size == "full"
    assert len(s.warnings) >= 2
    assert any("defaults.toml" in w for w in s.warnings)
    assert any("bootstrap.toml" in w for w in s.warnings)
