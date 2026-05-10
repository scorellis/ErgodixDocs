# ADR 0005: Single registry for roles, all-floaters model, multi-opus naming

- **Status**: Accepted
- **Date**: 2026-05-03
- **Spike**: [Spike 0004 — All roles as floaters; multi-corpus container named "opus"](../spikes/0004-roles-as-floaters-and-opus-naming.md)
- **Supersedes (in part)**: [ADR 0001](0001-click-cli-with-persona-floater-registries.md) — the persona-vs-floater duality. CLI framework choice (Click) and the importer registry stand unchanged.
- **Touches**: [ADR 0002](0002-repo-topology-and-editor-onboarding.md), [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) — terminology and settings-folder paths updated to match.

## Context

Topic 4 of [Story 0.8](../stories/SprintLog.md) was meant to be a fill-in-the-table exercise mapping cantilever's 22 operations to personas and floaters. The work surfaced three problems:

1. **Persona/floater duality was nominal, not structural.** `--developer` already added operations rather than modifying behavior, breaking the clean "personas add ops; floaters change behavior" framing.
2. **Most roles compose freely.** Writer composes with developer, with publisher, with both. Editor composes with developer. Only `focus-reader` is genuinely mutex with everything else.
3. **Multi-corpus support** (Story 0.X parking lot) needed a name for "a saved bundle of corpus + role-set." `compendium` collides with the narrative Hierarchy. `workspace` is generic.

## Decision

### Single registry: every role is a floater

The persona registry from ADR 0001 collapses into the floater registry. Each floater's TOML file declares:

