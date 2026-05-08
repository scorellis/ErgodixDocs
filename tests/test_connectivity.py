"""
Tests for ergodix.connectivity — the real connectivity probe that replaces
cantilever's ``_default_is_online_fn`` stub. Per ADR 0012's F1 reframe,
F1 is orchestrator-level concern (not a prereq module); the probe lives
here and is used by ``run_cantilever`` at pre-flight.

Tests use ``monkeypatch`` to fake ``socket.create_connection`` rather
than touching the real network. Real-network behavior is exercised by
the manual smoke at the test deploy directory, not by unit tests.
"""

from __future__ import annotations

import socket
from typing import Any

import pytest

# ─── is_online — basic true/false ─────────────────────────────────────────


def test_is_online_returns_true_when_first_endpoint_reachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix import connectivity

    calls: list[tuple[str, int]] = []

    def fake_create_connection(addr: tuple[str, int], timeout: float = 0.0) -> object:
        calls.append(addr)

        class _S:
            def close(self) -> None: ...

        return _S()

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    assert connectivity.is_online() is True
    # First endpoint succeeded; we should not have probed others.
    assert len(calls) == 1


def test_is_online_returns_false_when_all_endpoints_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ergodix import connectivity

    def fake_create_connection(*_args: Any, **_kwargs: Any) -> object:
        raise OSError("simulated network unreachable")

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    assert connectivity.is_online() is False


def test_is_online_falls_through_to_second_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """First endpoint fails, second succeeds → online. The fall-through
    matters for partial-network situations where one CDN is blocked but
    others reachable."""
    from ergodix import connectivity

    call_count = {"n": 0}

    def fake_create_connection(addr: tuple[str, int], timeout: float = 0.0) -> object:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise OSError("first endpoint blocked")

        class _S:
            def close(self) -> None: ...

        return _S()

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    assert connectivity.is_online() is True
    assert call_count["n"] == 2  # tried first, then second


def test_is_online_uses_short_timeout_per_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Probe must use a short timeout per endpoint (so total probe time is
    bounded, even if multiple endpoints are unreachable). Concrete
    invariant: each socket.create_connection call passes timeout <= 5s.
    """
    from ergodix import connectivity

    timeouts: list[float] = []

    def fake_create_connection(addr: tuple[str, int], timeout: float = 0.0) -> object:
        timeouts.append(timeout)
        raise OSError("network")

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    connectivity.is_online()

    assert timeouts, "is_online should have made at least one connection attempt"
    for t in timeouts:
        assert t <= 5.0, f"timeout too long: {t}s — would make probe cumulatively slow"


def test_is_online_handles_socket_timeout_as_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A socket.timeout (raised when timeout expires before connect) should
    be treated as 'this endpoint unreachable' the same way OSError is."""
    from ergodix import connectivity

    def fake_create_connection(*_args: Any, **_kwargs: Any) -> object:
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    assert connectivity.is_online() is False


# ─── ENDPOINTS list — sanity ──────────────────────────────────────────────


def test_endpoints_list_is_non_empty_and_uses_well_known_hosts() -> None:
    """
    The probe targets a small list of stable, widely-reachable endpoints.
    Pin the list shape (host, port) so future edits don't accidentally
    introduce a single point of failure or a non-standard port.
    """
    from ergodix.connectivity import ENDPOINTS

    assert len(ENDPOINTS) >= 2, "need at least 2 endpoints for fall-through"
    for host, port in ENDPOINTS:
        assert isinstance(host, str)
        assert host
        assert isinstance(port, int)
        assert port in {53, 80, 443}, f"unusual port {port}; reconsider"


def test_endpoints_are_ip_or_well_known_dns_names() -> None:
    """
    Don't probe via DNS names that themselves require DNS to be working
    *before* our probe can run — that confuses 'no DNS' with 'no
    network'. Use IPs (1.1.1.1, 8.8.8.8) or accept that DNS is part of
    'online' (api.github.com is fine because we use github regardless).
    """
    from ergodix.connectivity import ENDPOINTS

    # At least one endpoint should be a literal IPv4 address so DNS is
    # not a hard prerequisite for the probe.
    has_ip = any(host.replace(".", "").isdigit() for host, _ in ENDPOINTS)
    assert has_ip, "include at least one bare-IP endpoint so probe doesn't depend on DNS"


# ─── Public-API smoke ─────────────────────────────────────────────────────


def test_module_exports_is_online() -> None:
    from ergodix import connectivity

    assert callable(connectivity.is_online)
