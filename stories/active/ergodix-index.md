# `ergodix index` + `_AI/ergodix.map` — corpus content index

- **Status**: **ACTIVE** (Sprint 1 starter, 2026-05-10)
- **Spike**: [Spike 0015 — `ergodix index` design](../../spikes/0015-ergodix-index-design.md)
- **ADR**: [ADR 0016 — `ergodix index` + `_AI/ergodix.map` locked decisions](../../adrs/0016-ergodix-index-design.md) (2026-05-10)
- **Origin**: lifted from the parking-lot section of [stories/SprintLog.md](../SprintLog.md) — "near-term — after B2."

As the AI continuity engine and any incremental-analysis tool, so that we don't reconsume the entire corpus every session — the map records per-file SHA-256 hashes, sizes, and mtimes so a downstream tool can diff current state against the last-indexed state and only send *changed* chapters to the AI,

Value: massive cost savings on Anthropic API once Plot-Planner / Continuity-Engine tools start running over the corpus — without an index, every continuity-check pass re-tokenizes the whole opus; with an index, only the deltas; second-order: the map becomes the foundation for the future "multidimensional mind map" of plotlines, conversations, character arcs, etc. that lets the AI build incremental knowledge across sessions,

Risk: stale-map handling (user edits a file outside ErgodixDocs, the map doesn't refresh; tools work from outdated assumptions); merge-conflict noise if the map is git-tracked in a shared corpus repo; over-engineering the format too early — better to ship a simple v1 than design for the future N+1 tool,

Assumptions: SHA-256 of file content is sufficient for change-detection (collisions are not a threat-model concern); the map is regenerated on demand via an `ergodix index` subcommand and re-runs cheaply; lives at `_AI/ergodix.map` next to the corpus per the existing `_AI/` convention; TOML keeps it human-readable so the user can open and inspect without tooling.

## Tasks (post-ADR-0016)

ADR 0016 locked all 9 open questions from the spike. Per Spike 0015's "Implementation chunks" section, the work splits into 6 PRs in the smaller-units cadence:

- [ ] Helpers (`ergodix/index.py`): pure functions — `compute_sha256_of_file`, `walk_corpus_for_index`, `build_map_entry`, `serialize_map_toml`, `parse_map_toml`, schema constants.
- [ ] `generate_index` orchestrator: walks the corpus, builds the `Map`, writes `_AI/ergodix.map` atomically (tmp + rename), returns a summary record.
- [ ] `compare_to_map` + drift report: given an existing map and a fresh walk, compute new / changed / removed file sets.
- [ ] CLI wiring: real `ergodix index` command with `--check` / `--corpus` / `--quiet`. Exit codes per Spike 0015 §4.
- [ ] Migrate-fixture extension (or `examples/index-fixture/`) so hermetic e2e tests cover the index path.
- [ ] First-consumer doc: `docs/ergodix-map-consumers.md` documenting the read API + per-file shape, so Plot-Planner / Continuity-Engine designers don't reinvent the parsing.

## Cross-references

- [Spike 0015](../../spikes/0015-ergodix-index-design.md): design surface + 9 open questions.
- [Continuity-Engine parking-lot story](../parking-lot/continuity-engine.md): the first downstream consumer of the map. (Story file lands in PR 2 of the stories-folder migration.)
- [Plot-Planner parking-lot story](../parking-lot/plot-planner.md): second consumer.
- [Spike 0013 §C ergodite plugin registry](../../spikes/0013-style-sentinel-and-certificate.md): every future ergodite reads the map first.
- [ADR 0015 §4 migrate manifest schema](../../adrs/0015-migrate-from-gdocs.md): conceptually adjacent (per-file sha256, atomic-write pattern, schema-version refusal).
