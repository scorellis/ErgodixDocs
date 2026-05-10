# Multi-opus support (Story 0.X)

- **Status**: parking-lot (deferred to Sprint 1+ or first real use case)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

## Terminology

An **opus** is a named bundle of (corpus path + default floater set + last-used context). Plural: **opera**. Term chosen to fit the project's classical/Latin voice without colliding with Compendium (a level in the narrative Hierarchy).

## So that

One machine and one identity can address multiple opera with different role-sets per opus (you on Tapestry as writer/dev/publisher; you on a friend's manuscript as focus-reader; an editor working two authors' books in parallel).

## Value

Makes ErgodixDocs viable as the underlying tool when adoption broadens past one author; lets a single user split work across opera without re-installing per project.

## Risk

Introducing the dimension prematurely costs more than waiting; conflating this with enterprise tenancy concerns that aren't actually adjacent.

## Assumptions

Forward-compatible architectural pieces already in place (registries, settings folder, three-tier credential lookup); `local_config.py`'s `CORPUS_FOLDER` becoming a dict keyed by opus name is non-breaking.

## CLI shape (locked at story-open time)

```bash
ergodix opus list
ergodix opus add tapestry --corpus tapestry-of-the-mind --writer --developer --publisher
ergodix opus add friend-novel --corpus their-book --focus-reader
ergodix opus switch tapestry
ergodix cantilever                  # uses current opus
ergodix sync-out                    # uses current opus (per ADR 0008 rename)
```

Each opus is stateful — `opus switch <name>` sets a current-opus pointer (probably in `local_config.py`); subsequent commands inherit its corpus + floater config.

## Tasks (filled out when story moves out of parking lot)

- [ ] Confirm stateful (`switch`) vs. per-invocation (`--opus <name>`) — likely support both, with `switch` writing the current pointer used as default for subsequent invocations.
- [ ] Extend `local_config.py` schema: `OPERA = { "tapestry": {...}, "friend-novel": {...} }` plus `CURRENT_OPUS` pointer.
- [ ] Update cantilever to take opus context as input (which floaters apply to which opus).
- [ ] Update `ergodix sync-out`, `sync-in`, `migrate`, `render`, `status` to be opus-aware.
- [ ] Migration path for existing single-opus installs (the existing `CORPUS_FOLDER` becomes the first entry under `OPERA["default"]`).

## Cross-references

- [ADR 0005](../../adrs/0005-roles-as-floaters-and-opus-naming.md): roles as floaters + opus naming.
- [ADR 0008](../../adrs/0008-cleanup-sync-rename-ownership-autofix-static-analysis.md): `sync-out` rename.
