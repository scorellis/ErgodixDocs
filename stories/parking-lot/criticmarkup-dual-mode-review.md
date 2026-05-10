# Spike — CriticMarkup dual-mode review (deferred — not blocking v1)

- **Status**: parking-lot (spike, deferred — not blocking v1)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.
- **Type**: spike (design discussion needed before story can be written)

## So that

The author has a coherent UX for reviewing two parallel review surfaces — diff-level prose changes (per [ADR 0006](../../adrs/0006-editor-collaboration-sliced-repos.md)) and CriticMarkup `{>> <<}` annotations *inside* the changed prose — without confusion about precedence, render output, or "is this a comment about the old text or the new text?".

## Value

Prevents the editor's annotations from being lost or mis-applied during diff review; clarifies the rendered-output shape when a chapter has both an editor's prose edit AND an editor's comment about something else in the same paragraph.

## Risk

Not addressing this means the author has to mentally context-switch every review session; ad-hoc workflow forms before the spike can settle the convention.

## Tasks (when activated)

- [ ] Document the two surfaces and their interaction patterns.
- [ ] Decide rendering precedence in `--track-changes=all` mode when both diff and CriticMarkup are present.
- [ ] Decide whether `ergodix ingest` should auto-extract CriticMarkup `{>> <<}` blocks into review-comment metadata vs. leave them in-prose.
- [ ] Update [docs/comments-explained.md](../../docs/comments-explained.md) with the resolved convention.
