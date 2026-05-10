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
from pathlib import Path

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
