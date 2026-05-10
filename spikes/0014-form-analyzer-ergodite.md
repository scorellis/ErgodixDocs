# Spike 0014: `form-analyzer` ergodite — readability + rhetorical eloquence + Fibonacci structure

- **Date filed**: 2026-05-10
- **Sprint story**: Parking-lot until [Spike 0013](0013-style-sentinel-and-certificate.md)'s ergodite registry ships (ADR-X1). This spike is the first concrete instance of the ergodite plugin contract.
- **ADRs to produce**: none of its own — fits inside ADR-X1's plugin contract once that lands.
- **Touches**: [Spike 0013](0013-style-sentinel-and-certificate.md) (ergodite registry, integrity manifest), [Devil's Toolbox parking-lot story](../stories/SprintLog.md) (rhetoric primitives the eloquence sub-check references), [Spike 0010](0010-user-writing-preferences-interview.md) (preference-gated structural analysis).
- **Status**: Open — design surface enumerated, not yet resolved.

## Question

A single ergodite that grades the *form* of a chapter on three orthogonal axes:

1. **Readability / grade level.** What grade level (US K-12 + college) is the prose pitched at? Is the author writing too low or too high for the intended audience? Mostly a settled science — public formulas exist, no need to invent.
2. **Rhetorical eloquence.** Density of recognized rhetorical figures (anaphora, polysyndeton, chiasmus, etc.) per paragraph. Pulls primitive definitions from the [Devil's Toolbox](../stories/SprintLog.md) reference; the form-analyzer is one of its first concrete consumers.
3. **Fibonacci / golden-mean structural arc.** Does the chapter's tension/intensity curve follow the author's preferred narrative shape? This corresponds to the user's "Fibonacci writing prompt" — the prompt itself isn't yet captured in-tree (flagged in Spike 0013 cross-references); resolving that is a precondition.

The form-analyzer wraps these as a single `ErgoditeReport` so the writer / editor / publisher can see one combined readout per chapter rather than three separate runs.

## Discussion

### A. Readability / grade level — public formulas, no reinvention

Decades of public-domain formulas exist; pick a small portfolio rather than relying on any single one (each has known biases):

| Formula | What it weights | Notes |
|---|---|---|
| **Flesch-Kincaid Grade Level** | sentence length + syllables-per-word | most familiar; used in MS Word; correlates with US grade level |
| **Flesch Reading Ease** | inverse of FK Grade Level | 100 = very easy, 0 = extremely difficult |
| **Gunning Fog Index** | sentence length + percentage of "complex" (3+ syllable) words | similar grade-level output; fog penalizes academese |
| **SMOG Index** | polysyllable count over 30 sentences | designed for medical/health-info readability |
| **Coleman-Liau Index** | character count (no syllable counting) | lighter compute; useful as a cross-check against syllable-based formulas |
| **Automated Readability Index (ARI)** | character count + sentence length | similar to Coleman-Liau |
| **Dale-Chall** | percentage of words *not* in a fixed 3000-word "easy" list | grade-level interpretation; the easy-list is the load-bearing artifact |
| **Spache** | targets younger readers (K-4) specifically | useful only if education-mode targets primary school |

**Lean.** Ship a portfolio of all 7 (running them all is microseconds per chapter); report each plus a "consensus grade" (e.g. median across formulas with ARI/Coleman-Liau weighted lower because they're crude). The Python library `textstat` bundles all of these — single dependency, no implementation work for v1. (Look at it before deciding whether to inline our own; a ~5KB pure-Python module worth pulling in vs. inlining the formulas ourselves.)

**Proprietary alternatives we are NOT pulling in:**
- **Lexile Framework** (MetaMetrics) — most widely deployed in US K-12 schools but proprietary; would require a license. Treat as parking-lot for education-mode V2 if a school deployment requires it.
- **ATOS** (Renaissance Learning) — same posture.

**Open questions.**
- Output format: one number, a portfolio of numbers, or a band ("middle school," "early high school," "college lower-division")? Lean: portfolio + consensus grade + band, all in the report.
- How does this interact with the author's preferred reading level? Spike 0010's interview should ask for a target band; the form-analyzer flags as "off-target" only when the prose drifts outside the author's explicit target — not on every "your prose is at grade 9 but the formulas average 11" mismatch.

### B. Rhetorical eloquence — Devil's Toolbox dependency

The eloquence sub-check counts recognized rhetorical figures per paragraph and reports density (figures-per-100-words) plus a list of detected exemplars. It does *not* score "good vs. bad rhetoric" — that's an author-preference call (some authors deliberately avoid classical figures; others lean on them).

**Detection mechanism.** Two layers:
1. **Regex / pattern primitives** — anaphora ("It was X. It was Y. It was Z."), polysyndeton (consecutive coordinating conjunctions), tricolon (three parallel clauses), epistrophe, alliteration density, etc. These are cheap and deterministic. Devil's Toolbox provides the canonical list with classifier hints.
2. **LLM classifier (optional, behind a setting)** — for harder figures (chiasmus, antimetabole, parallelism, irony) where regex isn't enough. Gated behind `ergodix_use_llm_for_rhetoric: true` in settings; off by default to keep runs deterministic + free.

**Output shape per paragraph:**
```yaml
- paragraph: 3
  word_count: 87
  figures_detected:
    - {name: anaphora, count: 1, exemplar: "It was the best..."}
    - {name: polysyndeton, count: 1, exemplar: "and a sigh and a stillness and a..."}
  density: 2.30  # figures per 100 words
```

**Open questions.**
- What's the v1 minimum viable list of detected figures? Lean: anaphora, epistrophe, polysyndeton, asyndeton, tricolon, alliteration, anastrophe. ~7 covers most prose-fiction rhetoric without over-engineering.
- How does the form-analyzer call into the Devil's Toolbox reference? The toolbox is parking-lot too. For v1, inline a minimal reference inside form-analyzer; refactor to consume the toolbox once it ships.

### C. Fibonacci / golden-mean structural arc — needs the author's prompt

The user references a "Fibonacci writing prompt" they give to ChatGPT — a chapter-arc framework based on Fibonacci proportions (e.g. tension peaks at the 0.618 mark of the chapter, climax follows the golden-ratio split). The prompt itself isn't captured in the repo yet.

**Precondition.** Get the Fibonacci prompt into `docs/fibonacci-writing-prompt.md` (or wherever appropriate — already flagged as TBD in Spike 0013's cross-references). Without it, this sub-check can't be specified.

**Shape (placeholder until the prompt lands):**
- Per-paragraph "intensity" or "tension" score — how to compute? Options: word-density heuristics (action verbs + short sentences = high), sentiment-analysis valence, LLM-classified intensity.
- Compare the actual intensity curve to the target Fibonacci-derived curve.
- Report deviations: where the curve under- or over-shoots.

**Open questions.**
- Is the Fibonacci framework universal across all chapters, or per-chapter-type? (Climax chapter has a different target curve than a quiet character-development chapter.)
- Tunable: the author may want to disable this check for non-narrative chapters (prefaces, appendices, glossaries).

### D. Single-ergodite vs. three ergodites

We could ship the three sub-checks as three separate ergodites (`grade-level`, `rhetorical-eloquence`, `fibonacci-arc`). Bundling them as one `form-analyzer` has these tradeoffs:

| | Single `form-analyzer` (lean) | Three separate ergodites |
|---|---|---|
| **Single readout** | one report per chapter, easy to surface in UI | three separate reports to merge |
| **Composition** | author can't disable just one sub-check | each runs / disables independently |
| **Settings cascade** | one set of options to plumb | three sets |
| **Test surface** | bigger module per ergodite | smaller modules, cleaner tests |
| **Future split** | trivially refactorable to three | already separate, no refactor |

**Lean.** Single `form-analyzer` ergodite, with each sub-check toggled in settings (`form_analyzer.grade_level: on`, `form_analyzer.eloquence: on`, `form_analyzer.fibonacci: off`). One readout, but configurable.

### E. Output contract

Per Spike 0013 §C.1, the ergodite returns an `ErgoditeReport`. For form-analyzer, the per-chapter report shape:

```yaml
generator: "ergodix 1.x.y form-analyzer 1.0"
chapter: "Tapestry of the Mind/Book 1/Chapter 3.md"
chapter_hash: "abc123..."
sub_checks:
  grade_level:
    flesch_kincaid: 9.2
    flesch_ease: 62.4
    gunning_fog: 11.1
    smog: 10.4
    coleman_liau: 9.8
    ari: 9.5
    dale_chall: 7.8
    consensus_grade: 9.5
    consensus_band: "high school - lower"
    target_band_from_interview: "middle school - upper"
    on_target: false
    drift: 1.0
  eloquence:
    paragraph_density:
      - {paragraph: 1, density: 0.0}
      - {paragraph: 2, density: 1.15}
      # ... per-paragraph
    detected_figures:
      anaphora: 3
      polysyndeton: 1
      tricolon: 4
    overall_density: 1.62
  fibonacci:
    target_curve_label: "tension-1.618"
    actual_intensity_per_paragraph: [0.2, 0.3, 0.4, ...]
    deviation_score: 0.08  # lower = closer to target
    flagged_paragraphs: [12, 17]  # where actual diverges from target by > threshold
```

The author's writing-preferences interview (Spike 0010) supplies `target_band_from_interview` and the Fibonacci preferences. Without those, those fields are `null` and the corresponding `on_target` / `flagged_paragraphs` are not computed.

## Open questions

1. **`textstat` dependency**: pull it in vs. inline our own formulas? Lean: pull in (small, public-domain math, well-tested); revisit if footprint matters.
2. **LLM gate for hard figures**: default off vs. default on? Lean: off (deterministic, free); the author can opt in via settings.
3. **Fibonacci prompt capture**: who writes `docs/fibonacci-writing-prompt.md`? The author (Scott). Action item flagged elsewhere; this spike is blocked on it.
4. **Education-mode target band**: when education-mode lands (Spike 0013 §E), the target grade level becomes a *required* setting from the school / teacher rather than the optional interview field. The form-analyzer needs to handle both shapes.
5. **Devil's Toolbox readiness**: does form-analyzer ship before, after, or alongside the Devil's Toolbox reference? Lean: form-analyzer ships with an *inline minimal* rhetoric reference (the 7 figures listed in §B), and the Devil's Toolbox refactor extracts them later.

## Cross-references

- [Spike 0013 — style sentinel + ergodite registry](0013-style-sentinel-and-certificate.md): defines the ergodite plugin contract this spike instantiates.
- [Devil's Toolbox parking-lot story](../stories/SprintLog.md#story--devils-toolbox-foundational-rhetoric-reference-skill-sprint-2-when-activated): canonical rhetoric reference the eloquence sub-check will eventually consume.
- [Spike 0010 — user writing preferences interview](0010-user-writing-preferences-interview.md): supplies target reading band + Fibonacci preferences.
- Fibonacci writing prompt — TBD; not yet captured in-tree (Spike 0013's cross-references flag this as a precondition for the climax-detection / arc-analysis work).

## Why we're not implementing today

Same gating as Spike 0013: the ergodite registry (ADR-X1, post-Spike-0013) hasn't shipped yet, and the migrate arc is mid-flight. This spike captures the design surface for a representative ergodite so future readers can see how the registry is meant to be exercised. ADRs land first; implementation lands behind tests after.
