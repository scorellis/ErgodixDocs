"""
Tests for F2 — post-run cantilever run-record (per ADR 0003).

F2's responsibility (like F1 before it — see the F1 reframe note in
ADR 0003) lives in orchestrator code, not as a prereq module: it has
no install-vs-not state, just a side-effect after every cantilever
invocation. Each run appends a single JSONL line to
``~/.config/ergodix/cantilever.log``.

Record fields (per ADR 0003 §164):
  - ts                   ISO-8601 UTC timestamp at run start
  - floaters             sorted list of enabled floater keys
  - operations           per-op {id, status} — final status (configure
                         status > apply status > inspect status)
  - exit                 0 on applied / no-changes-needed / dry-run; 1 otherwise
  - duration_seconds     monotonic elapsed time, integer

Fail-safe: a write failure (read-only filesystem, permission denied)
must NOT crash cantilever. The orchestrator returns normally and the
caller never sees the F2 error.

Tests inject the log path via monkeypatching ``_default_log_path`` so
the real ``~/.config/ergodix/cantilever.log`` is never touched.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from ergodix.prereqs.types import (
    ApplyResult,
    ApplyStatus,
    InspectResult,
    InspectStatus,
)


# Reuse the FakePrereq pattern from tests/test_cantilever.py rather than
# importing it (cross-test imports break test isolation).
@dataclass
class _FakePrereq:
    op_id: str
    inspect_status: InspectStatus = "ok"
    description: str = "Fake op"
    current_state: str = "fake state"
    proposed_action: str | None = None
    needs_admin: bool = False
    estimated_seconds: int | None = None
    network_required: bool = False
    apply_status: ApplyStatus = "ok"
    apply_message: str = "fake applied"

    def inspect(self) -> InspectResult:
        return InspectResult(
            op_id=self.op_id,
            status=self.inspect_status,
            description=self.description,
            current_state=self.current_state,
            proposed_action=self.proposed_action,
            needs_admin=self.needs_admin,
            estimated_seconds=self.estimated_seconds,
            network_required=self.network_required,
        )

    def apply(self) -> ApplyResult:
        return ApplyResult(
            op_id=self.op_id,
            status=self.apply_status,
            message=self.apply_message,
        )

    def interactive_complete(self, prompt_fn: Callable[[str, bool], str | None]) -> ApplyResult:
        return ApplyResult(
            op_id=self.op_id,
            status="ok",
            message="not used in F2 tests",
        )


def _ok(op_id: str = "A1") -> _FakePrereq:
    return _FakePrereq(op_id=op_id, inspect_status="ok")


def _needs_install(op_id: str = "A3") -> _FakePrereq:
    return _FakePrereq(
        op_id=op_id,
        inspect_status="needs-install",
        proposed_action=f"install {op_id}",
    )


def _failed(op_id: str = "A2") -> _FakePrereq:
    return _FakePrereq(
        op_id=op_id,
        inspect_status="failed",
        current_state="fatal",
    )


def _redirect_log(monkeypatch: pytest.MonkeyPatch, log_path: Path) -> None:
    from ergodix import cantilever

    monkeypatch.setattr(cantilever, "_default_log_path", lambda: log_path)


def _read_records(log_path: Path) -> list[dict[str, Any]]:
    """Parse a JSONL log into list[dict]. Empty lines are ignored."""
    if not log_path.exists():
        return []
    return [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]


# ─── Happy path ────────────────────────────────────────────────────────────


def test_f2_writes_jsonl_record_after_applied_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    _redirect_log(monkeypatch, log_path)

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok("A1"), _needs_install("A3")],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    records = _read_records(log_path)
    assert len(records) == 1
    record = records[0]
    # Required fields per ADR 0003 §164.
    for key in ("ts", "floaters", "operations", "exit", "duration_seconds"):
        assert key in record, f"missing key {key!r} in record {record!r}"


def test_f2_record_floaters_is_sorted_list_of_enabled_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    _redirect_log(monkeypatch, log_path)

    run_cantilever(
        floaters={"writer": True, "developer": True, "ci": False, "dry-run": False},
        prereqs=[_ok("A1")],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    record = _read_records(log_path)[0]
    # Only the True keys, sorted.
    assert record["floaters"] == ["developer", "writer"]


def test_f2_record_operations_use_final_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When apply runs, the apply status overrides the inspect status in
    the F2 record. Future-proofs against partial-completion analysis."""
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    _redirect_log(monkeypatch, log_path)

    a3 = _needs_install("A3")
    a3.apply_status = "ok"  # apply will succeed → final status should be "ok"

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok("A1"), a3],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    record = _read_records(log_path)[0]
    by_id = {op["id"]: op["status"] for op in record["operations"]}
    assert by_id["A1"] == "ok"  # was inspect-ok, no apply ran
    assert by_id["A3"] == "ok"  # apply overrode inspect's "needs-install"


