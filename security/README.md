# Security records

This folder is the in-repo log of security findings — both self-found
(code review, static analysis) and externally reported. The convention
parallels [`adrs/`](../adrs) and [`spikes/`](../spikes): one file per
finding, monotonically numbered, write-once with status updates.

GitHub Security Advisories are appropriate for issues that warrant a CVE
or coordinated disclosure with external reporters. Self-found findings on
this project go here so they're versioned with the code and survive
tooling changes.

## File naming

`security/NNNN-short-kebab-title.md` where `NNNN` is a four-digit serial.

## Frontmatter

```markdown
---
id: NNNN
title: <short title>
status: open | accepted-as-known-risk | patched-in-#NN | superseded
severity: critical | high | medium | low | informational
filed: YYYY-MM-DD
file: <path/to/affected/file.py>:<line range>
fixed: <YYYY-MM-DD or empty>
---
```

## Body sections

- **Description** — what the issue is, in one short paragraph
- **Impact** — what an attacker could do under what threat model
- **Reproduction** — minimal steps or proof-of-concept
- **Decision** — patch / accept / defer, with reasoning
- **Patch** (when status is `patched-in-#NN`) — link to PR + brief summary

## Status transitions

- `open` — filed, awaiting decision or implementation
- `accepted-as-known-risk` — decided not to fix, with reasoning recorded
  (this is a valid terminal state for out-of-scope findings)
- `patched-in-#NN` — fix has landed; the record stays as the audit trail
- `superseded` — replaced by a later record (rare)

## Index

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| [0001](0001-tocttou-symlink-secrets-file.md) | TOCTOU + symlink swap on secrets.json read | medium | patched-in-#32 |
| [0002](0002-parent-dir-permissions-not-enforced.md) | `~/.config/ergodix/` mode not enforced at read time | medium | patched-in-#33 |
| [0003](0003-migrate-skips-type-validation.md) | `cmd_migrate_to_keyring` doesn't validate value types | low | open |
| [0004](0004-memory-scrubbing-out-of-scope.md) | No in-memory scrub of decoded credentials | informational | accepted-as-known-risk |
| [0005](0005-no-credential-read-audit-trail.md) | No rate-limiting / audit log on credential reads | informational | accepted-as-known-risk |
