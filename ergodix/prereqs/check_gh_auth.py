"""
Cantilever prereq C1 (per ADR 0003): ensure the user is authenticated
to GitHub via the ``gh`` CLI.

C1 unblocks the entire C-tier and most of D-tier: C2 clones the corpus
repo via ``gh repo clone`` (or ``git clone`` against an authed remote);
D6 registers the editor's signing key via ``gh ssh-key add``. Without
C1, those ops can't run.

Per ADR 0012, ``gh auth login`` is interactive (browser-based device
code) but the interactivity is owned by ``gh``'s own UI rather than
driven by Python prompts — that's why it fits the apply contract
cleanly without needing the configure phase. Our ``apply()`` is a
plain ``subprocess.run`` that does NOT redirect stdin/stdout/stderr,
so ``gh`` can take over the terminal and the user sees gh's flow
exactly as it would run standalone.

Network: required (``gh auth status`` validates the token against
GitHub's API). The orchestrator's offline-rewrite path turns this op
into ``deferred-offline`` when ``is_online_fn`` reports False.
Admin: not required.

Note: D6 (editor signing key) needs ``admin:public_key`` scope, which
C1 does NOT request upfront — per the least-privilege resolution in
ADR 0012, D6 prompts for a scope refresh via the configure phase when
the editor floater activates.
"""

from __future__ import annotations

import subprocess

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "C1"
DESCRIPTION = "Authenticate with GitHub via `gh auth login`"


def inspect() -> InspectResult:
    """
    Run ``gh auth status``. Three terminal states:

    - ``gh`` not on PATH → ``failed`` (halts cantilever via inspect-failed).
    - ``gh auth status`` exits 0 → ``ok`` (already authenticated).
    - ``gh auth status`` exits non-zero → ``needs-install`` (apply runs
      ``gh auth login``).
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return InspectResult(
            op_id=OP_ID,
            status="failed",
            description=DESCRIPTION,
            current_state="gh not found on PATH",
            proposed_action=None,
            network_required=True,
        )

    if result.returncode == 0:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state="gh is authenticated to GitHub",
            proposed_action=None,
            network_required=True,
        )

    return InspectResult(
        op_id=OP_ID,
        status="needs-install",
        description=DESCRIPTION,
        current_state="gh is not authenticated (gh auth status exited non-zero)",
        proposed_action="Run `gh auth login` to authenticate with GitHub",
        estimated_seconds=30,
        network_required=True,
    )


def apply() -> ApplyResult:
    """
    Run ``gh auth login`` interactively. The subprocess inherits the
    user's terminal (no ``capture_output``, no ``input``); ``gh`` owns
    the prompt UI until it returns. We then check the exit code and
    report success / failure.

    Failure cases:
    - ``gh`` disappeared between inspect and apply (race) → failed.
    - User cancelled the login flow → gh exits non-zero → failed.
    - Network error during the OAuth handshake → gh exits non-zero → failed.

    All failures point the user at the manual command in the
    ``remediation_hint`` so they can retry without re-running cantilever.
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "login"],  # noqa: S607
            check=False,
        )
    except FileNotFoundError:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message="gh not found on PATH at apply time",
            remediation_hint=(
                "Install GitHub CLI (https://cli.github.com), then re-run `gh auth login` manually."
            ),
        )

    if result.returncode == 0:
        return ApplyResult(
            op_id=OP_ID,
            status="ok",
            message="gh authentication completed",
        )

    return ApplyResult(
        op_id=OP_ID,
        status="failed",
        message=f"gh auth login exited {result.returncode}",
        remediation_hint=(
            "Run `gh auth login` manually and follow the browser-based device-code flow; "
            "re-run cantilever once authenticated."
        ),
    )
