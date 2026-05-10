# Migrate fixture

A small canned corpus used by the hermetic e2e tests at
`tests/test_migrate_fixture.py` to exercise `ergodix migrate` end-to-end
without needing a real Google Drive account or a network round-trip.
Mirrors the role `examples/showcase/` plays for the render pipeline.

## Layout

```
examples/migrate-fixture/
  Book 1/
    Chapter 1.gdoc   ← Drive placeholder (JSON pointer to a fake doc_id)
    Chapter 2.docx   ← real Word/Scrivener-shaped binary
  Notes.gsheet       ← out-of-scope file type (skipped by the importer)
```

The `.gdoc` is a normal Drive-style placeholder (a JSON object with
`doc_id` / `url` / `resource_id` fields). The test injects a mocked
`docs_service` whose `documents().get(documentId="fixture-doc-chapter-1")`
call returns canned Docs API JSON, so no network is touched.

The `.docx` is a real binary built by `tests/build_migrate_docx_fixture.py`
using `python-docx`. Re-run that script if you change the builder and
want to regenerate the binary; commit the new `.docx` alongside. The
binary is checked in (per ADR 0015 §"Implementation chunks" #7) so
tests are stable across `python-docx` version drift. The builder lives
under `tests/` rather than inside the fixture corpus so the migrate
walker doesn't pick the `.py` script up as an out-of-scope file.

The `.gsheet` exists to verify that out-of-scope file types are
recorded as `skipped` with `reason="out-of-scope file type"` in the
run manifest, per ADR 0015 §2.

## Running the fixture as a corpus

The fixture is also runnable as a real corpus to manually verify
migrate from the CLI side. From the repo root:

```bash
ergodix migrate --from gdocs --check --corpus examples/migrate-fixture
```

`--check` makes it a dry-run (no `_archive/` pollution). Drop the flag
to do a live run — be aware the gdoc placeholder won't resolve against
a real Drive doc, so you'll see a phase-1 failure for `Chapter 1.gdoc`
and a clean migrate for `Chapter 2.docx` (which doesn't need network).

## Why a fixture instead of mocks-only?

A checked-in fixture pins three properties the test suite would
otherwise have to ad-hoc-construct in every test:

1. The walker traverses a real on-disk tree (`Book 1/...`) and
   correctly resolves relative paths.
2. The `.docx` importer parses a real binary that python-docx wrote,
   not a unittest-fabricated in-memory Document.
3. The orchestrator's manifest, archive, and frontmatter outputs are
   asserted against a known-good corpus shape — so a regression in
   any layer (walker, importer, orchestrator, frontmatter generator)
   surfaces as a fixture-test failure rather than a unit-test failure
   in only one layer.
