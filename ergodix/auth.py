"""
ErgodixDocs — auth and credential store.

Designed to be local, frugal, and portable across operating systems so that any
author using ErgodixDocs gets the right credential storage on their platform
without configuration.

Three-tier lookup (Principle of Least Privilege):

    1. Environment variable           — preferred for CI / scripts / one-offs.
    2. OS keyring                     — primary live store for interactive use:
                                          * macOS:   Keychain
                                          * Linux:   Secret Service / KWallet
                                          * Windows: Credential Manager
       Service name: "ergodix"
    3. ~/.config/ergodix/secrets.json — file fallback for headless environments
                                          where no keyring backend is available.
                                          mode 600. Auth refuses to read it if
                                          permissions are loosened.

Per-project token store (Drive/Docs OAuth refresh tokens):

    <repo_dir>/.ergodix_tokens.json     — never reused by other tools, scoped
                                          only to what ErgodixDocs needs.

Scope policy (least privilege):
  - Drive: drive.readonly only. Reads happen via the local Mirror mount; writes
    happen via the filesystem (Drive for Desktop syncs the change). No write
    scope is requested.
  - Docs:  documents.readonly only.
  - Comments are accessed through drive.readonly (covered).
  - Broader scopes require an explicit decision and a justifying comment here.

CLI (run from your ErgodixDocs repo directory):

    python -m ergodix.auth set-key anthropic_api_key
    python -m ergodix.auth delete-key anthropic_api_key
    python -m ergodix.auth status
    python -m ergodix.auth migrate-to-keyring [--delete-file]
"""

from __future__ import annotations

import errno
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Defer keyring import so that --help and basic file fallback still work
# even if keyring isn't installed yet (e.g. before install_dependencies.sh ran).
try:
    import keyring
    import keyring.errors

    _HAS_KEYRING = True
except ImportError:
    keyring = None  # type: ignore
    _HAS_KEYRING = False


# ─── Constants ──────────────────────────────────────────────────────────────

KEYRING_SERVICE = "ergodix"


# Paths are resolved lazily so that tests (and any caller that monkeypatches
# HOME) get current values rather than what was true at import time. Keep
# these as functions, not module-level constants.


def _central_dir() -> Path:
    return Path.home() / ".config" / "ergodix"


def _central_secrets_file() -> Path:
    return _central_dir() / "secrets.json"


# Backwards-compatible names for code paths that still treat them as
# attributes (e.g. `auth.CENTRAL_SECRETS_FILE`). These shadow the constant
# names but evaluate at access time via the helpers above.
#
# _LazyPath forwards every attribute to a freshly resolved Path, including
# the operator surface (truediv, joinpath, etc.) so callers can treat it
# like a normal Path without surprises.
class _LazyPath:
    __slots__ = ("_fn",)

    def __init__(self, fn: Callable[[], Path]) -> None:
        self._fn = fn

    def _resolve(self) -> Path:
        return self._fn()

    def __getattr__(self, name: str) -> Any:
        # Falls through for attributes not on this class itself.
        return getattr(self._resolve(), name)

    # Path operators: resolve and delegate
    def __truediv__(self, other: str | Path) -> Path:
        return self._resolve() / other

    def __rtruediv__(self, other: str | Path) -> Path:
        return other / self._resolve()

    def joinpath(self, *args: str | Path) -> Path:
        return self._resolve().joinpath(*args)

    # Path-like protocol
    def __fspath__(self) -> str:
        return os.fspath(self._resolve())

    # String / repr / eq / hash forward to the resolved Path
    def __str__(self) -> str:
        return str(self._resolve())

    def __repr__(self) -> str:
        return f"_LazyPath({self._resolve()!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _LazyPath):
            return self._resolve() == other._resolve()
        return self._resolve() == other

    def __hash__(self) -> int:
        return hash(self._resolve())

    # Common Path methods we know are used in this module — explicit
    # forwards keep mypy happy without losing the lazy semantics.
    def exists(self) -> bool:
        return self._resolve().exists()

    def stat(self) -> os.stat_result:
        return self._resolve().stat()

    def unlink(self, missing_ok: bool = False) -> None:
        self._resolve().unlink(missing_ok=missing_ok)


CENTRAL_DIR: _LazyPath = _LazyPath(_central_dir)
CENTRAL_SECRETS_FILE: _LazyPath = _LazyPath(_central_secrets_file)

