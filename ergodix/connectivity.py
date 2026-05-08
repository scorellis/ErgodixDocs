"""
Real connectivity probe used by the cantilever orchestrator's pre-flight
phase. Per ADR 0012's F1 reframe, F1 is orchestrator-level concern
(connectivity probe + settings load), not a prereq module — its result
mutates orchestrator state (the ``online`` flag that downstream
network-required prereqs read), which doesn't fit ADR 0010's per-op
inspect/apply contract.

``is_online()`` runs a small fall-through TCP probe against well-known
endpoints. It returns True iff at least one endpoint accepts a TCP
connection within the timeout. Designed to be:

- **Fast under all outcomes.** Total wall time is bounded by
  ``len(ENDPOINTS) * _TIMEOUT_SECONDS`` even when fully offline.
- **DNS-independent for at least one fall-through.** A bare-IP endpoint
  (Cloudflare 1.1.1.1) is included so a broken DNS resolver doesn't get
  reported as "offline."
- **Conservative about success.** First endpoint reachable → return
  True; we don't probe the rest.

The default endpoints target port 443 because that's what every "real"
install path (Homebrew, GitHub, gh, Drive) needs. Swap-in for tests is
via ``socket.create_connection`` monkeypatching, not by exposing
``ENDPOINTS`` as a parameter — the production list is small and stable
enough to live as a constant.
"""

from __future__ import annotations

import socket

# (host, port) tuples. Keep ≥2 entries for fall-through; include at
# least one bare IPv4 so DNS isn't a hard prerequisite of the probe.
ENDPOINTS: list[tuple[str, int]] = [
    ("1.1.1.1", 443),  # Cloudflare — IP, no DNS needed
    ("8.8.8.8", 443),  # Google Public DNS — IP, no DNS needed
    ("api.github.com", 443),  # named host, validates DNS is working
]

_TIMEOUT_SECONDS: float = 3.0


def is_online() -> bool:
    """Return True if at least one endpoint in ``ENDPOINTS`` accepts a
    TCP connection within ``_TIMEOUT_SECONDS``."""
    for host, port in ENDPOINTS:
        try:
            sock = socket.create_connection((host, port), timeout=_TIMEOUT_SECONDS)
        except (OSError, TimeoutError):
            continue
        sock.close()
        return True
    return False
