"""
OAuth token persistence for Drive / Docs API access (per ADR 0015 §1).

Stores Google OAuth refresh tokens at ``<repo>/.ergodix_tokens.json``
(mode 600, gitignored). Subsequent runs use the persisted refresh
token; access tokens are kept in memory and refreshed on demand.

This module covers the **token-file plumbing only** (sub-chunk 1a of
ADR 0015's implementation chunks). The OAuth flow itself
(``acquire_oauth_credentials`` — paste-the-code dance) lands in
sub-chunk 1b. The service builders (``get_drive_service`` /
``get_docs_service``) land in sub-chunk 1c.

**Security**: same invariants as ``ergodix/auth.py``'s secrets.json
fallback (per security/0001 + security/0002):

  - ``O_NOFOLLOW`` on read so a swapped symlink fails loudly.
  - ``fstat`` on the open fd so the mode check + read consume the
    same inode (no TOCTOU window).
  - Parent directory mode validated at read time (not just at write
    time — a loose parent dir defeats the file's mode-600).
  - File written with mode 600; refuse to read if perms are loosened.

Token file location resolves lazily (per CLAUDE.md: no
``Path.home()`` baking) — reads ``TOKEN_FILE`` from ``local_config.py``
if available, falls back to ``<cwd>/.ergodix_tokens.json``.
"""

from __future__ import annotations

import contextlib
import errno
import json
import os
from pathlib import Path
from typing import Any


def _token_file_path() -> Path:
    """Resolve the token file path. Reads ``TOKEN_FILE`` from
    ``local_config.py`` at cwd if defined; falls back to
    ``<cwd>/.ergodix_tokens.json``.

    Defensive: import errors / missing field → fallback. Tests use
    ``monkeypatch.chdir`` to control the resolved path.
    """
    config_path = Path.cwd() / "local_config.py"
    if config_path.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location("_oauth_local_config", config_path)
        if spec is not None and spec.loader is not None:
            # Defensive: any failure (syntax error, missing import, etc.)
            # falls back to the default. Don't crash OAuth startup over
            # a broken local_config.py — the verify phase is the loud
            # surface for config validation.
            with contextlib.suppress(Exception):
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                token_file = getattr(module, "TOKEN_FILE", None)
                if isinstance(token_file, Path):
                    return token_file
                if isinstance(token_file, str) and token_file:
                    return Path(token_file)
    return Path.cwd() / ".ergodix_tokens.json"


def _check_parent_dir_mode(parent: Path) -> None:
    """Refuse to proceed if the token file's parent dir has loose
    perms. Mirrors security/0002's pattern. Caller catches
    PermissionError if it wants to soft-fail."""
    parent_st = parent.stat()
    if (parent_st.st_mode & 0o077) != 0:
        raise PermissionError(
            f"{parent} has loose permissions ({oct(parent_st.st_mode & 0o777)}); "
            f"the token file's mode-600 invariant is meaningless when the parent dir "
            f"is group/world accessible. Run: chmod 700 {parent}"
        )


def load_oauth_tokens() -> dict[str, Any] | None:
    """Load OAuth tokens from disk.

    Returns the parsed JSON dict, or ``None`` if the file doesn't
    exist. Raises ``PermissionError`` on:
      - parent directory has loose perms (mode > 700);
      - token file is a symlink (refused via ``O_NOFOLLOW``);
      - token file has loose perms (mode > 600);
    Raises ``ValueError`` on malformed JSON content.

    Same TOCTOU + symlink protections as
    ``ergodix.auth._read_file_data_checked`` (security/0001/0002).
    """
    path = _token_file_path()
    if not path.exists():
        return None

    parent = path.parent
    _check_parent_dir_mode(parent)

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(os.fspath(path), flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise PermissionError(
                f"{path} is a symlink; refusing to follow it. Remove it and re-run OAuth: rm {path}"
            ) from exc
        raise

    with os.fdopen(fd, encoding="utf-8") as f:
        st = os.fstat(f.fileno())
        if (st.st_mode & 0o077) != 0:
            raise PermissionError(
                f"{path} has loose permissions ({oct(st.st_mode & 0o777)}); "
                f"OAuth tokens must be mode 0o600. Run: chmod 600 {path}"
            )
        try:
            data: dict[str, Any] = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path} is malformed JSON: {exc}") from exc
    return data


def save_oauth_tokens(tokens: dict[str, Any]) -> None:
    """Persist OAuth tokens to disk at mode 0o600.

    Creates the parent directory if missing (analogous to F2's
    cantilever.log mkdir). Writes via a temp file + rename for
    atomicity — partial-write interrupts can't leave a corrupt
    tokens file.
    """
    path = _token_file_path()
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    # Write atomically: tmp file with mode 600, then rename into place.
    # The rename is atomic on POSIX so an interrupted save can't leave
    # a half-written tokens file at the canonical path.
    tmp = path.with_suffix(path.suffix + ".tmp")

    # Open with O_CREAT | O_WRONLY | O_TRUNC at mode 0o600 so the
    # narrow window between create and chmod is closed.
    fd = os.open(
        os.fspath(tmp),
        os.O_CREAT | os.O_WRONLY | os.O_TRUNC,
        0o600,
    )
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, sort_keys=True)
        f.write("\n")

    # If the file existed previously with different perms (e.g.,
    # someone chmod'd it loose), the os.open above created a fresh
    # file at 0o600 because O_CREAT + mode applies to new files. The
    # rename inherits the new file's mode. Belt-and-suspenders chmod
    # to be explicit:
    os.chmod(tmp, 0o600)

    os.rename(tmp, path)


def clear_oauth_tokens() -> None:
    """Delete the token file. Used on revocation detection (per
    ADR 0015: if the refresh token is revoked, migrate detects the
    failure, clears the stale file, and re-runs the OAuth dance)."""
    path = _token_file_path()
    # Idempotent: file may already be gone from a prior cleanup attempt.
    with contextlib.suppress(FileNotFoundError):
        os.unlink(os.fspath(path))
