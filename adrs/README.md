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

- **Status**: Proposed | Accepted | Deprecated | Superseded by ADR XXXX | Partially Superseded by ADR XXXX (and YYYY)
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

## Status values

- **Proposed** — under review, not locked.
- **Accepted** — locked and authoritative for everything it covers.
- **Deprecated** — withdrawn entirely; do not implement.
- **Superseded by ADR NNNN** — fully replaced; read ADR NNNN instead.
- **Partially Superseded by ADR NNNN (and YYYY)** — some sections replaced; rest still authoritative. Allowed because most architectural revisions touch only one or two sections of a prior ADR; full supersession would force re-writing everything that's still correct. The replacing ADRs name which sections they override; this ADR carries Notes pointing at them.

## Workflow

1. A spike or discussion produces a decision.
2. Open a feature branch.
3. Write the ADR in this folder. Status: `Accepted` if already decided in conversation; `Proposed` if still under review.
4. If superseding an earlier ADR fully, edit the older one's Status to `Superseded by ADR NNNN`.
5. If superseding part of an earlier ADR, edit the older one's Status to `Partially Superseded by ADR NNNN`, and add a Note block at the top of the older ADR pointing at the replacing ADR for the affected sections. The new ADR's frontmatter has a `Supersedes (in part)` line listing what it overrides.
6. Commit + PR + merge as usual.