def test_f2_record_exit_zero_on_applied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    _redirect_log(monkeypatch, log_path)

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok("A1")],
        consent_fn=lambda _plan: False,  # plan empty since A1 is already ok
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    record = _read_records(log_path)[0]
    assert record["exit"] == 0


def test_f2_record_exit_nonzero_on_inspect_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    _redirect_log(monkeypatch, log_path)

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_failed("A2")],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    record = _read_records(log_path)[0]
    assert record["exit"] != 0


def test_f2_appends_rather_than_overwrites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    log_path.write_text('{"ts": "2026-01-01T00:00:00Z", "exit": 0}\n')
    _redirect_log(monkeypatch, log_path)

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok("A1")],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    records = _read_records(log_path)
    assert len(records) == 2  # pre-existing + new
    assert records[0]["ts"] == "2026-01-01T00:00:00Z"  # old line preserved


def test_f2_creates_parent_dir_if_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The first cantilever run on a fresh machine: ~/.config/ergodix
    might not exist yet (C5 may not have run). F2 must mkdir parents."""
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "deep" / "missing" / "ergodix" / "cantilever.log"
    _redirect_log(monkeypatch, log_path)
    assert not log_path.parent.exists()

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok("A1")],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    assert log_path.exists()
    assert len(_read_records(log_path)) == 1


# ─── Records on every exit path ─────────────────────────────────────────────


def test_f2_writes_record_on_consent_declined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    _redirect_log(monkeypatch, log_path)

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[_needs_install("A3")],
        consent_fn=lambda _plan: False,  # decline
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    assert result.outcome == "consent-declined"
    assert len(_read_records(log_path)) == 1


def test_f2_writes_record_on_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    _redirect_log(monkeypatch, log_path)

    result = run_cantilever(
        floaters={"writer": True, "dry-run": True},
        prereqs=[_needs_install("A3")],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    assert result.outcome == "dry-run"
    record = _read_records(log_path)[0]
    assert record["exit"] == 0  # dry-run is a successful exit


def test_f2_writes_record_on_inspect_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    _redirect_log(monkeypatch, log_path)

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[_failed("A2")],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    assert result.outcome == "inspect-failed"
    assert len(_read_records(log_path)) == 1


# ─── Fail-safety ────────────────────────────────────────────────────────────


def test_f2_write_failure_does_not_crash_cantilever(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the log can't be written (read-only fs, perms, disk full), F2
    must not raise — cantilever returns its normal CantileverResult and
    the caller never sees the F2 failure. Loud-not-fatal: surfacing the
    error is appropriate, but not at the cost of the run."""
    from ergodix import cantilever

    # Patch the writer to raise. This is the broadest test of the fail-safe
    # boundary: any exception inside _write_run_record must be caught.
    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(cantilever, "_write_run_record", boom)

    # Should not raise.
    result = cantilever.run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok("A1")],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
        verify_checks=[],
    )
    assert result.outcome in ("no-changes-needed", "verify-failed")


def test_f2_write_to_unwritable_path_is_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end fail-safe: pointing the log at an unwritable destination
    (a directory where the parent is a regular file) must not raise."""
    from ergodix.cantilever import run_cantilever

    blocking_file = tmp_path / "blocker"
    blocking_file.write_text("I'm a file, not a directory")
    log_path = blocking_file / "cantilever.log"  # cannot mkdir under a regular file
    _redirect_log(monkeypatch, log_path)

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok("A1")],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    assert result.outcome in ("no-changes-needed", "verify-failed")


# ─── ts + duration semantics ───────────────────────────────────────────────


def test_f2_record_ts_is_iso8601_utc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ts must be parseable as ISO-8601 and end with 'Z' or '+00:00' (UTC)."""
    from datetime import datetime

    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    _redirect_log(monkeypatch, log_path)

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok("A1")],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    record = _read_records(log_path)[0]
    ts = record["ts"]
    assert isinstance(ts, str)
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None  # must be tz-aware


def test_f2_record_duration_is_nonneg_number(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.cantilever import run_cantilever

    log_path = tmp_path / "cantilever.log"
    _redirect_log(monkeypatch, log_path)

    run_cantilever(
        floaters={"writer": True},
        prereqs=[_ok("A1")],
        consent_fn=lambda _plan: False,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    record = _read_records(log_path)[0]
    assert isinstance(record["duration_seconds"], int | float)
    assert record["duration_seconds"] >= 0
