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
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials


def _token_file_path() -> Path:
    """Resolve the token file path. Reads ``TOKEN_FILE`` from
    ``local_config.py`` at cwd if defined; falls back to
    ``<cwd>/.ergodix_tokens.json``.

    A broken ``local_config.py`` (syntax error, import failure, etc.)
    no longer falls back silently — we emit a ``UserWarning`` so the
    user can see they have a config they wanted to honor that we
    couldn't load. The fallback path is still returned so OAuth doesn't
    refuse to start over a broken config; the verify phase is the loud
    surface for the deeper "fix your config" workflow.
    """
    config_path = Path.cwd() / "local_config.py"
    if config_path.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location("_oauth_local_config", config_path)
        if spec is not None and spec.loader is not None:
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as exc:
                warnings.warn(
                    (
                        f"local_config.py at {config_path} could not be loaded "
                        f"({type(exc).__name__}: {exc}); falling back to default "
                        f"token file path. Any TOKEN_FILE override in local_config.py "
                        f"is being ignored until you fix the file."
                    ),
                    UserWarning,
                    stacklevel=2,
                )
            else:
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
    # When we have to create the parent ourselves, apply mode 0o700 to
    # the leaf at creation time — `mode=` on `Path.mkdir` only affects
    # newly-created leaves (existing dirs are untouched even with
    # exist_ok=True). That way fresh installs sail through; a
    # pre-existing parent is left alone and validated on the next line.
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Mirror the load-side check: a 0o755 parent silently undermines the
    # file's 0o600 invariant. C5 (cantilever prereq) ensures
    # ``~/.config/ergodix/`` is mode 0o700, but if save_oauth_tokens()
    # runs against a different pre-existing parent (a sibling repo, an
    # ad-hoc test, a hand-edited deploy), we want the failure loud
    # rather than a quiet false-secure write. PR Review 1 finding #5.
    _check_parent_dir_mode(parent)

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


# ─── OAuth flow (sub-chunk 1b per ADR 0015) ────────────────────────────────
#
# Paste-the-code dance: print the auth URL, user opens in browser, copies
# the verification code from Google's confirmation page, pastes it back at
# the prompt. Per ADR 0015 §1: simpler than localhost-redirect, port-conflict-
# free, works over SSH.

# Locked scopes per ADR 0001 / ergodix.auth: drive.readonly + documents.readonly.
# Broader scopes require an explicit ADR amendment.
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
DOCS_SCOPE = "https://www.googleapis.com/auth/documents.readonly"
ALL_SCOPES: list[str] = [DRIVE_SCOPE, DOCS_SCOPE]

# Out-of-band redirect URI for the paste-the-code flow. Google displays the
# verification code on a confirmation page rather than redirecting to a
# localhost URL.
_OOB_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


PromptFn = Callable[[str], str]
"""User-input callback. Default is ``input``; tests inject their own."""

OutputFn = Callable[[str], None]
"""User-output callback. Default is ``print``; tests inject their own."""


def _build_client_config(client_id: str, client_secret: str) -> dict[str, Any]:
    """Build the OAuth client config dict that
    ``google_auth_oauthlib.flow.Flow.from_client_config`` expects.

    Uses the ``installed`` shape (per Google's "Desktop application"
    OAuth client type) — appropriate for ErgodixDocs since it's a
    locally-installed CLI rather than a web service.
    """
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_OOB_REDIRECT_URI],
        }
    }


def _credentials_to_dict(creds: Credentials) -> dict[str, Any]:
    """Serialize a ``google.oauth2.credentials.Credentials`` instance to
    a JSON-friendly dict that ``save_oauth_tokens`` can persist."""
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }


def _credentials_from_dict(data: dict[str, Any]) -> Credentials:
    """Reconstruct a ``Credentials`` instance from a saved dict.

    Mirror of ``_credentials_to_dict``. Used by sub-chunk 1c's
    ``get_drive_service`` / ``get_docs_service`` to rebuild creds on
    every cantilever / migrate run.
    """
    from datetime import datetime

    from google.oauth2.credentials import Credentials

    expiry_str = data.get("expiry")
    expiry = datetime.fromisoformat(expiry_str) if isinstance(expiry_str, str) else None

    return Credentials(  # type: ignore[no-untyped-call]
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
        expiry=expiry,
    )


