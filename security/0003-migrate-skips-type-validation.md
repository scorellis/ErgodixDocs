---
id: 0003
title: cmd_migrate_to_keyring doesn't validate value types
status: open
severity: low
filed: 2026-05-09
file: ergodix/auth.py:288-310
fixed:
---

## Description

`cmd_migrate_to_keyring()` reads each known credential out of the JSON
fallback file and writes it to the OS keyring:

```python
val = data.get(name)
# ... nested fallbacks for google_oauth.client_id / client_secret ...
if val:
    keyring.set_password(KEYRING_SERVICE, name, val)
```

The `if val:` guard rejects only falsy values (None, empty string, 0,
empty list). It does *not* check `isinstance(val, str)`. By contrast,
`_from_file()` is careful: it explicitly checks `isinstance(value, str)`
and returns `None` otherwise, so a user with a malformed JSON value
(`"anthropic_api_key": 12345`) gets a clean "credential not found"
rather than an unstable type at runtime.

If a user hand-edited `secrets.json` to use a non-string for a value,
`migrate-to-keyring` will pass the non-string to `keyring.set_password`,
where the failure mode depends on the backend — most will TypeError,
some may stringify silently.

## Impact

Low. The user has to deliberately corrupt their own secrets file for
this to fire. The failure mode is messy (an opaque traceback or a
keyring entry containing the literal string "12345"), not exploitable.

Filing as a defensive-polish record.

## Reproduction

```bash
echo '{"anthropic_api_key": 12345}' > ~/.config/ergodix/secrets.json
chmod 600 ~/.config/ergodix/secrets.json
python -m ergodix.auth migrate-to-keyring
# Backend-dependent traceback or silent type coercion
```

## Decision

**Open.** Trivial one-line fix when it lands: add
`isinstance(val, str)` to the guard, mirroring the pattern in
`_from_file()`. Not patched in PR #32 to keep that PR's diff minimal
and focused on the symlink/TOCTOU attack surface. Should land in a
later defensive-polish pass.
