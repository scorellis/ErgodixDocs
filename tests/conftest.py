"""
Shared pytest fixtures.

Strategy: lean heavily on pytest's built-in `tmp_path` and `monkeypatch`. We
avoid global state and prefer fresh isolated environments per test.

Fixtures here are deliberately thin — most tests should construct exactly the
state they need rather than reach for shared fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Returns a temp directory that stands in for ``$HOME`` for the duration of
    the test. Useful for tests that touch ``~/.config/ergodix/secrets.json``
    or anything else under ``Path.home()``.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Strip every env var that ``auth.py`` or other modules might consult, so
    tests start with a known-empty environment.
    """
    for key in [
        "ANTHROPIC_API_KEY",
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET",
    ]:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def fake_keyring(monkeypatch: pytest.MonkeyPatch) -> dict[tuple[str, str], str]:
    """
    Replace the ``keyring`` module's get/set/delete functions with an
    in-memory dict, so tests don't touch the real OS keyring. Returns the
    dict so tests can pre-seed values or assert on contents.
    """
    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, name: str) -> str | None:
        return store.get((service, name))

    def set_password(service: str, name: str, value: str) -> None:
        store[(service, name)] = value

    def delete_password(service: str, name: str) -> None:
        if (service, name) not in store:
            import keyring.errors

            raise keyring.errors.PasswordDeleteError(name)
        del store[(service, name)]

    import keyring

    monkeypatch.setattr(keyring, "get_password", get_password)
    monkeypatch.setattr(keyring, "set_password", set_password)
    monkeypatch.setattr(keyring, "delete_password", delete_password)

    return store
