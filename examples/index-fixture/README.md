# examples/index-fixture/

A small, hand-curated corpus shape that exercises the `ergodix index`
walker rules end-to-end (Spike 0015 §2 / ADR 0016).

This fixture is committed to the repo so the hermetic e2e tests in
[tests/test_index_e2e.py](../../tests/test_index_e2e.py) can run against
a stable layout without rebuilding it at test time. Tests copy the
fixture into a `tmp_path` before invoking the CLI so they never mutate
the tracked content.

## Layout

```
examples/index-fixture/
├── README.md                       indexed (this file)
├── _preamble.tex                   indexed (top-level preamble)
├── Book 1/
│   ├── _preamble.tex               indexed (sub-folder preamble)
│   ├── Chapter 1.md                indexed
│   ├── Chapter 2.md                indexed
│   └── Section A/
│       └── Chapter 3.md            indexed
├── _archive/                       skipped (walker excludes _archive)
│   └── Old Chapter.md
├── scratch/                        skipped (.ergodix-skip marker)
│   ├── .ergodix-skip
│   └── draft.md
└── _media/                         skipped (walker excludes _media)
    └── (no real images — binary out of scope)
```

## Expected counts

A fresh `ergodix index --corpus examples/index-fixture` should produce
a map with **6 files**:

1. `README.md`
2. `_preamble.tex`
3. `Book 1/_preamble.tex`
4. `Book 1/Chapter 1.md`
5. `Book 1/Chapter 2.md`
6. `Book 1/Section A/Chapter 3.md`

The hermetic e2e tests pin this count and the file path set; they also
exercise the round-trip (generate → check passes → modify → check
fails → re-generate → check passes again).
