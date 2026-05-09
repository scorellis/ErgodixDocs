---
id: 0002
title: ~/.config/ergodix/ mode not enforced at read time
status: open
severity: medium
filed: 2026-05-09
file: ergodix/auth.py:170-178
fixed:
---

## Description

[README.md](../README.md#file-mode-invariants) states that
`~/.config/ergodix/` should be mode `0o700`. The C5 prereq
([`check_credential_store`](../ergodix/prereqs/check_credential_store.py))
enforces this on first install. But `auth.py`'s file-read path
(`_read_file_data_checked`) only validates the mode of the
`secrets.json` file itself — never the parent directory.

If a user manually created `~/.config/ergodix/` outside of the cantilever
flow (e.g. `mkdir -p ~/.config/ergodix` from a shell), it lands at the
default umask — typically `0o755` on macOS and many Linux distros. The
mode-600 check on `secrets.json` then becomes a near-meaningless
guarantee: an attacker with the same uid (out-of-scope by SECURITY.md)
or any process with write access to the parent dir can rename
`secrets.json` out and substitute a different file.

## Impact

Under the project's stated threat model the impact is bounded — a
local same-uid attacker is explicitly out of scope. But the *invariant
the README promises* (mode 600 file in mode 700 directory) is not
actually enforced at read time, and that's a documentation drift. If
the project ever grows multi-user surfaces (a daemon, an MCP server,
a shared CI runner), this becomes load-bearing.

Related to finding 0001 — together, the parent-dir slack and the
TOCTOU/symlink path describe the same attack surface from different
angles.

## Reproduction

```bash
chmod 755 ~/.config/ergodix     # weaken the dir
chmod 600 ~/.config/ergodix/secrets.json
python -m ergodix.auth status   # passes silently — dir mode unchecked
```

## Decision

**Open** as of 2026-05-09. Not patched in PR #32 because it's a
distinct fix and the symlink/TOCTOU patch (#0001) was the priority
"show we mean business" item for the night.

When it's patched, the right pattern is to add a parent-dir mode check
inside `_read_file_data_checked` (and perhaps also at the
fd-from-os.open() step, fstating the dir fd via `os.open(dir, O_RDONLY |
O_DIRECTORY)`). The remediation message should point the user at
`chmod 700 ~/.config/ergodix`.

Could also be addressed at the C5 verify-side — re-check on every
cantilever run that the dir is still 700.
