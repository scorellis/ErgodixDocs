---
id: 0005
title: No rate-limiting / audit log on credential reads
filed: 2026-05-09
status: accepted-as-known-risk
severity: informational
file: ergodix/auth.py
fixed:
---

## Description

`get_credential()` performs no rate limiting, no audit logging, and
emits no event when a credential is fetched. A buggy or malicious
caller in the same Python process could query the same credential in
a tight loop without surfacing anything observable to the user.

## Impact

For a single-user local CLI tool, audit logging would create more noise
than signal — every render run, every cantilever run, every API call
would produce logs that no one reads. The convenience cost of "did the
keyring prompt me five times today?" is the user's *own* signal that
something unusual is happening.

The picture changes if ErgodixDocs ever grows:

- A daemon mode that stays resident.
- An MCP server other processes can call into.
- A multi-collaborator deployment.

In any of those, every credential read should produce a log entry
recording the credential *name* (never the value) and the calling
context, so post-incident forensics can reconstruct what happened.

## Decision

**Accepted as known risk** for the v1 single-user CLI. Recorded so
the future-mode trigger is explicit: when the project grows a daemon
or shared surface, this finding becomes load-bearing and the audit
log must land before that surface ships.

Cross-referenced from the future MCP-server-with-AI-user-persona
parking-lot story in [SprintLog.md](../stories/SprintLog.md).
