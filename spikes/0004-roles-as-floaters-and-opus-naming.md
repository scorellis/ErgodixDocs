# Spike 0004: All roles as floaters; multi-corpus container named "opus"

- **Date range**: 2026-05-03
- **Sprint story**: [Story 0.8 — Architecture spike](../SprintLog.md), Topic 4
- **ADRs produced**: [ADR 0005 — Single registry for roles, all-floaters model, multi-opus naming](../adrs/0005-roles-as-floaters-and-opus-naming.md)

## Question

Topic 4 was supposed to be a fill-in-the-table exercise: for each of cantilever's 22 operations, mark which persona triggers it and which floaters modify it. But the matrix work surfaced two architectural inconsistencies and a related design question:

1. The persona/floater split was less principled than it looked. `--developer` already behaved like a "capability layered on a persona," not a behavior modifier. Was "publisher" actually a persona, or was it the same kind of capability?
2. If most roles compose freely (writer + developer + publisher all make sense together), and only one (focus-reader) is genuinely mutex, do we need two separate registries at all?
3. If we're going to address the multi-corpus future story, what do we *call* a saved bundle of (corpus + role-set)? "Workspace" is generic; "compendium" collides with the narrative Hierarchy.

## Discussion

### The accidental two-class system

ADR 0001 locked **personas** (mutex primary identities) and **floaters** (composable behavior modifiers). But `--developer` was always a special case — it added operations (D3, D4, dev deps, branch tracking) rather than modifying behavior. We had quietly created two classes of floater (operation-adders vs. behavior-modifiers) without saying so.

When the author asked "should publisher be a persona?", the answer surfaced: publisher is the same kind of capability as developer. Layered onto a primary identity. Not its own primary identity.

### From three personas + floaters to one registry

The author pushed further: "what if all the roles are floaters?" with the observation that focus-reader was the only role that genuinely needed mutex. Everything else composes — writer can be a developer, writer can also publish, editor can be a developer.

The collapse:

- **Old model**: personas (mutex) + floaters (composable).
- **New model**: floaters only. Each floater declares its `adds_operations` and any `exclusive_with` constraints.

`focus-reader.toml` declares `exclusive_with = ["writer", "editor", "developer", "publisher"]` and the CLI fails fast on conflicting flags. Mutex is now a property of a floater, not an architectural concept.

This collapses two registries into one without losing any expressiveness. ADR 0001's persona-vs-floater duality is partially superseded by ADR 0005.

### CLI shape after collapse

`--persona <name>` flag disappears. Each role becomes its own flag:

```bash
ergodix --writer cantilever                              # author basic
ergodix --writer --developer --publisher cantilever      # author full kit
ergodix --editor cantilever                              # editor
ergodix --focus-reader cantilever                        # focus group reader
ergodix --focus-reader --writer cantilever               # ERROR: focus-reader excludes writer
```

Empty-flag policy: `ergodix cantilever` with no role flags fails with "specify at least one role: --writer, --editor, --developer, --publisher, or --focus-reader." Defaults are dangerous; explicit intent is safer.

### Effective operation set per invocation

Universal operations (A1, A2, A5, A6, C1, C2, C5, E1, E2, F1, F2) live in `bootstrap.toml` and always run. Each role floater's `adds_operations` is added to the union. Final example:

`ergodix --writer --developer cantilever` runs:
- All universal ops from `bootstrap.toml`
- `writer.toml`'s `adds_operations`: `["A7", "C3", "C4", "C6"]`
- `developer.toml`'s `adds_operations`: `["D2", "D3", "D4"]`
- Union; duplicates collapse silently

### Settings folder restructure

ADR 0003's `settings/personas/<name>.toml` + `settings/floaters/<name>.toml` collapses to just `settings/floaters/<name>.toml`. Universal ops still in `bootstrap.toml`. One folder, one concept.

### Cost of the collapse

Three ADRs need a note pointing to ADR 0005:

- **ADR 0001**: persona-vs-floater duality is the part that's superseded; CLI framework choice (Click) and the importer registry stand.
- **ADR 0002**: "editor persona" terminology becomes "editor floater"; behavior identical.
- **ADR 0003**: `settings/personas/` + `settings/floaters/` becomes just `settings/floaters/`; behavior identical.

Honest revision, not a redesign. Per ADR conventions (write-once), I add a "Note" line at the top of each pointing readers at ADR 0005 for the affected portion.

### Publishing-house stress test

Mid-discussion the author asked: "imagine we're a large publishing house — does this scale?"

Honest answer: the architecture is single-author-centric. It doesn't break for enterprise but isn't enterprise-ready. Each gap (multi-tenant repo structure, SSO, central credentials, central audit, IT-pushed config, organization API keys) maps to an additive extension using patterns already in the design (registries, settings layering, three-tier lookup). None require ripping anything out.

Filed as Story 0.Y in the parking lot with the gap analysis written down. Recommendation: don't design speculatively; activate the story when a real enterprise customer's procurement requirements clarify which gaps actually matter.

### The "what do we call a saved bundle" question

The user liked the workspace model from the multi-corpus options but rejected the word "workspace." Proposed "compendium" — but compendium is already a level in the narrative Hierarchy ("The Rêve of the Overmorrow" is a Compendium). Reusing the term across abstraction layers creates the kind of paper-cut ambiguity that makes a system feel slightly off without people knowing why.

Alternatives suggested: `opus`, `canon`, `shelf`, `desk`. Author picked **opus** — Latin for "a body of work," fits the Tapestry/Rêve/Overmorrow voice, no collision with the Hierarchy, short to type. Plural: opera (technically correct, slightly weird, fine).

CLI shape locked into Story 0.X (parking lot until activated):

```bash
ergodix opus list
ergodix opus add tapestry --corpus tapestry-of-the-mind --writer --developer --publisher
ergodix opus add friend-novel --corpus their-book --focus-reader
ergodix opus switch tapestry
ergodix cantilever                  # uses current opus
```

## Decisions reached

- **Single registry for roles**: the persona/floater duality from ADR 0001 collapses into one registry. Every role (writer, editor, developer, publisher, focus-reader) is a floater. Mutex constraints expressed declaratively via `exclusive_with`. → [ADR 0005](../adrs/0005-roles-as-floaters-and-opus-naming.md)
- **CLI shape**: each role is its own top-level flag. `--persona` flag disappears. `ergodix cantilever` with no role flags fails fast. → ADR 0005
- **Settings restructure**: `settings/floaters/<name>.toml` only, no separate `personas/` folder. → ADR 0005
- **Multi-corpus container naming**: `opus` (singular), `opera` (plural). Subcommand: `ergodix opus list/add/switch/remove`. Locked into Story 0.X. → ADR 0005
- **Publishing-house scaling**: documented as Story 0.Y in parking lot with gap analysis. Not designed speculatively. → SprintLog Story 0.Y

## Loose threads / deferred questions

- **Multi-opus implementation** — Story 0.X. Activated when a real second opus exists in someone's life.
- **Enterprise scaling** — Story 0.Y. Activated when a real enterprise customer surfaces.
- **Default opus on a single-opus install** — when v1 ships pre-Story-0.X, there's effectively one implicit "default" opus. The migration to Story 0.X (when it activates) wraps the existing single-corpus config into `OPERA["default"]`.
- **Documentation update sweep** — README, WorkingContext, ai.summary still reference "persona" terminology in places. Sweep done as part of the ADR 0005 commit.
