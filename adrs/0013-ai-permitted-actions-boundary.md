# ADR 0013: AI permitted-actions boundary

- **Status**: Accepted
- **Date**: 2026-05-09
- **Spike**: None — direct architectural decision based on author's clear specification.
- **Touches**: [CLAUDE.md](../CLAUDE.md) principle #2 (the "AI-prose boundary" tightens, narrows, and gains a small mechanical-edits exception). [Plot-Planner story](../stories/SprintLog.md#story--plot-planner-ai-assisted-authoring-analysis-tool-suite-sprint-2-when-activated). [Continuity-Engine story](../stories/SprintLog.md#story--continuity-engine-ai-assisted-story-logic-analysis-suite-sprint-1-when-activated). [Wordsmith Toolbox story](../stories/parking-lot/wordsmith-toolbox.md). [Spike 0010 — UserWritingPreferencesInterview](../spikes/0010-user-writing-preferences-interview.md). Future MCP server story.

## Context

CLAUDE.md principle #2 (the **AI-prose boundary**) has been the load-bearing identity statement for the project since [ADR 0005](0005-roles-as-floaters-and-opus-naming.md). It says, in short: *the AI never edits chapter prose*.

That has worked as a north star, but as the project approaches the first real Plot-Planner / Continuity-Engine / Skill-based tools, the boundary needs sharper edges:

- **Mechanical corrections** (punctuation, spelling) are narrow, deterministic, and not creative work. Forcing the AI to "flag, never fix" for a missing period creates editor friction and produces no creative drift. The blanket prohibition was correct as a default but is too broad for the genuine mechanical case.
- **Plot work** — generating plotlines, suggesting story beats *as if* the AI were authoring — is *not* covered crisply by "never edits prose." A future tool that produces a plot outline next to the chapter wouldn't have *edited* prose, but it would still violate the project's identity. The boundary needs to extend to creative-territory that isn't strictly prose mutation.
- **Stylistic critique** is permitted, but only when it's grounded in the author's own preferences. A generic LLM dropping `weak verb` flags on every passive construction is exactly the kind of generic-AI failure mode the project exists to avoid. Critique must be gated to the author's interview-captured preferences (see [Spike 0010](../spikes/0010-user-writing-preferences-interview.md)).
- **Suggestion vs. application** — when the AI offers craft advice (e.g., "the best plot lines follow rules a, b, c, with n permutations"), that's offered as *information for the author*, never as *changes applied to the corpus*. The author is always at the keyboard for creative work.

Without an explicit lock, every Skill, every tool, and every future agent surface (MCP server, in-app editor, BYO-key flows) re-derives "what am I allowed to do" from the broader CLAUDE.md principle and drifts. This ADR pins the answer.

## Decision

### Permitted on-corpus AI actions (closed list)

The AI may perform exactly the following four actions on the author's corpus:

1. **Mechanical correction.**
   - Scope: punctuation (missing periods, mismatched quotes, em-dash hygiene, smart-quote normalization), spelling (with respect to the author's preference language and any per-corpus dictionary).
   - Implementation note: where possible, this responsibility lives in the **editor** (VS Code with LTeX, etc.) rather than in an ErgodixDocs Skill. ErgodixDocs Skills only invoke mechanical corrections when the editor surface is unavailable (CI runs, headless smokes).
   - Boundary: this exception is **narrow**. Anything ambiguous between mechanical and creative — e.g., comma splice repair that changes meaning, sentence-fragment "corrections" that the author intended as style — defaults back to flag-not-fix.

2. **Chapter scoring.**
   - Scope: running the author's encoded scoring methodology (from the [Plot-Planner story](../stories/SprintLog.md#story--plot-planner-ai-assisted-authoring-analysis-tool-suite-sprint-2-when-activated)) over a chapter or the corpus and producing a structured report.
   - Output is *report data* (TOML/JSON/markdown), never mutations to the chapter.
   - The methodology must be encoded as a stable rubric (see Plot-Planner activation tasks); ad-hoc "score this however the model thinks best" is **not** in scope.

3. **Structural analysis aligned to the author's interview.**
   - Scope: continuity checks, plot-hole detection, character-arc reports, timeline reconciliation, worldbuilding consistency — the kind of output the [Continuity-Engine story](../stories/SprintLog.md#story--continuity-engine-ai-assisted-story-logic-analysis-suite-sprint-1-when-activated) describes.
   - **Hard gate**: every analysis tool reads the author's preferences from `_AI/preferences.toml` (per Spike 0010) and respects them as constraints. An author who has said "don't comment on dialogue" gets no dialogue analysis output, even if the underlying model has opinions.
   - Output is *report data*, never mutations.

4. **Suggestion-only craft advice.**
   - Scope: the AI may *offer* — at the author's request — boilerplate or methodology-grounded advice on craft questions ("what are the canonical structures for a B-plot?", "what does the Wordsmith Toolbox say about anaphora?"). It may *show* the author canonical patterns, frameworks, or comparable examples *from outside the corpus*.
   - The advice is *displayed* to the author; it is **never applied** to the corpus by the AI. The author works through it at the keyboard.
   - This includes plot-craft advice. The AI may explain plot structures, name them, illustrate with non-corpus examples; it may not generate plot content for the corpus and stage it as the author's work.

### Explicitly barred

Anything not on the closed list is barred. Specifically, the AI **must not**:

- **Plot for the author.** No autonomous generation of plotlines, story beats, scene outlines, or character introductions destined for the corpus. Even when explicitly asked, the response is craft-advice (action #4), not corpus content.
- **Substitute prose creatively.** No "let me rewrite this paragraph for you," no "here's a better opening," no AI-authored prose alternatives even when offered as suggestions. (This is the strongest position — even a *suggestion* of creative substitution risks the AI's voice contaminating the author's.)
- **Override the author's voice or tone.** No tone-normalization passes, no "your sentences are too long, here are shorter ones," no genre-conforming rewrites.
- **Inject themes, characters, or worldbuilding** the author has not already authored. The AI works *from* the corpus, never *into* it.
- **Apply changes autonomously to the corpus** under any circumstance — including mechanical-correction action #1, which (when invoked) operates on diffs the author reviews and accepts, not silent mutation.
- **Ignore author preferences from Spike 0010's interview.** Preferences are a hard gate, not a suggestion to consider.

### Consequences

- **CLAUDE.md principle #2** is updated to point at this ADR as the source of truth. The principle's tagline shifts from "the AI never edits chapter prose" to "the AI's permitted actions on the corpus are constrained per ADR 0013."
- **Every Skill** (`.claude/skills/<name>/`) must declare which of the four permitted actions it performs in its skill manifest. A Skill that performs none of them is not a corpus-touching Skill (e.g., the Wordsmith Toolbox is a *reference Skill* — it produces no corpus output, just structured data other tools consume).
- **Plot-Planner / Continuity-Engine tools** must publish their output as report data (TOML/markdown/JSON), never as edits. Tool implementers can lean on this guarantee in API design.
- **Mechanical-correction tooling** lives primarily in the editor (LTeX, VS Code spell-check) per CLAUDE.md's existing tool-chain. ErgodixDocs Skills that perform mechanical corrections (rare; mostly headless / CI cases) must produce *patches the author reviews*, not silent edits.
- **The MCP server** (when it exists, per the [parking-lot story](../stories/SprintLog.md#story--mcp-server--ai-user-persona-sprint-2-when-activated)) must enforce this boundary at the tool-registration layer: tools registered with the MCP server declare their permitted-action category, and the server refuses tool calls that exceed it.
- **The author interview** ([Spike 0010](../spikes/0010-user-writing-preferences-interview.md)) becomes load-bearing: structural-analysis tools (action #3) require interview output to gate their critique. Tools running before the interview is complete must either degrade gracefully (no output) or block on the interview.
- **Suggestion-only semantics need a UI distinction.** Output from action #4 (craft advice) must be visually / structurally distinguishable from output from actions #2 / #3 (analysis reports), so the author never confuses "AI is showing me a framework" with "AI has analyzed my work."

### Alternatives considered

- **Keep the existing blanket "AI never edits prose."** Rejected. Mechanical-correction tooling lives elsewhere in the project's plans (LTeX, editor extensions); the blanket prohibition forced these into "flag-only" workarounds that the editor ecosystem doesn't support cleanly. Keeping the rule blanket also leaves "no plot work" implicit, which weakens it.
- **Loosen to "AI may do anything the author hasn't specifically protected."** Rejected. Wrong default — the AI-prose boundary is a *project identity statement*, not a feature flag. The default must be tight.
- **Per-Skill capability declarations only, no central ADR.** Rejected. Without a central source of truth, capability declarations drift; two Skills with identical surface end up with different permissions. The ADR provides the closed list; Skills declare which slot they fill.
- **Three permitted actions instead of four (drop #4 suggestion-only craft advice).** Rejected. Action #4 is the cooperative case the project should support — an author asking "what are common ways to structure a B-plot?" should get a real answer, not a refusal. The discipline is in the *suggestion vs. application* line, not in refusing to discuss craft.
- **Five+ permitted actions (e.g., adding "in-line continuity flagging during writing").** Rejected for v1. Real-time inline tools blur the suggestion/application line and risk training the author into AI-shaped sentences. Re-evaluate for v2 when there's real evidence about how authors use the tool.

## Open questions deferred

- **What does "narrow" mean precisely for mechanical correction?** Em-dash insertion: yes. Comma-splice repair where meaning is preserved: probably yes. Sentence-fragment "fix" where the author intended the fragment: no. The boundary needs concrete examples in the implementing Skill's documentation; this ADR does not enumerate them, since the right venue is the editor / Skill that performs the corrections.
- **How is "preferences must be respected as a hard gate" enforced at runtime?** Probably the structural-analysis Skill loads `_AI/preferences.toml` at startup and refuses to run if it's missing. That implementation detail is for the Skill story, not this ADR.
- **What's the user-facing language when a Skill refuses an out-of-scope request?** "ErgodixDocs is configured not to plot for you. The author drives the map." or similar — needs UX design when the first Skill ships. This ADR pins the principle, not the wording.
