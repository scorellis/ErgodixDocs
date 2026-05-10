---
id: 0003
title: cmd_migrate_to_keyring doesn't validate value types
status: patched-in-#50
severity: low
filed: 2026-05-09
file: ergodix/auth.py:288-310
fixed: 2026-05-09
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

**Patched in PR #50.** One-line fix as anticipated: replaced the
truthiness check `if val:` with `if isinstance(val, str) and val:`,
mirroring the pattern in `_from_file()`. Two new tests pin the
behavior — non-string values are skipped cleanly, and empty-string
values continue to be skipped (already handled by the original
truthiness check, but pinning so a future "simpler" refactor doesn't
regress).

## Patch

PR #50 adds the type guard to the migrate loop and includes two
defensive tests:
- `test_migrate_to_keyring_skips_non_string_values`
- `test_migrate_to_keyring_skips_empty_string_values`

Cadence note: this is the third self-found finding closed via the
[CLAUDE.md §3 security review cadence](../CLAUDE.md#3-security-review-cadence)
since it was established. Critical / high findings (none filed) would
patch immediately; medium findings (#0001, #0002) patched within 24
hours; this low-severity finding closed within ~24 hours of filing.
