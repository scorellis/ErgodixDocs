"""
Tests for ergodix.prereqs.check_credential_prompts — the C6 prereq from
ADR 0003 (refined by ADR 0012's configure-phase pattern).

C6 inspects the three known credentials (anthropic_api_key,
google_oauth_client_id, google_oauth_client_secret) across the three-
tier auth lookup (env → keyring → file). Any missing →
status="needs-interactive". The configure phase then prompts via the
injected prompt_fn (hidden=True; these are secrets) and stores values
in the keyring.

Tests follow the C3 pattern but use ``fake_keyring`` and ``clean_env``
for credential-presence isolation.
"""

from __future__ import annotations

import json

import pytest

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_C6() -> None:
    from ergodix.prereqs import check_credential_prompts

    assert check_credential_prompts.OP_ID == "C6"


def test_description_mentions_credentials() -> None:
    from ergodix.prereqs import check_credential_prompts

    text = check_credential_prompts.DESCRIPTION.lower()
    assert "credential" in text or "api key" in text or "secret" in text


# ─── inspect() ──────────────────────────────────────────────────────────────


@pytest.mark.usefixtures("clean_env")
def test_inspect_ok_when_all_credentials_present(fake_keyring, fake_home) -> None:
    """All three known keys in the keyring → no missing → status=ok."""
    from ergodix.prereqs import check_credential_prompts

    fake_keyring[("ergodix", "anthropic_api_key")] = "ak"
    fake_keyring[("ergodix", "google_oauth_client_id")] = "ci"
    fake_keyring[("ergodix", "google_oauth_client_secret")] = "cs"

    result = check_credential_prompts.inspect()

    assert result.op_id == "C6"
    assert result.status == "ok"
    assert result.needs_action is False


@pytest.mark.usefixtures("clean_env")
def test_inspect_needs_interactive_when_any_missing(fake_keyring, fake_home) -> None:
    """One key set, two missing → needs-interactive (configure phase
    will prompt for the missing two)."""
    from ergodix.prereqs import check_credential_prompts

    fake_keyring[("ergodix", "anthropic_api_key")] = "ak"
    # google_oauth_client_id and _secret missing

    result = check_credential_prompts.inspect()

    assert result.status == "needs-interactive"
    assert result.needs_action is True
    proposed = (result.proposed_action or "").lower()
    # Must mention what's missing (two of three)
    assert "google" in proposed or "missing" in proposed or "credential" in proposed


@pytest.mark.usefixtures("clean_env")
def test_inspect_needs_interactive_when_all_missing(fake_keyring, fake_home) -> None:
    """All three missing → needs-interactive."""
    from ergodix.prereqs import check_credential_prompts

    result = check_credential_prompts.inspect()

    assert result.status == "needs-interactive"


@pytest.mark.usefixtures("clean_env")
def test_inspect_ok_when_present_via_env_only(monkeypatch, fake_keyring, fake_home) -> None:
    """Env-var source counts as present — three-tier lookup is honored."""
    from ergodix.prereqs import check_credential_prompts

    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "from-env")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "from-env")

    result = check_credential_prompts.inspect()

    assert result.status == "ok"


@pytest.mark.usefixtures("clean_env")
def test_inspect_ok_when_present_via_file_only(fake_keyring, fake_home) -> None:
    """File-fallback source counts as present."""
    from ergodix.prereqs import check_credential_prompts

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

    result = check_credential_prompts.inspect()

    assert result.status == "ok"


# ─── apply() — no-op for needs-interactive ops per ADR 0012 ───────────────


def test_apply_is_noop_skipped() -> None:
    from ergodix.prereqs import check_credential_prompts

    result = check_credential_prompts.apply()

    assert result.op_id == "C6"
    assert result.status == "skipped"


# ─── interactive_complete() ────────────────────────────────────────────────