KNOWN_KEYS = (
    "anthropic_api_key",
    "google_oauth_client_id",
    "google_oauth_client_secret",
)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DOCS_SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]
ALL_GOOGLE_SCOPES = DRIVE_SCOPES + DOCS_SCOPES

# Map known key names to the env var that overrides them.
ENV_OVERRIDES = {
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "google_oauth_client_id": "GOOGLE_OAUTH_CLIENT_ID",
    "google_oauth_client_secret": "GOOGLE_OAUTH_CLIENT_SECRET",
}


# ─── Layered credential lookup ──────────────────────────────────────────────


def _from_keyring(name: str) -> str | None:
    if not _HAS_KEYRING:
        return None
    try:
        return keyring.get_password(KEYRING_SERVICE, name)
    except keyring.errors.NoKeyringError:
        return None
    except keyring.errors.KeyringError as exc:
        raise RuntimeError(
            "Keyring lookup failed. Ensure your OS keyring is unlocked and available, then retry."
        ) from exc


def _read_file_data_checked() -> dict[str, Any]:
    """Read the secrets file with TOCTOU + symlink protection plus
    parent-dir mode enforcement.

    See ``security/0001-tocttou-symlink-secrets-file.md`` and
    ``security/0002-parent-dir-permissions-not-enforced.md``.

    Three layered checks:

    1. **Parent dir mode** — ``~/.config/ergodix/`` must be ``0o700``.
       README documents this; C5 enforces at install time; we re-check
       at every read because a directory at e.g. ``0o755`` (the default
       umask result) defeats the file's mode-600 invariant — anyone
       with same-uid write access could rename the file out and
       substitute their own.
    2. **Symlink rejection** — ``O_NOFOLLOW`` makes ``os.open`` fail
       with ``ELOOP`` if the path is a symlink, instead of silently
       following it. Translates to ``PermissionError``.
    3. **fstat on the open fd** — the mode check runs against the same
       inode the read consumes; no TOCTOU window between check and use.

    ``O_NOFOLLOW`` is POSIX; on platforms where it's undefined (Windows),
    ``getattr`` falls back to ``0`` and the symlink-swap protection
    degrades. The Windows threat model differs (NTFS symlinks require
    elevated privileges to create) and the loss of protection is
    acceptable for the cross-platform tradeoff.
    """
    path = CENTRAL_SECRETS_FILE
    parent = path.parent
    parent_st = parent.stat()
    if (parent_st.st_mode & 0o077) != 0:
        raise PermissionError(
            f"{parent} has loose permissions ({oct(parent_st.st_mode & 0o777)}); "
            f"the file's mode-600 invariant is meaningless when the parent dir "
            f"is group/world accessible. Run: chmod 700 {parent}"
        )

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(os.fspath(path), flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise PermissionError(
                f"{path} is a symlink; refusing to follow it. "
                f"Remove it and re-store your credentials: rm {path} && "
                f"python -m ergodix.auth set-key <name>"
            ) from exc
        raise
    with os.fdopen(fd, encoding="utf-8") as f:
        st = os.fstat(f.fileno())
        if (st.st_mode & 0o077) != 0:
            raise PermissionError(f"{path} has loose permissions. Run: chmod 600 {path}")
        data: dict[str, Any] = json.load(f)
    return data


def _from_file(name: str) -> str | None:
    if not CENTRAL_SECRETS_FILE.exists():
        return None
    data = _read_file_data_checked()
    if name in data:
        value = data[name]
        return value if isinstance(value, str) else None
    if name == "google_oauth_client_id":
        nested = data.get("google_oauth", {}).get("client_id")
        return nested if isinstance(nested, str) else None
    if name == "google_oauth_client_secret":
        nested = data.get("google_oauth", {}).get("client_secret")
        return nested if isinstance(nested, str) else None
    return None


def get_credential(name: str) -> str:
    """Resolve a credential by name. Raises RuntimeError if not found."""
    env_var = ENV_OVERRIDES.get(name)
    if env_var:
        env_val = os.environ.get(env_var)
        if env_val:
            return env_val

    kr = _from_keyring(name)
    if kr:
        return kr

    fl = _from_file(name)
    if fl:
        return fl

    raise RuntimeError(
        f"No credential found for {name!r}. Run: python -m ergodix.auth set-key {name}"
    )


def get_anthropic_api_key() -> str:
    return get_credential("anthropic_api_key")


def get_google_oauth_client() -> tuple[str, str]:
    return (
        get_credential("google_oauth_client_id"),
        get_credential("google_oauth_client_secret"),
    )


# ─── Per-project Google API service builders (stubs) ────────────────────────


def get_drive_service() -> Any:
    raise NotImplementedError(
        "Drive API access not yet wired up. Mirror mode covers v1 needs. "
        "Implement when Sprint 0 Story 0.3 (comment sync) starts."
    )


def get_docs_service() -> Any:
    raise NotImplementedError("Docs API access not yet wired up. Implement with Story 0.3.")


# ─── CLI ────────────────────────────────────────────────────────────────────


def _require_keyring() -> None:
    if not _HAS_KEYRING:
        print(
            "keyring is not installed. Run install_dependencies.sh first, or: pip install keyring",
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_set_key(name: str) -> None:
    _require_keyring()
    if name not in KNOWN_KEYS:
        print(f"Unknown key {name!r}. Known: {', '.join(KNOWN_KEYS)}", file=sys.stderr)
        sys.exit(1)
    import getpass

    value = getpass.getpass(f"Enter value for {name} (input hidden): ").strip()
    if not value:
        print("Empty value — aborted.", file=sys.stderr)
        sys.exit(1)
    keyring.set_password(KEYRING_SERVICE, name, value)
    print(f"Stored {name} in OS keyring (service: {KEYRING_SERVICE})")


def cmd_delete_key(name: str) -> None:
    _require_keyring()
    try:
        keyring.delete_password(KEYRING_SERVICE, name)
        print(f"Deleted {name} from keyring.")
    except keyring.errors.PasswordDeleteError:
        print(f"{name} not found in keyring.")


def cmd_status() -> None:
    print(f"Keyring service: {KEYRING_SERVICE}")
    if _HAS_KEYRING:
        print(f"Backend:         {keyring.get_keyring().__class__.__name__}")
    else:
        print("Backend:         (keyring not installed)")
    print(
        f"File fallback:   {CENTRAL_SECRETS_FILE} "
        f"({'exists' if CENTRAL_SECRETS_FILE.exists() else 'absent'})"
    )
    print()
    print("Credential presence (values never printed):")
    for name in KNOWN_KEYS:
        sources = []
        env_var = ENV_OVERRIDES.get(name)
        if env_var and os.environ.get(env_var):
            sources.append(f"env:{env_var}")
        try:
            if _from_keyring(name):
                sources.append("keyring")
        except RuntimeError as e:
            sources.append(f"keyring:ERROR({e})")
        try:
            if _from_file(name):
                sources.append("file")
        except PermissionError as e:
            sources.append(f"file:ERROR({e})")
        marker = "✓" if sources else "✗"
        src = ", ".join(sources) if sources else "(none)"
        print(f"  {marker} {name:<30} {src}")


def cmd_migrate_to_keyring(delete_file: bool) -> None:
    _require_keyring()
    if not CENTRAL_SECRETS_FILE.exists():
        print(f"No file at {CENTRAL_SECRETS_FILE} — nothing to migrate.")
        return
    data = _read_file_data_checked()
    moved = 0
    for name in KNOWN_KEYS:
        val = data.get(name)
        if val is None and name == "google_oauth_client_id":
            val = data.get("google_oauth", {}).get("client_id")
        if val is None and name == "google_oauth_client_secret":
            val = data.get("google_oauth", {}).get("client_secret")
        if val:
            keyring.set_password(KEYRING_SERVICE, name, val)
            print(f"  ✓ migrated {name}")
            moved += 1
    print(f"Migrated {moved} keys to keyring.")
    if delete_file:
        CENTRAL_SECRETS_FILE.unlink()
        print(f"Deleted {CENTRAL_SECRETS_FILE}")
    elif moved:
        print(
            f"Original file kept at {CENTRAL_SECRETS_FILE}. Re-run with --delete-file to remove it."
        )


def _main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__)
        return
    cmd, rest = args[0], args[1:]
    if cmd == "set-key" and len(rest) == 1:
        cmd_set_key(rest[0])
    elif cmd == "delete-key" and len(rest) == 1:
        cmd_delete_key(rest[0])
    elif cmd == "status" and not rest:
        cmd_status()
    elif cmd == "migrate-to-keyring":
        cmd_migrate_to_keyring(delete_file="--delete-file" in rest)
    else:
        print(f"Unknown command: {' '.join(args)}", file=sys.stderr)
        print("Run with --help for usage.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    _main()
