---
id: 0004
title: No in-memory scrub of decoded credentials
status: accepted-as-known-risk
filed: 2026-05-09
severity: informational
file: ergodix/auth.py
fixed:
---

## Description

`get_credential()` returns a decoded credential as a Python `str`. The
caller passes it to (e.g.) the Anthropic SDK or `keyring.set_password`,
and the string sits in the Python heap until garbage collection.

Python provides no reliable way to wipe credentials from memory:

- Strings are immutable; `del s` doesn't zero the underlying bytes.
- Python has no `mlock` equivalent — credentials may swap to disk.
- `bytearray` + `ctypes.memset` is occasionally suggested but has to
  be done before any string conversion happens, which is impractical
  for an SDK that takes a `str`.

## Impact

A process with debugger access (memory scraping, core dumps, ptrace)
can recover credentials. This requires either:

- Local same-uid attacker — already out of scope per
  [SECURITY.md](../SECURITY.md), and at that point keyring values are
  also accessible.
- A vulnerability that crashes the process and produces a core dump
  readable by another user — would require an additional bug.

## Decision

**Accepted as known risk.** This is unfixable in pure Python, and the
relevant invariant — credentials encrypted at rest — is provided by
the OS keyring. Going down the `bytearray` + `ctypes.memset` path is
almost always cargo-cult: credentials get copied into immutable strings
the moment any SDK sees them, defeating the scrub.

Recorded so future contributors don't reopen this question without
reading the reasoning.

If the project ever moves to a daemon mode or long-lived process
holding many credentials, revisit — at that scale, separating
credential-handling into a subprocess that can be killed and
respawned starts to be worth the complexity.
