# Skill factory-seal protection

- **Status**: parking-lot (Sprint 2+ when activated; activates with first proprietary Skill)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.

## As / So that

As a publisher (and the author wearing the publisher floater), so that the proprietary Skills that constitute the project's actual moat — the author's scoring methodology, the Devil's Toolbox rhetoric reference, the Plot-Planner tool suite, future Continuity-Engine analyzers — cannot be silently modified, forked, or ratioed-into-meaninglessness by a downstream user; if a user wants to change a Skill, they file a comment / PR on the upstream repo and we decide whether to accept it.

## Value

Protects the IP that distinguishes ErgodixDocs from "Claude with a markdown folder"; ensures the Skills a user runs are the Skills the project author signed off on (no silent local modification that produces *worse* output the author then attributes to ErgodixDocs); creates a clean upstream-feedback channel (repo comments) that improves Skills over time without fragmenting them; pairs naturally with the [licensing-monetization](licensing-monetization.md) story since both want signed certs and a phone-home channel — share the infrastructure.

## Risk

Signing infrastructure is real engineering (key generation, secure storage of the signing key, signature verification at runtime, key rotation, revocation) and easy to get subtly wrong; "tampered Skill refuses to load" UX must be excellent or legitimate users will be locked out by file-mode glitches; monthly key rotation creates a hard online-once-a-month dependency that conflicts with the indy-mode design — needs a graceful-degrade story; a determined attacker can always strip signatures and run modified code (the seal is a *trust signal*, not a DRM shield) — the value is "honest users can verify they're running unmodified Skills," not "no one can modify Skills".

## Assumptions

Skills live at `.claude/skills/<name>/` (per [plot-planner](plot-planner.md) story); Ed25519 or RSA-PSS signatures are sufficient (no need for hardware-token signing in v1); the project author holds the signing key offline; monthly key rotation is achievable (issue a new validity-window certificate; old signatures stay valid until they expire from the trust window); the user accepts a once-monthly online check as part of the "local and frugal" stance because the alternative — perpetual offline trust — undermines revocation.

## Mechanism (rough sketch — to be refined when activated)

- Each Skill ships with a `manifest.toml` declaring its permitted-actions category per [ADR 0013](../../adrs/0013-ai-permitted-actions-boundary.md) and a detached signature file (`manifest.sig`).
- ErgodixDocs ships with a bundled public key + a *validity-window* certificate (e.g., "this signing key is trusted for the 60 days starting 2026-MM-DD").
- At Skill-load: verify the signature against the pubkey; verify the cert is within its validity window. Both must pass or the Skill refuses to load with a clear error (`Skill <name> failed signature check; the factory seal is broken. To request changes, comment on the upstream repo at <url>`).
- A scheduled check (cantilever follow-on or a small `ergodix refresh-keys` command) fetches the current validity-window cert from a known endpoint when the local cert is within 14 days of expiry. Network required at most once / 30 days.
- Offline grace: cert expired within last 30 days → load with a soft warning. Cert expired > 30 days → refuse to load with clear remediation ("connect to the network and run `ergodix refresh-keys`"). Tunable via the future `settings/defaults.toml` once the settings cascade lands.
- Indy-mode users can still run with cached certs as long as they've refreshed at least once; first-time install requires a network roundtrip to fetch the initial cert.

## Tasks (when activated)

- [ ] Cross-reference [licensing-monetization](licensing-monetization.md) and consolidate where the infrastructure overlaps (signed certs + phone-home cadence + privacy story).
- [ ] Choose signing algorithm — Ed25519 (fast verify, small signatures, modern) is the default unless there's a good reason to pick RSA-PSS.
- [ ] Build `ergodix refresh-keys` subcommand — fetches the current validity-window cert from a known HTTPS endpoint and writes to `~/.config/ergodix/skill-keys/`.
- [ ] Build the Skill-loader's signature-verification path — runs at every Skill invocation; cached after first verify per process.
- [ ] Decide validity-window cadence (30 days is a starting point; 60 or 90 may be friendlier for long-offline users; shorter than 30 starts to feel hostile).
- [ ] Decide what gets signed: just the manifest (cheap, but doesn't catch code modification), the entire Skill directory tarball (heavier, but real tamper detection), or both layers (defense in depth).
- [ ] Document the change-via-comment workflow: a user wants to modify a Skill → they comment on the upstream repo / file a PR / propose the change; if the project author accepts, the modified Skill is signed and shipped in the next release.
- [ ] Decide the network-required-once-monthly UX — calendar-driven cantilever prereq that runs `refresh-keys` if last-refresh > N days, with a clear warning before any refusal.
- [ ] Document loudly that the seal is a *trust signal*, not anti-piracy: a determined attacker can strip signatures and modify code; the seal protects honest users from drift, not against active subversion.
- [ ] Cross-reference [SECURITY.md](../../SECURITY.md) — add a section explaining the threat model for Skill integrity (in-scope: silent local modification by tools/agents; out-of-scope: a determined local attacker with the user's account).
