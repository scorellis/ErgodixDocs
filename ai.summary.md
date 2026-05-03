# AI Session Summary

## 2026-05-02 (updated)

### Prompt To Resume Conversation

You are an AI in my ErgodixDocs workspace. Continue from this saved state.

**Project intent:**
- Build a bidirectional synchronization workflow between Google Docs and this repo.
- Canonical repo format should be Pandoc Markdown with raw LaTeX passthrough.
- Support or preserve Google Docs comments in a reversible way.
- Keep creative materials in an untracked local folder; push only tooling and non-sensitive docs to GitHub.
- AI's role is **Architectural Analysis only** — never edit prose chapters; track plotlines, flag plot holes, build summaries/storyboards, support worldbuilding.

**Known files and planning docs:**
- README.md — Origin / Goal / AI Boundaries / Install / Auth & Secrets sections.
- WorkingContext.md — running session log with resolved items.
- SprintLog.md — SVRAT sprint stories (Sprint 0 Stories 0.1, 0.4, 0.5 DONE; 0.2 and 0.3 open).
- Hierarchy.md — narrative document hierarchy (EPOCH → Compendium → BOOK → SECTION → CHAPTER).
- install_dependencies.sh — bootstraps brew, pandoc, MacTeX, python venv, Drive, generates local_config.py and central secrets.json.
- auth.py — scope policy (drive.readonly, documents.readonly), central-secrets reader, env-var fallback for Anthropic, stub Drive/Docs service builders.
- local_config.example.py — Python module template for per-machine config.
- .gitignore — excludes local_config.py, .ergodix_*, .venv/, *.gdoc/*.gsheet/*.gslides, /build/, /creative/, /content/.

**Resolved:**
- Drive sync working in **Mirror mode**.
- Canonical Drive path: `/Users/scorellis/My Drive/`.
- Tapestry source: `/Users/scorellis/My Drive/Tapestry of the Mind/`.
- Single-directory model adopted: one repo checkout, update via `git pull`, local secrets/state protected by `.gitignore` and permission checks.
- Auth: three-tier lookup (env var → OS keyring via `keyring` lib, service `ergodix` → fallback file at `~/.config/ergodix/secrets.json` mode 600). Per-project OAuth refresh tokens at `<deploy>/.ergodix_tokens.json`. Drive/Docs scopes are read-only by policy.
- Tool reframed for **general-author distribution** — naming purged of `scorellis-tools`; uses generic `ergodix` identifiers everywhere. "Local and frugal" is an explicit design principle (no cloud vault, no subscription).
- `auth.py` includes a CLI: `python auth.py {set-key|delete-key|status|migrate-to-keyring}` with hidden-input prompts.

**Story 0.2 format decisions LOCKED (2026-05-02):**
- Canonical content format: Pandoc Markdown + raw LaTeX passthrough.
- File extension: `.md` with **mandatory YAML frontmatter** declaring `format: pandoc-markdown` plus active `pandoc-extensions` list.
- Render pipeline: Pandoc → XeLaTeX → PDF.
- Editorial review: CriticMarkup in-file (`{++add++} {--del--} {>>comment<<}`).
- Authoring: VS Code is primary editor; chapters live as `.md` files in `~/My Drive/Tapestry of the Mind/`; Drive Mirror handles sync; AI reads files directly. No Drive/Docs API at runtime.
- Story 0.2 still has open tasks: build the migration script (`ergodix migrate`), define frontmatter schema, fidelity audit, VS Code setup recipe, render command.

**Most recent objective:**
- Wait for Mirror first-sync to complete; keep setup and daily work in a single repo checkout.
- Then continue **Sprint 0 Story 0.2 — Define canonical repo format** by building the migration script and frontmatter schema.

Please start by asking how the Mirror sync is progressing and whether GitHub remote is set up, then continue Story 0.2 work.