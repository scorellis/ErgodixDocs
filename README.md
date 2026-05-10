# ErgodixDocs

> **License: [PolyForm Strict 1.0.0](https://polyformproject.org/licenses/strict/1.0.0).** Source-available, **not** open source. Personal / hobby / academic / nonprofit use is permitted; **any commercial use requires a separate written commercial license** from the copyright holder. Reading the source as a model or architectural reference is encouraged. See [LICENSE](LICENSE) for full terms. Commercial licensing inquiries: scorellis@gmail.com.

## Origin of the Name

The name supports the author's effort to create **Xience Fixtion** (yes, with the X's — creative licence) in the form of an **Ergodic text**: a work that requires nontrivial effort from the reader to traverse, where structure, branching, and navigation are part of the storytelling itself.

"Ergodix" = **Ergod**ic + the author's playful **X**, with **Docs** for the document tooling that supports it.

## What ErgodixDocs Does

In one paragraph: **ErgodixDocs takes a manuscript from Google Docs or Scrivener, converts it into a versioned Pandoc-Markdown corpus organized as opus → compendium → book → section → chapter (per [Hierarchy.md](Hierarchy.md)), supports footnotes and ergodic-text features (rotation, special fonts, landscape pages, TikZ), and synchronizes between collaborators via Google Drive. An AI layer (eventually exposed via an MCP-like interface) reads the corpus and generates non-creative supporting material — glossaries, character sketches, tables of contents, storyboards, timelines, plot-hole flags — and answers the author's questions about the work. The AI never edits prose; that boundary is load-bearing for the project's identity (see [AI Boundaries](#ai-boundaries--prose-is-human-written) below).**

## Goal

Build a system that uses AI as a co-author and continuity engine for a fictional universe larger than any single human can hold in their head. The tooling is meant to:

- track plotlines across books, sections, and chapters
- detect plot holes and continuity errors
- generate summary documents, glossaries, character sketches, timelines, and storyboards on demand
- support worldbuilding for a universe far more complex than one author can manage alone
- let the author ask questions of the corpus and get grounded answers

The repository hosts the tooling and non-sensitive planning docs. Creative source material lives outside the tracked tree.

## Reviews

External PR reviews (Copilot, ChatGPT, human peers — reviewer-agnostic) are collected in `reviews/` using ADR-scoped filenames:

- [reviews/0013.external-review.md](reviews/0013.external-review.md)

If multiple PRs map to the same ADR, use suffixes:

- `reviews/0015.1.external-review.md`
- `reviews/0015.2.external-review.md`

Reviews with open security findings are held until the corresponding fixes ship — published alongside the follow-up PR rather than ahead of it.

## Integration smoke test

`scripts/integration-smoke.sh` runs an end-to-end deployment-pipeline smoke against a fresh test deploy. It:

1. Syncs the source tree to a deploy directory (default `/tmp/ergodix-smoke-deploy`, override via `ERGODIX_SMOKE_DEPLOY`).
2. Runs `bootstrap.sh` to install ergodix into a fresh venv and run cantilever's inspect/plan phases.
3. Verifies the `ergodix` console-script is registered and that `ergodix --version` matches the source's `VERSION` file.
4. Runs `ergodix status` and `ergodix migrate --from docx --check --corpus examples/migrate-fixture`, asserting expected counts.

Run locally from the repo root:

```bash
scripts/integration-smoke.sh
```

The script is structured so it can be lifted to GitHub Actions later by referencing the same script — no rewrite needed when CI/CD shifts off-machine.

## AI Boundaries — Prose Is Human-Written

The chapters and prose files authored by the human are **not to be touched, edited, or rewritten by the AI**. There is significant community sentiment opposed to books being written by AI, and that concern is respected here.

The AI's role is strictly **Architectural Analysis**:

- read the prose to understand it
- track continuity, plotlines, and worldbuilding
- generate summaries, storyboards, and reference material
- flag plot holes or inconsistencies for the author to resolve

The hope is that the universe is interesting enough on its own merits that readers won't mind AI was used to help **architect** it — but the writing itself remains the author's.

## Install

ErgodixDocs now uses a **single-directory model**.

Clone one repo, run the installer there, and keep local machine-specific files gitignored. No deploy checkout, no update wrapper script.

### First-time setup

1. **Clone the repo** somewhere you keep code (`~/Documents/source/ErgodixDocs/`):
   ```bash
   git clone <your-ergodixdocs-repo-url> ~/Documents/source/ErgodixDocs
   cd ~/Documents/source/ErgodixDocs
   ```
2. **Run the bootstrap script from the repo directory:**
   ```bash
   ./bootstrap.sh
   ```
   `bootstrap.sh` is intentionally minimal (per [ADR 0007](adrs/0007-bootstrap-prereqs-cli-entry.md)): it finds a Python ≥3.11 interpreter, creates `.venv/`, runs `pip install -e ".[dev]"` so the `ergodix` console-script lands on PATH, and hands off to `ergodix cantilever`.

   `ergodix cantilever` then runs the four-phase orchestrator from [ADR 0010](adrs/0010-installer-preflight-consent-gate.md): **inspect** the system (read-only) → show a **plan** and ask for consent once → **apply** the changes (admin password requested at most once) → **verify** the install with smoke checks. Pandoc, MacTeX, Google Drive for Desktop, `local_config.py` generation, the credential-store layout, and VS Code extension installs all happen here, not in `bootstrap.sh`.

   `bootstrap.sh` is re-runnable: a second run is fast when the venv already exists and cantilever's inspect phase reports everything as already-satisfied. Pass `--dry-run` to preview without applying, `--ci` to bypass the consent prompt for non-interactive use.

3. **Manual one-time Drive steps** (cantilever surfaces the prompt; sign-in itself is outside the script):
   - Sign in to Google Drive for Desktop in the menu-bar app.
   - In Drive Preferences, choose **Mirror files** (recommended) or **Stream files**.
   - Re-run `./bootstrap.sh` once Drive is signed in if paths weren't detected on the first pass.

### Daily workflow

1. **Edit tooling** in this repo.
2. **Commit and push** to GitHub. `local_config.py`, tokens, and runtime state are gitignored, so secrets never go up.
3. **Pull latest changes** when needed:
   ```bash
   git pull
   ```

### What's tracked vs. ignored

**Tracked in git** (safe for GitHub):
- `bootstrap.sh`, `ergodix/auth.py`
- `local_config.example.py` (template, only `Path.home()`-relative defaults — no real values)
- `README.md`, `Hierarchy.md`, `WorkingContext.md`, `SprintLog.md`, `ai.summary.md`
- Future tooling code

**Ignored** (see `.gitignore`):
- `local_config.py` — your real paths
- `.ergodix_tokens.json`, `.ergodix_state.json`, `.ergodix.lock`, `ergodix.log`
- `.venv/`, `__pycache__/`, `*.pyc`
- `/build/` — Pandoc output
- `*.gdoc`, `*.gsheet`, `*.gslides` — Google Drive placeholder files
- `/creative/`, `/content/` — any creative material accidentally placed in the repo
- `.DS_Store` and editor scratch

## Auth & Secrets

ErgodixDocs is **local and frugal**: secrets stay on your machine in the OS-native credential store, with a plaintext file as a fallback for headless environments. No cloud vault, no extra services, no subscription required. The same code works on macOS, Linux, and Windows because the `keyring` library abstracts the platform-specific store underneath.

### Three-tier credential lookup

Whenever ErgodixDocs needs an API key, it asks `auth.py`, which resolves in this order:

1. **Environment variable** — preferred for CI/scripts/one-offs. E.g. `ANTHROPIC_API_KEY`.
2. **OS keyring** — primary live store for interactive use:
   - **macOS** → Keychain
   - **Linux** → Secret Service / KWallet
   - **Windows** → Credential Manager

   Service name: `ergodix`.
3. **Fallback file** — `~/.config/ergodix/secrets.json` (mode 600, gitignored by location). Only used if the keyring backend is unavailable. `auth.py` refuses to read this file if its permissions are loosened.

A missing credential raises `RuntimeError` pointing the user at the right `python -m ergodix.auth set-key …` command.

### Storing keys (interactive, hidden input)

```bash
python -m ergodix.auth set-key anthropic_api_key
python -m ergodix.auth set-key google_oauth_client_id
python -m ergodix.auth set-key google_oauth_client_secret
```

Each command prompts for the value with hidden input (no shell history, no `ps` exposure) and stores it in your OS keyring under service `ergodix`.

> **Where do the Google OAuth client values come from?** Follow [docs/gcp-setup.md](docs/gcp-setup.md) — the canonical SOP for creating the GCP project, enabling the Drive and Docs APIs, configuring the OAuth consent screen, and minting the OAuth client credential. ~10 minutes, one time per install.

### Inspecting state (without revealing values)

```bash
python -m ergodix.auth status
```

Shows:
- which keyring backend is active on this machine
- whether the fallback file exists
- for each known key, which sources currently have a value (env / keyring / file) — never the value itself

### Other commands

```bash
python -m ergodix.auth delete-key <name>            # remove a key from the keyring
python -m ergodix.auth migrate-to-keyring           # move keys from secrets.json into the keyring
python -m ergodix.auth migrate-to-keyring --delete-file   # …and delete the fallback file
```

### Per-project OAuth tokens

Long-lived OAuth refresh tokens for Google Drive/Docs (used only when we move past Mirror-mode reads, in Sprint 0 Story 0.3) live in `<repo_dir>/.ergodix_tokens.json` (mode 600, gitignored). They are **never reused by other tools** — each application that uses your Google account gets its own refresh token scoped only to what it needs.

### Scope policy (declared in `auth.py`)

- **Google Drive**: `drive.readonly` only. Reads happen via the local Mirror mount; writes happen via the filesystem (Drive for Desktop syncs the change). No write scope needed.
- **Google Docs**: `documents.readonly` only. Same reasoning.
- **Comments**: covered by `drive.readonly`.
- Broader scopes require an explicit decision and a justifying comment in `auth.py`.

### File-mode invariants

The installer enforces:

- `~/.config/ergodix/` → mode `700`
- `~/.config/ergodix/secrets.json` → mode `600` (when present)
- `<repo_dir>/local_config.py` → mode `600`
- `<repo_dir>/.ergodix_tokens.json` → mode `600` (when created)

`auth.py` re-checks the fallback file's mode at read time and refuses to load if loosened — surfacing the misconfiguration loudly rather than silently reading a world-readable secret.

### What `keyring` is and why we picked it

`keyring` is a small, well-maintained Python library that talks to whichever credential store is native to the current OS. On macOS the first read by a given Python interpreter triggers a one-time Keychain "Allow" dialog; after "Always allow," subsequent reads are silent. There is **no service to install, no daemon to run, and no cloud account to pay for** — secrets are encrypted at rest by the OS itself. If a user's environment has no keyring backend (some headless Linux installs, some Docker images), the code automatically falls through to the file at `~/.config/ergodix/secrets.json`, which keeps the tool usable in CI without compromising the security model on machines where the keyring is available.

