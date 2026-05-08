"""
Cantilever prereq C3 (per ADR 0003): ensure ``git config --global
user.name`` and ``user.email`` are both set.

Per ADR 0012, C3 is **interactive**: when either field is unset, inspect
returns ``status="needs-interactive"``, the apply phase skips this op,
and the configure phase prompts the user via the injected ``prompt_fn``.
The prereq runs its own multi-prompt loop inside ``interactive_complete``
and shells out to ``git config --global`` to apply each answer.

Skip is a valid user choice — if the user presses Enter without
answering, that field stays unset; the next ``inspect()`` will surface
it again. Partial completion (one set, one skipped) is reported as
``ok`` for what got set; verify will note the remaining gap.

Network: not required. Admin: not required (writes the user's own
``~/.gitconfig``).
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "C3"
DESCRIPTION = "Configure git user.name and user.email (global identity)"


def _read_git_config(key: str) -> str | None:
    """
    Return the global git config value for ``key``, or None if unset.
    Raises FileNotFoundError if ``git`` itself isn't on PATH (caller
    surfaces this as inspect-failed; without git, no other prereq's
    ``git config --global`` will work either).

    Resolving ``git`` via PATH is intentional for this developer-tool
    project; the bandit S607 warning targets server contexts where PATH
    may be attacker-controlled (not applicable here).
    """
    result = subprocess.run(
        ["git", "config", "--global", key],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _write_git_config(key: str, value: str) -> bool:
    """Run ``git config --global <key> <value>``; return True on success."""
    result = subprocess.run(
        ["git", "config", "--global", key, value],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def inspect() -> InspectResult:
    """
    Read the current global git identity. Returns:

    - ``ok`` if both ``user.name`` and ``user.email`` are set,
    - ``needs-interactive`` if either is unset (configure phase prompts),
    - ``failed`` if ``git`` is not on PATH.
    """
    try:
        name = _read_git_config("user.name")
        email = _read_git_config("user.email")
    except FileNotFoundError:
        return InspectResult(
            op_id=OP_ID,
            status="failed",
            description=DESCRIPTION,
            current_state="git not found on PATH",
            proposed_action=None,
        )

    if name and email:
        return InspectResult(
            op_id=OP_ID,
            status="ok",
            description=DESCRIPTION,
            current_state=f"user.name={name}, user.email={email}",
            proposed_action=None,
        )

    missing: list[str] = []
    if not name:
        missing.append("user.name")
    if not email:
        missing.append("user.email")

    return InspectResult(
        op_id=OP_ID,
        status="needs-interactive",
        description=DESCRIPTION,
        current_state=f"unset: {', '.join(missing)}",
        proposed_action=f"Prompt for git {' and '.join(missing)} during configure phase",
        estimated_seconds=5,
    )


def apply() -> ApplyResult:
    """
    No-op for needs-interactive ops per ADR 0012. The configure phase
    runs the real work via ``interactive_complete``. Returns ``skipped``
    so cantilever's apply progress display reflects "nothing to do."
    """
    return ApplyResult(
        op_id=OP_ID,
        status="skipped",
        message="git config is set in the configure phase, not apply",
    )


def interactive_complete(prompt_fn: Callable[[str, bool], str | None]) -> ApplyResult:
    """
    Prompt the user for whichever of ``user.name`` / ``user.email`` is
    currently unset, and run ``git config --global`` for each non-empty
    answer. A blank answer (prompt_fn returns None) leaves that field
    unset — the user explicitly skipped.

    Outcomes:
    - All fields skipped → ``skipped`` (user chose to defer).
    - Some fields set, all writes succeeded → ``ok`` (partial config is
      acceptable; verify will surface any remaining gap).
    - Any ``git config --global`` write fails → ``failed`` with a
      remediation hint pointing at the manual command.
    """
    name = _read_git_config("user.name")
    email = _read_git_config("user.email")

    set_count = 0
    skip_count = 0
    failed_keys: list[str] = []

    if not name:
        answer = prompt_fn(
            "Enter your git user.name (your full name, or press Enter to skip): ",
            False,
        )
        if answer is None:
            skip_count += 1
        elif _write_git_config("user.name", answer):
            set_count += 1
        else:
            failed_keys.append("user.name")

    if not email:
        answer = prompt_fn(
            "Enter your git user.email (or press Enter to skip): ",
            False,
        )
        if answer is None:
            skip_count += 1
        elif _write_git_config("user.email", answer):
            set_count += 1
        else:
            failed_keys.append("user.email")

    if failed_keys:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"git config --global write failed for: {', '.join(failed_keys)}",
            remediation_hint=(
                "Run manually: " + "; ".join(f'git config --global {k} "..."' for k in failed_keys)
            ),
        )

    if set_count == 0:
        return ApplyResult(
            op_id=OP_ID,
            status="skipped",
            message="user skipped all git-identity prompts",
        )

    return ApplyResult(
        op_id=OP_ID,
        status="ok",
        message=f"set {set_count} git config value(s); {skip_count} skipped",
    )
