# `form-analyzer` ergodite — grade-level + rhetorical eloquence + Fibonacci arc

- **Status**: parking-lot (Sprint 2+ when activated)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

## As / So that

As a writer (and a teacher in education-mode), so that one ergodite produces a single readout grading a chapter's *form* on three orthogonal axes — readability/grade-level (publicly-defined formulas: Flesch-Kincaid, Gunning Fog, SMOG, Coleman-Liau, ARI, Dale-Chall), rhetorical eloquence (density of detected figures per paragraph, drawing on Wordsmith Toolbox primitives), and Fibonacci/golden-mean structural arc (per the author's Fibonacci writing prompt) — instead of needing to run three separate analyses to diagnose whether the prose is pitched at the right grade level, rich enough rhetorically, and following the author's preferred narrative shape.

## Value

This is the first concrete instance of the ergodite plugin contract from [Spike 0013](../../spikes/0013-style-sentinel-and-certificate.md) — proves the plumbing works end-to-end with a useful output that the writer / editor / publisher floaters can all consume; bundling three sub-checks under one ergodite gives a unified per-chapter readout (one report to read, not three to merge); grade-level analysis directly enables the education-mode target audience match (school deploys with a target band like "middle school - upper" and the ergodite flags drift); the eloquence axis becomes the first concrete consumer of Wordsmith Toolbox rhetoric primitives, validating that abstraction; the Fibonacci axis lets the author check whether their structural intuition matches the prose actually written.

## Risk

The Fibonacci sub-check is blocked on capturing the author's prompt artifact in-tree (`docs/fibonacci-writing-prompt.md` — flagged in Spike 0013 cross-references); the eloquence sub-check is fully useful only after Wordsmith Toolbox ships its rhetoric reference (we can ship a minimal inline list for v1 and refactor later); grade-level scope creep (Lexile and ATOS are widely deployed in K-12 but proprietary — pulling those in needs a license + commercial discussion, not in scope for v1); reports without an interview-supplied target band only show "the prose is at grade 9.5" without flagging "off-target" — handles cleanly via null fields.

## Assumptions

`textstat` (or equivalent) bundles the public formulas so we don't reimplement; LLM-classified rhetoric is a setting-gated optional (default off for determinism); single ergodite with toggleable sub-checks is the right grain rather than three separate ergodites.

## Tasks (when activated)

- [ ] Implement after the ergodite registry from [Spike 0013](../../spikes/0013-style-sentinel-and-certificate.md) / ADR-X1 ships — this story instantiates the contract, doesn't define it.
- [ ] Decide `textstat` vs. inline formulas. Lean: pull in `textstat` (small dep, well-tested, public-domain math).
- [ ] Build the grade-level sub-check: portfolio (FK / Flesch-Ease / Gunning Fog / SMOG / Coleman-Liau / ARI / Dale-Chall), consensus grade, band classification, target-band comparison from [Spike 0010](../../spikes/0010-user-writing-preferences-interview.md) interview.
- [ ] Build the rhetorical-eloquence sub-check: 7 v1 figures (anaphora, epistrophe, polysyndeton, asyndeton, tricolon, alliteration, anastrophe) via regex; per-paragraph density; LLM classifier behind setting.
- [ ] Build the Fibonacci sub-check (after `docs/fibonacci-writing-prompt.md` lands): per-paragraph intensity score, target curve, deviation flagging.
- [ ] Pull rhetoric primitives from [wordsmith-toolbox](wordsmith-toolbox.md) once that ships; until then, inline a minimal definition table inside the form-analyzer module.

## Cross-references

- [Spike 0014 — form-analyzer ergodite](../../spikes/0014-form-analyzer-ergodite.md): design.
- [Spike 0013](../../spikes/0013-style-sentinel-and-certificate.md): registry contract.
- [Spike 0010](../../spikes/0010-user-writing-preferences-interview.md): target band + Fibonacci preferences.
- [wordsmith-toolbox](wordsmith-toolbox.md): rhetoric primitives.
