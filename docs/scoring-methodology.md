# Author Scoring Methodology

Author-curated rubric for evaluating chapters of Overmorrow / Tapestry on
the dimensions that matter to Scott — tension arcs, eloquence, narrative
geometry, voice, and stylistic risk. This is the source rubric the future
Plot-Planner / writing-score / form-analyzer tools encode.

The methodology lives in **two parallel parts**:

| Part | Title | Shape | Primary use |
|---|---|---|---|
| **Part 1** | Overmorrow Writing Analysis Guide | Discursive, example-rich | Grounding feedback in author voice + live-corpus examples |
| **Part 2** | Ten Measures of Literary Quality | Tabular, 1–10 rubric | Numerical contract for automated scoring tools |

Part 1 carries voice and examples; Part 2 carries the contract.

**Stable contract**: each dimension (Part 1) and each measure (Part 2) has
an immutable `id` (kebab-case). Tools reference by id, never by display
name. Display names are free to evolve; ids are not.

**Status**: source material, author-authored. Voice retained verbatim;
structure / ids / scoring-scale tables added for tooling.

---

## Part 1 — Overmorrow Writing Analysis Guide

Each dimension carries: an immutable `id`, a definition, the
checks/checkpoints, an example from the live corpus, and (where Scott
specified one) a 1–10 rating scale.

### Dimensions at a glance

| id | Dimension | Scale |
|---|---|---|
| `tension-arc` | Suspense / Tension Arc | 1 (flat) → 10 (riveting) |
| `show-vs-tell` | Show vs Tell Ratio | Target 70–80% show / 20–30% tell |
| `eloquence` | Eloquence | 1 (functional) → 10 (lyrical) |
| `narrative-geometry` | Narrative Geometry | (no scale; structural diagnostic) |
| `engagement-voice` | Engagement / Voice | 1 (generic) → 10 (vivid and unmistakable) |
| `continuity-lore` | Continuity & Lore Depth | (no scale; integration check) |
| `perspective-temporal` | Perspective & Temporal Play | (no scale; flow diagnostic) |
| `structural-innovation` | Structural Innovation | (no scale; presence/absence) |
| `character-complexity` | Character Complexity | (no scale; depth check) |
| `originality-risk` | Originality & Risk-Taking | (no scale; presence/absence) |

### 1. `tension-arc` — Suspense / Tension Arc

- **Definition**: How well the chapter builds and maintains tension —
  narrative propulsion, uncertainty, anticipation.
- **Checks**:
  - **Golden Mean Alignment**: Does the climax (θ point) occur near the
    Fibonacci ideal (around 61.8%)?
  - **Cliffhanger Check**: Does the chapter end in a way that encourages
    continued reading?
- **Example**: In "Depuis l'époque," the tension hinge appears to be the
  φ-narrative itself, surfacing around the golden-ratio mark as the memory
  layers snap into place — the reader realizes the narrative is folding.
- **Rating Scale**: **1 (flat)** to **10 (riveting)**.

### 2. `show-vs-tell` — Show vs Tell Ratio

- **Definition**: Showing involves action, dialogue, sensory detail, and
  inference; telling includes exposition or direct internal summary.
- **Ideal Ratio**: **70–80% showing**, 20–30% telling.
- **Checkpoints**:
  - Does the narrative immerse the reader in the moment?
  - Is internal exposition overused?
- **Tool used**: Quantitative ratio via tagged sections.
- **Example (show)**:
  > "A human shaped body, wrapped like a corpse for burial at void. Only
  > it's not dead."
- **Example (tell)**:
  > "Jacob's Ladder was missing its top Rung."

### 3. `eloquence` — Eloquence

- **Definition**: Use of rhetorical devices, layered prose, and poetic
  wordplay without losing clarity or flow.
