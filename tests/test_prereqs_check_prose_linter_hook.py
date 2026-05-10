"""
Tests for ergodix.prereqs.check_prose_linter_hook — D2 verify-only
check (per ADR 0003).

Mirrors D4's defensive subprocess-stubbing pattern: tests fake
``subprocess.run`` for the ``git rev-parse --git-dir`` call so they're
deterministic regardless of the dev-machine's actual git state.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest


def test_op_id_is_D2() -> None:
    from ergodix.prereqs import check_prose_linter_hook

    assert check_prose_linter_hook.OP_ID == "D2"


def test_description_mentions_hook_or_linter() -> None:
    from ergodix.prereqs import check_prose_linter_hook

    text = check_prose_linter_hook.DESCRIPTION.lower()
    assert "hook" in text or "lint" in text


# ─── inspect() ────────────────────────────────────────────────────────────


def test_inspect_ok_when_not_a_git_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-git cwd → ok with deferred current_state."""
    from ergodix.prereqs import check_prose_linter_hook

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="not a git repo")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_prose_linter_hook.inspect()

    assert result.op_id == "D2"
    assert result.status == "ok"
    assert "not a git repo" in result.current_state.lower()


def test_inspect_ok_deferred_when_no_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """git repo present + no pre-commit hook → ok with deferred state
    pointing at the future `ergodix lint init`."""
    from ergodix.prereqs import check_prose_linter_hook

    monkeypatch.chdir(tmp_path)
    git_dir = tmp_path / ".git"
    (git_dir / "hooks").mkdir(parents=True)

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        if cmd[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_prose_linter_hook.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "not installed" in state_lower or "lint init" in state_lower


def test_inspect_ok_when_ergodix_managed_hook_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hook file present with the ergodix marker → ok with happy state."""
    from ergodix.prereqs import check_prose_linter_hook

    monkeypatch.chdir(tmp_path)
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "pre-commit").write_text(
        "#!/bin/sh\n# ergodix-managed prose-lint hook\nergodix lint --pre-commit\n"
    )

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        if cmd[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_prose_linter_hook.inspect()

    assert result.status == "ok"
    assert "ergodix-managed" in result.current_state.lower()


def test_inspect_ok_when_unmanaged_hook_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-commit hook exists but doesn't have our marker → ok with
    a "leaving it alone" current_state. Critical: D2 must NOT report
    success here as if it owned the hook (would mask the user's own
    hook), nor flag it as failure (that hook is the user's choice)."""
    from ergodix.prereqs import check_prose_linter_hook

    monkeypatch.chdir(tmp_path)
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "pre-commit").write_text(
        "#!/bin/sh\n# user's own pre-commit hook\nrun-some-other-tool\n"
    )

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        if cmd[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_prose_linter_hook.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "not ergodix-managed" in state_lower or "leaving it alone" in state_lower


def test_inspect_handles_git_not_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive: git not installed → D2 doesn't crash. Treats as
    "not a git repo" and stays out of the way."""
    from ergodix.prereqs import check_prose_linter_hook

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", boom)

    result = check_prose_linter_hook.inspect()

    assert result.status == "ok"


# ─── apply() — no-op ───────────────────────────────────────────────────────


def test_apply_is_skipped() -> None:
    from ergodix.prereqs import check_prose_linter_hook

    result = check_prose_linter_hook.apply()

    assert result.op_id == "D2"
    assert result.status == "skipped"
    assert "verify-only" in result.message.lower() or "lint init" in result.message.lower()


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_prose_linter_hook

    assert isinstance(check_prose_linter_hook.OP_ID, str)
    assert callable(check_prose_linter_hook.inspect)
    assert callable(check_prose_linter_hook.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "D2" in op_ids, f"D2 not registered; have {sorted(op_ids)}"
