# Sell-My-Book — book-marketing assistance suite

- **Status**: parking-lot (way later, after the corpus is finished)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

## As / So that

As a publisher (and as the author wearing the publisher floater), so that there is a tool surface for the post-writing phase — turning a finished corpus into something readers actually find and buy — without bolting marketing concerns onto the authoring tools.

## Value

The tool's value continues past "draft is done" into the part of writing that most authors find hardest (selling); creates a complete pipeline from blank page to launched book; tools live in their own namespace so they don't pollute the writing workflow.

## Risk

Huge surface (audience research, blurb generation, cover design feedback, price-point analysis, launch-platform comparison, ad copy, review-funnel design, social media seeding, etc.); easy to wander into commodity ad-tech territory; ethical concerns about AI-generated promotional content need their own handling; doing this *before* the author's own book launch validates the approach risks building features that don't survive contact with real publication realities.

## Assumptions

The author's own book ships first and surfaces concrete needs; lessons from that launch flow back into the tooling rather than the tooling being designed in the abstract; a clean separation between authoring tools (Plot-Planner) and marketing tools (Sell-My-Book) is maintained; some tools may share infrastructure with Plot-Planner (corpus indexing, character extraction) without sharing tool surface.

## Tasks (when activated — *after the author's own book has shipped*)

- [ ] Run the author's own launch and harvest "what tools would have made this 10x easier" intel.
- [ ] Decide the Sell-My-Book tool surface (likely separate slash-command/skill namespace from [plot-planner](plot-planner.md)).
- [ ] Enumerate concrete tools based on the launch retrospective.
- [ ] Address ethical guardrails on AI-generated marketing content (transparency, disclosure norms).
- [ ] Decide whether Sell-My-Book ships with Plot-Planner or as a separate phase / package.
