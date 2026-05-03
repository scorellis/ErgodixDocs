# Spikes

This folder holds **design spike documents** — narrative records of architectural exploration that produced one or more decisions.

## What goes here

A spike captures the *journey* of a discussion: the question being investigated, the options weighed, the dialogue that led to the decision, loose threads surfaced along the way.

Spikes complement [ADRs](../adrs/) but are not the same thing:

| | Spike | ADR |
|---|---|---|
| Captures | The discussion | The decision |
| Tense | Narrative, exploratory | Assertive, past tense |
| Mutability | Append-only narrative | Write-once / superseded |
| Audience | Future contributors trying to understand *why* we explored what we did | Future contributors trying to understand *what* was decided |

A spike usually produces one or more ADRs. The ADR lives in [adrs/](../adrs/) and links back to the spike doc here.

## Naming and numbering

`NNNN-kebab-case-title.md` with four-digit zero-padded numbers, assigned in order. First spike is `0001-…`. Numbers are never reused.

Spike numbers are *separate* from ADR numbers. Spike 0003 may produce ADR 0007, etc.

## Format

Free-form, but the following structure works well:

```markdown
# Spike NNNN: Title

- **Date range**: YYYY-MM-DD — YYYY-MM-DD
- **Sprint story**: [link to story in SprintLog.md]
- **ADRs produced**: [link to each ADR this spike led to]

## Question
What were we trying to figure out?

## Discussion
Narrative of the conversation. Quote, paraphrase, or synthesize. Capture the
options weighed, the user's contributions, the AI's contributions, where we
diverged and converged.

## Decisions reached
Bullet list of decisions made during this spike. Each links to its ADR.

## Loose threads / deferred questions
Things that came up but didn't get answered in this spike. Where they went
(future story, future spike, parking lot).
```
