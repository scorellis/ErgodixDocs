# Publishing-house / enterprise scale (Story 0.Y)

- **Status**: parking-lot (deferred — not a current target)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

Documented for future architectural consideration. Not actively planned.

## What scales as-is

- **Persona/floater registry** — adding `line-editor`, `developmental-editor`, `proofreader`, etc. is the existing extension pattern.
- **Cantilever orchestrator** — independent of user count; each machine runs its own.
- **Continuous polling** — per-machine, each machine independent.
- **AI-prose boundary** — applies uniformly regardless of org size.
- **Settings TOML structure** — same registry shape works at any scale.
- **Importer registry** — new sources added without touching core.

## What doesn't scale and would need additions

- **Two-repo single-tenant model**: 500 authors = 500 corpus repos. Need org-level GitHub structure (sub-orgs per imprint), bulk-onboarding, repo templates.
- **Per-machine OS keyring credentials**: enterprise wants SSO (SAML/OIDC), centrally issued/revoked tokens, vault integration (Vault, AWS Secrets Manager). Current three-tier lookup extends cleanly — add a "Tier 0: SSO/vault" stage above env var.
- **Per-individual GitHub auth (`gh auth login`)**: enterprise wants GitHub Enterprise + SAML SSO. Same OAuth flow, different IdP.
- **Per-machine `local_config.py`**: managed devices need IT-pushed config. Add an `org_config.toml` URL or path that gets layered under `local_config.py`.
- **Per-machine cantilever / poller logs**: enterprise audit needs centralized log forwarding (Splunk, Datadog, S3). Add a "log destination" setting that supports remote sinks.
- **Individual Anthropic API keys**: enterprise wants centralized billing + per-author quotas. Add support for organization-issued keys with per-author allocation tracking.
- **GitHub branch protection per-repo**: enterprise wants policies enforced org-wide. GitHub provides this at org level; we'd document the recommended config but enforcement is GitHub's job, not ours.
- **Compliance** (SOC 2, ISO 27001, GDPR): out of scope for the tool itself; the surrounding deployment + ops practice carries the compliance burden.

## Architectural verdict

The current design is single-author-centric and **doesn't preclude** enterprise scaling. Every gap above maps to an additive extension using patterns we already have (registries, settings layering, three-tier lookup). None require tearing anything out.

## Recommendation if/when this story activates

Treat it as Sprint 3+ work. Start by identifying the first real enterprise customer's actual needs rather than designing speculative abstractions. Most of the "enterprise readiness" list above is wrong until a specific buyer's procurement requirements clarify it.

## Cross-references

- [scale-concerns](scale-concerns.md): Z1–Z5 single-tenant scale issues that interact with this story.
