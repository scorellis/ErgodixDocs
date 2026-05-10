"""
Tests for ergodix.oauth — token-file plumbing (sub-chunk 1a of
ADR 0015's migrate implementation).

Pure file I/O; no Google OAuth library involved (that's sub-chunk
1b). Mirrors the security pattern from tests/test_auth.py for
parent-dir mode + symlink rejection + loose-file-mode rejection.
"""

from __future__ import annotations

import json
import os
from datetime import UTC
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# ─── _token_file_path ──────────────────────────────────────────────────────


def test_token_file_path_falls_back_to_cwd_when_local_config_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.oauth import _token_file_path

    monkeypatch.chdir(tmp_path)

    assert _token_file_path() == tmp_path / ".ergodix_tokens.json"


def test_token_file_path_reads_from_local_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.oauth import _token_file_path

    custom = tmp_path / "custom-location" / "tokens.json"
    monkeypatch.chdir(tmp_path)
    (tmp_path / "local_config.py").write_text(
        f"from pathlib import Path\nTOKEN_FILE = Path('{custom}')\n"
    )

    assert _token_file_path() == custom


def test_token_file_path_handles_malformed_local_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed local_config.py → fall back to default. Don't crash
    OAuth startup over a syntax error in someone's config."""
    from ergodix.oauth import _token_file_path

    monkeypatch.chdir(tmp_path)
    (tmp_path / "local_config.py").write_text("import nonexistent_module_xyz\n")

    assert _token_file_path() == tmp_path / ".ergodix_tokens.json"


# ─── load_oauth_tokens — happy paths ───────────────────────────────────────


def test_load_returns_none_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.oauth import load_oauth_tokens

    monkeypatch.chdir(tmp_path)

    assert load_oauth_tokens() is None


def test_load_returns_parsed_dict_when_file_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.oauth import load_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    tokens = {
        "refresh_token": "rt-abc",
        "client_id": "ci",
        "client_secret": "cs",
    }
    token_file = tmp_path / ".ergodix_tokens.json"
    token_file.write_text(json.dumps(tokens))
    token_file.chmod(0o600)

    result = load_oauth_tokens()

    assert result == tokens


# ─── load_oauth_tokens — security invariants (per security/0001 + 0002) ───


def test_load_rejects_loose_parent_dir_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.oauth import load_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o755)  # loose
    token_file = tmp_path / ".ergodix_tokens.json"
    token_file.write_text(json.dumps({"refresh_token": "rt"}))
    token_file.chmod(0o600)

    with pytest.raises(PermissionError, match="700"):
        load_oauth_tokens()


def test_load_rejects_loose_file_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.oauth import load_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    token_file = tmp_path / ".ergodix_tokens.json"
    token_file.write_text(json.dumps({"refresh_token": "rt"}))
    token_file.chmod(0o644)  # loose

    with pytest.raises(PermissionError, match="600"):
        load_oauth_tokens()


@pytest.mark.skipif(
    not hasattr(os, "O_NOFOLLOW"),
    reason="Symlink protection requires O_NOFOLLOW (POSIX). Windows tests skipped.",
)
def test_load_rejects_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A token file that's a symlink must be refused — even if the
    target has good perms. Mirrors security/0001's pattern."""
    from ergodix.oauth import load_oauth_tokens

    target = tmp_path / "elsewhere" / "tokens.json"
    target.parent.mkdir()
    target.write_text(json.dumps({"refresh_token": "attacker-supplied"}))
    target.chmod(0o600)

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    token_link = tmp_path / ".ergodix_tokens.json"
    token_link.symlink_to(target)

    with pytest.raises(PermissionError, match="symlink"):
        load_oauth_tokens()


def test_load_raises_on_malformed_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.oauth import load_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    token_file = tmp_path / ".ergodix_tokens.json"
    token_file.write_text("{ not valid [json")
    token_file.chmod(0o600)

    with pytest.raises(ValueError, match="malformed"):
        load_oauth_tokens()


# ─── save_oauth_tokens ─────────────────────────────────────────────────────


