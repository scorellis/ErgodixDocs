"""
Tests for ergodix.prereqs.check_launchagent_poller — D5 verify-only
check (per ADR 0003 + ADR 0004). Mirrors the D4 / D6 read-only
pattern.

Tests stub ``Path.exists`` so they're deterministic regardless of
whether the dev machine actually has the LaunchAgent plist installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_op_id_is_D5() -> None:
    from ergodix.prereqs import check_launchagent_poller

    assert check_launchagent_poller.OP_ID == "D5"


def test_description_mentions_polling_or_launchagent() -> None:
    from ergodix.prereqs import check_launchagent_poller

    text = check_launchagent_poller.DESCRIPTION.lower()
    assert "poll" in text or "launchagent" in text


# ─── inspect() ────────────────────────────────────────────────────────────


def test_inspect_ok_deferred_when_plist_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """No plist on disk → status=ok with deferred current_state. D5
    stays out of the way until `ergodix poller init` lands."""
    from ergodix.prereqs import check_launchagent_poller

    monkeypatch.setattr(Path, "exists", lambda _self: False)

    result = check_launchagent_poller.inspect()

    assert result.op_id == "D5"
    assert result.status == "ok"
    state_lower = result.current_state.lower()
    assert "not installed" in state_lower or "poller init" in state_lower


def test_inspect_ok_when_plist_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plist on disk → status=ok with happy current_state naming the path."""
    from ergodix.prereqs import check_launchagent_poller

    monkeypatch.setattr(Path, "exists", lambda _self: True)

    result = check_launchagent_poller.inspect()

    assert result.status == "ok"
    assert "com.ergodix.poller.plist" in result.current_state


# ─── apply() — no-op ───────────────────────────────────────────────────────


def test_apply_is_skipped() -> None:
    from ergodix.prereqs import check_launchagent_poller

    result = check_launchagent_poller.apply()

    assert result.op_id == "D5"
    assert result.status == "skipped"
    assert "verify-only" in result.message.lower() or "poller init" in result.message.lower()


# ─── PrereqSpec protocol + registry ────────────────────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_launchagent_poller

    assert isinstance(check_launchagent_poller.OP_ID, str)
    assert callable(check_launchagent_poller.inspect)
    assert callable(check_launchagent_poller.apply)


def test_registered_in_prereqs_registry() -> None:
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "D5" in op_ids, f"D5 not registered; have {sorted(op_ids)}"
