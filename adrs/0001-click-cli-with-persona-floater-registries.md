# ADR 0001: Click CLI with persona, floater, and importer registries

- **Status**: Accepted
- **Date**: 2026-05-03
- **Spike**: [Spike 0001 — Orchestrator pattern, persona model, floater registry](../spikes/0001-orchestrator-pattern.md)

## Context

ErgodixDocs needs a CLI surface that is:

1. Coherent — a single entry point users can discover and learn from.
2. Composable — a small number of orthogonal subcommands (`migrate`, `render`, `sync`, `cantilever`, `status`, `auth`).
3. Persona-aware — different roles (writer, editor, reviewer, publisher, focus-reader, …) need different setup and tooling. The set of personas is **not bounded** at design time and must accommodate dozens of human collaborators.
4. Behavior-modifier-aware — flags like `--developer`, `--dry-run`, `--verbose`, `--ci` cut across personas and subcommands. They must be composable, not duplicated as per-subcommand options.
5. Open for extension — adding a persona, a floater, or a new `migrate` source must not require modifying existing code (Open/Closed).

UpFlick uses `argparse` mode flags in a single-file orchestrator. That works at UpFlick's scale but does not scale to ErgodixDocs's expected contributor model or extensibility requirements.

## Decision

ErgodixDocs uses **Click subcommand groups** as its CLI framework, with three plugin registries layered on top:

### CLI surface

```
ergodix [floaters...] [--persona <name>] <subcommand> [subcommand-args]
```

**Subcommands** (initial set; extensible):

| Subcommand | Purpose |
|---|---|
| `cantilever` | Full setup / upgrade / deploy for the active persona. Persona-aware. |
| `migrate --from <importer>` | Import an external corpus (Google Docs, Scrivener, .docx folder, …) into canonical `.md` + frontmatter. |
| `render <chapter\|book>` | Pandoc → XeLaTeX → PDF (or `.docx` for editor review). |
| `sync` | Apply pending edits, pull/push as appropriate. |
| `status` | Read-only health check. |
| `auth <subcmd>` | Credential management (already implemented in `auth.py`). |

**Floaters** (top-level global options, registry-backed):

| Floater | Effect |
|---|---|
| `--developer` | Engineering responsibilities layered on the chosen persona (git hooks, dev deps, branch setup). |
| `--dry-run` | Preview only, no mutations. |
| `--verbose` | Detailed logging. |
| `--ci` | Non-interactive, no prompts. For automation. |

Floaters are composable. `--persona writer --developer --dry-run` means "preview what cantilever would do for a writer who is also a developer."

**Persona** (top-level global option, registry-backed):

`--persona <name>` selects one of the registered persona modules. `cantilever` consults the persona to decide which install steps to run; other subcommands may also consult it if and when later topics surface a need.

### Three registries, all plugin-driven

1. **Persona registry** — `personas/<name>.py` modules. Each exports name, description, and the cantilever-step set the persona runs. Adding a persona = add a file. The CLI does not hardcode persona names anywhere.

2. **Floater registry** — `floaters/<name>.py` modules. Each exports name, default value, and an optional handler invoked by subcommands that opt into honoring it. Adding a floater = add a file.

3. **Importer registry** — `importers/<name>.py` modules. Each exports name, description, and a `run(source_path, target_path) -> None` function. `migrate --from <name>` resolves to an importer module via the registry. Adding an importer = add a file.

All three registries scan their folder at startup and assemble the available options dynamically. Open/Closed compliance: new personas, floaters, and import sources require zero changes to `cli.py` or any subcommand.

### Help-text trade

Click's idiomatic enum is `Choice([...])`, which produces a static list in `--help`. Because personas and floaters are registry-driven (not enumerated at compile time), `--help` for `--persona` and floater flags directs users to `ergodix personas list` and `ergodix floaters list` respectively. Accepted as a worthwhile cost for the extensibility win.

## Consequences

**Easier:**
- Adding a new persona, floater, or import source is a contained change — one new file, no edits to existing code.
- Subcommands stay small and focused. `cantilever` doesn't need to know about every persona; it just asks the registry "what steps does this persona need?"
- The CLI grows naturally as the project scales to more contributor types without architectural rewrites.
- New importers (Scrivener, .docx folder, plain text) drop in without the migration orchestrator changing.
- Testing is easier: each persona / floater / importer is a unit testable in isolation.

**Harder:**
- `--help` for `--persona` and floaters can't enumerate values inline; users discover via `ergodix personas list`. Mild discoverability cost.
- Slightly more file-system ceremony than a single-file CLI: three registries, three folders, plugin discovery code at startup.
- Persona / floater / importer plugins must follow a contract; bad plugins can break startup. Mitigated by keeping the contracts minimal and testing the registries.

**Accepted tradeoffs:**
- Click was chosen over Typer despite Typer's smaller boilerplate. Click's escape hatches matter more for our nuanced flag semantics than Typer's type-hint convenience.
- Persona is global-option (option A from the spike), not subcommand-namespace (option B). Most subcommands are persona-agnostic, so namespacing them by persona would force duplication. Accepted that `cantilever` is the only persona-heavy consumer for now.

## Alternatives considered

- **argparse + mode flags (UpFlick's pattern)** — rejected. Mode flags scale badly past ~5 modes; subcommand semantics become awkward; doesn't match 2026 Python convention.
- **Typer** — rejected. Type-hint-driven CLIs fight us when subcommands need nuanced flag behavior; `click` is already a dep; Click's escape hatches matter more than Typer's boilerplate savings at this size.
- **Invoke / `tasks.py`** — rejected. Invoke is a developer build-tool, not a user-facing CLI for non-developer authors and editors.
- **Persona as subcommand namespace** (`ergodix writer cantilever`) — rejected. Most subcommands are persona-agnostic; namespacing forces duplication.
- **Persona as Click `Choice`** — rejected. Closed set; violates Open/Closed when new personas land.

## References

- Spike 0001 — captures the discussion this decision flowed from.
- [Click documentation](https://click.palletsprojects.com/) — the framework chosen.
- [Hierarchy.md](../Hierarchy.md) — the narrative-structure model that personas operate in service of.
