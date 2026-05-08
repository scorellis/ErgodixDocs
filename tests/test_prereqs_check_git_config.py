"""
Tests for ergodix.prereqs.check_git_config — the C3 prereq from ADR 0003.

C3 ensures that ``git config --global user.name`` and ``user.email`` are
both set; if either is unset, the configure phase (per ADR 0012) prompts
the user and runs ``git config --global`` to apply.

This is the **first prereq using the configure phase end-to-end** — A1,
C4, and C5 are all non-interactive. C3 exercises the
``status="needs-interactive"`` path, the multi-prompt loop inside
``interactive_complete``, and the partial-success semantics (user fills
one but not the other).

Per CLAUDE.md TDD norm: tests landed before implementation. Tests use
``monkeypatch`` to fake the ``subprocess.run`` calls that read/write
git config so they don't touch the user's real ~/.gitconfig.
"""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_C3() -> None:
    from ergodix.prereqs import check_git_config

    assert check_git_config.OP_ID == "C3"


def test_description_mentions_git_config() -> None:
    from ergodix.prereqs import check_git_config

    desc = check_git_config.DESCRIPTION.lower()
    assert "git" in desc
    assert "config" in desc or "identity" in desc or "user" in desc


# ─── inspect() — three states ───────────────────────────────────────────────


def _stub_git_config_reader(
    monkeypatch: pytest.MonkeyPatch,
    name: str | None,
    email: str | None,
) -> list[list[str]]:
    """
    Replace ``subprocess.run`` so calls of the shape
    ``git config --global user.<key>`` return the value (rc=0) when set,
    or rc=1 (key missing) when None. Also captures the calls in a list
    so tests can assert what was queried.
    """
    calls: list[list[str]] = []
    values = {"user.name": name, "user.email": email}

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        # Match `git config --global user.<key>`
        if len(cmd) >= 4 and cmd[0] == "git" and cmd[1] == "config" and cmd[2] == "--global":
            key = cmd[3]
            value = values.get(key)
            if value is None:
                return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=value + "\n", stderr="")
        # Default: pretend success with empty output for any unrecognized cmd.
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_inspect_returns_ok_when_both_user_name_and_email_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_git_config

    _stub_git_config_reader(monkeypatch, name="Stephen Corellis", email="s@example.com")

    result = check_git_config.inspect()

    assert result.op_id == "C3"
    assert result.status == "ok"
    assert result.proposed_action is None
    assert result.needs_action is False
    assert result.needs_admin is False
    assert result.network_required is False


def test_inspect_returns_needs_interactive_when_user_name_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_git_config

    _stub_git_config_reader(monkeypatch, name=None, email="s@example.com")

    result = check_git_config.inspect()

    assert result.status == "needs-interactive"
    assert result.proposed_action is not None
    assert "user.name" in result.proposed_action.lower() or "name" in result.proposed_action.lower()
    assert result.needs_action is True


def test_inspect_returns_needs_interactive_when_user_email_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_git_config

    _stub_git_config_reader(monkeypatch, name="Stephen Corellis", email=None)

    result = check_git_config.inspect()

    assert result.status == "needs-interactive"
    assert (
        "user.email" in (result.proposed_action or "").lower()
        or "email" in (result.proposed_action or "").lower()
    )


def test_inspect_returns_needs_interactive_when_both_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_git_config

    _stub_git_config_reader(monkeypatch, name=None, email=None)

    result = check_git_config.inspect()

    assert result.status == "needs-interactive"
    pa = (result.proposed_action or "").lower()
    assert "name" in pa
    assert "email" in pa


def test_inspect_returns_failed_when_git_not_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If ``git`` is missing entirely (subprocess raises FileNotFoundError),
    surface as ``status='failed'`` so cantilever halts via the inspect-failed
    path. Don't pretend git config is unset — that would lead to apply
    attempts that all fail.
    """
    from ergodix.prereqs import check_git_config

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", boom)

    result = check_git_config.inspect()

    assert result.op_id == "C3"
    assert result.status == "failed"
    assert "git" in result.current_state.lower()


# ─── apply() — no-op for needs-interactive ─────────────────────────────────


def test_apply_is_a_no_op_returning_skipped() -> None:
    """
    Per ADR 0012, apply() for a needs-interactive prereq is a no-op stub.
    Configure phase does the real work via interactive_complete.
    """
    from ergodix.prereqs import check_git_config

    result = check_git_config.apply()

    assert result.op_id == "C3"
    assert result.status == "skipped"
    assert result.message  # non-empty


# ─── interactive_complete() — the real work ─────────────────────────────────


def _capture_git_writes(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Replace subprocess.run with a recorder that succeeds for any write."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_interactive_complete_prompts_for_unset_values_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    interactive_complete is called by the configure phase. It re-checks
    which fields are unset (using the inspect helpers), prompts only for
    those, and runs `git config --global` for each answer the user gave.

    Setup: name unset, email set. Should prompt for name only.
    """
    from ergodix.prereqs import check_git_config

    # First subprocess.run reads — second/subsequent reads are repeats from
    # within interactive_complete itself so we must keep the reader behaviour
    # consistent across the call.
    values = {"user.name": None, "user.email": "s@example.com"}
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if len(cmd) >= 4 and cmd[:3] == ["git", "config", "--global"]:
            key = cmd[3]
            if len(cmd) == 4:  # read
                v = values.get(key)
                if v is None:
                    return subprocess.CompletedProcess(cmd, returncode=1, stdout="")
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=v + "\n")
            else:  # write: cmd is [git, config, --global, key, value]
                values[key] = cmd[4]
                return subprocess.CompletedProcess(cmd, returncode=0, stdout="")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    prompts_seen: list[tuple[str, bool]] = []

    def prompt_fn(prompt: str, hidden: bool) -> str | None:
        prompts_seen.append((prompt, hidden))
        # Answer for user.name; nothing else should be prompted.
        return "Stephen Corellis"

    result = check_git_config.interactive_complete(prompt_fn)

    assert result.op_id == "C3"
    assert result.status == "ok"
    # Only one prompt should have been issued (for user.name).
    assert len(prompts_seen) == 1
    # The hidden flag must be False — git identity isn't a credential.
    assert prompts_seen[0][1] is False
    # The write must have happened with the user's answer.
    write_cmds = [c for c in calls if len(c) == 5 and c[:3] == ["git", "config", "--global"]]
    assert ["git", "config", "--global", "user.name", "Stephen Corellis"] in write_cmds