def test_save_writes_tokens_at_mode_600(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.oauth import save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tokens = {"refresh_token": "rt-xyz", "client_id": "ci"}

    save_oauth_tokens(tokens)

    token_file = tmp_path / ".ergodix_tokens.json"
    assert token_file.exists()
    mode = token_file.stat().st_mode & 0o777
    assert mode == 0o600, f"expected 0o600, got {oct(mode)}"


def test_save_then_load_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the canonical save → load contract — tokens written via
    save_oauth_tokens must read back identically via load_oauth_tokens."""
    from ergodix.oauth import load_oauth_tokens, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    tokens = {
        "refresh_token": "rt-abc",
        "access_token": "at-def",
        "client_id": "ci",
        "client_secret": "cs",
        "expiry": "2026-05-10T03:00:00Z",
    }

    save_oauth_tokens(tokens)
    loaded = load_oauth_tokens()

    assert loaded == tokens


def test_save_creates_parent_dir_if_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When TOKEN_FILE points at a path whose parent doesn't exist,
    save_oauth_tokens creates it (so first-time auth doesn't fail
    on a fresh machine)."""
    from ergodix.oauth import save_oauth_tokens

    deep = tmp_path / "deep" / "missing" / "tokens.json"
    monkeypatch.chdir(tmp_path)
    (tmp_path / "local_config.py").write_text(
        f"from pathlib import Path\nTOKEN_FILE = Path('{deep}')\n"
    )

    save_oauth_tokens({"refresh_token": "rt"})

    assert deep.exists()


def test_save_overwrites_existing_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """save_oauth_tokens replaces an existing file via tmp + rename.
    Pin that the resulting file is at mode 0o600 even when the prior
    file had loose perms — a regression where save inherited the old
    perms would leave tokens world-readable after a refresh."""
    from ergodix.oauth import save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    token_file = tmp_path / ".ergodix_tokens.json"
    token_file.write_text(json.dumps({"refresh_token": "old"}))
    token_file.chmod(0o644)  # deliberately loose

    save_oauth_tokens({"refresh_token": "new"})

    mode = token_file.stat().st_mode & 0o777
    assert mode == 0o600, f"expected 0o600 after save, got {oct(mode)}"
    assert json.loads(token_file.read_text()) == {"refresh_token": "new"}


# ─── clear_oauth_tokens ────────────────────────────────────────────────────


def test_clear_removes_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.oauth import clear_oauth_tokens

    monkeypatch.chdir(tmp_path)
    token_file = tmp_path / ".ergodix_tokens.json"
    token_file.write_text(json.dumps({"refresh_token": "rt"}))

    clear_oauth_tokens()

    assert not token_file.exists()


def test_clear_is_idempotent_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No file → no-op, no exception. Used on revocation cleanup
    where the file may already be gone from a prior cleanup attempt."""
    from ergodix.oauth import clear_oauth_tokens

    monkeypatch.chdir(tmp_path)

    # Should not raise
    clear_oauth_tokens()


# ─── OAuth flow (sub-chunk 1b) ─────────────────────────────────────────────
#
# Tests mock google_auth_oauthlib.flow.Flow + ergodix.auth.get_credential
# so the dance never hits real Google or the real keyring.


def _setup_mock_flow(monkeypatch, *, fetched_credentials: dict[str, Any] | None = None):
    """Wire a fake Flow class so ``acquire_oauth_credentials`` can be
    exercised without network. Returns the (FakeFlowClass,
    fake_flow_instance) tuple so tests can assert on what was passed."""
    fake_creds = MagicMock()
    creds_data = fetched_credentials or {
        "token": "at-acquired",
        "refresh_token": "rt-acquired",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test-cid",
        "client_secret": "test-cs",
        "scopes": ["scope-a"],
        "expiry": None,
    }
    fake_creds.token = creds_data["token"]
    fake_creds.refresh_token = creds_data["refresh_token"]
    fake_creds.token_uri = creds_data["token_uri"]
    fake_creds.client_id = creds_data["client_id"]
    fake_creds.client_secret = creds_data["client_secret"]
    fake_creds.scopes = creds_data["scopes"]
    fake_creds.expiry = creds_data["expiry"]

    fake_flow = MagicMock()
    fake_flow.authorization_url.return_value = (
        "https://auth.example.com/url",
        "state-token",
    )
    fake_flow.credentials = fake_creds

    fake_flow_class = MagicMock()
    fake_flow_class.from_client_config.return_value = fake_flow

    import google_auth_oauthlib.flow

    monkeypatch.setattr(google_auth_oauthlib.flow, "Flow", fake_flow_class)
    return fake_flow_class, fake_flow


def _stub_get_credential(
    monkeypatch,
    *,
    client_id: str = "test-cid",
    client_secret: str = "test-cs",  # noqa: S107 — test fixture, not a real secret
):
    """Stub ergodix.auth.get_credential so it returns canned client
    creds rather than hitting the real keyring."""
    import ergodix.auth

    def fake_get_credential(name: str) -> str:
        if name == "google_oauth_client_id":
            return client_id
        if name == "google_oauth_client_secret":
            return client_secret
        raise RuntimeError(f"unexpected credential name: {name}")

    monkeypatch.setattr(ergodix.auth, "get_credential", fake_get_credential)


def test_acquire_returns_dict_with_acquired_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.oauth import acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    _setup_mock_flow(monkeypatch)

    result = acquire_oauth_credentials(
        prompt_fn=lambda _: "the-pasted-code", output_fn=lambda _: None
    )

    assert result["token"] == "at-acquired"
    assert result["refresh_token"] == "rt-acquired"
    assert result["client_id"] == "test-cid"
    assert "scopes" in result


def test_acquire_uses_locked_readonly_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scopes are exactly drive.readonly + documents.readonly. Drift
    to broader scopes (e.g. drive.file) needs an explicit ADR; this
    test guards against accidental scope creep."""
    from ergodix.oauth import ALL_SCOPES, acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    fake_flow_class, _fake_flow = _setup_mock_flow(monkeypatch)

    acquire_oauth_credentials(prompt_fn=lambda _: "code", output_fn=lambda _: None)

    call_kwargs = fake_flow_class.from_client_config.call_args.kwargs
    assert call_kwargs["scopes"] == ALL_SCOPES
    assert "drive.readonly" in ALL_SCOPES[0]
    assert "documents.readonly" in ALL_SCOPES[1]
    assert len(ALL_SCOPES) == 2


def test_acquire_uses_offline_access_for_refresh_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """access_type=offline is required for Google to issue a refresh
    token. Without it the access token expires after an hour."""
    from ergodix.oauth import acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    _, fake_flow = _setup_mock_flow(monkeypatch)

    acquire_oauth_credentials(prompt_fn=lambda _: "code", output_fn=lambda _: None)

    auth_url_kwargs = fake_flow.authorization_url.call_args.kwargs
    assert auth_url_kwargs.get("access_type") == "offline"


def test_acquire_uses_oob_redirect_for_paste_the_code_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Paste-the-code (OOB) flow needs the OOB redirect URI so Google
    shows the code on a confirmation page (no localhost server needed)."""
    from ergodix.oauth import acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    fake_flow_class, _fake_flow = _setup_mock_flow(monkeypatch)

    acquire_oauth_credentials(prompt_fn=lambda _: "code", output_fn=lambda _: None)

    call_kwargs = fake_flow_class.from_client_config.call_args.kwargs
    assert call_kwargs.get("redirect_uri") == "urn:ietf:wg:oauth:2.0:oob"


def test_acquire_prints_authorization_url_via_output_fn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.oauth import acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    _setup_mock_flow(monkeypatch)

    captured: list[str] = []
    acquire_oauth_credentials(prompt_fn=lambda _: "code", output_fn=captured.append)

    output = "\n".join(captured)
    assert "https://auth.example.com/url" in output


def test_acquire_passes_pasted_code_to_fetch_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """The pasted code (stripped of whitespace) reaches fetch_token verbatim."""
    from ergodix.oauth import acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    _, fake_flow = _setup_mock_flow(monkeypatch)

    acquire_oauth_credentials(
        prompt_fn=lambda _: "  4/0AY0e-g5...mock-code  ", output_fn=lambda _: None
    )

    call_kwargs = fake_flow.fetch_token.call_args.kwargs
    assert call_kwargs.get("code") == "4/0AY0e-g5...mock-code"


def test_acquire_raises_on_empty_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """User pressed Enter without pasting → clear RuntimeError."""
    from ergodix.oauth import acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    _setup_mock_flow(monkeypatch)

    with pytest.raises(RuntimeError, match="No authorization code"):
        acquire_oauth_credentials(prompt_fn=lambda _: "   ", output_fn=lambda _: None)


def test_acquire_propagates_missing_client_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If C6 hasn't run, get_credential raises. acquire propagates so
    the user sees a 'run auth set-key' remediation."""
    import ergodix.auth
    from ergodix.oauth import acquire_oauth_credentials

    def fake_get_credential(_name: str) -> str:
        raise RuntimeError("No credential found for 'google_oauth_client_id'")

    monkeypatch.setattr(ergodix.auth, "get_credential", fake_get_credential)

    with pytest.raises(RuntimeError, match="No credential found"):
        acquire_oauth_credentials(prompt_fn=lambda _: "code", output_fn=lambda _: None)


# ─── Credentials dict roundtrip ─────────────────────────────────────────────


def test_credentials_to_dict_serializes_canonical_fields() -> None:
    from ergodix.oauth import _credentials_to_dict

    fake_creds = MagicMock()
    fake_creds.token = "at"
    fake_creds.refresh_token = "rt"
    fake_creds.token_uri = "https://oauth2.googleapis.com/token"
    fake_creds.client_id = "ci"
    fake_creds.client_secret = "cs"
    fake_creds.scopes = ["scope-a", "scope-b"]
    fake_creds.expiry = None

    result = _credentials_to_dict(fake_creds)

    assert set(result.keys()) >= {
        "token",
        "refresh_token",
        "token_uri",
        "client_id",
        "client_secret",
        "scopes",
        "expiry",
    }
    assert result["scopes"] == ["scope-a", "scope-b"]


def test_credentials_to_dict_handles_none_scopes() -> None:
    """None scopes → []. Don't let None propagate to JSON / disk."""
    from ergodix.oauth import _credentials_to_dict

    fake_creds = MagicMock()
    fake_creds.token = "at"
    fake_creds.refresh_token = "rt"
    fake_creds.token_uri = "https://oauth2.googleapis.com/token"
    fake_creds.client_id = "ci"
    fake_creds.client_secret = "cs"
    fake_creds.scopes = None
    fake_creds.expiry = None

    result = _credentials_to_dict(fake_creds)

    assert result["scopes"] == []


def test_credentials_to_dict_serializes_expiry_as_iso_string() -> None:
    from datetime import datetime

    from ergodix.oauth import _credentials_to_dict

    expiry = datetime(2026, 5, 10, 3, 0, 0, tzinfo=UTC)

    fake_creds = MagicMock()
    fake_creds.token = "at"
    fake_creds.refresh_token = "rt"
    fake_creds.token_uri = "https://oauth2.googleapis.com/token"
    fake_creds.client_id = "ci"
    fake_creds.client_secret = "cs"
    fake_creds.scopes = ["s"]
    fake_creds.expiry = expiry

    result = _credentials_to_dict(fake_creds)

    assert result["expiry"] == "2026-05-10T03:00:00+00:00"


def test_credentials_from_dict_roundtrip() -> None:
    """to_dict + from_dict roundtrips the loadable fields against
    the real Credentials class — verifies the wiring matches Google's
    expectations."""
    from datetime import datetime

    from ergodix.oauth import _credentials_from_dict, _credentials_to_dict

    expiry = datetime(2026, 5, 10, 3, 0, 0, tzinfo=UTC)
    original = MagicMock()
    original.token = "at"
    original.refresh_token = "rt"
    original.token_uri = "https://oauth2.googleapis.com/token"
    original.client_id = "ci"
    original.client_secret = "cs"
    original.scopes = ["scope-a"]
    original.expiry = expiry

    serialized = _credentials_to_dict(original)
    rebuilt = _credentials_from_dict(serialized)

    assert rebuilt.token == "at"
    assert rebuilt.refresh_token == "rt"
    assert rebuilt.client_id == "ci"
    assert rebuilt.client_secret == "cs"
    assert list(rebuilt.scopes) == ["scope-a"]


# ─── load_or_acquire_credentials (sub-chunk 1c) ────────────────────────────


def test_load_or_acquire_returns_valid_loaded_creds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tokens on disk + creds.valid → return the loaded creds without
    refresh, without acquire. Pure load-from-disk path."""
    import ergodix.oauth as oauth_module
    from ergodix.oauth import load_or_acquire_credentials, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    save_oauth_tokens(
        {
            "token": "valid-at",
            "refresh_token": "rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": None,
        }
    )

    fake_creds = MagicMock()
    fake_creds.valid = True
    fake_creds.expired = False
    fake_creds.token = "valid-at"
    monkeypatch.setattr(oauth_module, "_credentials_from_dict", lambda _data: fake_creds)

    # acquire and refresh paths must NOT be hit
    monkeypatch.setattr(
        oauth_module,
        "acquire_oauth_credentials",
        lambda **_kwargs: pytest.fail("acquire should not be called"),
    )

    result = load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=lambda _: None)

    assert result is fake_creds


def test_load_or_acquire_refreshes_expired_creds_and_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tokens on disk + expired access token + refresh token present
    → call creds.refresh(), persist the new state, return."""
    import ergodix.oauth as oauth_module
    from ergodix.oauth import load_or_acquire_credentials, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    save_oauth_tokens(
        {
            "token": "stale-at",
            "refresh_token": "rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": "2020-01-01T00:00:00+00:00",
        }
    )

    fake_creds = MagicMock()
    fake_creds.valid = False
    fake_creds.expired = True
    fake_creds.refresh_token = "rt"
    refresh_called = []

    def fake_refresh(_request):
        refresh_called.append(True)
        fake_creds.token = "fresh-at"
        fake_creds.valid = True

    fake_creds.refresh.side_effect = fake_refresh
    fake_creds.token = "stale-at"
    fake_creds.token_uri = "https://oauth2.googleapis.com/token"
    fake_creds.client_id = "ci"
    fake_creds.client_secret = "cs"
    fake_creds.scopes = ["scope-a"]
    fake_creds.expiry = None
    monkeypatch.setattr(oauth_module, "_credentials_from_dict", lambda _data: fake_creds)

    result = load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=lambda _: None)

    assert refresh_called == [True]
    assert result is fake_creds


