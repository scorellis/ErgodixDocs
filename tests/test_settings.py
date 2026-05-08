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
