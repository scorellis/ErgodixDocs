"""
Tests for ergodix.prereqs.check_vscode_task — D1 verify-only check
(per ADR 0003).

Tests use ``monkeypatch.chdir(tmp_path)`` for hermeticity — each test
controls whether ``.vscode/tasks.json`` exists and what's in it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_op_id_is_D1() -> None:
    from ergodix.prereqs import check_vscode_task

    assert check_vscode_task.OP_ID == "D1"


def test_description_mentions_vscode_or_task() -> None:
    from ergodix.prereqs import check_vscode_task

    text = check_vscode_task.DESCRIPTION.lower()
    assert "vs code" in text or "vscode" in text or "task" in text


# ─── inspect() ────────────────────────────────────────────────────────────


def test_inspect_ok_deferred_when_no_tasks_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No `.vscode/tasks.json` → ok with deferred state pointing at
    the future `ergodix vscode init`."""
    from ergodix.prereqs import check_vscode_task

    monkeypatch.chdir(tmp_path)

    result = check_vscode_task.inspect()

    assert result.op_id == "D1"
    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "not present" in state_lower or "vscode init" in state_lower


def test_inspect_ok_when_ergodix_tagged_tasks_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tasks.json contains a task with the 'Ergodix:' label prefix →
    ok with happy current_state."""
    from ergodix.prereqs import check_vscode_task

    monkeypatch.chdir(tmp_path)
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "tasks.json").write_text(
        json.dumps(
            {
                "version": "2.0.0",
                "tasks": [
                    {
                        "label": "Ergodix: Sync In",
                        "type": "shell",
                        "command": "ergodix sync-in",
                    }
                ],
            }
        )
    )

    result = check_vscode_task.inspect()

    assert result.status == "ok"
    assert "ergodix-managed" in result.current_state.lower()


def test_inspect_ok_when_unrelated_tasks_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tasks.json has tasks but none with the 'Ergodix:' prefix → ok
    with "leaving it alone" current_state. Critical: D1 must not
    claim ownership of unrelated user-installed tasks."""
    from ergodix.prereqs import check_vscode_task

    monkeypatch.chdir(tmp_path)
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "tasks.json").write_text(
        json.dumps(
            {
                "version": "2.0.0",
                "tasks": [
                    {
                        "label": "Run pytest",
                        "type": "shell",
                        "command": "pytest",
                    },
                    {
                        "label": "Build docs",
                        "type": "shell",
                        "command": "make docs",
                    },
                ],
            }
        )
    )

    result = check_vscode_task.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "no ergodix-tagged tasks" in state_lower or "leaving it alone" in state_lower


def test_inspect_ok_when_tasks_json_malformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed tasks.json → ok with "leaving it alone" state. D1
    never touches a file the user owns, even when broken."""
    from ergodix.prereqs import check_vscode_task

    monkeypatch.chdir(tmp_path)
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "tasks.json").write_text("{ this is not [valid] = JSON")

    result = check_vscode_task.inspect()

    assert result.status == "ok"
    assert (
        "unreadable" in result.current_state.lower() or "malformed" in result.current_state.lower()
    )


def test_inspect_ok_when_tasks_json_has_no_tasks_array(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tasks.json present but missing the 'tasks' key (or it's a
    non-list) → treated as "no ergodix tasks present." Defensive
    parsing — _has_ergodix_task returns False on shape mismatches."""
    from ergodix.prereqs import check_vscode_task

    monkeypatch.chdir(tmp_path)
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir()
    # tasks key is a string, not a list — recognized as "no ergodix tasks"
    (vscode_dir / "tasks.json").write_text(json.dumps({"version": "2.0.0", "tasks": "wrong"}))

    result = check_vscode_task.inspect()

    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "no ergodix-tagged tasks" in state_lower or "leaving it alone" in state_lower


# ─── apply() — no-op ───────────────────────────────────────────────────────


def test_apply_is_skipped() -> None:
    from ergodix.prereqs import check_vscode_task

    result = check_vscode_task.apply()

    assert result.op_id == "D1"
    assert result.status == "skipped"
    assert "verify-only" in result.message.lower() or "vscode init" in result.message.lower()


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_vscode_task

    assert isinstance(check_vscode_task.OP_ID, str)
    assert callable(check_vscode_task.inspect)
    assert callable(check_vscode_task.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "D1" in op_ids, f"D1 not registered; have {sorted(op_ids)}"