def test_load_or_acquire_falls_through_to_acquire_when_refresh_revoked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tokens on disk but refresh raises (revocation simulated) →
    clear the stale file + run acquire + persist + return new creds."""
    from google.auth.exceptions import RefreshError

    import ergodix.oauth as oauth_module
    from ergodix.oauth import load_or_acquire_credentials, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    save_oauth_tokens(
        {
            "token": "stale-at",
            "refresh_token": "revoked-rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": None,
        }
    )

    fake_creds = MagicMock()
    fake_creds.valid = False
    fake_creds.expired = True
    fake_creds.refresh_token = "revoked-rt"
    fake_creds.refresh.side_effect = RefreshError("token revoked")
    monkeypatch.setattr(oauth_module, "_credentials_from_dict", lambda _data: fake_creds)

    new_token_dict = {
        "token": "fresh-at",
        "refresh_token": "fresh-rt",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "ci",
        "client_secret": "cs",
        "scopes": ["scope-a"],
        "expiry": None,
    }
    monkeypatch.setattr(
        oauth_module,
        "acquire_oauth_credentials",
        lambda **_kwargs: new_token_dict,
    )

    rebuilt = MagicMock()
    rebuilt.token = "fresh-at"

    def from_dict(data):
        # First call (load path): fake_creds. Second call (post-acquire): rebuilt.
        if data == new_token_dict:
            return rebuilt
        return fake_creds

    monkeypatch.setattr(oauth_module, "_credentials_from_dict", from_dict)

    result = load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=lambda _: None)

    assert result is rebuilt
    # Saved file should now contain fresh tokens
    from ergodix.oauth import load_oauth_tokens

    persisted = load_oauth_tokens()
    assert persisted == new_token_dict


def test_load_or_acquire_runs_full_flow_when_no_tokens_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No token file → run acquire → persist → return."""
    import ergodix.oauth as oauth_module
    from ergodix.oauth import load_oauth_tokens, load_or_acquire_credentials

    monkeypatch.chdir(tmp_path)

    new_token_dict = {
        "token": "fresh-at",
        "refresh_token": "fresh-rt",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "ci",
        "client_secret": "cs",
        "scopes": ["scope-a"],
        "expiry": None,
    }
    monkeypatch.setattr(
        oauth_module,
        "acquire_oauth_credentials",
        lambda **_kwargs: new_token_dict,
    )
    rebuilt = MagicMock()
    rebuilt.token = "fresh-at"
    monkeypatch.setattr(oauth_module, "_credentials_from_dict", lambda _data: rebuilt)

    result = load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=lambda _: None)

    assert result is rebuilt
    # File was created with the acquired tokens
    persisted = load_oauth_tokens()
    assert persisted == new_token_dict