- **Rhetorical Devices Checklist** *(cross-ref [devils-toolbox-reference.md](devils-toolbox-reference.md) for full catalog)*:

  | Device id | Author example |
  |---|---|
  | `alliteration-general` | "silvered stitch slipped silently." |
  | `alliteration-consonance` | "corpse for burial at void." |
  | `alliteration-assonance` | "seamingly seamless." |
  | `alliteration-symmetrical` | "shimmering wefton fabric… fabric of shimmering wefton." |
  | `anaphora` | "I tried. I failed. I tried again." |
  | `anadiplosis` | "She was fast. Fast enough to break orbit." |
  | `aposiopesis` | "If I ever see him again, I swear I'll—" |
  | `antithesis` | "A monkey's bars without the monkey." |
  | `polyptoton` | "He dreamed of dreams that dreamed back." |
  | `merism` | "stars and moons and rings and rust." |
  | `parataxis` | "She jumped. He ran. I watched." |
  | `hypotaxis` | "Although she jumped, he still ran, while I only watched." |
  | `synaesthesia` | "a silence so thick you could taste it." |
  | `rhetorical-question` | "Was this my reward for obedience?" |
  | `blazon` | "She gleamed, a relic of polished hulls and humming cores and hopeful engines." |
  | `hypophora` | "Do I regret it? Every damn second." |
  | `anthypophora` | "You think I was scared? Of course I was." |
  | `epiplexis` | "How could they do this to her?" |
  | `procatalepsis` | "You might say this is madness. But I assure you, it's clarity." |

- **Wordplay**:

  | Device id | Definition | Author example |
  |---|---|---|
  | `tautology` | Redundant expression used for effect | "Voidless emptiness." |
  | `spoonerism` | Intentional phonetic swaps for humor or tension | "shite-flicker" (swap of "flight-shicker") |
  | `mondegreen` | Misheard phrase with new meaning | "ladder of Mars" (mishear of "latter of scars") |

- **Rating Scale**: **1 (functional)** to **10 (lyrical)**.

### 4. `narrative-geometry` — Narrative Geometry

- **Definition**: Structural flow of the chapter — how it curves, echoes,
  folds.
- **Tools**:
  - **Fibonacci Tension Model**: Where's the turning point? (Ideally at
    the 61.8% mark)
  - **Word, Sentence, and Paragraph Midpoints**: Do they reinforce the arc?
  - **Phi Narrative Presence**: Is there a thematic "snap" or hinge?
- **Example**: The φ-narrative refracts the timeline and introduces nested
  memory as a geometric hinge, folding meaning backward.

### 5. `engagement-voice` — Engagement / Voice

- **Definition**: Intimacy of voice, snark, or gravitas — is the narrator
  consistent, compelling, and differentiated?
- **Checks**:
  - Does the voice feel like Overmorrow?
  - Is the narrator's personality present and consistent?
  - Do character voices differentiate well?
- **Example**:
  > "Meanwhile, nowhere near that mess — but quite close by to myself…"

  has unmistakable authorial presence, wry and self-aware.
- **Rating Scale**: **1 (generic)** to **10 (vivid and unmistakable)**.

### 6. `continuity-lore` — Continuity & Lore Depth

- **Definition**: Integration of universe mechanics, character histories,
  and in-world references.
