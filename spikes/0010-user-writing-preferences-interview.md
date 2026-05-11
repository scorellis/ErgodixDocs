# Spike 0010: UserWritingPreferencesInterview — onboarding interview design

- **Date filed**: 2026-05-09
- **Sprint story**: Parking lot — onboarding flow for new authors/editors. Activates when a Plot-Planner / Continuity-Engine tool needs author preference data.
- **ADRs produced**: TBD (pending resolution).
- **Touches**: [Plot-Planner story](../stories/SprintLog.md#story--plot-planner-ai-assisted-authoring-analysis-tool-suite-sprint-2-when-activated), [Wordsmith Toolbox story](../stories/parking-lot/wordsmith-toolbox.md), [ADR 0005](../adrs/0005-roles-as-floaters-and-opus-naming.md) (floater/persona model).
- **Status**: Open question — design surface enumerated, not yet resolved.

## Question

When a new author or editor first runs ErgodixDocs against a corpus, the AI has no information about their voice, their craft preferences, or what kind of feedback they want. A generic LLM dropped into a manuscript will produce generic feedback — frequently *wrong* feedback for the author's intent (telling a literary author their sentences are too long, telling an ergodic author their typography is "distracting").

A short, structured onboarding interview captures the author's preferences once, stores them next to the corpus, and informs every Plot-Planner / Continuity-Engine tool downstream.

The questions to resolve:

1. **What does the interview ask?** Categories, depth, total length.
2. **When does it run?** First cantilever after a corpus is configured? On first use of a Plot-Planner tool? Re-runnable on demand?
3. **Where do answers live?** `local_config.py`, `_AI/preferences.toml` next to the corpus, or somewhere else in the settings cascade?
4. **What's the surface?** CLI prompt loop, markdown form the user fills out, GUI later?
5. **Per-author or per-corpus?** A writer with multiple opera (different genres) may want different preferences per opus. An editor reviewing multiple authors needs per-author overrides.
6. **What does the AI *do* with the answers?** Stuffed into every prompt? Used to gate which tools surface? Encoded as a rubric the AI references on demand?

## Discussion

### 1. Question categories

A first cut at categories the interview must cover:

- **Voice & POV**: first / second / third / omniscient / multi-POV; present / past tense; tense shifts allowed.
- **Genre & tradition**: literary / genre / experimental / ergodic; specific traditions (cyberpunk, slipstream, hard SF, lyric novel, etc.).
- **Influences & dis-influences**: writers the author wants the AI to compare them *to* and *against* ("don't suggest I'm sounding like Stephen King").
- **Process**: planner vs. pantser; where they get stuck; what kind of feedback they want at draft stage vs. revision stage.
- **Editorial preferences**: line-edit vs. structural; harsh vs. gentle; copy-edit-style vs. craft-style; CriticMarkup density tolerance.
- **Ergodic-specific** (if writing ergodic): do they use rotation / mirror / footnote-as-narrative / spiral / collage typography? Should the AI flag *uses* of these or stay silent because the author knows what they're doing?
- **Anti-patterns**: things the author specifically *doesn't* want flagged ("don't tell me my Latin needs translation"; "don't tell me adverbs are weak").
- **AI boundaries (per-corpus)**: where can the AI opine vs. stay silent? Already covered globally by the AI-prose boundary in CLAUDE.md, but per-author preferences (e.g. "don't comment on dialogue at all — that's my strength") refine it.
- **Scoring weights**: of the Plot-Planner dimensions (pacing, originality, repetition, tone, dynamics, Fibonacci peaks, show-vs-tell, dialogue ratio), which matter most to *this* author? Default: equal weight; author may want pacing-heavy or tone-heavy weighting.

### 2. When the interview runs

**Options:**
- **(a) After cantilever's first successful install**, before any Plot-Planner tool runs. Pros: captures preferences before the AI ever produces output. Cons: front-loads UX onto an installer that's already long; user may not be ready to think about voice when they just want to render a chapter.
- **(b) On first use of any Plot-Planner / Continuity-Engine tool.** Pros: just-in-time; the user is already engaging with AI feedback. Cons: blocks the first tool run with a 5-minute interview; might frustrate.
- **(c) Optional — `ergodix interview` subcommand the user runs explicitly.** Pros: zero friction for users who don't want it; preferences gracefully default. Cons: most users won't run it; tools degrade to generic-LLM mode.
- **(d) Hybrid: short version inline (3 questions) on first tool run, full version available via `ergodix interview` when the user is ready to deepen.**

Lean toward **(d)** — minimum viable preferences captured cheaply, full depth available on demand.

### 3. Where answers live

Three candidate locations:

- **`local_config.py`** — per-machine. Wrong: preferences are per-author + per-corpus, not per-machine. A writer using multiple machines wants the same preferences everywhere.
- **`_AI/preferences.toml` at the corpus root.** Right: lives next to the corpus, syncs with the corpus repo (when collaborators share preferences), regenerated on `ergodix interview`. Matches the `_AI/` convention for AI-side artifacts already in CLAUDE.md.
- **`settings/floaters/writer.toml`** — wrong scope: floater settings are per-repo defaults shared across all users of this ErgodixDocs install. Author preferences are per-corpus.

Lean toward **`_AI/preferences.toml`** at the corpus root. Cross-references the future `_AI/ergodix.map` (corpus content index) parking-lot story for sibling files.

### 4. Surface

Initial v1: CLI prompt loop using the existing `prompt_fn` (per ADR 0012). Hidden/visible toggles where appropriate (most preference answers are non-secret). Editor-mode (`ergodix interview --editor`) variant could ask different questions.

Later: a markdown form the user fills out and `ergodix interview --import` parses. Lower friction for authors who'd rather type-think than answer-prompt.

### 5. Per-author or per-corpus

Both, layered:

- Per-corpus: `_AI/preferences.toml` lives in the corpus repo, applies to that opus.
- Per-author override: when the corpus is shared (writer + editor flow per ADR 0006), each contributor's slice repo can carry an `_AI/preferences.<author>.toml` that overrides the shared file when *they* run tools.

Settles cleanly with the existing slice-repo model.

### 6. What the AI does with answers

**Three competing patterns:**
- **System-prompt stuffing** — every Plot-Planner tool's prompt prepends the preferences. Simple, expensive (tokens per call), but every tool gets full context.
- **Tool-gated** — preferences decide *which* tools surface. (Author who hates adverb-flagging never sees adverb-flag output.) Cheap, but coarse-grained.
- **Rubric-referenced** — preferences live as a structured rubric the AI calls out to during scoring. The author's "don't comment on dialogue" becomes a `dialogue_commentary: false` field the writing-score tool reads and silently respects.

Lean toward a **mix**: rubric-referenced for structured fields (scoring weights, anti-patterns), system-prompt stuffing for narrative fields (voice, influences). Token cost is manageable with prompt caching.

### Open considerations

- Should the interview *itself* be an AI-driven Skill? (e.g. follow-up questions when an answer is short, clarifying probes.) Pros: deeper data capture. Cons: a non-deterministic interview where two users get different question sets is hard to evolve and document.
- How does the interview handle authors writing in non-English? The AI's stylistic feedback assumptions are deeply English-centric. Worth flagging as an explicit answer up-front.
- Is there an interview-of-record format that survives the AI generation that built it? (TOML/YAML schema + version field, so the rubric can evolve without breaking old preferences files.)

## Resolution

Pending. Spike captures the design surface; resolution lands as an ADR when the parking-lot story activates (probably alongside the first Plot-Planner tool, when there's a real consumer for the preferences data).
