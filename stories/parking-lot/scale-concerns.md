# Scale concerns (Stories 0.Z1–0.Z5)

- **Status**: parking-lot (deferred; each sub-story activates per real signal)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

The dimensions below are real architectural considerations even though they don't have urgency yet. Forward-compatibility decisions made now should not foreclose any of them. Each becomes its own story when activated.

## Story 0.Z1 — Concurrency and write-collision handling

**So that** multiple editors can work on the corpus simultaneously without losing edits or producing broken merges.

**Value**: real-world co-editing (writer + editor + future line editor) needs to be safe; auto-sync racing against itself across machines is the failure mode this prevents.

**Risk if ignored**: silent data loss when two auto-syncs land in overlapping windows; surprising conflicts that bypass the editor persona's "zero-friction" promise.

**Assumptions**: each editor's machine works on independent feature branches by default; sync conflicts on shared branches surface as standard git conflicts; debouncing in the auto-sync VS Code task is part of the solution but not the whole solution.

**Investigate when activated**: per-machine sync queues; conflict detection in `ergodix sync-out` before push (warn user when remote has new commits on the same branch); fast-forward-only sync as default; explicit `ergodix sync-out --force` for the rare overrule case.

## Story 0.Z2 — Corpus volume and AI analysis efficiency

**So that** the AI architectural-analysis features (plotline tracking, continuity detection, summaries, storyboards — Sprint 1) work on a full multi-book corpus (200+ chapters, 1M+ words) without per-invocation context-bloat or cost explosion.

**Value**: this is the actual product. "Load the whole corpus into the context window every time" stops working at corpus sizes serious authors will quickly reach.

**Risk if ignored**: AI features are demoware that only work on tiny samples; the tool's reason-for-existing fails to scale with the user's actual writing.

**Assumptions**: prompt caching meaningfully cuts repeat-analysis cost (Anthropic's prompt cache has a 5-minute TTL — useful for active sessions); per-chapter analysis with cross-chapter index is tractable; vector-store retrieval-augmented generation is a viable layer on top; incremental analysis (only re-analyze what changed) is implementable.

**Investigate when activated**: chapter-level analysis index; embedding-based retrieval over the corpus; prompt-caching strategy per command; result caching on disk so repeat invocations are free; batch APIs (Anthropic supports batch jobs) for non-interactive work.

## Story 0.Z3 — Long-tail: history, retention, storage growth

**So that** the corpus repo remains performant after 5+ years of edits, render outputs don't bloat git, and old AI artifacts don't accumulate forever.

**Value**: serious authors work on multi-decade projects; the tool should not become the bottleneck.

**Risk if ignored**: git operations slow as history grows; PDF render outputs balloon the repo; the `_AI/` folder becomes a graveyard of stale analyses; clone times become a barrier for new contributors.

**Assumptions**: git LFS for binary render outputs is viable; `.gitattributes` patterns can isolate large artifacts; retention policies are configurable per opus.

**Investigate when activated**: git LFS for `_AI/` PDFs and render outputs; `.gitattributes` configuration; retention policy in `settings/` (e.g. "keep latest 5 render outputs per chapter, delete older"); cantilever-time pruning operation; corpus-archive command for cold-storing old material.

## Story 0.Z4 — AI cost and quota management

**So that** AI architectural-analysis features have predictable cost, hard caps to prevent runaway billing, and (eventually) per-user allocation when an organization runs the tool.

**Value**: a writer running daily continuity analysis on a million-word corpus can rack up real bills; an enterprise running it across many authors will demand budget controls.

**Risk if ignored**: surprise bills become a tool-killer; users avoid AI features because cost is opaque; enterprise adoption is blocked entirely.

**Assumptions**: aggressive prompt caching cuts the dominant cost; monthly caps configured at cantilever time are practical; usage telemetry can be opt-in for users who want a cost dashboard; per-feature cost reporting is implementable.

**Investigate when activated**: prompt caching strategy; per-user / per-opus monthly cap with hard cutoff; cost dashboard (`ergodix cost report`); telemetry that respects privacy (opt-in, never includes prose); enterprise extension hooks for centralized billing (relates to [publishing-house-enterprise-scale](publishing-house-enterprise-scale.md)).

## Story 0.Z5 — Graceful degradation and resilience

**So that** ErgodixDocs works (or fails gracefully and informatively) under partial outages: keyring locked, Anthropic API down, GitHub unavailable, Drive offline, Pandoc broken, XeLaTeX missing.

**Value**: trust. The tool should not become a catastrophic single point of failure when any one external dependency is degraded; users should not develop workaround habits that bypass the tool.

**Risk if ignored**: any single dependency outage blocks all work; users learn to circumvent the tool; the auto-sync flow becomes a liability when the network is intermittent.

**Assumptions**: most operations have viable fallback paths (cached results, deferred operations, read-only modes); failure mode classification is implementable; "degraded mode" can be communicated clearly via `ergodix status`.

**Investigate when activated**: failure-mode catalog per operation (already has a kernel in [ADR 0003](../../adrs/0003-cantilever-bootstrap-orchestrator.md)'s auto-fix concept); circuit breakers on external API calls; explicit degraded-mode indicators surfaced in CLI output and the run-record; cached-result fallback for AI features when the API is unavailable.