# ─── PR Review 1 follow-ups (Findings 1, 2, 5, 6) ──────────────────────────


def test_load_or_acquire_explains_refresh_failure_via_output_fn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 1 (Medium): on RefreshError, the user previously got
    silently re-prompted. Now we surface the underlying error via
    output_fn so the user understands why re-auth is happening."""
    from google.auth.exceptions import RefreshError

    import ergodix.oauth as oauth_module
    from ergodix.oauth import load_or_acquire_credentials, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    save_oauth_tokens(
        {
            "token": "stale-at",
            "refresh_token": "revoked-rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": None,
        }
    )

    fake_creds = MagicMock()
    fake_creds.valid = False
    fake_creds.expired = True
    fake_creds.refresh_token = "revoked-rt"
    fake_creds.client_id = "ci"
    fake_creds.refresh.side_effect = RefreshError(
        "invalid_grant: Token has been expired or revoked."
    )

    new_token_dict = {
        "token": "fresh-at",
        "refresh_token": "fresh-rt",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "ci",
        "client_secret": "cs",
        "scopes": ["scope-a"],
        "expiry": None,
    }
    rebuilt = MagicMock()

    def from_dict(data: Any) -> Any:
        return rebuilt if data == new_token_dict else fake_creds

    monkeypatch.setattr(oauth_module, "_credentials_from_dict", from_dict)
    monkeypatch.setattr(oauth_module, "acquire_oauth_credentials", lambda **_kwargs: new_token_dict)

    captured: list[str] = []
    load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=captured.append)

    joined = "\n".join(captured)
    assert "Refresh token couldn't be used" in joined
    assert "invalid_grant" in joined
    assert "Re-authenticating" in joined


def test_load_or_acquire_clears_stale_tokens_on_client_id_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 2 (Low): if the OAuth client_id in the token file doesn't
    match the current config (user rotated GCP credentials), the
    refresh token is useless. Clear immediately, surface a clear
    message, run acquire — don't burn a refresh attempt that's
    guaranteed to fail."""
    import ergodix.oauth as oauth_module
    from ergodix.oauth import load_or_acquire_credentials, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    save_oauth_tokens(
        {
            "token": "stale-at",
            "refresh_token": "old-rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "old-ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": None,
        }
    )

    fake_creds = MagicMock()
    fake_creds.valid = True  # Even valid tokens shouldn't be returned on mismatch.
    fake_creds.client_id = "old-ci"

    new_token_dict = {
        "token": "fresh-at",
        "refresh_token": "fresh-rt",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "new-ci",
        "client_secret": "cs",
        "scopes": ["scope-a"],
        "expiry": None,
    }
    rebuilt = MagicMock()

    def from_dict(data: Any) -> Any:
        return rebuilt if data == new_token_dict else fake_creds

    monkeypatch.setattr(oauth_module, "_credentials_from_dict", from_dict)
    monkeypatch.setattr(oauth_module, "acquire_oauth_credentials", lambda **_kwargs: new_token_dict)
    # The current config says client_id is "new-ci" — mismatch with token's "old-ci".
    monkeypatch.setattr(
        "ergodix.auth.get_credential",
        lambda name: "new-ci" if name == "google_oauth_client_id" else "x",
    )

    captured: list[str] = []
    result = load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=captured.append)

    # Stale tokens cleared, fresh acquire ran, fresh creds returned.
    assert result is rebuilt
    joined = "\n".join(captured)
    assert "client" in joined.lower()
    assert "id" in joined.lower()
    assert "old-ci" in joined
    assert "new-ci" in joined


