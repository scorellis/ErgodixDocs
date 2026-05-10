"""
Tests for ergodix.prereqs.check_python_packages — A6 verify-only stub.
"""

from __future__ import annotations

import importlib.util

import pytest


def test_op_id_is_A6() -> None:
    from ergodix.prereqs import check_python_packages

    assert check_python_packages.OP_ID == "A6"


def test_description_mentions_packages() -> None:
    from ergodix.prereqs import check_python_packages

    text = check_python_packages.DESCRIPTION.lower()
    assert "package" in text or "dependenc" in text


def test_inspect_returns_ok_when_all_packages_importable() -> None:
    """The venv that runs the test suite has all dependencies installed
    via bootstrap.sh's `pip install ".[dev]"`, so this is the canonical
    happy path."""
    from ergodix.prereqs import check_python_packages

    result = check_python_packages.inspect()

    assert result.op_id == "A6"
    assert result.status == "ok"


def test_inspect_returns_needs_install_when_a_package_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock find_spec to claim 'click' is missing — A6 should surface
    that as needs-install with a clear remediation pointing at bootstrap
    AND the manual pip install command."""
    from ergodix.prereqs import check_python_packages

    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str, *args, **kwargs):
        if name == "click":
            return None
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    result = check_python_packages.inspect()

    assert result.status == "needs-install"
    assert "click" in result.current_state
    assert "click" in (result.proposed_action or "")


def test_inspect_returns_needs_install_when_multiple_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_python_packages

    def fake_find_spec(name: str, *args, **kwargs):
        return None  # everything "missing"

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    result = check_python_packages.inspect()

    assert result.status == "needs-install"
    # All seven required packages should be flagged
    assert "anthropic" in result.current_state
    assert "click" in result.current_state


def test_apply_is_skipped() -> None:
    from ergodix.prereqs import check_python_packages

    result = check_python_packages.apply()

    assert result.op_id == "A6"
    assert result.status == "skipped"
    assert "bootstrap.sh" in (result.remediation_hint or "")


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_python_packages

    assert isinstance(check_python_packages.OP_ID, str)
    assert callable(check_python_packages.inspect)
    assert callable(check_python_packages.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "A6" in op_ids, f"A6 not registered; have {sorted(op_ids)}"
