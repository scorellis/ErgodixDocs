# ADR 0011: ASVRAT story format required for persona-driven stories

- **Status**: Accepted
- **Date**: 2026-05-06
- **Spike**: (none — short convention decision)
- **Touches**: [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) — formalizes how floater personas surface in sprint stories.

## Context

Sprint 0 stories were written in **SVRAT** form (So that, Value, Risk, Assumptions, Tasks). The format keeps each story honest about purpose and risk, but it elides *whose* perspective the story serves. Once roles became floaters in [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) (`--writer`, `--editor`, `--developer`, `--publisher`, `--focus-reader`), every persona-driven feature has a clear voice it should be written in. Leaving that voice implicit invites two failure modes:

1. **Drift away from the persona who actually benefits.** A story written without naming its audience tends to optimize for whoever is implementing it, not whoever uses the result.
2. **Cross-persona scope creep.** When a story doesn't declare its persona up front, it's easy to bolt on tasks that serve a different floater and lose focus on the original need.

Not every story has a persona, though. Infrastructure work (CI, dependency pinning, the installer itself, test scaffolding) serves the project and the contributor stack rather than a creative role. Forcing those stories into a persona shape is contrived.

## Decision

**Persona-driven stories use ASVRAT.** When a story exists to serve a real human persona — writer, editor (the human collaborator who reviews prose), developer, publisher, focus-reader — the story **must** lead with an `As a [persona]` line that names which floater (or floater combination) it serves. Format:

```
### Story N.M - <title>

As a <persona>,
So that <value statement>,
Value: <why this matters now>,
Risk: <what could go wrong>,
Assumptions: <what must hold for this to be tractable>,
Tasks:
- [ ] ...
```

A story may name a floater combination if it serves more than one (`As a writer/developer,`). It may also name a system actor as the persona where genuinely useful — the cantilever orchestrator, the polling job, the migration importer — when the story is about that subsystem's behavior toward the system itself.

**Infrastructure / KTLO stories may omit the `As a` line and use SVRAT.** The implicit persona for these is the contributor stack: keep-the-lights-on, efficiency, build/test/CI hygiene, dependency management, installer correctness, repo topology. Forcing an artificial persona on this work obscures rather than clarifies.

**No retroactive migration.** Existing SVRAT stories in `SprintLog.md` stay as they are. This ADR applies forward only — every new story added from 2026-05-06 onward follows it. Migrating old stories would be churn for no clarity gain; the convention earns its keep on the next story written, not the last one.

## Consequences

**Easier:**
- New persona stories declare their audience in the first line, which keeps task lists from drifting cross-persona.
- Reviewing a story for scope no longer requires inferring whose problem it solves.
- The floater set in [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) becomes load-bearing in planning, not just in CLI surface.

**Harder:**
- Mixed sprint logs (some ASVRAT, some SVRAT) require the reader to recognize both formats. CLAUDE.md documents both and explains when each applies, so the cost is one-time learning, not ongoing friction.
- Edge cases: a story that *might* benefit a persona but is mostly infrastructure (e.g., the installer redesign, which serves contributors but also "the writer who installs once and never thinks about it again"). The judgment call lives with whoever writes the story; ADR 0011 doesn't try to legislate every boundary.

**Accepted tradeoffs:**
- Inconsistency between old SVRAT stories and new ASVRAT ones is a permanent feature of the sprint log. Worth it to avoid the churn of a mass migration.
- "System actor as persona" (cantilever, poller, importer) blurs the persona/infrastructure line. Allowed deliberately — sometimes the clearest framing of an infrastructure story really is "as the orchestrator, so that..."

## Alternatives considered

- **Mandatory ASVRAT for every story, including infrastructure.** Rejected — invents fake personas for CI / dependency / installer work and produces forced phrasing like "As a contributor, so that the build is green." That's not a persona, it's a tautology.
- **Keep SVRAT for everything, document persona separately.** Rejected — the persona ends up buried in prose where it's easy to miss. The whole point of ASVRAT is to surface persona at the top.
- **Migrate all existing stories to ASVRAT.** Rejected per the principle that retroactive sweeps cost cycles for marginal clarity gain. Late-arriving conventions apply forward (CLAUDE.md "Working partnership norms").

## References

- [ADR 0005](0005-roles-as-floaters-and-opus-naming.md) — defines the floater set used as the persona vocabulary.
- [CLAUDE.md](../CLAUDE.md) "What goes in which doc" → `SprintLog.md` entry — the steady-state description of ASVRAT vs. SVRAT.