def test_load_or_acquire_skips_client_id_check_when_config_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If `get_credential` raises (no client_id in keyring/config), the
    consistency check can't run — proceed normally and let any
    downstream refresh failure handle the problem."""
    import ergodix.oauth as oauth_module
    from ergodix.oauth import load_or_acquire_credentials, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    save_oauth_tokens(
        {
            "token": "valid-at",
            "refresh_token": "rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": None,
        }
    )

    fake_creds = MagicMock()
    fake_creds.valid = True
    fake_creds.client_id = "ci"

    monkeypatch.setattr(oauth_module, "_credentials_from_dict", lambda _data: fake_creds)

    def raise_runtime(name: str) -> str:
        raise RuntimeError(f"No credential found for {name!r}.")

    monkeypatch.setattr("ergodix.auth.get_credential", raise_runtime)

    # Should not raise; should not call acquire; should return the loaded creds.
    result = load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=lambda _: None)
    assert result is fake_creds


def test_save_rejects_loose_parent_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Finding 5 (Low): save_oauth_tokens previously created the parent
    dir but didn't check its mode. A 0o755 parent silently undermines
    the file's 0o600 invariant. Now mirrors the load-side check and
    raises with a clear remediation."""
    from ergodix.oauth import save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o755)  # Loose parent

    with pytest.raises(PermissionError, match="loose permissions"):
        save_oauth_tokens(
            {
                "token": "x",
                "refresh_token": "y",
                "token_uri": "z",
                "client_id": "a",
                "client_secret": "b",
                "scopes": [],
                "expiry": None,
            }
        )

    # Make sure no token file was created with bad-mode parent.
    assert not (tmp_path / ".ergodix_tokens.json").exists()


