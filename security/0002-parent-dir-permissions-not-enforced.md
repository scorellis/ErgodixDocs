---
id: 0002
title: ~/.config/ergodix/ mode not enforced at read time
status: patched-in-#33
severity: medium
filed: 2026-05-09
file: ergodix/auth.py:170-178
fixed: 2026-05-09
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

**Patched in PR #33.** First patch landed under the security review
cadence in CLAUDE.md §3 — a medium-severity finding closed within 24
hours of being filed.

## Patch

PR #33 adds a parent-dir mode check at the top of
`_read_file_data_checked`: before any file open, we `stat()` the parent
and reject if `(mode & 0o077) != 0`. Three tests pin the behavior:

- `test_parent_dir_with_world_readable_perms_rejects_read` — 0o755 fails
- `test_parent_dir_with_any_group_or_world_bit_rejects_read` — 0o710 fails
- `test_parent_dir_at_700_passes` — 0o700 + file 0o600 succeeds (happy path)

Pre-existing tests that constructed `~/.config/ergodix/` via
`mkdir(parents=True)` were updated to `chmod(0o700)` immediately after
— the previous default of whatever-the-umask-was happened to be 0o755
on macOS, so those fixtures would have started false-failing under the
new check. The fixture tightening is consistent with what production
installs land via C5.

## What's NOT in the patch

The fancier `os.open(parent, O_DIRECTORY) + fstat(dirfd)` pattern was
considered but skipped: the realistic threat is "parent dir was created
loose by accident," not "parent dir gets swapped between our stat and
our open." A simple `parent.stat()` is right-sized; the TOCTOU window
on the directory is small enough relative to the threat model in
[SECURITY.md](../SECURITY.md) that the extra complexity isn't earned.
