# Devil's Toolbox — foundational rhetoric reference Skill

- **Status**: parking-lot (Sprint 2+ when activated)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

## As / So that

As a writer, so that the AI tools that score and critique prose have a stable, comprehensive reference for rhetorical devices, logical fallacies, persuasion techniques, and narrative structures — instead of each tool re-deriving "what counts as a metaphor" or "what counts as a strawman" from the model's free-floating knowledge — and the author can trust that two tools using the same primitive (e.g. `writing-score` and `PC-placator` both reasoning about *ethos*) reach consistent verdicts.

## Value

A structured rhetoric knowledge base is the *moat* under Plot-Planner's tool suite; without it, every tool is a thin LLM wrapper that may classify the same passage differently across runs; with it, tools become deterministic enough to be testable; second-order: enables Devil's-Advocate-style review tools that intentionally apply hostile rhetorical analysis to expose weaknesses.

## Risk

Scope explosion (rhetoric is a *huge* field — Aristotelian appeals, classical figures, modern persuasion taxonomies, narrative theory, prosody, etc. — picking a curriculum boundary is hard); reference drift (the canonical taxonomy changes between editions of textbooks; pinning a *version* matters); over-engineering — if no Plot-Planner tool actually consumes the toolbox, it's documentation no one reads.

## Assumptions

A single foundational reference is more valuable than per-tool inline definitions; the reference is consulted by tools, not directly by humans (humans get *output* from the tools, not raw rhetoric lookups); a TOML/YAML rubric is rich enough to encode each device (name, definition, exemplars, classifier hints) without prose; the umbrella "Devil's Toolbox" name lands the right tone — analytical, slightly adversarial, useful for both critique and stylistic advice.

## Tasks (when activated)

- [ ] Decide curriculum scope — what does "rhetoric" cover here? Likely union of: Aristotelian appeals (ethos / pathos / logos / kairos), classical figures (anaphora, chiasmus, polysyndeton, etc.), logical fallacies (formal + informal), persuasion patterns (Cialdini's six + variants), narrative-structural primitives (hero's journey beats, kishōtenketsu, etc.), prosody-adjacent devices (sentence rhythm, paragraph cadence). Probably *not* covered: pure literary theory (deconstruction, reader-response), academic rhetoric (debate-style argumentation).
- [ ] Encode each entry in a stable TOML/YAML schema with id, name, category, definition, exemplars, classifier-hint (a few examples the AI can match against).
- [ ] Land as a Skill at `.claude/skills/devils-toolbox/` with reference data in the skill's data files; tools reference by id.
- [ ] First consumer: `writing-score` references device-ids when flagging strengths/weaknesses ("strong anaphora in §3.2" / "logos appeal undermined by post hoc fallacy in §4.1").
- [ ] Decide version pinning + amendment process — when a new device is added or a definition changes, do existing scored chapters re-score? Probably not; record the version-of-record in `_AI/scoring-runs/<run>.toml`.
- [ ] Cross-reference: [Spike 0010 — UserWritingPreferencesInterview](../../spikes/0010-user-writing-preferences-interview.md) (author may opt out of certain rhetoric categories — "don't flag classical figures unless explicitly asked").
- [ ] Cross-reference: [plot-planner](plot-planner.md) (Devil's Toolbox is a dependency of `writing-score`, `PC-placator`, and any future stylistic-feedback tool).
