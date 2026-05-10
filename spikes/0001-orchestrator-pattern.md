# Spike 0001: Orchestrator pattern, persona model, floater registry

- **Date range**: 2026-05-03
- **Sprint story**: [Story 0.8 — Architecture spike](../stories/SprintLog.md#story-08---architecture-spike-orchestrator-pattern-role-based-cantilever-editor-collaboration-model-design-spike), Topic 1
- **ADRs produced**: [ADR 0001 — Click CLI with persona and floater registries](../adrs/0001-click-cli-with-persona-floater-registries.md)

## Question

What CLI / orchestration pattern should ErgodixDocs adopt? The author proposed modeling on UpFlick's `--cantilever` orchestrator with a manifest of single-purpose scripts. Is that the right pattern in 2026 Python, or is a more idiomatic alternative warranted?

## Discussion

### Initial framing

The author's stated vision: a single `ergodix` orchestrator command that, when invoked with a role flag (`--writer`, `--editor`, `--developer`), runs through all setup checks, fixes anything missing, and ultimately wires up daily-loop tooling. Modeled loosely on UpFlick's `--cantilever`. SOLID design principles emphasized; "open for extension, closed for modification" called out explicitly.

### What UpFlick actually does

Investigation showed UpFlick does *not* implement a manifest of single-purpose scripts in the strict sense. `UpFlick.py` is a large single-file orchestrator (~88 KB) that uses `argparse` mode flags (`--cantilever`, `--smoke`, `--ignore-raw`, etc.) and imports from sibling modules (`router.py`, `geocoder.py`, `exif.py`). The `workflow/` subpackage is a refactor in progress, not the original pattern.

Conclusion: the choice is not "UpFlick's pattern vs. modern Python." UpFlick's pattern is **argparse + flags + dispatch in a single file** — fine for its size, but mode flags scale badly past ~5 modes, and subcommand semantics become awkward.

### Options weighed

| Pattern | Verdict |
|---|---|
| **Click subcommand groups** | Recommended. Composable subcommands, automatic per-command `--help`, plays well with global options for personas and floaters. Already in our pip deps. |
| **Typer** (Click under the hood, type-hint driven) | Rejected. Smaller project than UpFlick — Typer's type-hint magic adds friction when subcommands need nuanced flag behavior. |
| **argparse + mode flags** (UpFlick's actual pattern) | Rejected. Author agreed: "as the project scaled, we should have switched to Click or Typer." |
| **Invoke / `tasks.py`** | Rejected. It's a developer build-tool, not a user-facing CLI. |

### Author's contributions that shaped the design

1. **Personas as first-class** — the role flags aren't fixed at writer/editor/developer; the project may scale to dozens of human collaborators (focus-group readers, line editors, publishers, reviewers). The CLI must support this without enumeration in code.
2. **`--developer` is a floater** — engineering responsibilities can layer on *any* persona. So `--developer` is not a persona, it's a behavior modifier composable with personas. Strongly hinted that it would not be the only floater.
3. **SOLID principles, especially Open/Closed and Liskov substitution** — the design must accommodate new personas, new floaters, and new import sources without modifying existing code.
4. **`migrate` is not one-time** — author's existing prose corpus is in Scrivener, not Google Docs (Drive corpus is a partial in-progress copy). So `migrate` needs to support multiple import surfaces.

### AI's contributions that shaped the design

1. **Persona as global option vs. as top-level subcommand** — Two viable Click designs: `ergodix --persona writer cantilever` (persona as global option) vs. `ergodix writer cantilever` (persona as subcommand namespace). Recommended option A because most subcommands (`render`, `sync`, `migrate`, `auth`) are persona-agnostic; baking persona into the namespace duplicates them across personas.
2. **Persona registry over Click `Choice`** — Click's idiomatic enum (`Choice(["writer","editor",...])`) is a closed set. To honor Open/Closed, personas live as plugin modules in a `personas/` registry; each declares its name, description, and the cantilever steps it runs. Adding a persona = drop a file. Tradeoff: `--help` for `--persona` becomes "see `ergodix personas list`" rather than a static enum. Author accepted.
3. **Floater registry** — `--developer`, `--dry-run`, `--verbose`, `--ci` all behave the same way: behavior modifiers any subcommand can opt into honoring. Formalized as a "modifier" registry rather than scattering `if developer:` checks. Same Open/Closed pattern as personas.
4. **Importer registry for `migrate`** — `migrate --from gdocs`, `migrate --from scrivener`, etc. Each `--from` value resolves to an importer plugin in an `importers/` registry. The `migrate` orchestrator itself never changes when a new source is added.
5. **Distinguishing `migrate` and `render`** — clarified during discussion: `migrate` is the source-import operation (Drive/Scrivener → `.md` + frontmatter); `render` is the publish operation (`.md` → typeset PDF/docx via Pandoc + XeLaTeX). Separate inputs, separate cadences, separate purposes.

### Scrivener-specific findings

Author's existing corpus is partially in Scrivener (large), partially in Google Docs (in-progress copy made for editor review). The `.scriv` bundle is a folder structure with `Files/Data/<UUID>/content.rtf` per chunk and a `Files/version.xml` + `Docs.xml` index. **No API needed** — direct filesystem read.

The Scrivener structure does **not** match the project's target hierarchy (`Epoch / Compendium / Book / Section / Chapter` per [Hierarchy.md](../Hierarchy.md)). Scrivener's organization is described as "kind of a mess" — arbitrary folders/subfolders, no enforced structure.

Three approaches to handling the structural mismatch were discussed. Recommendation for v1: **flat dump to `_unsorted/`** — the importer dumps every Scrivener leaf into one folder; the author reorganizes manually into the proper hierarchy in VS Code afterward. Future enhancement: mapping manifest (YAML file declaring `Drafts/Book One/Part Two/` → `Tapestry Compendium/Book One/Part Two/`) for re-importable consistency. Skipped: interactive remapping (too tedious for ~100+ items).

### Loose thread surfaced: corpus location

Author asked, partway through Topic 1: "Where did we land on the target for the corpus? keep it as a separate repo?" Recognized as a Topic 6 question (permissions and public/private split) but answered with a pre-position:

**Pre-position: two repos.**
- `ErgodixDocs` (public) — tooling, planning, ADRs, spikes.
- `tapestry-of-the-mind` (private) — `.md` chapter files, frontmatter, AI artifacts.

Reasoning: different audiences, different update cadences, different sensitivity. Tooling reads `CORPUS_FOLDER` from `local_config.py`; doesn't import from the corpus repo. Coordination is "tooling can run against any corpus folder."

Not locked here — Topic 6 will formalize it. Recorded so we have continuity.

## Decisions reached

- Use **Click subcommand groups** for the CLI surface. → [ADR 0001](../adrs/0001-click-cli-with-persona-floater-registries.md)
- **Persona** is a top-level global option (`--persona <name>`), backed by a registry of plugin modules. → ADR 0001
- **Floaters** (`--developer`, `--dry-run`, `--verbose`, `--ci`) are top-level global options, also backed by a registry. → ADR 0001
- **Importers for `migrate`** are a registry (`importers/<name>.py`); selected via `--from <name>`. Open/Closed at the command surface. → ADR 0001
- **`migrate` and `render` are distinct subcommands** with distinct inputs and purposes. → ADR 0001

## Loose threads / deferred questions

- **Are there other persona-aware subcommands besides `cantilever`?** Probably yes. Deferred to Topics 5 (bidirectional flow), 6 (permissions), 7 (comments explainer), and 8 (editor mode). Architecture supports it either way; no urgency to enumerate now.
- **Corpus location** — pre-positioned (two repos: public tooling, private corpus); formal lock in Topic 6.
- **Scrivener importer's structural-remap strategy** — v1 ships as flat dump; mapping-manifest support is a future enhancement. Filed as a task under Story 0.2.
- **Persona discoverability without `Choice`** — accepted that `--help` for `--persona` will say "see `ergodix personas list`" instead of enumerating values. If this proves confusing in practice, revisit.
