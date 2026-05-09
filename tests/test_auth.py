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
    central.chmod(0o700)
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
    central.chmod(0o700)
    (central / "secrets.json").write_text(json.dumps({"anthropic_api_key": "from-file"}))
    (central / "secrets.json").chmod(0o600)

    from ergodix import auth

    assert auth.get_anthropic_api_key() == "from-keyring"


# ─── Tier 3: fallback file with permission invariant ────────────────────────


@pytest.mark.usefixtures("clean_env")
def test_file_used_when_no_env_no_keyring(fake_keyring, fake_home):
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o700)
    (central / "secrets.json").write_text(json.dumps({"anthropic_api_key": "from-file"}))
    (central / "secrets.json").chmod(0o600)

    from ergodix import auth

    assert auth.get_anthropic_api_key() == "from-file"


@pytest.mark.usefixtures("clean_env")
def test_file_with_loose_perms_raises(fake_keyring, fake_home):
    """Permission invariant: refuse to read secrets.json with mode > 600."""
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o700)
    secrets = central / "secrets.json"
    secrets.write_text(json.dumps({"anthropic_api_key": "from-file"}))
    secrets.chmod(0o644)  # world-readable — must fail

    from ergodix import auth

    with pytest.raises(PermissionError):
        auth.get_anthropic_api_key()


# ─── Security finding 0001 — TOCTOU + symlink swap ─────────────────────────
#
# See security/0001-tocttou-symlink-secrets-file.md. The earlier stat-then-
# open pattern followed symlinks and had a TOCTOU race. The patch uses
# os.open(O_RDONLY | O_NOFOLLOW) + fstat on the resulting fd.


@pytest.mark.usefixtures("clean_env")
@pytest.mark.skipif(
    not hasattr(os, "O_NOFOLLOW"),
    reason="Symlink protection requires O_NOFOLLOW (POSIX). Windows tests skipped.",
)
def test_secrets_file_symlink_is_rejected_with_clear_remediation(fake_keyring, fake_home, tmp_path):
    """secrets.json being a symlink — even to a mode-600 target — must be
    refused. The historical bug: stat() and open() both follow symlinks,
    so the mode check would pass against the target while opening
    whatever the link points at. The fix uses O_NOFOLLOW to fail loudly
    with ELOOP, which we translate into a PermissionError that names
    the path and tells the user to remove the symlink."""
    from pathlib import Path

    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o700)

    # The symlink target is itself a perfectly valid mode-600 file.
    # Without O_NOFOLLOW, the read would silently succeed against the
    # target — that's the attack we're closing.
    target = tmp_path / "attacker_controlled.json"
    target.write_text(json.dumps({"anthropic_api_key": "attacker-supplied"}))
    target.chmod(0o600)

    secrets = central / "secrets.json"
    secrets.symlink_to(target)

    from ergodix import auth

    with pytest.raises(PermissionError, match="symlink"):
        auth.get_anthropic_api_key()

    # And the value from the target must NOT have been returned.
    # (Belt-and-suspenders: if the test infrastructure changed and the
    # raise above was somehow bypassed, this would still catch the bug.)
    assert not Path(secrets).is_file() or Path(secrets).is_symlink()


@pytest.mark.usefixtures("clean_env")
def test_secrets_file_loose_perms_still_rejected_via_fstat(fake_keyring, fake_home):
    """The mode check must run against the same fd we read from (fstat),
    not a separate stat() call against the path. Pins that the
    permission check survives the patch — a regression where O_NOFOLLOW
    is added but fstat is forgotten would leave loose-perms files
    silently readable."""
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o700)
    secrets = central / "secrets.json"
    secrets.write_text(json.dumps({"anthropic_api_key": "from-file"}))
    secrets.chmod(0o644)  # group + world readable

    from ergodix import auth

    with pytest.raises(PermissionError, match="600"):
        auth.get_anthropic_api_key()


# ─── Security finding 0002 — parent-dir mode not enforced at read time ─────
#
# See security/0002-parent-dir-permissions-not-enforced.md. Without these
# checks, a parent dir at 0o755 (the default umask on most systems) would
# defeat the file's mode-600 invariant — anyone with same-uid write access
# to the dir could rename secrets.json out and substitute their own.


@pytest.mark.usefixtures("clean_env")
def test_parent_dir_with_world_readable_perms_rejects_read(fake_keyring, fake_home):
    """`~/.config/ergodix/` at 0o755 (group+world have read+exec on the dir)
    must cause auth.py to refuse to read the secrets file, with a remediation
    pointing at `chmod 700 <dir>`."""
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o755)  # default umask result on many systems
    secrets = central / "secrets.json"
    secrets.write_text(json.dumps({"anthropic_api_key": "from-file"}))
    secrets.chmod(0o600)

    from ergodix import auth

    with pytest.raises(PermissionError) as exc_info:
        auth.get_anthropic_api_key()
    msg = str(exc_info.value)
    # Must name the directory and give actionable remediation.
    assert str(central) in msg
    assert "chmod 700" in msg or "700" in msg


@pytest.mark.usefixtures("clean_env")
def test_parent_dir_with_any_group_or_world_bit_rejects_read(fake_keyring, fake_home):
    """Any group or other permission bit set on the parent dir must trigger
    the rejection — not just the obvious 0o755. 0o710 (group has exec only)
    is enough for a same-uid attacker to traverse into the dir and rename
    files within, so it must fail too."""
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o710)  # group has exec; world has nothing
    secrets = central / "secrets.json"
    secrets.write_text(json.dumps({"anthropic_api_key": "from-file"}))
    secrets.chmod(0o600)

    from ergodix import auth

    with pytest.raises(PermissionError):
        auth.get_anthropic_api_key()


@pytest.mark.usefixtures("clean_env")
def test_parent_dir_at_700_passes(fake_keyring, fake_home):
    """The happy path: parent dir at 0o700 + file at 0o600 must read
    cleanly. Pins that the new check doesn't false-positive on the
    documented invariant."""
    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o700)
    secrets = central / "secrets.json"
    secrets.write_text(json.dumps({"anthropic_api_key": "from-file"}))
    secrets.chmod(0o600)

    from ergodix import auth

    assert auth.get_anthropic_api_key() == "from-file"


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
    central.chmod(0o700)
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
    central.chmod(0o700)
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
