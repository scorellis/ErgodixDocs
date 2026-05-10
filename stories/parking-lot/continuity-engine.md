# Continuity-Engine — AI-assisted story-logic analysis suite

- **Status**: parking-lot (Sprint 1+ when activated)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.
- **Partially supersedes / consolidates**: Sprint 1 stories 1.1 (plotline tracking), 1.2 (plot-hole detection), and 1.5 (worldbuilding support). Decide at activation time whether to retire Sprint 1.1/1.2/1.5 or keep them as sub-stories.

## As / So that

As a writer, so that the author can ask focused, named questions about whether the *story* holds together (not whether the *prose* is good — that's Plot-Planner's job) — Does this timeline make sense? Where did this character disappear from chapter 4? What promise did chapter 1 make that I haven't paid off? — and get grounded, evidence-backed answers from an AI that has read the whole corpus, without that AI ever writing a word of prose.

## Value

This is the project's stated raison d'être ("AI as architectural co-author and continuity engine"); concretely-named tools turn vague "the AI helps you" into "I just ran timeline-continuity-analyzer on Compendium 2 and it flagged three conflicting season references"; respects the AI-prose boundary (every tool *flags* and *cites*, never edits); the named-tool surface makes the value teachable to other authors during distribution.

## Risk

Scope explosion — there are infinite "story-logic checks" you could imagine; the methodology behind each tool needs to be defensible (an AI saying "this is a plot hole" without grounded evidence is worse than no tool); cross-chapter context windows are expensive without smart retrieval; tool overlap with Plot-Planner needs clear boundaries (Plot-Planner = *prose mechanics*; Continuity-Engine = *story logic*); some tools depend on hierarchy decisions still in flux (multi-opus, sliced-repo collaboration).

## Assumptions

Per-chapter analysis with cross-chapter retrieval is tractable using the prompt-caching strategy from [scale-concerns](scale-concerns.md) §Z2; tools are best invoked via Claude Code's skill / slash-command surface (`.claude/skills/<name>/`) so they live close to the corpus repo, with `ergodix` subcommand mirrors for CI / scripting; an umbrella `continuity-engine` namespace separates these from `plot-planner` (craft) and from `sell-my-book` (marketing); evidence-citation is non-negotiable — every flag must point at the chapter / line that triggered it.

## Tools known so far (list grows when activated)

- **`timeline-continuity-analyzer`** — extracts every temporal anchor (dates, seasons, "three weeks later", character ages) and flags conflicts across the corpus.
- **`plot-hole-finder`** — surfaces internal logical contradictions (character knows X in ch.3 but acts surprised by X in ch.7; an event is described as "unprecedented" when ch.2 shows precedent).
- **`character-arc-tracker`** — extracts each character's appearances + decisions + emotional state; flags inconsistencies, abrupt shifts without setup, and disappearances.
- **`worldbuilding-consistency-checker`** — checks magic-system rules, geography, technology level, currency, languages — every named worldbuilding fact tracked across chapters.
- **`foreshadowing-tracker`** — pairs planted seeds (chekov's guns) with their payoffs; flags unresolved seeds and unsetup payoffs.
- **`promise-and-payoff-tracker`** — chapter-level: what did this chapter promise the reader, was it paid off later, by whom, and how cleanly?
- **`POV-leak-detector`** — tags POV per scene; flags information leaks (third-person-limited POV reveals knowledge the POV character couldn't have).
- **`name-disambiguator`** — flags same-named or near-same-named characters / places / objects that may confuse readers.
- **`relationship-graph-walker`** — who knows what about whom? Who has met whom? Tracks secrets, disclosures, alliances, betrayals, and surfaces "this character shouldn't know that yet" violations.
- **`death-and-resurrection-ledger`** — who died, who came back, intentional or continuity error?
- **`question-the-corpus`** — open-ended Q&A: "Why does Aria distrust the council?" — AI grounds the answer in citations; the answer is a *summary of evidence*, never a creative interpretation that wasn't in the prose.
- **+ more** when the story activates.

## Tasks (when activated)

- [ ] Decide implementation surface: Claude Code skills (`.claude/skills/<name>/`) vs `ergodix` subcommands vs both. Likely both — slash-commands for in-editor use, `ergodix` subcommand mirrors for CI/scripting/headless.
- [ ] Lock the namespace: `continuity-engine` (working name) — distinguishes from `plot-planner` (craft) and `sell-my-book` (marketing). Could collapse if architecturally cleaner.
- [ ] Settle on per-chapter analysis index + cross-chapter retrieval pattern — cross-references [scale-concerns](scale-concerns.md) §Z2; prompt-caching strategy is load-bearing.
- [ ] **Evidence-citation contract**: every flag points at chapter / paragraph / line. Non-negotiable. No "trust me, AI says so."
- [ ] Build the first three tools (`timeline-continuity-analyzer`, `plot-hole-finder`, `character-arc-tracker`) end-to-end — establish the cookie-cutter pattern, then enumerate the rest.
- [ ] AI-prose boundary enforcement: every tool emits flags / citations / artifacts in `_AI/` subfolders, *never* mutates chapter prose. The MCP server (parking-lot) inherits this constraint.
- [ ] Documentation page mapping each tool's question / inputs / outputs / methodology. The methodology is the moat — vague "I asked the AI" beats nothing, but a defensible methodology is what makes Continuity-Engine valuable.

## Cross-references

- [ADR 0013](../../adrs/0013-ai-permitted-actions-boundary.md): AI permitted-actions boundary.
- [scale-concerns](scale-concerns.md) §Z2: corpus volume / prompt caching strategy.
- [active/ergodix-index](../active/ergodix-index.md): the map this engine reads to decide which chapters to re-scan.
