# MCP server + AI-user persona

- **Status**: parking-lot (Sprint 2+ when activated)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

## As / So that

As an **AI-user** (a Claude or other LLM instance acting on behalf of a human author), so that an AI assistant can read this repo's documentation (ADRs, spikes, README, CLAUDE.md), understand the tool's architecture, and run ergodix commands on the user's behalf — turning "Claude, render chapter 3" or "Claude, what plotlines are unresolved?" into actual ergodix invocations.

## Value

Amplifies the "AI as architectural co-author" thesis that drives the project; lets users who don't want a CLI experience still benefit from ergodix; centralizes documentation as the AI's context source rather than scattered prompt engineering; opens a distribution channel where the user's existing AI subscription (Claude, ChatGPT, etc.) drives the experience; introduces a new persona (AI-user) as a proper floater alongside writer / editor / developer / publisher / focus-reader.

## Risk

AI-user must NOT cross the AI-prose boundary (per CLAUDE.md and [ADR 0006](../../adrs/0006-editor-collaboration-sliced-repos.md) — the AI never edits chapter prose, never acts as the writer); the tool's existing safeguards need an MCP-layer enforcement so an AI-user can't bypass them via the MCP surface; expanding the floater set introduces another persona that needs careful scoping; MCP itself is a relatively new spec, so betting on it has stability risk; users may expect the AI-user to write chapters and we have to enforce "no" gracefully.

## Assumptions

MCP (Model Context Protocol) is a stable enough surface to build against; the existing ADRs / spikes / README provide enough context for an AI to operate ergodix without runtime training; an AI-user is a real persona (per [ADR 0011](../../adrs/0011-asvrat-story-format-for-persona-stories.md) the story leads with "As an AI-user"); the ethical stance "AI flags, human decides" extends cleanly to "AI invokes the analysis tools, never the prose-mutating ones".

## Tasks (when activated)

- [ ] New ADR locking the AI-user persona + floater + scope (alongside writer/editor/developer/publisher/focus-reader from [ADR 0005](../../adrs/0005-roles-as-floaters-and-opus-naming.md)).
- [ ] Add `--ai-user` floater (or `--mcp` server-mode) to the CLI.
- [ ] Build `ergodix-mcp` (or similar) MCP server exposing a curated tool surface to a Claude/AI client — render, status, plotline-tracking, summaries, etc.
- [ ] Lock the AI-user out of any operation that would edit prose chapters (extends [ADR 0013](../../adrs/0013-ai-permitted-actions-boundary.md)'s AI-permitted-actions boundary; explicit deny list in the MCP surface).
- [ ] Decide whether the MCP server reads the live filesystem or a snapshot — Drive sync + concurrency interactions.
- [ ] Documentation surface for the MCP tools (so the AI knows what's available); auto-generate from CLI?
- [ ] User flow for pointing Claude (or other) at the MCP server; auth model for the MCP.
