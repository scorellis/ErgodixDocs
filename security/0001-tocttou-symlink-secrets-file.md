---
id: 0001
title: TOCTOU + symlink swap on secrets.json read
status: patched-in-#32
severity: medium
filed: 2026-05-09
file: ergodix/auth.py:170-178
fixed: 2026-05-09
---

## Description

`_read_file_data_checked()` validates the secrets file's mode and then
opens it as two separate syscalls against the same path:

```python
if (CENTRAL_SECRETS_FILE.stat().st_mode & 0o077) != 0:
    raise PermissionError(...)
with open(CENTRAL_SECRETS_FILE) as f:
    data = json.load(f)
```

Two latent issues:

1. **Time-of-check vs. time-of-use (TOCTOU).** `stat()` and `open()` resolve
   the path independently. An attacker who can write to the parent
   directory can swap the file out of band between the two syscalls — the
   mode check passes against one inode, the read happens against another.
2. **Symlink following.** Both `Path.stat()` and `open()` follow symlinks
   by default. If `~/.config/ergodix/secrets.json` is a symlink to
   `/tmp/attacker-controlled.json`, the mode check inspects the target's
   mode, and we cheerfully read whatever the target points to.

## Impact

Limited under the project's threat model — a local attacker with the
user's account is already explicitly out of scope per
[SECURITY.md](../SECURITY.md). The realistic risk is:

- A trusted third-party tool that drops files into `~/.config/` could
  inadvertently shadow `secrets.json` with a symlink (intentional misuse
  or buggy behavior), and ErgodixDocs would silently read whatever the
  symlink targets.
- An attacker with write access to the parent dir but not the file
  itself (uncommon, but possible via shared-tmp or quirky umask) could
  swap the file post-mode-check.

Severity is **medium** because the file holds API keys whose disclosure
could cost the user money (Anthropic, GCP) — not catastrophic, but
worth defending against cheaply.

## Reproduction

```bash
mkdir -p ~/.config/ergodix
echo '{"anthropic_api_key": "real-secret"}' > /tmp/legit.json
chmod 600 /tmp/legit.json
ln -s /tmp/legit.json ~/.config/ergodix/secrets.json
python -m ergodix.auth status   # silently reads /tmp/legit.json
```

The attack variant: replace the legit target with an attacker-controlled
file that has the same mode but different contents.

## Decision

**Patch.** Cost is ~15 lines; readability impact is negligible. Defending
against an explicitly-out-of-scope attacker is OK when it's free.

The fix replaces the stat-then-open pattern with a single `os.open` call
using `O_RDONLY | O_NOFOLLOW`, then `fstat`s the resulting fd before
reading. `O_NOFOLLOW` makes the symlink case fail loudly (`ELOOP`)
rather than silently following. `fstat` on the fd guarantees the same
inode is read as is mode-checked.

## Patch

PR #32 — replaces `_read_file_data_checked` with a fd-based read that
uses `O_NOFOLLOW`, fstats the fd, and translates `ELOOP` into a
human-readable `PermissionError` pointing the user at the symlink. Two
new tests pin the new behavior:

- `test_secrets_file_symlink_is_rejected_with_clear_remediation`
- `test_secrets_file_loose_perms_still_rejected_via_fstat`

`O_NOFOLLOW` falls back to `0` on platforms where it's not defined
(Windows). The Windows threat model differs anyway and a symlink on
NTFS requires elevated privileges to create — the loss of protection
is acceptable for the cross-platform tradeoff.
