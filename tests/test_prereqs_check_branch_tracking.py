"""
Tests for ergodix.prereqs.check_branch_tracking — D4 (per ADR 0003,
reframed for trunk-based branching).

D4 is read-only and informational. inspect() always returns ``ok`` —
the current_state describes what was found (correct upstream / wrong
upstream / no upstream / not a git repo). apply() is a no-op.
"""

from __future__ import annotations

import subprocess
from typing import Any

import pytest


def test_op_id_is_D4() -> None:
    from ergodix.prereqs import check_branch_tracking

    assert check_branch_tracking.OP_ID == "D4"


def test_description_mentions_branch_or_tracking() -> None:
    from ergodix.prereqs import check_branch_tracking

    text = check_branch_tracking.DESCRIPTION.lower()
    assert "branch" in text or "main" in text or "track" in text


# ─── inspect() — happy paths ───────────────────────────────────────────────


def test_inspect_ok_when_main_tracks_origin_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """Canonical happy path: cwd is a git repo, local main → origin/main."""
    from ergodix.prereqs import check_branch_tracking

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        if cmd[:2] == ["git", "rev-parse"] and "--git-dir" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        if cmd[:2] == ["git", "rev-parse"] and any("@{upstream}" in part for part in cmd):
            return subprocess.CompletedProcess(cmd, 0, stdout="origin/main\n", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_branch_tracking.inspect()

    assert result.op_id == "D4"
    assert result.status == "ok"
    assert "origin/main" in result.current_state


def test_inspect_ok_when_not_a_git_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Writer / editor running from a non-git folder → ok with a clear
    "not a git repo" current_state. D4 stays out of the way."""
    from ergodix.prereqs import check_branch_tracking

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        # rev-parse --git-dir fails outside a git repo
        return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="not a git repo")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_branch_tracking.inspect()

    assert result.status == "ok"
    assert "not a git repo" in result.current_state.lower()


# ─── inspect() — informational warnings ────────────────────────────────────


def test_inspect_ok_with_no_upstream_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """main exists but has no upstream → ok status, but current_state
    surfaces the fix suggestion. inspect-failed would halt cantilever
    over an informational concern; ok-with-warning is the right shape."""
    from ergodix.prereqs import check_branch_tracking

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        if cmd[:2] == ["git", "rev-parse"] and "--git-dir" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        # main@{upstream} fails when no upstream is set
        return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="no upstream")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_branch_tracking.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "no upstream" in state_lower or "set-upstream" in state_lower


def test_inspect_ok_with_wrong_upstream_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """main tracks something other than origin/main (e.g. a fork) →
    ok with a hint, not failure. User might be intentional."""
    from ergodix.prereqs import check_branch_tracking

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        if cmd[:2] == ["git", "rev-parse"] and "--git-dir" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        if cmd[:2] == ["git", "rev-parse"] and any("@{upstream}" in part for part in cmd):
            return subprocess.CompletedProcess(cmd, 0, stdout="upstream/main\n", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_branch_tracking.inspect()

    assert result.status == "ok"
    assert "upstream/main" in result.current_state
    assert "origin/main" in result.current_state


def test_inspect_handles_git_not_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """If git itself isn't on PATH, D4 doesn't crash — treats it as
    "not a git repo" and stays out of the way. Other prereqs (C3) are
    the loud surface for missing git."""
    from ergodix.prereqs import check_branch_tracking

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", boom)

    result = check_branch_tracking.inspect()

    assert result.status == "ok"


# ─── apply() — no-op ───────────────────────────────────────────────────────


def test_apply_is_skipped() -> None:
    from ergodix.prereqs import check_branch_tracking

    result = check_branch_tracking.apply()

    assert result.op_id == "D4"
    assert result.status == "skipped"


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_branch_tracking

    assert isinstance(check_branch_tracking.OP_ID, str)
    assert callable(check_branch_tracking.inspect)
    assert callable(check_branch_tracking.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "D4" in op_ids, f"D4 not registered; have {sorted(op_ids)}"
