# Licensing + monetization framework

- **Status**: parking-lot (way later — pre-distribution)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

## As / So that

As a publisher (and the author wearing the publisher floater), so that ErgodixDocs can be sold as a commercial product when it ships out of the ~1-year solo-dev window — license-key validation, expiry handling, "trial / expired" UX, payment integration, and distribution channels (DMG, App Store, brew tap, web download) need a coherent design before anyone pays for it.

## Value

A defensible monetization path that survives common piracy patterns, integrates with whatever payment platform we pick, and degrades gracefully when payment lapses (read-only? grace period? hard block?); also blocks the obvious "anyone can run it for free forever" failure mode that would foreclose the publisher persona's reason to exist.

## Risk

Getting this wrong creates support load, alienates legitimate users, or leaves obvious workarounds; over-engineering it before any users exist is also waste; license-validation that phones home creates a privacy story that needs to match the rest of the project's "local and frugal" stance.

## Assumptions

~1 year of pre-commercial dev gives time to learn how the tool is actually used; the licensing layer will be a separate concern from cantilever (a wrapper / decorator pattern rather than a hard cantilever dep); the eventual distribution mode (DMG, App Store, web download, brew tap, etc.) shapes how the license-check integrates.

## Tasks (when activated)

- [ ] Choose license-validation model — server-validated keys vs offline-signed certs vs hybrid; decide phone-home cadence (session-start? daily? never?).
- [ ] Decide grace-period / hard-cutoff behavior on expiry (read-only mode? N-day grace? feature-gating?).
- [ ] Pick payment platform (Stripe, App Store, Paddle, Lemon Squeezy, etc.) and wire it.
- [ ] Decide trial mechanics (free for X days, free with N chapters, free forever for personal non-commercial, etc.).
- [ ] Build the licensing layer as an opt-in wrapper around the CLI — not a hard dep that breaks the existing dev workflow.
- [ ] Distribution: DMG signing + notarization (macOS), App Store packaging, brew tap, possibly Microsoft Store + apt repo.
- [ ] Privacy: no telemetry beyond license-validation pings; document clearly; respect the "local and frugal" posture from README.
- [ ] Decide whether existing open-source-licensed bits (any third-party deps) constrain commercial distribution; license-compatibility audit.

## Cross-references

- [skill-factory-seal-protection](skill-factory-seal-protection.md): wants signed certs + phone-home channel; share the infrastructure.
- [ip-strategy](ip-strategy.md): trademark + patent decision feeds into commercial distribution posture.