def acquire_oauth_credentials(
    *,
    prompt_fn: PromptFn = input,
    output_fn: OutputFn = print,
) -> dict[str, Any]:
    """Run the paste-the-code OAuth flow.

    Steps:
      1. Read ``google_oauth_client_id`` + ``google_oauth_client_secret``
         from the keyring (via ``ergodix.auth.get_credential``; C6's
         configure phase sets these).
      2. Build a ``google_auth_oauthlib.flow.Flow`` with the locked
         readonly scopes.
      3. Print the authorization URL via ``output_fn``.
      4. Prompt the user via ``prompt_fn`` to paste the verification
         code Google shows after sign-in.
      5. Exchange the code for an access + refresh token pair.
      6. Return a JSON-friendly dict ready for ``save_oauth_tokens``.

    Caller is responsible for calling ``save_oauth_tokens`` on the
    returned dict — keeping acquire and persist as separate concerns
    means tests can verify acquire's exchange logic without filesystem
    side effects.

    Raises ``RuntimeError`` if the user enters an empty code (they
    pressed Enter without pasting). Raises whatever ``Flow.fetch_token``
    raises on a bad / expired / already-used code (typically
    ``google.auth.exceptions.OAuthError``); migrate's caller surfaces
    these to the user with a "code didn't work, run again" remediation.
    """
    from google_auth_oauthlib.flow import Flow

    from ergodix.auth import get_credential

    client_id = get_credential("google_oauth_client_id")
    client_secret = get_credential("google_oauth_client_secret")

    flow = Flow.from_client_config(
        _build_client_config(client_id, client_secret),
        scopes=ALL_SCOPES,
        redirect_uri=_OOB_REDIRECT_URI,
    )

    # access_type=offline tells Google to issue a refresh token along
    # with the access token. prompt=consent forces the consent screen
    # even on re-auth — matters for users who previously authorized at
    # different scopes.
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    output_fn("")
    output_fn("Open this URL in your browser to authorize ErgodixDocs:")
    output_fn(f"  {auth_url}")
    output_fn("")
    output_fn("After signing in, Google will display a verification code.")

    code = prompt_fn("Paste the code here: ").strip()
    if not code:
        raise RuntimeError("No authorization code provided. OAuth aborted; re-run when ready.")

    flow.fetch_token(code=code)
    return _credentials_to_dict(flow.credentials)


def _client_id_matches_config(creds: Credentials, output_fn: OutputFn) -> bool:
    """Return True if ``creds.client_id`` matches the current config's
    ``google_oauth_client_id``, else False.

    On mismatch, emits a clear message via ``output_fn`` so the user
    sees that their token is being thrown away because their OAuth
    client credentials rotated. PR Review 1 finding #2.

    Returns True (assume match, proceed normally) when the current
    config can't be read — ``get_credential`` raising RuntimeError
    means C6 hasn't run, or the keyring is unreachable, and the
    downstream flow will surface that as a clearer error.
    """
    try:
        from ergodix.auth import get_credential

        current_client_id = get_credential("google_oauth_client_id")
    except RuntimeError:
        return True

    if not current_client_id or not creds.client_id:
        return True
    if creds.client_id == current_client_id:
        return True

    output_fn(
        f"OAuth client ID changed (token was issued for '{creds.client_id}', "
        f"current config is '{current_client_id}'). Clearing stale tokens and "
        f"re-authenticating with the new client."
    )
    return False


def load_or_acquire_credentials(
    *,
    prompt_fn: PromptFn = input,
    output_fn: OutputFn = print,
) -> Credentials:
    """Return a usable ``Credentials`` for Drive / Docs API access.

    Decision tree:
      1. Try ``load_oauth_tokens()``. If a token file exists:
         - Reconstruct ``Credentials`` from it.
         - **Client-ID consistency check** (PR Review 1 #2): if the
           token's client_id doesn't match the current configured
           ``google_oauth_client_id``, the refresh is doomed — clear
           and fall through to acquire.
         - If the access token is still valid, return it.
         - If expired but a refresh token is present, attempt
           ``creds.refresh(Request())``. On success, persist the
           refreshed creds + return.
         - On refresh failure (token revoked, network unreachable,
           etc.), surface the underlying error via ``output_fn``
           (PR Review 1 #1), clear the stale file, fall through to
           acquire.
      2. No usable token on disk → run ``acquire_oauth_credentials``
         (the paste-the-code dance), persist the result, return.

    Tests inject ``prompt_fn`` / ``output_fn`` so the dance is
    exercised without real stdin / stdout. Production uses
    ``input`` / ``print`` defaults.
    """
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request

    tokens = load_oauth_tokens()
    if tokens is not None:
        creds = _credentials_from_dict(tokens)
        if not _client_id_matches_config(creds, output_fn):
            # Stale tokens — issued for a different OAuth client than
            # the one currently configured. Clear and fall through.
            clear_oauth_tokens()
        else:
            if creds.valid:
                return creds
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())  # type: ignore[no-untyped-call]
                except RefreshError as exc:
                    # Surface the underlying error so the user knows why
                    # they're being re-prompted, instead of seeing a
                    # silent restart of the OAuth dance.
                    output_fn(
                        f"Refresh token couldn't be used (Google reports: {exc}). "
                        f"Re-authenticating. If this persists, check your network "
                        f"and that your OAuth client credentials are still valid."
                    )
                    clear_oauth_tokens()
                else:
                    # Refresh succeeded — persist the new access token +
                    # any updated expiry the server returned.
                    save_oauth_tokens(_credentials_to_dict(creds))
                    return creds

    new_tokens = acquire_oauth_credentials(prompt_fn=prompt_fn, output_fn=output_fn)
    save_oauth_tokens(new_tokens)
    return _credentials_from_dict(new_tokens)
