# Security

ErgodixDocs is a single-user local tool. The threat model below describes what
the project defends against and what it explicitly does not. Reports of
vulnerabilities are welcomed and acted on; everything else is decided in
the open.

## Reporting a vulnerability

Email **scorellis@gmail.com** with the words "ErgodixDocs security" in the
subject line. Include enough detail to reproduce. We will:

- Acknowledge within 5 business days.
- Triage and respond with a timeline within 14 days.
- Credit the reporter in the fix's changelog entry unless they prefer
  otherwise.

Please do not file public GitHub issues for vulnerabilities until a fix has
landed; see [`security/`](security/) for our internal tracking convention.

## In scope

- The credential layer ([`ergodix/auth.py`](ergodix/auth.py)) — env var,
  OS keyring, and file-fallback paths.
- The bootstrap installer ([`bootstrap.sh`](bootstrap.sh)) and the cantilever
  orchestrator ([`ergodix/cantilever.py`](ergodix/cantilever.py)) — anything
  that runs with elevated privileges or writes to system locations.
- The render pipeline ([`ergodix/render.py`](ergodix/render.py)) when invoked
  on attacker-controlled markdown / TeX files (e.g. shell escape via raw
  LaTeX, path traversal via include directives).
- File-mode and directory-mode invariants documented in
  [README.md](README.md#file-mode-invariants).
- Future surfaces: the AI / MCP server interface (Story 1.X), the migrate
  importer (Story 0.2), the editor signing-key flow (ADR 0006).

## Out of scope

- **Local attacker with the user's account.** ErgodixDocs assumes the user
  controls their own machine. An adversary with shell access as the user has
  unrestricted access to keyring, files, and processes — defending against
  this requires OS-level protections (FileVault, full-disk encryption, screen
  lock) that are outside this project's surface.
- **In-memory credential scrubbing.** Python doesn't give a clean way to
  zero memory holding decoded credentials, and strings are immutable. We
  rely on the OS keyring's encryption-at-rest as the relevant invariant.
  See [`security/0004-memory-scrubbing-out-of-scope.md`](security/0004-memory-scrubbing-out-of-scope.md).
- **Supply-chain compromise of pinned dependencies.** ADR 0009 requires
  pinning, but ErgodixDocs does not run integrity checks on PyPI packages
  beyond what `pip` does by default.
- **Side-channel / physical-access attacks.**

## Tracking

We file findings — both self-found and external — into [`security/`](security/)
as numbered records, parallel to the `adrs/` and `spikes/` conventions.
Each record includes severity, status (`open` / `accepted-as-known-risk` /
`patched-in-#NN`), and the reasoning. See
[`security/README.md`](security/README.md) for the format.
