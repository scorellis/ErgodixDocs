# Architectural Decision Records (ADRs)

This folder holds the canonical record of significant architectural decisions for ErgodixDocs.

## What goes here

An ADR captures a single decision, the context that made it necessary, and its consequences. ADRs are write-once and append-only — a decision doesn't get revised, it gets *superseded* by a new ADR that points back to the one it replaces.

ADRs are not:
- Sprint stories (those live in [SprintLog.md](../SprintLog.md))
- Design exploration / discussion notes (those live in [spikes/](../spikes/))
- General documentation (that lives in [docs/](../docs/) or the [README](../README.md))

## Naming and numbering

`NNNN-kebab-case-title.md` where `NNNN` is a four-digit zero-padded number assigned in order. First ADR is `0001-…`. Numbers are never reused.

## Format

Modified [Michael Nygard format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions). Each ADR has:

```markdown
# ADR NNNN: Title

- **Status**: Proposed | Accepted | Deprecated | Superseded by ADR XXXX
- **Date**: YYYY-MM-DD
- **Spike**: [link to corresponding spike doc, if any]

## Context
What's the issue, what forces are at play, what are we deciding?

## Decision
The decision, stated assertively. Past tense, declarative.

## Consequences
What becomes easier. What becomes harder. What we accept as tradeoffs.

## Alternatives considered
Brief — why each alternative was rejected.

## References
Spike doc, related ADRs, external links.
```

## Workflow

1. A spike or discussion produces a decision.
2. Open a feature branch.
3. Write the ADR in this folder. Status: `Accepted` if already decided in conversation; `Proposed` if still under review.
4. If superseding an earlier ADR, edit the older one's Status to `Superseded by ADR NNNN` (this is the only allowed edit to an existing ADR).
5. Commit + PR + merge as usual.