@pytest.mark.usefixtures("clean_env")
def test_interactive_complete_stores_each_provided_credential(fake_keyring, fake_home) -> None:
    """For each missing credential, prompt; store in keyring on
    non-empty answer."""
    from ergodix.prereqs import check_credential_prompts

    answers = iter(["ak-value", "ci-value", "cs-value"])

    def prompt_fn(_prompt: str, _hidden: bool) -> str | None:
        return next(answers)

    result = check_credential_prompts.interactive_complete(prompt_fn)

    assert result.status == "ok"
    assert fake_keyring[("ergodix", "anthropic_api_key")] == "ak-value"
    assert fake_keyring[("ergodix", "google_oauth_client_id")] == "ci-value"
    assert fake_keyring[("ergodix", "google_oauth_client_secret")] == "cs-value"


@pytest.mark.usefixtures("clean_env")
def test_interactive_complete_uses_hidden_prompts(fake_keyring, fake_home) -> None:
    """Every prompt must use hidden=True. These are secrets — the
    prompt_fn invariant per ADR 0012 is that hidden=True invokes
    getpass.getpass; under no circumstances should a credential prompt
    echo to terminal."""
    from ergodix.prereqs import check_credential_prompts

    hidden_flags: list[bool] = []

    def prompt_fn(_prompt: str, hidden: bool) -> str | None:
        hidden_flags.append(hidden)
        return "value"

    check_credential_prompts.interactive_complete(prompt_fn)

    assert all(hidden_flags), f"all prompts must be hidden=True; got {hidden_flags}"


@pytest.mark.usefixtures("clean_env")
def test_interactive_complete_skips_when_user_returns_none(fake_keyring, fake_home) -> None:
    """A None answer (user pressed Enter without typing) means skip
    that credential. Do not write empty-string values to the keyring;
    that would mask "actually unset" and could survive into runtime
    use as a confusing empty key."""
    from ergodix.prereqs import check_credential_prompts

    def prompt_fn(_prompt: str, _hidden: bool) -> str | None:
        return None  # user skips every prompt

    result = check_credential_prompts.interactive_complete(prompt_fn)

    assert result.status == "skipped"
    # No credentials should have been written.
    for k in ("anthropic_api_key", "google_oauth_client_id", "google_oauth_client_secret"):
        assert ("ergodix", k) not in fake_keyring


@pytest.mark.usefixtures("clean_env")
def test_interactive_complete_partial_completion(fake_keyring, fake_home) -> None:
    """Some answers given, some skipped → status=ok with message
    reflecting the partial set."""
    from ergodix.prereqs import check_credential_prompts

    answers: list[str | None] = ["ak-value", None, "cs-value"]

    def prompt_fn(_prompt: str, _hidden: bool) -> str | None:
        return answers.pop(0)

    result = check_credential_prompts.interactive_complete(prompt_fn)

    assert result.status == "ok"
    assert fake_keyring[("ergodix", "anthropic_api_key")] == "ak-value"
    assert ("ergodix", "google_oauth_client_id") not in fake_keyring
    assert fake_keyring[("ergodix", "google_oauth_client_secret")] == "cs-value"


@pytest.mark.usefixtures("clean_env")
def test_interactive_complete_only_prompts_for_missing(fake_keyring, fake_home) -> None:
    """If a credential is already present (env / keyring / file),
    don't prompt for it. Idempotency: a re-run after partial
    completion only asks for what's still missing."""
    from ergodix.prereqs import check_credential_prompts

    fake_keyring[("ergodix", "anthropic_api_key")] = "already-set"

    prompts_seen: list[str] = []

    def prompt_fn(prompt: str, _hidden: bool) -> str | None:
        prompts_seen.append(prompt)
        return "new-value"

    check_credential_prompts.interactive_complete(prompt_fn)

    # Should only have prompted for the two Google keys — anthropic was set.
    assert len(prompts_seen) == 2
    assert all("google" in p.lower() for p in prompts_seen)
    # And the existing anthropic value must be untouched.
    assert fake_keyring[("ergodix", "anthropic_api_key")] == "already-set"


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_credential_prompts

    assert isinstance(check_credential_prompts.OP_ID, str)
    assert callable(check_credential_prompts.inspect)
    assert callable(check_credential_prompts.apply)
    assert callable(check_credential_prompts.interactive_complete)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "C6" in op_ids, f"C6 not registered; have {sorted(op_ids)}"