- `adds_operations = [...]` — operations that get added to the cantilever set when this floater is enabled
- `exclusive_with = [...]` — other floater names this one cannot coexist with (mutex)
- `behavior_modifier = true|false` — distinguishes operation-adders from pure behavior modifiers (informational; doesn't change semantics)

**Initial floater set:**

| Floater | adds_operations | exclusive_with | behavior_modifier |
|---|---|---|---|
| `writer` | A7, C3, C4, C6 | focus-reader | false |
| `editor` | A7, C3, D1, D5, D6 | focus-reader | false |
| `developer` | D2, D3, D4 | focus-reader | false |
| `publisher` | A3, A4, B1, B2, C3, D5 | focus-reader | false |
| `focus-reader` | B1, B2, D5 | writer, editor, developer, publisher | false |
| `dry-run` | (none) | — | true |
| `verbose` | (none) | — | true |
| `ci` | (none) | — | true |

`exclusive_with` is symmetric — declaring it on one side is sufficient; the CLI honors it from either direction.

### CLI shape

Role flags are top-level options; `--persona` disappears.

```bash
ergodix --writer cantilever
ergodix --writer --developer --publisher cantilever
ergodix --editor cantilever
ergodix --focus-reader cantilever
ergodix --focus-reader --writer cantilever            # ERROR: exclusive_with violation
```

CLI startup checks `exclusive_with` constraints; conflicts fail fast with a clear message naming both flags and pointing to documentation.

**Empty-flag policy:** `ergodix cantilever` with no role flags fails with "specify at least one role: --writer, --editor, --developer, --publisher, or --focus-reader." No default — explicit intent is safer than hidden default.

### Effective operation set

Cantilever's operation set per invocation is:

```
universal_ops (from bootstrap.toml)
  ∪ {floater.adds_operations for each enabled role floater}
```

Universal ops: A1, A2, A5, A6, C1, C2, C5, E1, E2, F1, F2 (the 11 operations that run for every persona regardless).

### Settings folder restructure

ADR 0003's structure simplifies:

```
settings/
  bootstrap.toml             # universal ops + global defaults
  floaters/
    writer.toml
    editor.toml
    developer.toml
    publisher.toml
    focus-reader.toml
    dry-run.toml
    verbose.toml
    ci.toml
```

The `personas/` folder (proposed in ADR 0003 but never implemented) is dropped. Same registry pattern, one folder.

### Multi-opus container naming

A saved bundle of `(corpus_path + default_floater_set + last_used_context)` is called an **opus**. Plural: **opera**.

Term chosen for:
- Latin root (Tapestry/Rêve/Overmorrow voice)
- Means "a body of work" — exactly what we're naming
- No collision with `compendium` (already a Hierarchy level), `workspace` (generic), or `project` (overloaded)
- Short to type

CLI shape:

```bash
ergodix opus list
ergodix opus add tapestry --corpus tapestry-of-the-mind --writer --developer --publisher
ergodix opus add friend-novel --corpus their-book --focus-reader
ergodix opus switch tapestry
ergodix opus remove friend-novel
```

`ergodix opus switch <name>` writes a `CURRENT_OPUS` pointer (probably to `local_config.py` or a sibling state file). Subsequent commands read the pointer and apply that opus's stored corpus + floater set as the default.

This naming and CLI shape is **locked now** even though the implementation is deferred to Story 0.X — the locked vocabulary lets us reference "opus" consistently across docs, ADRs, and future stories without re-deciding.

### What does NOT change

- **Click as the CLI framework**. ADR 0001 stands on this point.
- **Importer registry** for `migrate --from <name>`. ADR 0001 stands.
- **Three-tier credential lookup**. ADR auth design stands.
- **Two-repo topology** (public ErgodixDocs + private corpus repos). ADR 0002 stands; only "editor persona" terminology becomes "editor floater."
- **Cantilever's operation menu and idempotency rules** (count grew from 21→24→25 as ADRs 0004 and 0006 added ops; current count maintained in ADR 0003). Settings folder structure simplifies to `settings/floaters/` only.

## Consequences

**Easier:**
- One mental model for users: pick your role flags and any modifiers; CLI tells you immediately if your combination is invalid.
- One registry concept; settings simpler; less code to maintain.
- Adding a new role (line-editor, beta-reader, developmental-editor) is exactly the same operation as adding `--developer` or `--publisher` was — drop a TOML file with `adds_operations`.
- Composition is symmetric: every role is "first-class" in the same way; no second-class persona-vs-capability distinction.
- "Opus" gives us a clean, project-voice-fitting container name that won't have to be revisited.

**Harder:**
- Three existing ADRs (0001, 0002, 0003) carry stale terminology that has to be reconciled via Notes pointing to this ADR. Future readers may be momentarily confused before reading this one.
- Empty-flag invocation fails — slightly more typing for the common case. Acceptable tradeoff for explicit intent.
- Larger flag surface in `--help`. CLI now lists 8 floaters instead of `--persona <enum>` + 4 floaters. Mitigated by the registry's `--help` strategy from ADR 0001 (point users at `ergodix floaters list`).

**Accepted tradeoffs:**
- Some readers will object that "everything is a floater" overloads the term. Acceptable — the alternative was overloading "persona" or maintaining two near-identical registries.
- `focus-reader.toml`'s `exclusive_with = [writer, editor, developer, publisher]` is the only mutex case in v1. Looks asymmetric. Honest reflection of the actual usage pattern; if more mutex roles emerge later, they get the same treatment.
- `opera` (Latin plural of opus) is technically correct but mildly archaic. Code uses `opera`; docs may use "opuses" or "opera" interchangeably.

## Alternatives considered

- **Keep persona + floater two-registry model**: rejected. Less principled than it looked; complicates extension; the "publisher = persona" question forced confronting it.
- **Multi-persona at runtime** (`--persona writer,publisher`): rejected. More complex than collapsing to a single registry; conflict-resolution between persona files; help text becomes confusing.
- **Personas as primary identity + capabilities as floaters** (a hybrid): rejected. Asymmetric without the focus-reader mutex actually justifying the asymmetry.
- **`compendium` as the multi-corpus container name**: rejected. Collides with the narrative Hierarchy.
- **`workspace`**: rejected. Generic; doesn't fit the project's voice.
- **`project`**: rejected. Overloaded with software-engineering connotations; doesn't honor the literary domain.

## References

- [Spike 0004](../spikes/0004-roles-as-floaters-and-opus-naming.md) — full discussion record.
- [ADR 0001](0001-click-cli-with-persona-floater-registries.md) — partially superseded.
- [ADR 0002](0002-repo-topology-and-editor-onboarding.md) — terminology touched.
- [ADR 0003](0003-cantilever-bootstrap-orchestrator.md) — settings paths touched.
- [Hierarchy.md](../Hierarchy.md) — the narrative model whose vocabulary `opus` is chosen to avoid colliding with.
- [SprintLog.md](../stories/SprintLog.md) Story 0.X — multi-opus implementation deferred.