def test_token_file_path_warns_when_local_config_is_broken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 6 (Low): a broken local_config.py previously caused a
    silent fallback to <cwd>/.ergodix_tokens.json — meaning the user's
    intended TOKEN_FILE override was ignored without warning. Now emit
    a warning so --verbose / pytest can surface the problem."""
    import ergodix.oauth as oauth_module

    monkeypatch.chdir(tmp_path)
    # Syntax error in local_config.py — should not crash but should warn.
    (tmp_path / "local_config.py").write_text("THIS IS NOT VALID PYTHON =\n", encoding="utf-8")

    with pytest.warns(UserWarning, match="local_config"):
        result = oauth_module._token_file_path()

    # Falls back to default location.
    assert result == tmp_path / ".ergodix_tokens.json"


def test_token_file_path_no_warning_when_local_config_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid local_config.py with TOKEN_FILE set should not warn."""
    import warnings

    import ergodix.oauth as oauth_module

    monkeypatch.chdir(tmp_path)
    custom_path = tmp_path / "custom-tokens.json"
    (tmp_path / "local_config.py").write_text(
        f"from pathlib import Path\nTOKEN_FILE = Path('{custom_path}')\n",
        encoding="utf-8",
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Any warning becomes an error
        result = oauth_module._token_file_path()

    assert result == custom_path


# ─── PR Review 1 follow-up: finding #4 (rate-limit / OAuth-exchange messaging) ─


def test_acquire_emits_friendly_message_on_invalid_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bad / expired / re-used code raises with `invalid_grant` in
    the message. Surface a friendlier explanation via output_fn before
    re-raising."""
    from ergodix.oauth import acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    _, fake_flow = _setup_mock_flow(monkeypatch)
    fake_flow.fetch_token.side_effect = RuntimeError(
        "(invalid_grant: Token has been expired or revoked.)"
    )

    captured: list[str] = []
    with pytest.raises(RuntimeError, match="invalid_grant"):
        acquire_oauth_credentials(prompt_fn=lambda _: "bad-code", output_fn=captured.append)

    joined = "\n".join(captured)
    assert "code" in joined.lower()
    assert any(token in joined.lower() for token in ("expire", "fresh", "rejected")), (
        "should explain that codes expire / be fresh"
    )


def test_acquire_emits_friendly_message_on_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Google rate-limit errors look different to the eye but indicate
    the user needs to wait, not retry immediately."""
    from ergodix.oauth import acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    _, fake_flow = _setup_mock_flow(monkeypatch)
    fake_flow.fetch_token.side_effect = RuntimeError("HTTP 429 Too Many Requests: rate-limited")

    captured: list[str] = []
    with pytest.raises(RuntimeError, match="429"):
        acquire_oauth_credentials(prompt_fn=lambda _: "code", output_fn=captured.append)

    joined = "\n".join(captured).lower()
    assert "rate" in joined or "wait" in joined
    assert any(token in joined for token in ("60", "minute", "later"))


def test_acquire_emits_generic_message_on_unknown_oauth_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Errors that don't match invalid_grant or rate-limit get a
    generic 'try again, check network/credentials' message."""
    from ergodix.oauth import acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    _, fake_flow = _setup_mock_flow(monkeypatch)
    fake_flow.fetch_token.side_effect = RuntimeError("completely-unexpected-network-blip-xyz")

    captured: list[str] = []
    with pytest.raises(RuntimeError, match="completely-unexpected-network-blip"):
        acquire_oauth_credentials(prompt_fn=lambda _: "code", output_fn=captured.append)

    joined = "\n".join(captured).lower()
    assert "completely-unexpected-network-blip" in joined  # raw error preserved
    assert any(token in joined for token in ("network", "credential", "again", "fail")), (
        "should suggest a remediation path"
    )


# ─── PR Review 1 follow-up: finding #7 (deserialization validation) ────────


def test_credentials_from_dict_rejects_missing_token_uri() -> None:
    """A token file missing the load-bearing `token_uri` field should
    fail at deserialization with a clear message — not silently produce
    a Credentials object that fails cryptically on the first refresh
    attempt."""
    from ergodix.oauth import _credentials_from_dict

    with pytest.raises(ValueError, match="token_uri"):
        _credentials_from_dict(
            {
                "token": "at",
                "refresh_token": "rt",
                # no token_uri
                "client_id": "ci",
                "client_secret": "cs",
                "scopes": [],
                "expiry": None,
            }
        )


def test_credentials_from_dict_rejects_missing_client_id() -> None:
    from ergodix.oauth import _credentials_from_dict

    with pytest.raises(ValueError, match="client_id"):
        _credentials_from_dict(
            {
                "token": "at",
                "refresh_token": "rt",
                "token_uri": "https://oauth2.googleapis.com/token",
                # no client_id
                "client_secret": "cs",
            }
        )


def test_credentials_from_dict_rejects_empty_string_client_secret() -> None:
    """Empty-string is treated as missing for required fields — a
    falsy required field is just as broken as an absent one."""
    from ergodix.oauth import _credentials_from_dict

    with pytest.raises(ValueError, match="client_secret"):
        _credentials_from_dict(
            {
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "ci",
                "client_secret": "",  # empty
                "refresh_token": "rt",
            }
        )


def test_credentials_from_dict_lists_all_missing_fields_at_once() -> None:
    """Don't fail on the first missing field; list them all so the
    user fixes the file in one pass."""
    from ergodix.oauth import _credentials_from_dict

    with pytest.raises(ValueError, match="missing or empty") as excinfo:
        _credentials_from_dict({"token": "at", "refresh_token": "rt"})

    msg = str(excinfo.value)
    assert "token_uri" in msg
    assert "client_id" in msg
    assert "client_secret" in msg


# ─── PR Review 1 follow-up: finding #3 (refresh-token age check) ───────────


def test_acquire_records_refresh_token_issued_at(monkeypatch: pytest.MonkeyPatch) -> None:
    """The dict returned by `acquire_oauth_credentials` should include
    a `refresh_token_issued_at` ISO-8601 timestamp so a future load
    can detect stale tokens."""
    from ergodix.oauth import acquire_oauth_credentials

    _stub_get_credential(monkeypatch)
    _setup_mock_flow(monkeypatch)

    result = acquire_oauth_credentials(prompt_fn=lambda _: "code", output_fn=lambda _: None)

    assert "refresh_token_issued_at" in result
    issued_at_str = result["refresh_token_issued_at"]
    assert isinstance(issued_at_str, str)
    # Should parse as a Z-suffixed timestamp.
    from datetime import datetime as _datetime

    parsed = _datetime.fromisoformat(issued_at_str)
    assert parsed is not None


def test_load_or_acquire_warns_on_stale_refresh_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A token file whose `refresh_token_issued_at` is >90 days old
    should emit a warning via `output_fn` (Google may invalidate
    refresh tokens after 6 months of non-use). Doesn't force re-auth —
    just informs the user."""
    from ergodix.oauth import load_or_acquire_credentials, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)

    # 100 days ago — clearly past the 90-day warning threshold.
    save_oauth_tokens(
        {
            "token": "at",
            "refresh_token": "rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": None,
            "refresh_token_issued_at": "2026-01-30T00:00:00Z",
        }
    )

    fake_creds = MagicMock()
    fake_creds.valid = True
    fake_creds.client_id = "ci"

    import ergodix.oauth as oauth_module

    monkeypatch.setattr(oauth_module, "_credentials_from_dict", lambda _data: fake_creds)
    monkeypatch.setattr(
        "ergodix.auth.get_credential",
        lambda name: "ci" if name == "google_oauth_client_id" else "x",
    )

    captured: list[str] = []
    load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=captured.append)

    joined = "\n".join(captured).lower()
    assert any(token in joined for token in ("days old", "stale", "invalidate", "6 months"))


