"""
Cantilever prereq C6 (per ADR 0003, refined by ADR 0012's configure-
phase pattern): prompt the user for any missing API credentials.

Three known credentials per ``ergodix.auth.KNOWN_KEYS``:
    - ``anthropic_api_key`` — for AI calls (Plot-Planner, Continuity-
      Engine, future Skills).
    - ``google_oauth_client_id`` — for the future Drive/Docs API
      flow (Sprint 0 Story 0.3).
    - ``google_oauth_client_secret`` — same flow.

C6 walks the standard three-tier auth lookup (env var → keyring →
``~/.config/ergodix/secrets.json``) per credential. Any missing →
``status="needs-interactive"``. The configure phase prompts via the
injected ``prompt_fn`` (always ``hidden=True``; these are secrets)
and writes any non-empty answer into the keyring.

A blank answer (``prompt_fn`` returns ``None``) leaves the credential
unset — the user explicitly skipped. No empty-string values are ever
written; an empty key in the keyring would shadow "unset" and could
survive into runtime as a confusing zero-length credential.

Network: not required (keyring is local). Admin: not required
(per-user keyring writes don't need sudo).

NOTE: C6's surface is currently persona-agnostic — it prompts for all
three known keys. A persona-aware refinement (writer needs anthropic;
drive-mirror also needs Google OAuth) is a future polish, deferred
until a real consumer enforces credential needs end-to-end.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from ergodix.auth import (
    ENV_OVERRIDES,
    KEYRING_SERVICE,
    KNOWN_KEYS,
    _from_file,
    _from_keyring,
)
from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "C6"
DESCRIPTION = "Prompt for missing API credentials (Anthropic, Google OAuth)"


def _is_credential_present(name: str) -> bool:
    """True if ``name`` resolves via env var, keyring, or fallback file.

    Treats backend errors as "not present" — if the keyring lookup
    raises (locked keychain, daemon crashed) or the file fallback has
    loose perms, the user can either fix the underlying problem or
    re-run cantilever to be prompted again. C6's job is "did we find
    a value to use," not "is the storage backend healthy" (which is
    C5's territory and the verify phase's loud-failure surface).
    """
    env_var = ENV_OVERRIDES.get(name)
    if env_var and os.environ.get(env_var):
        return True
    try:
        if _from_keyring(name):
            return True
    except RuntimeError:
        # Keyring backend error — treat as not present so the configure
        # phase prompts; if writing to the keyring also fails, the
        # ApplyResult will surface the real backend problem.
        pass
    try:
        if _from_file(name):
            return True
    except PermissionError:
        # Loose-mode secrets.json — security/0001/0002 territory; not
        # C6's concern.
        pass
    return False


def _missing_credentials() -> list[str]:
    """Return KNOWN_KEYS entries not present via any auth tier, in
    the canonical KNOWN_KEYS order."""
    return [k for k in KNOWN_KEYS if not _is_credential_present(k)]


def _prompt_label(name: str) -> str:
    """Friendly prompt label for a known credential. Maps the snake-
    case key to a slightly more human form."""
    labels = {
        "anthropic_api_key": "Anthropic API key",
        "google_oauth_client_id": "Google OAuth client_id",
        "google_oauth_client_secret": "Google OAuth client_secret",
    }
    return labels.get(name, name)


def inspect() -> InspectResult:
    missing = _missing_credentials()

    if not missing:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state="all known credentials resolve via env / keyring / file",
            proposed_action=None,
            network_required=False,
        )

    return InspectResult(
        op_id=OP_ID,
        status="needs-interactive",
        description=DESCRIPTION,
        current_state=f"missing credentials: {', '.join(missing)}",
        proposed_action=(
            f"Prompt for {len(missing)} missing credential(s) "
            f"({', '.join(_prompt_label(k) for k in missing)}) during configure phase"
        ),
        estimated_seconds=10 * len(missing),
        network_required=False,
    )


def apply() -> ApplyResult:
    """No-op for needs-interactive ops per ADR 0012. The configure
    phase runs the real work via ``interactive_complete``."""
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message="credentials are set in the configure phase, not apply",
    )


def interactive_complete(prompt_fn: Callable[[str, bool], str | None]) -> ApplyResult:
    """Prompt for each missing credential and store via keyring.

    Outcomes:
      - All prompts skipped (None answers) → ``skipped``.
      - Some / all credentials stored, no failures → ``ok`` with a
        message reflecting set / skip counts.
      - Any keyring write fails → ``failed`` with remediation pointing
        at ``python -m ergodix.auth set-key <name>``.
    """
    import keyring

    missing = _missing_credentials()
    set_count = 0
    skip_count = 0
    failed_keys: list[str] = []

    for key in missing:
        prompt = f"Enter your {_prompt_label(key)} (input hidden; press Enter to skip): "
        answer = prompt_fn(prompt, True)
        if answer is None:
            skip_count += 1
            continue
        try:
            keyring.set_password(KEYRING_SERVICE, key, answer)
        except Exception:
            failed_keys.append(key)
            continue
        set_count += 1

    if failed_keys:
        first_failed = failed_keys[0]
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"keyring write failed for: {', '.join(failed_keys)}",
            remediation_hint=(
                "Check that your OS keyring is unlocked and available, then "
                f"run: python -m ergodix.auth set-key {first_failed}"
            ),
        )

    if set_count == 0:
        return ApplyResult(
            op_id=OP_ID,
            status="skipped",
            message="user skipped all credential prompts",
        )

    return ApplyResult(
        op_id=OP_ID,
        status="ok",
        message=f"stored {set_count} credential(s); {skip_count} skipped",
    )
