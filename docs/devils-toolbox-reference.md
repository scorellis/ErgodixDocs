# Devil's Toolbox — Rhetorical Device Reference

Author-curated catalog of rhetorical devices that grounds the future
Plot-Planner / form-analyzer / writing-score tools when they need to cite
"what counts as anaphora" or "what counts as polysyndeton."

This is the **content** the [Devil's Toolbox parking-lot story](../stories/parking-lot/devils-toolbox.md)
will eventually encode as a structured Skill (`.claude/skills/devils-toolbox/`)
with TOML/YAML data files keyed by device `id`. The story stays parked until
a downstream tool needs it; this reference lives in tree so the source
material is preserved in the author's voice and not lost between sessions.

**Status**: source material, author-authored. Voice and examples retained
verbatim from Scott's drop. Structure / categorization / ids added to make
the catalog scannable for humans and lift-ready for tooling.

**Stable contract**: each device has an immutable `id` (kebab-case). Tools
reference devices by id, never by display name — display names are free to
evolve; ids are not.

## Categories at a glance

| Category | Devices |
|---|---|
| [Sound](#sound-devices) | `alliteration-general`, `alliteration-consonance`, `alliteration-assonance`, `alliteration-symmetrical`, `alliteration-word`, `alliteration-compound`, `paroemion` |
| [Repetition & Structure](#repetition--structure) | `anaphora`, `anadiplosis`, `polyptoton`, `merism`, `polysyndeton`, `parataxis`, `hypotaxis`, `hyperbaton` |
| [Interruption & Reversal](#interruption--reversal) | `aposiopesis`, `antithesis`, `tautology` |
| [Ornament](#ornament) | `blazon`, `diacope`, `epigram`, `synaesthesia` |
| [Rhetorical Questions](#rhetorical-questions) | `anacoenosis`, `anthypophora`, `antiphora`, `apocrisis`, `aporia`, `erotesis`, `erotema`, `epiplexis`, `epitemesis`, `hypophora`, `interrogatio`, `percontatio`, `procatalepsis`, `pysma`, `rogatio`, `ratiocinatio`, `subjectio` |

Each device below carries:

- **id** — kebab-case stable identifier (tools reference this)
- **category** — one of the buckets above
- **definition** — one or two sentences in the author's voice
- **example(s)** — the live examples Scott provided
- **classifier-hint** *(when present)* — short note for AI pattern-matching

---

## Sound Devices

### `alliteration-general`

- **Category**: sound
- **Definition**: The most common form of alliteration — the same consonant
  sound is repeated at the beginning of closely connected words.
- **Example**: "She sells seashells by the seashore."
- **Classifier-hint**: ≥3 successive content words starting with the same
  consonant sound within a single clause.

### `alliteration-consonance`

- **Category**: sound
- **Definition**: Repetition of consonant sounds, which can appear at the
  beginning, middle, or end of words. When used at the beginning, it
  overlaps with `alliteration-general`.
- **Example**: "Mike likes his new bike."

### `alliteration-assonance`

- **Category**: sound
- **Definition**: Repetition of vowel sounds within words that are close
  together. While not strictly alliteration, it's often used in conjunction
  with it.
- **Example**: "The rain in Spain stays mainly in the plain."

### `alliteration-symmetrical`

- **Category**: sound
- **Definition**: A more complex form where a sequence of sounds is mirrored
  around a central point.
- **Example**: "He who sees sees who he."
- **Classifier-hint**: detect palindrome-like sound mirror across a clause's
  center.

### `alliteration-word`

- **Category**: sound
- **Definition**: Full-word alliteration — entire words are repeated, often
  for emphasis or to create a rhythmic effect.
- **Examples**:
  - "Would that the wood were seemingly seamless."
  - "Fair is fair."
  - "Man to man."
  - "Word for word."

### `alliteration-compound`

- **Category**: sound
- **Definition**: Consonant sounds repeated in two or more sets of compound
  words or multi-syllable words.
- **Example**: "Wild and woolly, willfully in the woods."

### `paroemion`

- **Category**: sound
- **Definition**: Overuse of alliteration. Often deliberate — leans into the
  excess for tonal effect.
- **Example**: "We watched as westerly winds wickedly whipped the wilting
  weeping willows."

---

## Repetition & Structure

### `anaphora`

- **Category**: repetition
- **Definition**: Strategically repeating a word or phrase at the start of
  successive clauses or sentences.
- **Example**:
  > "I had a dream that one day this nation will rise up.
  > I had a dream that my four little children will one day live in a
  > nation where they will not be judged by the color of their skin but by
  > the content of their character.
  > I had a dream today."

### `anadiplosis`

- **Category**: repetition
- **Definition**: Take the last word of a clause and use it as the first
  word of the next. Chains the thought.
- **Example**:
  > "We glory in tribulations also, knowing that tribulation worketh
  > patience, and patience, experience, and experience, hope, and hope
  > maketh man not ashamed."

### `polyptoton`

- **Category**: repetition
- **Definition**: Variation of the same root word in different grammatical
  forms — adjective then noun, or noun then verb, etc.
- **Examples**:
  - "Sweet suite."
  - "Seemingly seamless."
  - "The impossibility of possible possibilities, bordered by boards."

### `merism`

- **Category**: structure
- **Definition**: Refer to a whole by listing its parts, often using
  contrasting elements to express a broader concept. A way of implying
  totality or completeness by mentioning two or more extremes or parts.
- **Examples**:
  - "He searched high and low" (meaning he searched everywhere).
  - "We need to protect both young and old" (meaning everyone).
  - "You are either with me, or against me."

### `polysyndeton`

- **Category**: structure
- **Definition**: Using lots of conjunctions where typical grammar would
  omit them. The opposite is `asyndeton` (total absence of conjunctions).
- **Example**: "I have time and time and time and she can move in the Next
  and Next and Next."

### `parataxis`

- **Category**: structure
- **Definition**: Short sentences. Juxtaposed phrases without subordination.
  Opposite of `hypotaxis`.
- **Example**:
  > "Writing should be a blend of things. Parataxis can be nice. It allows
  > you to be understood. It explicitly follows conventions. It doesn't
  > pollute sentences with complexity. It shuns adjectives. It shuns
  > adjectives. It avoids conjunctions. It allows the reader to understand
  > simple thoughts."

### `hypotaxis`

- **Category**: structure
- **Definition**: Very long, complicated sentences with subordinate clauses
  inside subordinate clauses. Opposite of `parataxis`.
- **Example** (from Forsyth, *The Elements of Eloquence*, p. 75):
  > "The alternative, should you, or any writer of English, choose to
  > employ it (and who is to stop you?) is, by use of subordinate clause
  > upon subordinate clause, which itself may be subordinated to those
  > clauses that have gone before or after, to construct a sentence of
  > such labyrinthine grammatical complexity that, like Theseus before you
  > when he searched the dark Minoan mazes for that monstrous monster,
  > half bull and half man, or rather half woman for it had been conceived
  > from, or in, Pasiphae, herself within a Daedalian contraption of
  > perverted intention, you must unravel a ball of grammatical yarn lest
  > you wander forever, amazed in the maze, searching through dark
  > eternity for a full stop. That's hypotaxis, and it used to be
  > everywhere."

### `hyperbaton`

- **Category**: structure
- **Definition**: Words in the wrong order — or the correct order, a not
  familiar way in. (Albeit correctly not this is.)
- **Example**: Winston Churchill allegedly wrote in the margin of some
  document: "This is the kind of English up with which I will not put."

---

## Interruption & Reversal

### `aposiopesis`

- **Category**: interruption
- **Definition**: When the cat has your tongue, and doesn't give it back.
  A deliberate breaking-off mid-sentence — typically denoted by an ellipsis
  or em-dash.
- **Example**: "If I ever see him again, I swear I'll—"

### `antithesis`

- **Category**: reversal
- **Definition**: Contrasting ideas placed in parallel for emphasis.
- **Example**: "People say 'A tide rising raises all boats.' Everyone
  forgets that every tide has two sides."

### `tautology`

- **Category**: reversal
- **Definition**: A statement that repeats the same idea in different
  words, often unnecessarily. Can also mean a logical statement that is
  always true by its form, regardless of content. In everyday language it's
  redundancy; in logic it's vacuous truth. Both can be wielded for
  emphasis.
- **Examples (everyday)**:
  - "Free gift."
  - "I saw it with my own eyes."
- **Examples (logical)**:
  - "It will either rain tomorrow or it won't."
  - "A or not A."
- **Example (author's, for emphasis)**:
  > "If you begin to alphabetically sort something, the last word will
  > always be the last word. In any list, the last word is always the
  > last word until it is not, and the last word is always the last word,
  > no matter where it is in the list."

---

## Ornament

### `blazon`

- **Category**: ornament
- **Definition**: Cataloguing the beauty of a figure or vessel — itemizing
  features in praise.
- **Example**: "Roses are red, violets are blue, your lips are like flower
  petals and your words like sweet wine…"

### `diacope`

- **Category**: ornament
- **Definition**: Answer your own question — typically with a word or short
  phrase that gets repeated for emphasis around an intervening qualifier.
- **Example**: "How did this happen? Ignorance, my dear friend, pure,
  unbridled ignorance."

### `epigram`

- **Category**: ornament
- **Definition**: A pithy saying or remark expressing an idea in a clever
  and amusing way.
- **Example**: "You will never remember to reload, it's far better to
  master it and be so fast at reloading, it doesn't matter you forgot."

### `synaesthesia`

- **Category**: ornament
- **Definition**: Crossing senses — describing something perceived through
  one sense using terms from another.
- **Examples**:
  - "Music that stings like a bee the tenders of the mind."
  - "She voiced her concern as pleasantly as fingernails dragged across a
    chalkboard."

---

## Rhetorical Questions

This family is large enough to warrant its own table — many devices that
look similar at first glance carry different rhetorical intent. Tools
should classify carefully.

### `anacoenosis`

- **Category**: rhetorical-question
- **Definition**: A rhetorical question that involves the audience and
  builds consensus. The question's answer is obvious or aligns with the
  speaker's viewpoint; the audience nods along, building shared ground.
- **Function tags**: engagement, consensus-building, persuasion.
- **Examples**:
  - "Don't we all want a better future for our children?"
  - At a company meeting, CEO Stanley might say, "Who makes the best
    Cogs?" To which the gathered employees will of course say, "We do!"

### `anthypophora`

- **Category**: rhetorical-question
- **Definition**: Pose a question and immediately answer it. Used to
  anticipate objections and address them.
- **Example** (from *Julius Caesar*):
  > "Did this in Caesar seem ambitious? When that the poor have cried,
  > Caesar hath wept; Ambition should be made of sterner stuff. Yet Brutus
  > says he was ambitious; And Brutus is an honourable man."

### `antiphora`

- **Category**: rhetorical-question
- **Definition**: Often used interchangeably with `anthypophora` — pose
  and answer your own question to control the narrative.
- **Examples** (from Milton's *Areopagitica*, and the author's voice):
  - "What should ye do then? Should ye suppress all this flowery crop of
    knowledge?"
  - "What is my path forward then? Should I just walk out and leave you?
    Should I perhaps go lay down in the grass, and wait for the roots and
    the ground to take me? Or should I stay here, and suffer your abuses?"

### `apocrisis`

- **Category**: rhetorical-question
- **Definition**: A question posed and answered in a formal or
  authoritative manner. Establishes a point by providing a clear answer to
  a posed question.
- **Example** (from Conrad's *Heart of Darkness*):
  > "What did he expect? I would not have believed him. I had rather my
  > heart had been broken."

### `aporia`

- **Category**: rhetorical-question
- **Definition**: A rhetorical expression of doubt or perplexity. Can be
  genuine or feigned — to engage the audience or highlight the complexity
  of an issue.
- **Example** (from Hamlet):
  > "To be, or not to be, that is the question."

### `erotesis`

- **Category**: rhetorical-question
- **Definition**: A rhetorical question posed to make a point rather than
  to elicit an answer. The answer is implied; the question itself asserts.
- **Example** (from Dickens's *A Tale of Two Cities*):
  > "Is it possible! Is it possible that vile habit of mine should rob me
  > of life in this manner? And that, too, at such a time?"

### `erotema`

- **Category**: rhetorical-question
- **Definition**: Another term for a rhetorical question used for emphasis
  or persuasion. Like `erotesis`, it implies that the answer is obvious or
  already known.
- **Example** (from Twain's *Huckleberry Finn*):
  > "What's the use you learning to do right, when it's troublesome to do
  > right and ain't no trouble to do wrong, and the wages is just the
  > same?"

### `epiplexis`

- **Category**: rhetorical-question
- **Definition**: A rhetorical question used to rebuke, shame, or
  criticize. Accusatory or challenging; meant to provoke a reaction.
- **Examples**:
  - "What's the point?"
  - "Why would you want that?"
  - "How could they do this to her?"

### `epitemesis`

- **Category**: rhetorical-question
- **Definition**: Like `epiplexis`, but the question is followed by an
  accusation or judgment. Reprimand + assertion in one beat.
- **Examples**:
  - "What were you thinking when you ignored all the warnings? Do you have
    any idea how much damage you've caused?"
  - "Why did you ignore my advice? Clearly, you've made a mess of things."

### `hypophora`

- **Category**: rhetorical-question
- **Definition**: Raise a question and immediately answer it, guiding the
  audience to the desired conclusion.
- **Example**: "What have you done for me lately? NOTHING."

### `interrogatio`

- **Category**: rhetorical-question
- **Definition**: A rhetorical question asked for effect, where the answer
  is often obvious and does not require a response. Used to engage the
  audience or to highlight a point.

### `percontatio`

- **Category**: rhetorical-question
- **Definition**: A rhetorical question used to probe deeply into a
  subject or issue, often with the intention of revealing something hidden
  or unexpected. More inquiry, less assertion.

### `procatalepsis`

- **Category**: rhetorical-question
- **Definition**: Anticipating and responding to an opponent's objection
  before it can be voiced. Also known as *prebuttal*, *prolepsis*,
  *anticipatio*, or *figure of presupposal*.

### `pysma`

- **Category**: rhetorical-question
- **Definition**: A series of questions asked in rapid succession.
  Overwhelm the opponent or create a sense of urgency / pressure.

### `rogatio`

- **Category**: rhetorical-question
- **Definition**: A formal term for asking a question, particularly in a
  rhetorical context. Synonymous with `interrogatio` or `erotesis`
  depending on usage.

### `ratiocinatio`

- **Category**: rhetorical-question
- **Definition**: A question is asked, and the answer involves reasoning
  or argumentation. Leads the audience through a logical process to a
  specific conclusion.

### `subjectio`

- **Category**: rhetorical-question
- **Definition**: Speaker asks a question and answers it with a pointed or
  assertive statement. Emphasizes the speaker's point; keeps control of
  the argument.

---

## Encoding plan (when the Skill activates)

When the [Devil's Toolbox parking-lot story](../stories/parking-lot/devils-toolbox.md)
activates, the structure above lifts cleanly into a TOML data file at
`.claude/skills/devils-toolbox/data/devices.toml`:

```toml
[[devices]]
id = "anaphora"
category = "repetition"
display_name = "Anaphora"
definition = "Strategically repeating a word or phrase at the start of successive clauses or sentences."

  [[devices.examples]]
  source = "MLK Jr — I Have a Dream"
  text = """I had a dream that one day this nation will rise up.
I had a dream that my four little children will one day live in a nation where they will not be judged by the color of their skin but by the content of their character.
I had a dream today."""

[[devices]]
id = "anadiplosis"
category = "repetition"
display_name = "Anadiplosis"
definition = "Take the last word of a clause and use it as the first word of the next. Chains the thought."

  [[devices.examples]]
  source = "Romans 5:3–5 (paraphrase)"
  text = "We glory in tribulations also, knowing that tribulation worketh patience…"
```

The Skill's loader builds a `dict[id, Device]` from this. Downstream tools
(`writing-score`, `PC-placator`, `form-analyzer`'s eloquence sub-check)
import and reference devices by id.

## Cross-references

- [Devil's Toolbox parking-lot story](../stories/parking-lot/devils-toolbox.md):
  the eventual Skill that encodes this reference as TOML keyed by id.
- [scoring-methodology.md](scoring-methodology.md): the chapter-evaluation
  rubric. Part 1 §3's rhetorical-devices checklist references the catalog
  here; Part 2 §4 (Eloquence) deducts on watchpoints (clichés, dead
  metaphors, etc.) but credits on intentional use of devices listed here.
- [Plot-Planner parking-lot story](../stories/parking-lot/plot-planner.md):
  `writing-score` / `PC-placator` / future stylistic-feedback tools
  reference rhetoric primitives by id; the Devil's Toolbox Skill is the
  canonical reference.
- [form-analyzer ergodite parking-lot story](../stories/parking-lot/form-analyzer-ergodite.md):
  the eloquence sub-check (7 v1 figures via regex) draws its candidate
  set from the catalog here.
- [Spike 0010 — UserWritingPreferencesInterview](../spikes/0010-user-writing-preferences-interview.md):
  author may opt out of certain rhetoric categories ("don't flag classical
  figures unless explicitly asked"). The interview captures opt-in/opt-out
  per category — this reference's categories are the legal values.