def test_load_or_acquire_no_warning_for_fresh_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recently-issued refresh token should NOT warn."""
    from datetime import datetime as _datetime
    from datetime import timedelta as _timedelta

    from ergodix.oauth import load_or_acquire_credentials, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)

    # 5 days ago — well within the warning threshold.
    recent = (_datetime.now(UTC) - _timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_oauth_tokens(
        {
            "token": "at",
            "refresh_token": "rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": None,
            "refresh_token_issued_at": recent,
        }
    )

    fake_creds = MagicMock()
    fake_creds.valid = True
    fake_creds.client_id = "ci"

    import ergodix.oauth as oauth_module

    monkeypatch.setattr(oauth_module, "_credentials_from_dict", lambda _data: fake_creds)
    monkeypatch.setattr(
        "ergodix.auth.get_credential",
        lambda name: "ci" if name == "google_oauth_client_id" else "x",
    )

    captured: list[str] = []
    load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=captured.append)

    joined = "\n".join(captured).lower()
    # No staleness-related warning. (Other captures from the flow are fine.)
    assert "days old" not in joined
    assert "stale" not in joined


def test_load_or_acquire_silent_when_issued_at_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token files written before chunk 6c (no `refresh_token_issued_at`
    field) should not warn — we don't know their age."""
    from ergodix.oauth import load_or_acquire_credentials, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)

    save_oauth_tokens(
        {
            "token": "at",
            "refresh_token": "rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": None,
            # no refresh_token_issued_at
        }
    )

    fake_creds = MagicMock()
    fake_creds.valid = True
    fake_creds.client_id = "ci"

    import ergodix.oauth as oauth_module

    monkeypatch.setattr(oauth_module, "_credentials_from_dict", lambda _data: fake_creds)
    monkeypatch.setattr(
        "ergodix.auth.get_credential",
        lambda name: "ci" if name == "google_oauth_client_id" else "x",
    )

    captured: list[str] = []
    load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=captured.append)

    joined = "\n".join(captured).lower()
    assert "days old" not in joined
    assert "stale" not in joined


