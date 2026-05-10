"""
Tests for ergodix.prereqs.check_dev_dependencies — D3 verify-only stub.
Mirrors the test pattern of A6 (check_python_packages) but for the
[dev] extras (pytest, ruff, mypy, pytest-cov).
"""

from __future__ import annotations

import importlib.util

import pytest


def test_op_id_is_D3() -> None:
    from ergodix.prereqs import check_dev_dependencies

    assert check_dev_dependencies.OP_ID == "D3"


def test_description_mentions_dev() -> None:
    from ergodix.prereqs import check_dev_dependencies

    text = check_dev_dependencies.DESCRIPTION.lower()
    assert "dev" in text or "test" in text or "lint" in text


def test_inspect_returns_ok_when_all_dev_packages_importable() -> None:
    """The venv that runs the test suite has all dev dependencies
    installed via bootstrap.sh's `pip install ".[dev]"`."""
    from ergodix.prereqs import check_dev_dependencies

    result = check_dev_dependencies.inspect()

    assert result.op_id == "D3"
    assert result.status == "ok"


def test_inspect_returns_needs_install_when_pytest_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_dev_dependencies

    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str, *args, **kwargs):
        if name == "pytest":
            return None
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    result = check_dev_dependencies.inspect()

    assert result.status == "needs-install"
    assert "pytest" in result.current_state


def test_inspect_returns_needs_install_when_multiple_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix.prereqs import check_dev_dependencies

    def fake_find_spec(name: str, *args, **kwargs):
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    result = check_dev_dependencies.inspect()

    assert result.status == "needs-install"
    # All four dev packages should be flagged
    assert "pytest" in result.current_state
    assert "ruff" in result.current_state
    assert "mypy" in result.current_state


def test_apply_is_skipped() -> None:
    from ergodix.prereqs import check_dev_dependencies

    result = check_dev_dependencies.apply()

    assert result.op_id == "D3"
    assert result.status == "skipped"
    assert "bootstrap.sh" in (result.remediation_hint or "")


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_dev_dependencies

    assert isinstance(check_dev_dependencies.OP_ID, str)
    assert callable(check_dev_dependencies.inspect)
    assert callable(check_dev_dependencies.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "D3" in op_ids, f"D3 not registered; have {sorted(op_ids)}"