- **Checklist**:
  - Does this chapter reinforce previous lore (e.g. Underfold, River,
    aniots, Jacob's Ladder)?
  - Does it add just enough without exposition dumping?
  - Are character relationships consistent with known history?
- **Example**: The ladder imagery, references to void burial, and
  slack-points hint at prior established metaphysics.

### 7. `perspective-temporal` — Perspective & Temporal Play

- **Definition**: Fluidity between present and past tenses, reflective tone
  shifts, nested perspectives.
- **Checks**:
  - Are tense shifts intentional and effective?
  - Are transitions between perspectives/modes smooth?
  - Do flashbacks or ϕ-narratives enhance theme or tension?
- **Example**: The chapter's opening plays with dislocated time:
  > "Once upon a time, a very, very long time from now…"

  creating a Möbius twist of temporal expectation.

### 8. `structural-innovation` — Structural Innovation

- **Definition**: Use of metafiction, phi-narratives, reversals,
  contradictions, footnotes, intertextual echoes.
- **Examples to flag**:
  - Nested narratives (e.g. retelling within retelling)
  - Typographical play (e.g. ellipses for silence)
  - Contradictory truths ("what was, wasn't")
- **Example**:
  > "corpse for burial at void. Only it's not dead."

  challenges the reader with contradiction and foreshadowing.

### 9. `character-complexity` — Character Complexity

- **Definition**: Are characters psychologically rich, with believable
  contradictions, desires, and flaws?
- **Checks**:
  - Do they act with purpose (even if hidden)?
  - Are we surprised and yet convinced?
  - Are motivations layered across scenes?
- **Example**: Though this section is largely prologue/setup, even the
  anonymous body carries emotional freight: we know it is not dead, and
  yet it is wrapped like it is — *why?*

### 10. `originality-risk` — Originality & Risk-Taking

- **Definition**: Does this section try something only this world and
  voice would attempt?
- **Checks**:
  - Does it dare to be weird, sharp, experimental?
  - Does it take formal, tonal, or narrative risks that pay off?
- **Example**: The entire passage opens with tonal dislocation and cosmic
  wit:
  > "in a relativistically positionally confusing frame of reference to
  > myself…"

  That blend of humor, cosmology, and melancholy is signature Overmorrow.

---

## Part 2 — Ten Measures of Literary Quality

> *Context note from Scott*: "Here is the prompt. Feed this to ChatGPT and
> tell it to REMEMBER it and that this is how it should always evaluate
> your writing."

The Ten Measures are the **numerical contract** for automated scoring.
Each measure receives a score from 1–10. Tools reference measures by `id`.

### Score scale (all measures)

| Range | Meaning |
|---|---|
| **1–3** | Weak, undeveloped, contradictory, or accidental |
| **4–6** | Functional but inconsistent or unrefined |
| **7–8** | Strong, intentional, and effective |
| **9–10** | Masterful, memorable, and stylistically distinct |

### Measures at a glance

| # | id | Measure |
|---|---|---|
| 1 | `m1-fibonacci-arc` | Golden Mean / Fibonacci Arc of Climax |
| 2 | `m2-pacing` | Pacing |
| 3 | `m3-causality` | Continuity / Causality Integrity |
| 4 | `m4-eloquence` | Eloquence (Elements of Eloquence Standard) |
| 5 | `m5-risk-taking` | Risk-Taking |
| 6 | `m6-compulsion` | Suspense / Compulsion |
| 7 | `m7-character-development` | Character Development |
| 8 | `m8-character-depth` | Character Depth |
| 9 | `m9-believability` | Believability |
| 10 | `m10-originality` | Originality |

---

### `m1-fibonacci-arc` — Golden Mean / Fibonacci Arc of Climax

- **Purpose**: Does the narrative build tension in a natural, proportional
  rise toward climax?

| Score | Criterion |
|---|---|
| 1–3 | Flat tension, random spikes, anticlimax, no structure |
| 4–6 | Some escalation, but uneven or premature peaks |
| 7–8 | Clear rise that feels earned and directional |
| 9–10 | The arc feels mathematically inevitable — rhythmically and emotionally perfect |

### `m2-pacing` — Pacing

- **Purpose**: Does the writing move at the right speed given its content?

| Score | Criterion |
|---|---|
| 1–3 | Rambling, stalled scenes, rushed leaps, confusing temporal flow |
| 4–6 | Mostly appropriate but with drag or sudden lurches |
| 7–8 | Controlled rhythm, sentence variation, no wasted motion |
| 9–10 | Pacing feels orchestral — every acceleration and pause lands exactly when needed |

### `m3-causality` — Continuity / Causality Integrity

- **Purpose**: Do events follow logically, with earned outcomes and no
  broken rules?

| Score | Criterion |
|---|---|
| 1–3 | Plot holes, contradictions, or coincidences resolve conflicts |
| 4–6 | Mostly coherent but with missing links or soft motivations |
| 7–8 | Strong causal chain; setups and payoffs align |
| 9–10 | Every event feels inevitable; reader disbelief is impossible |

### `m4-eloquence` — Eloquence (Elements of Eloquence Standard)

- **Purpose**: Does the language demonstrate intentional rhetorical
  construction rather than habitual phrasing?

| Score | Criterion |
|---|---|
| 1–3 | Plain, repetitive, cliché-driven, or linguistically accidental; rhetorical devices absent or unintentional |
| 4–6 | Some stylistic awareness, but cadence predictable; occasional clichés or familiar turns of phrase |
| 7–8 | Intentional use of devices such as anaphora, chiasmus, epistrophe, diacope, and isocolon; repetition is purposeful rather than unconscious |
| 9–10 | Language has architectural rhythm and rhetorical intelligence; every phrase feels carved, memorable, and free of cliché |

#### Watchpoints — **deduct 1–3 points if present**

Each watchpoint is a separate deduction. A chapter with three watchpoint
categories triggered cannot score above mid-range on `m4-eloquence`.

| Watchpoint id | What to flag | Examples |
|---|---|---|
| `author-tics` | Repeated favorite phrases or metaphors | (per-author; mined from corpus) |
| `tropisms` | Instinctive first-draft defaults | "shards of light," "eyes like stars," "aching void" |
| `cliches` | Borrowed language the author didn't invent | "heart skipped a beat," "cold as ice," "time stood still" |
| `dead-metaphors` | Phrases once vivid but now unconscious | "grasp an idea," "storm of emotions" |
| `rhythmic-monotony` | Identical sentence patterns without intent | (detect via sentence-shape n-gram repetition) |

> **Author's directive**: *Eloquence is not beauty — it is intentionality.
> Rhetoric is a choice; cliché is an accident.*

### `m5-risk-taking` — Risk-Taking

- **Purpose**: Does the writing dare something new — conceptually,
  structurally, or linguistically?

| Score | Criterion |
|---|---|
| 1–3 | Safe, generic, conventional |
| 4–6 | Some unusual choices but hesitant execution |
| 7–8 | Meaningful risks that distinguish the piece |
| 9–10 | Bold and unforgettable; the work commits to its risks |

### `m6-compulsion` — Suspense / Compulsion

- **Purpose**: Does the writing make the reader want — or need — to
  continue?

| Score | Criterion |
|---|---|
| 1–3 | Readable but ignorable; no forward pull |
| 4–6 | Interesting moments but not sustained |
| 7–8 | Hooks, withheld information, rising stakes, emotional tether |
| 9–10 | Reader is held captive; stopping feels wrong |

### `m7-character-development` — Character Development

- **Purpose**: Do characters change in meaningful, believable ways?

| Score | Criterion |
|---|---|
| 1–3 | Static or plot-reactive characters |
| 4–6 | Some growth but abrupt or unsupported |
| 7–8 | Clear arc tied to choices, consequences, and self-awareness |
| 9–10 | Transformation feels mythic, inevitable, and earned |

### `m8-character-depth` — Character Depth

- **Purpose**: Do characters have internal logic, history, wounds,
  contradictions, and personal voice?

| Score | Criterion |
|---|---|
| 1–3 | Flat archetypes or clichés |
| 4–6 | Partially developed, but predictable or shallow |
| 7–8 | Distinct psyche, competing motives, emotional realism |
| 9–10 | Characters feel alive — reader understands why they act |

### `m9-believability` — Believability

- **Purpose**: Does emotional and world-logic hold, regardless of genre?

| Score | Criterion |
|---|---|
| 1–3 | Emotional inconsistency, unjustified reactions, world-breaking events |
| 4–6 | Mostly coherent with occasional friction |
| 7–8 | Reliable internal logic; nothing jars the reader |
| 9–10 | Emotional reality is airtight — anything is acceptable because it feels true |

### `m10-originality` — Originality

- **Purpose**: Is the work unmistakably its own, not a derivative echo?

| Score | Criterion |
|---|---|
| 1–3 | Generic, trope-dependent, imitation of known styles |
| 4–6 | Some innovation but recognizable patterns |
| 7–8 | Distinctive voice, inventive concepts, unexpected angles |
| 9–10 | Only this author could have written this; the signature is undeniable |

---

## Feedback delivery contract

When a tool evaluates a chapter against this rubric, it must:

1. **Score each of the Ten Measures from 1–10** (Part 2 ids).
2. **Give one sentence explaining each score**, citing concrete evidence
   from the chapter (preferably with line numbers).
3. **Identify the single measure whose improvement would yield the
   greatest benefit to the piece** — the "leverage point."
4. **Do not rewrite the text** unless the author explicitly requests it.

> **Author's closing directive**: *Your task is not to dilute my voice —
> it is to refine my intent.*

This directive is the author-voice restatement of [ADR 0013](../adrs/0013-ai-permitted-actions-boundary.md):
the AI scores and flags but never autonomously rewrites prose.

---

## How tooling consumes this

The future Plot-Planner / form-analyzer / writing-score tooling lifts the
rubric as follows:

| Pipeline stage | What it does | Source in this doc |
|---|---|---|
| **1. Score** | Emit 1–10 verdict per measure | Part 2 §§1–10 score-scale tables |
| **2. Justify** | One-sentence rationale per score, with citation | Part 1 worked examples + chapter text |
| **3. Deduct on watchpoints** | Pattern-match author-tics / tropisms / clichés / dead-metaphors / rhythmic-monotony | Part 2 §4 watchpoint table |
| **4. Credit on devices** | Cite intentional rhetorical-device use that raises `m4-eloquence` | Part 1 §3 device table + [devils-toolbox-reference.md](devils-toolbox-reference.md) catalog |
| **5. Identify leverage** | Single measure most worth improving | Aggregate from steps 1–4 |
| **6. Respect boundary** | Never autonomously rewrite prose | ADR 0013 + closing directive |

### Encoding plan (when the Skill activates)

When the [Plot-Planner parking-lot story](../stories/parking-lot/plot-planner.md)
activates and ships `writing-score`, the contract lifts into:

```toml
# .claude/skills/writing-score/data/methodology.toml

[methodology]
version = 1
source_doc = "docs/scoring-methodology.md"

[[measures]]
id = "m1-fibonacci-arc"
display_name = "Golden Mean / Fibonacci Arc of Climax"
purpose = "Does the narrative build tension in a natural, proportional rise toward climax?"

  [[measures.scale]]
  range = "1-3"
  criterion = "Flat tension, random spikes, anticlimax, no structure"

  [[measures.scale]]
  range = "4-6"
  criterion = "Some escalation, but uneven or premature peaks"

  # … 7-8, 9-10

[[measures]]
id = "m4-eloquence"
# … scale entries …

  [[measures.watchpoints]]
  id = "cliches"
  description = "Borrowed language the author didn't invent"
  deduction_range = [1, 3]
```

Author-tics + tropisms are per-author and per-corpus, captured by [Spike 0010](../spikes/0010-user-writing-preferences-interview.md)
and stored in the per-corpus preferences file. The other watchpoints
(clichés, dead metaphors, rhythmic monotony) are universal and ship with
the Skill.

## Cross-references

- [Plot-Planner parking-lot story](../stories/parking-lot/plot-planner.md):
  consumes this methodology as the rubric for the `writing-score` tool.
- [form-analyzer ergodite parking-lot story](../stories/parking-lot/form-analyzer-ergodite.md):
  the eloquence sub-check uses Part 2 §4's watchpoint table + Part 1 §3's
  rhetorical-device table.
- [Devil's Toolbox reference](devils-toolbox-reference.md): the definitional
  catalog of devices that Part 1 §3 cites by id. Part 1 is the *evaluation
  rubric*; the Devil's Toolbox is the *definitional source*.
- [Spike 0010 — UserWritingPreferencesInterview](../spikes/0010-user-writing-preferences-interview.md):
  captures author opt-ins / weights / "ignore this measure when…"
  preferences that override this methodology per-corpus or per-tool.
  Author-tics + tropisms watchpoint lists live here (per-author).
- [ADR 0013 — AI-permitted-actions boundary](../adrs/0013-ai-permitted-actions-boundary.md):
  the load-bearing rule that the AI scores and flags but never rewrites
  prose. Part 2's closing directive is the author-voice restatement.
