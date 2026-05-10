"""
Tests for ergodix.prereqs.check_python_venv — A5 verify-only stub.
"""

from __future__ import annotations

import sys

import pytest


def test_op_id_is_A5() -> None:
    from ergodix.prereqs import check_python_venv

    assert check_python_venv.OP_ID == "A5"


def test_description_mentions_python_or_venv() -> None:
    from ergodix.prereqs import check_python_venv

    text = check_python_venv.DESCRIPTION.lower()
    assert "python" in text or "venv" in text or "virtual" in text


def test_inspect_returns_ok_when_in_venv() -> None:
    """Cantilever runs in the .venv created by bootstrap.sh, so this
    is the canonical happy path. Implementation: sys.prefix is distinct
    from sys.base_prefix when we're inside a venv. The pytest run
    itself is in the venv, so this assertion holds without any
    monkeypatching."""
    from ergodix.prereqs import check_python_venv

    if sys.prefix == sys.base_prefix:
        pytest.skip("pytest is not running in a venv; A5 happy path can't be exercised")

    result = check_python_venv.inspect()

    assert result.op_id == "A5"
    assert result.status == "ok"
    assert sys.prefix in result.current_state


def test_inspect_returns_needs_install_when_outside_venv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When sys.prefix == sys.base_prefix, we're not in a venv. Inspect
    surfaces this as needs-install with a remediation pointing at
    bootstrap.sh."""
    from ergodix.prereqs import check_python_venv

    # Force the no-venv condition.
    monkeypatch.setattr(sys, "prefix", sys.base_prefix)

    result = check_python_venv.inspect()

    assert result.status == "needs-install"
    assert "bootstrap.sh" in (result.proposed_action or "")


def test_apply_is_skipped() -> None:
    from ergodix.prereqs import check_python_venv

    result = check_python_venv.apply()

    assert result.op_id == "A5"
    assert result.status == "skipped"
    assert result.remediation_hint is not None
    assert "bootstrap.sh" in result.remediation_hint


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_python_venv

    assert isinstance(check_python_venv.OP_ID, str)
    assert callable(check_python_venv.inspect)
    assert callable(check_python_venv.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "A5" in op_ids, f"A5 not registered; have {sorted(op_ids)}"