def test_refresh_preserves_refresh_token_issued_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the access token expires and we refresh it, the
    `refresh_token_issued_at` timestamp must NOT be reset — only the
    access token has rolled over, not the refresh token."""
    from ergodix.oauth import load_oauth_tokens, load_or_acquire_credentials, save_oauth_tokens

    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)

    issued_at = "2026-04-01T00:00:00Z"
    save_oauth_tokens(
        {
            "token": "stale-at",
            "refresh_token": "rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": None,
            "refresh_token_issued_at": issued_at,
        }
    )

    fake_creds = MagicMock()
    fake_creds.valid = False
    fake_creds.expired = True
    fake_creds.refresh_token = "rt"
    fake_creds.client_id = "ci"
    # Refresh succeeds; new access token populated.
    fake_creds.token = "fresh-at"
    fake_creds.token_uri = "https://oauth2.googleapis.com/token"
    fake_creds.client_secret = "cs"
    fake_creds.scopes = ["scope-a"]
    fake_creds.expiry = None

    import ergodix.oauth as oauth_module

    monkeypatch.setattr(oauth_module, "_credentials_from_dict", lambda _data: fake_creds)
    monkeypatch.setattr(
        "ergodix.auth.get_credential",
        lambda name: "ci" if name == "google_oauth_client_id" else "x",
    )

    load_or_acquire_credentials(prompt_fn=lambda _: "x", output_fn=lambda _: None)

    persisted = load_oauth_tokens()
    assert persisted is not None
    assert persisted["refresh_token_issued_at"] == issued_at, (
        "refresh_token_issued_at must be preserved across access-token refresh"
    )


# ─── Review 0015.2: extra coverage requested ────────────────────────────────


def test_credentials_from_dict_partial_field_corruption_token_uri_only_missing() -> None:
    """Realistic hand-edit corruption: two of three required fields
    present, one missing. Error should still name the specific
    missing field."""
    from ergodix.oauth import _credentials_from_dict

    with pytest.raises(ValueError, match="token_uri"):
        _credentials_from_dict(
            {
                "token": "at",
                "refresh_token": "rt",
                "client_id": "ci",
                "client_secret": "cs",
                # token_uri missing
            }
        )


def test_credentials_from_dict_happy_path_all_required_present() -> None:
    """Happy path: all required fields present. No exception, returns
    a Credentials object."""
    from ergodix.oauth import _credentials_from_dict

    creds = _credentials_from_dict(
        {
            "token": "at",
            "refresh_token": "rt",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "ci",
            "client_secret": "cs",
            "scopes": ["scope-a"],
            "expiry": None,
        }
    )
    assert creds is not None
    assert creds.token == "at"


def test_emit_diagnostic_invalid_grant_bucket() -> None:
    """Direct test of the invalid_grant heuristic bucket."""
    from ergodix.oauth import _emit_token_exchange_diagnostic

    captured: list[str] = []
    _emit_token_exchange_diagnostic(
        RuntimeError("invalid_grant: Token has been expired"),
        captured.append,
    )
    joined = "\n".join(captured).lower()
    assert "fresh code" in joined or "expire" in joined or "rejected" in joined


def test_emit_diagnostic_already_used_phrase_anchored() -> None:
    """The phrase-anchored bucket catches "already used" but NOT a
    bare "used" embedded in unrelated text."""
    from ergodix.oauth import _emit_token_exchange_diagnostic

    captured_phrase: list[str] = []
    _emit_token_exchange_diagnostic(RuntimeError("OAuth code already used"), captured_phrase.append)
    assert any("fresh code" in m.lower() or "rejected" in m.lower() for m in captured_phrase)

    captured_unrelated: list[str] = []
    _emit_token_exchange_diagnostic(
        RuntimeError("connection failed: address used by another process"),
        captured_unrelated.append,
    )
    joined = "\n".join(captured_unrelated).lower()
    # Should land in the GENERIC bucket, not the bad-code bucket.
    assert "rejected" not in joined
    assert "network" in joined or "credential" in joined or "again" in joined


def test_emit_diagnostic_rate_limit_bucket() -> None:
    from ergodix.oauth import _emit_token_exchange_diagnostic

    for trigger in (
        "HTTP 429 Too Many Requests",
        "rate-limited by Google",
        "quota exceeded for OAuth token endpoint",
        "too many requests; backoff",
    ):
        captured: list[str] = []
        _emit_token_exchange_diagnostic(RuntimeError(trigger), captured.append)
        joined = "\n".join(captured).lower()
        assert (
            "wait" in joined or "rate" in joined or "60 seconds" in joined or "minute" in joined
        ), f"trigger {trigger!r} didn't land in rate-limit bucket"


def test_emit_diagnostic_generic_bucket_for_unknown_errors() -> None:
    """Errors that match neither known bucket get the generic message
    + the raw error text preserved."""
    from ergodix.oauth import _emit_token_exchange_diagnostic

    captured: list[str] = []
    _emit_token_exchange_diagnostic(
        RuntimeError("completely-unknown-network-blip-xyz"), captured.append
    )
    joined = "\n".join(captured).lower()
    assert "completely-unknown-network-blip-xyz" in joined
    assert any(token in joined for token in ("network", "credential", "again", "fail"))
