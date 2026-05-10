"""
Tests for ergodix.prereqs.check_corpus_clone — C2 verify-only check
(per ADR 0003).

Tests stub ``read_corpus_folder_from_local_config`` and
``subprocess.run`` so they're deterministic regardless of the dev-
machine's actual local_config / git state.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest


def test_op_id_is_C2() -> None:
    from ergodix.prereqs import check_corpus_clone

    assert check_corpus_clone.OP_ID == "C2"


def test_description_mentions_corpus_or_clone() -> None:
    from ergodix.prereqs import check_corpus_clone

    text = check_corpus_clone.DESCRIPTION.lower()
    assert "corpus" in text or "clone" in text


# ─── inspect() ────────────────────────────────────────────────────────────


def test_inspect_ok_deferred_when_corpus_folder_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No CORPUS_FOLDER in local_config → ok deferred. (B2 surfaces
    the missing-config case loudly; C2 stays out of the way.)"""
    from ergodix.prereqs import check_corpus_clone

    monkeypatch.setattr(
        check_corpus_clone,
        "read_corpus_folder_from_local_config",
        lambda: None,
    )

    result = check_corpus_clone.inspect()

    assert result.op_id == "C2"
    assert result.status == "ok"
    assert "not configured" in result.current_state.lower()


def test_inspect_ok_when_corpus_folder_doesnt_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CORPUS_FOLDER set but doesn't resolve on disk → ok with
    deferred state. (B2 catches this case as `failed`; C2 should not
    duplicate the loud failure — its job is just the clone state.)"""
    from ergodix.prereqs import check_corpus_clone

    nonexistent = tmp_path / "MyOpus"
    monkeypatch.setattr(
        check_corpus_clone,
        "read_corpus_folder_from_local_config",
        lambda: nonexistent,
    )

    result = check_corpus_clone.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "doesn't exist" in state_lower or "opus clone" in state_lower


def test_inspect_ok_when_corpus_is_clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Corpus folder exists + is a git repo + has origin → ok with
    happy state naming the origin URL."""
    from ergodix.prereqs import check_corpus_clone

    corpus = tmp_path / "MyOpus"
    corpus.mkdir()
    monkeypatch.setattr(
        check_corpus_clone,
        "read_corpus_folder_from_local_config",
        lambda: corpus,
    )

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        if "remote" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="git@github.com:author/myopus.git\n", stderr=""
            )
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_corpus_clone.inspect()

    assert result.status == "ok"
    assert "git@github.com:author/myopus.git" in result.current_state


def test_inspect_ok_when_corpus_exists_but_not_a_git_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Corpus folder exists but isn't a git repo (pure-local author)
    → ok with informational state pointing at `ergodix opus clone`
    as the opt-in path. Pure-local users can ignore."""
    from ergodix.prereqs import check_corpus_clone

    corpus = tmp_path / "MyOpus"
    corpus.mkdir()
    monkeypatch.setattr(
        check_corpus_clone,
        "read_corpus_folder_from_local_config",
        lambda: corpus,
    )

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        # rev-parse fails outside a git repo
        return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="not a git repo")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_corpus_clone.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "not a git repo" in state_lower or "opus clone" in state_lower


def test_inspect_ok_when_git_repo_has_no_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Corpus is a git repo but has no origin remote → ok with
    "add origin" remediation."""
    from ergodix.prereqs import check_corpus_clone

    corpus = tmp_path / "MyOpus"
    corpus.mkdir()
    monkeypatch.setattr(
        check_corpus_clone,
        "read_corpus_folder_from_local_config",
        lambda: corpus,
    )

    def fake_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        if "remote" in cmd:
            # No origin remote configured
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="error: No such remote")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_corpus_clone.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "no `origin` remote" in state_lower or "git remote add" in state_lower


def test_inspect_handles_git_not_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """git not installed → C2 doesn't crash. Returns ok with the
    "not a git repo" branch (since rev-parse fails). Other prereqs
    (D4, D2) report the missing git loudly."""
    from ergodix.prereqs import check_corpus_clone

    corpus = tmp_path / "MyOpus"
    corpus.mkdir()
    monkeypatch.setattr(
        check_corpus_clone,
        "read_corpus_folder_from_local_config",
        lambda: corpus,
    )

    def boom(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", boom)

    result = check_corpus_clone.inspect()

    assert result.status == "ok"


# ─── apply() — no-op ───────────────────────────────────────────────────────


def test_apply_is_skipped() -> None:
    from ergodix.prereqs import check_corpus_clone

    result = check_corpus_clone.apply()

    assert result.op_id == "C2"
    assert result.status == "skipped"
    assert "verify-only" in result.message.lower() or "opus clone" in result.message.lower()


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_corpus_clone

    assert isinstance(check_corpus_clone.OP_ID, str)
    assert callable(check_corpus_clone.inspect)
    assert callable(check_corpus_clone.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "C2" in op_ids, f"C2 not registered; have {sorted(op_ids)}"
