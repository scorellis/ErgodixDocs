# Phil-trained custom prose linter

- **Status**: parking-lot (Sprint 1+ when activated)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

## So that

A custom linter trained on the human editor's repeated corrections becomes a first-pass automatic editor — catching the things the editor consistently fixes (specific verb-tense patterns, comma habits, clichés the author falls into) so the human editor can focus on higher-level work.

## Value

Amortizes the editor's expertise into reusable tooling; reduces the editor's repetitive workload; demonstrates the AI-as-architectural-analyst principle in a concrete way that respects the AI-prose boundary (the linter *flags*; the human *decides*).

## Risk

Linter false-positives become noise that the author learns to ignore, defeating the purpose; over-fitting to one editor's idiosyncrasies may reduce portability when adding a second editor.

## Assumptions

The editor's review history (post-merge diffs over time) is sufficient training signal; flagging-not-fixing preserves the AI-prose boundary; per-editor and per-author training is feasible at the corpus scale.

## Tasks (when activated)

- [ ] Mine accepted editor patches from `git log` to extract recurring corrections.
- [ ] Build a rule-based first pass (regex / token-pattern matching) for high-confidence patterns.
- [ ] Layer ML or LLM-driven detection for fuzzier patterns (style consistency, tone drift).
- [ ] Wire as `ergodix lint` subcommand; integrate with `--developer` floater's pre-commit hooks.
- [ ] Per-author + per-editor training profiles in `settings/`.
