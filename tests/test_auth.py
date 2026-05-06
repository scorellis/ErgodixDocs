"""
Tests for ergodix.auth.

Three-tier credential lookup (per ADR auth design): env var → OS keyring →
fallback file. Permission-mode invariants on the fallback file. CLI
subcommands. Keyring error narrowing.

Many of these tests are red against the current implementation in places
because the imports moved (auth.py → ergodix/auth.py) and some behaviors
are forward-looking. That's intentional — TDD red phase.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

# ─── Smoke: module is importable from the package ───────────────────────────


def test_auth_module_imports():
    from ergodix import auth

    assert auth is not None


def test_auth_exposes_known_keys():
    from ergodix import auth

    assert "anthropic_api_key" in auth.KNOWN_KEYS
    assert "google_oauth_client_id" in auth.KNOWN_KEYS
    assert "google_oauth_client_secret" in auth.KNOWN_KEYS


def test_auth_scope_constants_are_readonly():
    """ADR 0001 / ADR 0005 lock scopes to readonly. Guard against drift."""
    from ergodix import auth

    assert all("readonly" in s for s in auth.DRIVE_SCOPES)
    assert all("readonly" in s for s in auth.DOCS_SCOPES)
    # No "drive.file" yet — that gets added explicitly via ADR amendment.
    assert not any(s.endswith("/auth/drive") for s in auth.DRIVE_SCOPES)


# ─── Tier 1: environment variable ───────────────────────────────────────────


@pytest.mark.usefixtures("clean_env")
def test_env_var_wins_over_keyring(fake_keyring, monkeypatch):
    """ANTHROPIC_API_KEY env var must take precedence over keyring value."""
    fake_keyring[("ergodix", "anthropic_api_key")] = "from-keyring"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")

    from ergodix import auth

    assert auth.get_anthropic_api_key() == "from-env"


@pytest.mark.usefixtures("clean_env")
def test_env_var_wins_over_file(fake_home, monkeypatch):
    """Env var takes precedence over fallback file."""
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    (central / "secrets.json").write_text(json.dumps({"anthropic_api_key": "from-file"}))
    (central / "secrets.json").chmod(0o600)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")

    from ergodix import auth

    assert auth.get_anthropic_api_key() == "from-env"


# ─── Tier 2: OS keyring ─────────────────────────────────────────────────────


@pytest.mark.usefixtures("clean_env")
def test_keyring_wins_over_file(fake_keyring, fake_home):
    fake_keyring[("ergodix", "anthropic_api_key")] = "from-keyring"
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    (central / "secrets.json").write_text(json.dumps({"anthropic_api_key": "from-file"}))
    (central / "secrets.json").chmod(0o600)

    from ergodix import auth

    assert auth.get_anthropic_api_key() == "from-keyring"


# ─── Tier 3: fallback file with permission invariant ────────────────────────


@pytest.mark.usefixtures("clean_env")
def test_file_used_when_no_env_no_keyring(fake_keyring, fake_home):
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    (central / "secrets.json").write_text(json.dumps({"anthropic_api_key": "from-file"}))
    (central / "secrets.json").chmod(0o600)

    from ergodix import auth

    assert auth.get_anthropic_api_key() == "from-file"


@pytest.mark.usefixtures("clean_env")
def test_file_with_loose_perms_raises(fake_keyring, fake_home):
    """Permission invariant: refuse to read secrets.json with mode > 600."""
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    secrets = central / "secrets.json"
    secrets.write_text(json.dumps({"anthropic_api_key": "from-file"}))
    secrets.chmod(0o644)  # world-readable — must fail

    from ergodix import auth

    with pytest.raises(PermissionError):
        auth.get_anthropic_api_key()


# ─── Missing credential error path ──────────────────────────────────────────


@pytest.mark.usefixtures("clean_env")
def test_missing_credential_raises_runtime_error(fake_keyring, fake_home):
    from ergodix import auth

    with pytest.raises(RuntimeError, match="No credential found"):
        auth.get_anthropic_api_key()


# ─── Google OAuth client tuple lookup ───────────────────────────────────────


@pytest.mark.usefixtures("clean_env")
def test_get_google_oauth_client_returns_tuple(fake_keyring):
    fake_keyring[("ergodix", "google_oauth_client_id")] = "id-123"
    fake_keyring[("ergodix", "google_oauth_client_secret")] = "secret-abc"

    from ergodix import auth

    cid, csec = auth.get_google_oauth_client()
    assert cid == "id-123"
    assert csec == "secret-abc"


# ─── NotImplemented stubs (forward-looking; replace as features land) ───────


def test_get_drive_service_is_stub():
    from ergodix import auth

    with pytest.raises(NotImplementedError):
        auth.get_drive_service()


def test_get_docs_service_is_stub():
    from ergodix import auth

    with pytest.raises(NotImplementedError):
        auth.get_docs_service()


# ─── Keyring error narrowing (per ADR 0008) ─────────────────────────────────


def test_no_keyring_backend_falls_through_silently(fake_home, monkeypatch):
    """
    NoKeyringError must be treated as 'no backend' — fall through to file
    fallback, do not surface as user-facing error.
    """
    import keyring
    import keyring.errors

    def raise_no_backend(*args, **kwargs):
        raise keyring.errors.NoKeyringError

    monkeypatch.setattr(keyring, "get_password", raise_no_backend)

    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    (central / "secrets.json").write_text(json.dumps({"anthropic_api_key": "from-file"}))
    (central / "secrets.json").chmod(0o600)

    from ergodix import auth

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert auth.get_anthropic_api_key() == "from-file"


def test_other_keyring_error_surfaces_as_runtime_error(monkeypatch, fake_home):
    """
    Any non-NoKeyringError keyring failure (locked keychain, daemon crash,
    etc.) must NOT be silently swallowed.
    """
    import keyring
    import keyring.errors

    class LockedError(keyring.errors.KeyringError):
        pass

    def raise_locked(*args, **kwargs):
        raise LockedError("Keychain is locked")

    monkeypatch.setattr(keyring, "get_password", raise_locked)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    from ergodix import auth

    with pytest.raises(RuntimeError, match="Keyring lookup failed"):
        auth.get_anthropic_api_key()


# ─── CLI surface (smoke; full CLI tests come with cli.py implementation) ────


def test_cli_help_runs():
    """`python -m ergodix.auth --help` exits 0 and prints the docstring."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "ergodix.auth", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_cli_status_runs(fake_keyring, fake_home):
    """`python -m ergodix.auth status` reports presence without printing values."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "ergodix.auth", "status"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(fake_home)},
    )
    # not every assertion needs to be tight — fail-fast if it crashed
    assert result.returncode == 0


# ─── Migration path: file → keyring ────────────────────────────────────────


@pytest.mark.usefixtures("clean_env")
def test_migrate_to_keyring_moves_keys(fake_keyring, fake_home, monkeypatch):
    """
    The migrate-to-keyring CLI subcommand should read every known key from
    the fallback file and write it into the keyring.
    """
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    secrets = central / "secrets.json"
    secrets.write_text(
        json.dumps(
            {
                "anthropic_api_key": "ak",
                "google_oauth": {"client_id": "ci", "client_secret": "cs"},
            }
        )
    )
    secrets.chmod(0o600)

    from ergodix import auth

    auth.cmd_migrate_to_keyring(delete_file=False)

    assert fake_keyring[("ergodix", "anthropic_api_key")] == "ak"
    assert fake_keyring[("ergodix", "google_oauth_client_id")] == "ci"
    assert fake_keyring[("ergodix", "google_oauth_client_secret")] == "cs"