def test_interactive_complete_handles_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    User presses Enter without typing → prompt_fn returns None → that field
    stays unset. Result is 'skipped' (not 'failed') because skipping is a
    valid user choice; the verify phase will surface the still-unset state.
    """
    from ergodix.prereqs import check_git_config

    _stub_git_config_reader(monkeypatch, name=None, email=None)
    write_calls = _capture_git_writes(monkeypatch)
    # Reset write_calls because _capture_git_writes overwrites _stub's behavior.
    # Re-stub a unified fake.
    values: dict[str, str | None] = {"user.name": None, "user.email": None}
    cmds: list[list[str]] = []

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        cmds.append(cmd)
        if cmd[:3] == ["git", "config", "--global"] and len(cmd) == 4:
            v = values.get(cmd[3])
            return subprocess.CompletedProcess(
                cmd, returncode=(0 if v is not None else 1), stdout=(v + "\n") if v else ""
            )
        if cmd[:3] == ["git", "config", "--global"] and len(cmd) == 5:
            values[cmd[3]] = cmd[4]
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    _ = write_calls  # suppress unused warning

    def prompt_fn(_prompt: str, _hidden: bool) -> str | None:
        return None  # user skipped every prompt

    result = check_git_config.interactive_complete(prompt_fn)

    assert result.status == "skipped"
    # No writes should have happened.
    assert not any(len(c) == 5 for c in cmds)


def test_interactive_complete_handles_partial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    User answers user.name but skips user.email. Status should be 'ok'
    for what was set (the user got partway through configuration); the
    verify phase will note user.email still missing on the next inspect.
    """
    from ergodix.prereqs import check_git_config

    values: dict[str, str | None] = {"user.name": None, "user.email": None}
    cmds: list[list[str]] = []

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        cmds.append(cmd)
        if cmd[:3] == ["git", "config", "--global"] and len(cmd) == 4:
            v = values.get(cmd[3])
            return subprocess.CompletedProcess(
                cmd, returncode=(0 if v is not None else 1), stdout=(v + "\n") if v else ""
            )
        if cmd[:3] == ["git", "config", "--global"] and len(cmd) == 5:
            values[cmd[3]] = cmd[4]
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    answers = iter(["Stephen Corellis", None])

    def prompt_fn(_prompt: str, _hidden: bool) -> str | None:
        return next(answers)

    result = check_git_config.interactive_complete(prompt_fn)

    assert result.status == "ok"
    # user.name was written; user.email was not.
    assert values["user.name"] == "Stephen Corellis"
    assert values["user.email"] is None


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_git_config

    assert isinstance(check_git_config.OP_ID, str)
    assert callable(check_git_config.inspect)
    assert callable(check_git_config.apply)
    assert callable(check_git_config.interactive_complete)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "C3" in op_ids, f"C3 not registered; have {sorted(op_ids)}"


def test_end_to_end_through_cantilever_drives_configure_phase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Full inspect → plan → apply → configure → verify via run_cantilever.
    Demonstrates that C3 is the first real prereq using the configure
    phase end-to-end (A1, C4, C5 are all non-interactive).

    Setup: both git config values unset. User provides both via prompt_fn.
    Expected: outcome="applied" (apply has nothing for C3, configure
    handles it). C3's interactive_complete should run once.
    """
    from ergodix.cantilever import run_cantilever
    from ergodix.prereqs import check_git_config

    values: dict[str, str | None] = {"user.name": None, "user.email": None}

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if cmd[:3] == ["git", "config", "--global"] and len(cmd) == 4:
            v = values.get(cmd[3])
            return subprocess.CompletedProcess(
                cmd, returncode=(0 if v is not None else 1), stdout=(v + "\n") if v else ""
            )
        if cmd[:3] == ["git", "config", "--global"] and len(cmd) == 5:
            values[cmd[3]] = cmd[4]
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    class ModulePrereq:
        op_id = check_git_config.OP_ID

        def inspect(self):
            return check_git_config.inspect()

        def apply(self):
            return check_git_config.apply()

        def interactive_complete(self, prompt_fn):
            return check_git_config.interactive_complete(prompt_fn)

    answers = iter(["Stephen Corellis", "s@example.com"])

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[ModulePrereq()],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        prompt_fn=lambda _p, _h: next(answers),
        verify_checks=[],
    )

    assert result.outcome == "applied"
    assert len(result.configure_results) == 1
    assert result.configure_results[0].op_id == "C3"
    assert result.configure_results[0].status == "ok"
    assert values == {"user.name": "Stephen Corellis", "user.email": "s@example.com"}
