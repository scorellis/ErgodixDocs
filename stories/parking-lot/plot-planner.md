# Plot-Planner — AI-assisted authoring-analysis tool suite

- **Status**: parking-lot (Sprint 2+ when activated)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

## As / So that

As a writer, so that the author has a cadre of focused, narrow-purpose AI tools that surface specific craft issues across a chapter or the whole corpus — pacing, originality, repetition, tone — without conflating them into one monolithic "review" that's hard to act on.

## Value

Each tool answers a single, named question and produces a focused report; the author iterates against one craft dimension at a time rather than drowning in a generic "make this better" pass; "hook to get authors using this tool" — a memorable, action-named tool surface (writing-score, copyright-quest, duplicate-smasher, PC-placator) is the thing that builds adoption habits; respects the AI-prose boundary because every tool *flags* / *scores*, never edits prose.

## Risk

Scope creep — 20+ tools is a lot of surface to design, document, and maintain; without a strong umbrella concept the suite fragments; tool overlap (e.g. duplicate-smasher vs. writing-score's repetition signal) creates user confusion; tool quality drops if each tool is a thin LLM wrapper without a real scoring methodology behind it.

## Assumptions

The author has a defined scoring methodology (Fibonacci peaks, dynamics, show-vs-tell, etc.) that can be encoded; per-chapter analysis with cross-chapter context is tractable using the prompt-caching strategy from [scale-concerns](scale-concerns.md) §Z2; tools are best invoked via Claude Code's skill/slash-command surface (`.claude/skills/` or `.claude/commands/`) so they live close to the corpus repo, with the option of also surfacing them as `ergodix` subcommands; an umbrella "plot-planner" name is the right grouping primitive.

## Tools known so far (more TBD)

- **`writing-score`** — scores a chapter (or the whole corpus) using the author's methodology; flags pacing, dynamics, show-vs-tell, Fibonacci peaks, weak verbs, dialogue-vs-narration ratio, etc.
- **`copyright-quest`** — searches across known works (corpus + author's prior drafts + a curated public-domain index?) to flag accidental copy/paste, residual placeholder text, or inadvertent close-paraphrase that could read as infringement.
- **`duplicate-smasher`** — finds repeated patterns: copy-paste duplicates, excessive same-word/same-phrase clusters, structural repetition across chapters.
- **`PC-placator`** — detects the full tone spectrum, from hate-speech / triggering / incendiary / rage-baiting at one end through edgy / raw / extreme, past kind / saccharine / boring / explainery, to raunchy / sensual / heart-pounding-action / page-turning / re-read-inducing at the other. Reports where each chapter sits and where the author may want to push or pull.
- **+ ~16 more** to be enumerated when the story activates.

## Tasks (when activated)

- [ ] Decide implementation surface: Claude Code skills/commands (`.claude/skills/<name>/`) vs. `ergodix` subcommands vs. both. Likely both — slash-commands for in-editor use, `ergodix` subcommand mirrors for CI/scripts.
- [ ] Name the umbrella concept (`plot-planner` is the working name; could be `authoring-suite`, `craft-tools`, etc.).
- [ ] **Dependency**: [wordsmith-toolbox](wordsmith-toolbox.md). `writing-score`, `PC-placator`, and most stylistic-feedback tools reference rhetoric primitives by id; the Wordsmith Toolbox Skill provides the canonical reference. Sequence: ship Wordsmith Toolbox before (or alongside) the first stylistic-feedback tool.
- [ ] **Dependency**: [Spike 0010 — UserWritingPreferencesInterview](../../spikes/0010-user-writing-preferences-interview.md). Tool output is shaped by author preferences (scoring weights, anti-patterns, AI-boundary refinements) — the interview captures these once and tools reference them every run.
- [ ] Encode the author's scoring methodology in a stable, testable form (probably a TOML/YAML rubric).
- [ ] Settle on per-chapter analysis index + cross-chapter retrieval pattern — cross-references [scale-concerns](scale-concerns.md) §Z2.
- [ ] Build the first three tools (`writing-score`, `duplicate-smasher`, `PC-placator`) end-to-end — establish the cookie-cutter pattern, then enumerate the remaining ~16.
- [ ] Decide adoption hook: which tool is the "first one a new author tries" that demonstrates value in <5 minutes?
- [ ] Documentation page mapping each tool's question / inputs / outputs / scoring methodology.

## Cross-references

- [wordsmith-toolbox](wordsmith-toolbox.md): rhetoric primitives used by stylistic-feedback tools.
- [Spike 0010](../../spikes/0010-user-writing-preferences-interview.md): author preference capture.
- [continuity-engine](continuity-engine.md): sibling suite (story logic, not craft).
