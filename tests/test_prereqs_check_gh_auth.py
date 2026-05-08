"""
Tests for ergodix.prereqs.check_gh_auth — the C1 prereq from ADR 0003.

C1 ensures the user is authenticated to GitHub via the ``gh`` CLI. It
unblocks every downstream op that touches GitHub: C2 (clone corpus
repo), D6 (editor signing-key registration via ``gh ssh-key add``), and
any future ``gh``-based prereqs.

Per ADR 0012, ``gh auth login`` itself is interactive (browser-based)
but the interactivity is handed off to ``gh``'s own UI, not driven by
Python prompts — that's why it fits the apply contract cleanly without
needing the configure phase. C1 is therefore mutative-not-interactive:
``inspect()`` reports needs-install when unauthenticated; ``apply()``
runs ``gh auth login`` as a subprocess that owns the terminal until it
returns.

Tests use ``monkeypatch`` to fake ``subprocess.run`` so the test suite
doesn't pop a browser window or touch the user's real ``gh`` token.
"""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_C1() -> None:
    from ergodix.prereqs import check_gh_auth

    assert check_gh_auth.OP_ID == "C1"


def test_description_mentions_gh_auth() -> None:
    from ergodix.prereqs import check_gh_auth

    desc = check_gh_auth.DESCRIPTION.lower()
    assert "github" in desc or "gh" in desc
    assert "auth" in desc or "login" in desc or "authenticat" in desc


# ─── inspect() — three states ───────────────────────────────────────────────


def _stub_subprocess_run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rc: int,
    file_not_found: bool = False,
) -> list[list[str]]:
    """Stub subprocess.run with controlled exit code; return calls list."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if file_not_found:
            raise FileNotFoundError("gh")
        return subprocess.CompletedProcess(cmd, returncode=rc, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_inspect_returns_ok_when_gh_auth_status_exits_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User is authenticated → no plan entry, status=ok."""
    from ergodix.prereqs import check_gh_auth

    _stub_subprocess_run(monkeypatch, rc=0)

    result = check_gh_auth.inspect()

    assert result.op_id == "C1"
    assert result.status == "ok"
    assert result.proposed_action is None
    assert result.needs_action is False
    assert result.needs_admin is False
    assert result.network_required is True


def test_inspect_returns_needs_install_when_gh_auth_status_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User isn't authenticated (or token is invalid) → plan a login."""
    from ergodix.prereqs import check_gh_auth

    _stub_subprocess_run(monkeypatch, rc=1)

    result = check_gh_auth.inspect()

    assert result.status == "needs-install"
    assert result.proposed_action is not None
    assert "gh auth login" in result.proposed_action.lower()
    assert result.needs_action is True
    assert result.network_required is True


def test_inspect_returns_failed_when_gh_not_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """gh is missing entirely → halt cantilever via inspect-failed.

    Without gh, no subsequent gh-using prereq can succeed; surfacing as
    'failed' produces a clear, actionable inspect-failed report rather
    than a confusing chain of attempted-then-failed apply calls.
    """
    from ergodix.prereqs import check_gh_auth

    _stub_subprocess_run(monkeypatch, rc=0, file_not_found=True)

    result = check_gh_auth.inspect()

    assert result.op_id == "C1"
    assert result.status == "failed"
    assert "gh" in result.current_state.lower()


def test_inspect_invokes_gh_auth_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the actual command shape so future refactors don't accidentally
    break the contract by switching to a different subcommand."""
    from ergodix.prereqs import check_gh_auth

    calls = _stub_subprocess_run(monkeypatch, rc=0)

    check_gh_auth.inspect()

    assert any(cmd[:3] == ["gh", "auth", "status"] for cmd in calls), (
        f"expected `gh auth status` invocation; got {calls!r}"
    )


# ─── apply() — runs gh auth login ──────────────────────────────────────────


def test_apply_runs_gh_auth_login_returns_ok_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful gh auth login (subprocess returns 0) → ApplyResult ok."""
    from ergodix.prereqs import check_gh_auth

    calls = _stub_subprocess_run(monkeypatch, rc=0)

    result = check_gh_auth.apply()

    assert result.op_id == "C1"
    assert result.status == "ok"
    assert any(cmd[:3] == ["gh", "auth", "login"] for cmd in calls)


def test_apply_returns_failed_when_gh_auth_login_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """gh auth login failed (user cancelled, network error, etc.) → failed
    with a remediation hint pointing at the manual command."""
    from ergodix.prereqs import check_gh_auth

    _stub_subprocess_run(monkeypatch, rc=1)

    result = check_gh_auth.apply()

    assert result.op_id == "C1"
    assert result.status == "failed"
    assert result.message
    assert result.remediation_hint is not None
    assert "gh auth login" in result.remediation_hint


def test_apply_returns_failed_when_gh_disappears_between_inspect_and_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Race: inspect saw gh, then it's gone (uninstalled mid-run, or PATH
    changed). Don't crash on FileNotFoundError; report as failed."""
    from ergodix.prereqs import check_gh_auth

    _stub_subprocess_run(monkeypatch, rc=0, file_not_found=True)

    result = check_gh_auth.apply()

    assert result.status == "failed"
    assert "gh" in result.message.lower()


def test_apply_does_not_capture_subprocess_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    gh auth login is interactive — it prints "Press Enter to open the
    browser..." and reads from stdin. Our subprocess.run call must NOT
    set capture_output=True (which redirects stdout/stderr) nor pass
    input= (which redirects stdin). Pin this so a future refactor doesn't
    accidentally make the login prompt invisible or unfunctional.
    """
    from ergodix.prereqs import check_gh_auth

    captured_kwargs: list[dict[str, Any]] = []

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured_kwargs.append(kwargs)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    check_gh_auth.apply()

    # Find the gh auth login call's kwargs.
    for kwargs in captured_kwargs:
        # apply()'s kwargs must not silence or steal the user's terminal.
        assert kwargs.get("capture_output") is not True
        assert "input" not in kwargs  # not feeding scripted input


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_gh_auth

    assert isinstance(check_gh_auth.OP_ID, str)
    assert callable(check_gh_auth.inspect)
    assert callable(check_gh_auth.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "C1" in op_ids, f"C1 not registered; have {sorted(op_ids)}"


def test_end_to_end_through_cantilever_when_already_authed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User is already authenticated → empty plan, no apply calls,
    cantilever exits cleanly with no-changes-needed."""
    from ergodix.cantilever import run_cantilever
    from ergodix.prereqs import check_gh_auth

    _stub_subprocess_run(monkeypatch, rc=0)

    class ModulePrereq:
        op_id = check_gh_auth.OP_ID

        def inspect(self):
            return check_gh_auth.inspect()

        def apply(self):
            return check_gh_auth.apply()

        def interactive_complete(self, prompt_fn):
            return check_gh_auth.apply()  # not used; status will be ok

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[ModulePrereq()],
        consent_fn=lambda _plan: pytest.fail("consent should not run; status is ok"),
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    assert result.outcome == "no-changes-needed"
