# Spike 0013: Style sentinel, AI-writing detection, and tamper-resistant authorship certificate

- **Date filed**: 2026-05-10
- **Sprint story**: Parking-lot today; will become a Sprint 2+ story (or its own sprint) once the design surface stabilizes. The migrate arc (Story 0.2) and Sprint 1 features (Plot-Planner / Continuity-Engine) take priority.
- **ADRs to produce**: at least three — analysis registry shape, certificate format + key distribution, education-mode extension. Numbers TBD.
- **Touches**: [ADR 0001](../adrs/0001-click-cli-with-persona-floater-registries.md) (CLI + plugin registries), [ADR 0005](../adrs/0005-roles-as-floaters-and-opus-naming.md) (writer / editor / publisher / focus-reader roles), [ADR 0006](../adrs/0006-editor-collaboration-sliced-repos.md) (signed commits, baseline-tracked resync), [ADR 0013](0013-ai-permitted-actions-boundary.md) (AI permitted-actions closed list), [ADR 0014](../adrs/0014-sync-transport-and-settings-cascade.md) (sync transport + settings cascade), [Spike 0010](0010-user-writing-preferences-interview.md) (preference-gated structural analysis).
- **Status**: Open — design surface enumerated, not yet resolved. Intentionally not implementing today; this is the brainstorm-to-record pass so the conversation survives the session.

## Question

Three threads surfaced together in conversation on 2026-05-10. They share an underlying engine — stylometric fingerprinting — and a shared honesty problem: how do we make analysis results trustworthy to a third party (a teacher, an editor, a future reader) who didn't watch the writing happen?

1. **Style sentinel.** Watch the author's prose for drift from their own established style — paste-detection, ghostwriter-detection, AI-injection-detection. Same engine across all three; only the reference corpus changes.
2. **Authorship certificate.** Write a tamper-resistant artifact next to (or inside) the manuscript that asserts "this was written by this author, here are the analysis results, here are the supporting fingerprints — and a third party can verify this without trusting the author's word."
3. **Education extension.** A second product surface where students = writers and teachers = editors (mapping cleanly onto ADR 0005's existing roles). The kids-using-AI problem is the trigger; the same engine that protects an author's voice in fiction is the one that flags AI-generated paragraphs in a school essay.

The question isn't *can we build it* — most of the pieces have prior art. The question is **what does the design surface look like once the pieces are stitched together**, and which decisions are load-bearing enough to deserve their own ADRs.

## Source messages

Per the partnership norm of preserving the *journey* in spikes, here are the prompts that opened this thread, verbatim. Future readers reconstruct the reasoning from these, not from a tidied summary.

### Message 1 (2026-05-10, exploratory framing)

> let's do some planning while its reviewing. Let's say you have a skill, and the skill is to detect plagiarism. Can we spawn a stand alone binary? I should think you would need the entire library of congress and every book ever written. Or maybe we can come at it from the other side — lock in on the writers' style. Maybe with a series of regexes, and through other pattern matching techniques, you could build a "linguistic probability" tree. For every sentence we figure out the writers style by evaluating their writing style the moment their fingers start tapping out keys, and what we do is then detect when something appears that is NOT their style. I can also train this model on chatGPT and Claude and other writing styles by consuming books that we know were written by ai ….. then we can also detect if AI wrote something.
>
> The reason I'm bringing this up is that a friend of mine was telling me about how kids writing with ai is a real problem. 1: I think we could easily extend this product to that sort of use
>
> 2. We should check and do some research and see if this tool already exists
> 3. Build a skill map, and determine if we can build stand alone "skills" — binaries — that can do things like review for devil's toolbox (regex again, detecting things like anaphora, and we can also have a near-rhyme topography map. Finding the climax of the story, I don't know how we would do that. We will have to look at my fibonacci writing prompt that I give to chat got and figure out if there exists a tool or if we can build one that would be able to do it.
> instead of calling them "skills" like claude does, we will call them ergodites which meshes nicely with the notion of ergodic documents plus they are like little "egos" that have the ability to carry out tasks. We will want to ensure they aren't tampered with either -- maybe we salt their hashes and create a dictionary of their hashes that we update with each release if they change.

### Assistant response (summarized, not verbatim — captured for context)

Three threads, each with a concrete next move:

- **Style fingerprint + AI detection are the same engine, different reference corpus.** Stylometry (function-word frequencies, sentence-length distributions, character n-grams, Yule's K, type-token ratio) profiles "this author" from a window of the corpus and scores each new paragraph against it. Train the same model on known-AI-generated books and you get an AI detector. Signal is weakest at sentence-level; strongest at paragraph-or-passage level. Existing libs to evaluate before building: pystylometry, Stylo (R), spaCy + a custom feature extractor. Public AI-detector tools to study before reinventing: GPTZero, Originality.ai, Copyleaks.
- **Plagiarism at LoC scale: don't roll our own.** Commercial APIs exist (Copyleaks, Turnitin, Originality.ai). Realistic path is an opt-in skill that calls one with the user's API key. What we *can* build cheaply is self-plagiarism within the opus.
- **Skills as binaries vs Python modules.** Recommend mirroring the just-shipped `ergodix/importers/` pattern — an `ergodix/analyses/` (or `ergodix/lenses/`; avoid "skills" because of the Claude Code skill-concept collision) plugin registry with `NAME`, `DESCRIPTION`, `run(corpus_root, **opts) -> Report`. Standalone binaries (PyInstaller / Nuitka) only worth it for non-Python audiences (educators, LMS integrations).

### Message 2 (2026-05-10, the certificate + GUI + education extension)

> I was also thinking that there could be a certificate file that we write in such a way as to prevent altering. We'd have to think of how to store a hash of the written material along with another hash that says "this paper is authentic" so that the hash can be stored with the md.... maybe we use steganography and our own embedded viewer --- can you embed a viewer in an md?..... then, if the code in the image is wrong, the viewer will show "Plagiarism detected on page x, paragraph y" etc. We'd have to write whatever ngrams and "fingerprinting" files into the md somehow as hidden files? I don't know if you can do that. So that the certification can be authenticated, the supporting materials would have to be available to the editor (the teacher or parent) on the google drive the school owns that the student uses. Presumably, that is how schools do it so that teachers can see their studen't work. They would even be able to see it in progress then....which is maybe a bit to "big brother"-like. If the files are embedded, then all the student has to do is share the .md through google docs functionality. Maybe we use a zip container that uses PK....somehow we'd have to seamlessly and unseen, generate a layer of encryption on the outside so that the student can decrypt it on the drive and then ErgodixDocs can decrypt it, because we don't want other students to somehow get access to another student's drive and steal their work. Then the teacher will have to have the private key of every student. I am not sure how we will transmit that securely. I imagine there is a protocol out there in some security model that tells us how to do it. the next layer would have to be when ergodix, with its various skills, makes its assessments with each paragraph written. We need a way to prevent tampering by the student with the results. This is where we would have the hash of the WORK, and an encryption of the problems found that only the teacher can decrypt. This part of the file will be written directly to the google drive doc. Unless the student has an understanding of advanced cryptography, he likely won't be able to encrypt a false package because he won't know what we put in the package, and Ergodix on the student side will put a secure hash into the file to certify the certifier is authentic and not some file encrypted by the kid. I honestly want to know how that would work. ANyway, let's not mull through this now, we need to make a spike. Also, let's include the original message, such as this one, as the "source", documented IN the spike. Also, let's assume students are writer and teachers are editors. That way, they can leverage the comments capabilities. We will need our own gui, you realize....because we will want a very simple interface that can show students and teachers their style scoring in a panel off to one side, and if a student pastes something in that is detected to be misaligned stylometry vectors, a red box around the paragraph can light up and will stay lit up until it matches the students style and until it has been so significantly altered, it no longer matches the paste. then it lights up green for 10 seconds and then fades away. I am not sure what copyright law says, I think every 8 words must be different than the original, but we would probably want to go with every fourth word must be different. That way, if the student is able to create a sensible paragraph by changing every fourth word, well, then he's getting some writing practice in, which is what we want. This level of granularity could be an instance setting called "InfringementThreatLevelWords:4"

## Discussion

The decisions cluster into eight themes. Each is enumerated as a design surface — open questions, lean choices where we have one, prior art to study before deciding.

### A. Stylometric fingerprint engine (the shared core)

**Approach.** Per-paragraph (or per-sliding-window) feature vector built from:
- Function-word frequency distribution (Mosteller-Wallace tradition)
- Sentence-length distribution (mean + variance + tail)
- Character n-gram frequencies (3-grams and 4-grams)
- Punctuation cadence (commas-per-sentence, semicolons, em-dashes, ellipses)
- Type-token ratio + Yule's K (vocabulary richness)
- Part-of-speech bigram distributions (via spaCy)
- Average syllable count per word; Flesch-Kincaid grade

The author's reference profile is the centroid (or distribution) computed over a sufficient window of their established corpus. Each new paragraph gets a similarity score (cosine on normalized vectors, or Mahalanobis distance accounting for the author's per-feature variance). Drift = score below threshold.

**Reference corpora.** Same engine, three modes:
1. *Author profile.* Built from this opus / this student's prior submissions.
2. *AI-style profile.* Built from known-AI-generated books / essays. Detects AI injection.
3. *Generic-style baseline.* A "what does ordinary English look like" reference, useful for telling "drift from author" from "drift from English."

**Live UX.** Per-keystroke is too noisy. Per-paragraph (on Enter / on save) is the practical unit. Per-sentence with running-window smoothing might give the author useful real-time signal without over-flagging.

**Prior art to study before building.**
- pystylometry (Python; explicit feature extraction)
- Stylo (R; the academic reference implementation)
- JStylo / JGAAP (Java; older but well-cited)
- GPTZero, Originality.ai, Copyleaks (commercial AI detectors — read their public methodology pages)
- Token-statistical AI detectors (perplexity, burstiness — DetectGPT and successors)

**Open questions.**
- Minimum corpus size for a useful author profile? Probably tens of thousands of words.
- Do we ship a pretrained baseline (English literature) so authors with thin corpora still get signal?
- When does the engine cold-start? First chapter has no profile to compare against.

### B. Plagiarism detection — scope honestly

**Don't roll our own at LoC scale.** Library-of-Congress-grade plagiarism corpora are the business of Turnitin / Copyleaks; rebuilding that from scratch is not where ErgodixDocs adds value.

**What we can build cheaply:**
- *Self-plagiarism within the opus.* Find accidental near-duplicate passages across chapters as the manuscript grows. Useful for fiction continuity. Cheap (n-gram fingerprint over corpus chapters; pairwise compare).
- *Opt-in commercial-API skill.* User supplies a Copyleaks / Originality.ai API key in the credential store; an `analysis` plugin calls it with the chapter text and writes the report.

**Open questions.**
- Which commercial API has the cleanest API + most permissive ToS for our use case (corpus-scale repeated checks)?
- Does the author / school want self-plagiarism on by default, or opt-in?

### C. Ergodite plugin registry

The user landed on **"ergodites"** as the name for these plugins (Message 1 addendum) — locking what was an open naming question. Etymology: "ergodic" + "-ite" suffix → small thing belonging to / participating in ergodic-text work; the user also notes the framing of each ergodite as a little "ego" that carries out a task. Avoids the Claude Code / Agent SDK "skill" collision and embeds the project's identity in the name. Drops the "analysis" vs "lens" debate — both were placeholders. New package: `ergodix/ergodites/`.

#### C.1. Pattern + module contract

Mirror `ergodix/importers/` and `ergodix/prereqs/`. Explicit registry.

```python
NAME: str                                # short id, matches CLI surface (e.g. "style-sentinel")
DESCRIPTION: str                         # one-line, surfaced in --help
REQUIRES: tuple[str, ...] = ()           # optional, e.g. ("python-docx",), ("openai-key",)
def run(corpus_root: Path, **opts: Any) -> ErgoditeReport: ...
```

`ErgoditeReport` is a frozen dataclass: timestamp, generator (ergodite name + version), per-finding records (location ref, severity, message, optional supporting JSON), summary stats. Reports never mutate the corpus — the read-only contract is a load-bearing piece of ADR 0013 compliance.

**Standalone binaries.** Python module by default. PyInstaller / Nuitka build path becomes a separate concern (and a separate ADR) when an actual non-Python audience materializes — not before.

**Open questions.**
- Does an ergodite declare which floaters / personas it's relevant to, so the CLI surfaces only relevant ones per role?
- How does an ergodite call into the OAuth-scoped Drive / Docs services? Probably the same `auth.get_*_service()` pattern the migrate importer uses.

#### C.2. Ergodite integrity — tamper resistance

The user's instinct (Message 1 addendum): *"We will want to ensure they aren't tampered with either — maybe we salt their hashes and create a dictionary of their hashes that we update with each release if they change."*

**Threat.** A hostile actor (a student trying to evade detection in the education-mode case; any local attacker more generally) swaps an ergodite module on disk to disable or neuter its analysis. Without ergodite integrity, the certificate machinery in §D is undermined — a faked AI-detection ergodite always emits "no AI here," and the certificate it produces is technically valid but materially false. **Ergodite integrity is a prerequisite for certificate trust**, not a separate concern from it.

**Approach 1: hash dictionary (the user's proposal).**

- Each release ships a manifest `ergodix/ergodites/.lock.json` listing every shipped ergodite by name with its salted SHA-256.
- Salt = the release version string (or a per-release random committed alongside the manifest). The salt is part of what gets hashed, not a separate field, so a forger can't precompute hashes for arbitrary ergodite payloads.
- At load time, ergodix recomputes the hash of each ergodite and refuses to run any whose hash doesn't match the manifest entry.
- CI regenerates the manifest as part of the release process whenever an ergodite changes.

Strengths: simple, no PKI, works fully offline. Weakness: the manifest itself becomes the trust anchor — if the attacker swaps the manifest too, integrity collapses. So the manifest needs *its own* protection (signing, embedding in the ergodix binary, or a known-good distribution channel).

**Approach 2: detached signatures (subsumes Approach 1).**

- Each release signs every ergodite (and the manifest) with the project's release key (Ed25519 / minisign / signify-style).
- Ergodix verifies the signature on each ergodite at load time using the project's public key, which is compiled into the ergodix binary or pinned in an in-tree constant.
- The hash manifest still exists but is now a signed artifact; individual ergodites carry detached signatures too.

Strengths: standard, well-understood; defends the trust anchor; the same signing infrastructure protects the certificate flow in §D, so it's reusable. Weakness: more moving parts (signing infrastructure, key custody, key rotation policy).

**Lean.** Start with **Approach 1** (hash manifest in `ergodix/ergodites/.lock.json`, regenerated on release, salted with release version). Promote to **Approach 2** (signed manifest + signed ergodites) in the same ADR / release as the certificate flow ships, since the signing infrastructure is shared.

**Threat-model honesty.** Approach 1 is *tamper-evident under a trusted distribution channel* (the wheel comes from PyPI / our release pipeline, the user hasn't been compromised). It detects accidental corruption and casual swapping. **It does not resist a local attacker who can modify both the ergodites and the manifest** — that scenario only starts to be defended at Approach 2, when the manifest is signed by a release key the local attacker can't forge. The education-mode threat model in §E *requires* Approach 2; Approach 1 is the ergonomic floor we ship while §D's signing infrastructure lands.

**Custom / user-authored ergodites.** A school deploying a custom ergodite (or a fiction author writing one for their own opus) has to escape the "ships-from-upstream" trust path. Options to evaluate in the ADR:
- A separate trust namespace: locally-trusted ergodites live under `<corpus>/.ergodix/ergodites/` and are signed (or hash-pinned) with a *local* trust key the user generates at first use.
- An allowlist of content hashes the user explicitly opts into (`ergodix ergodite trust <hash>` once per ergodite).
- Refuse to run unsigned ergodites at all in school-mode; allow them in personal-author mode behind a flag.

**Open questions.**
- Salt strategy: per-release version string, per-install random, or both (release + install)?
- Where lives the manifest at runtime — bundled in the wheel, downloaded on first launch, or both with cross-verification?
- How does an end-user write their own ergodite (custom analysis) without breaking integrity? See the three options above; pick one in the ADR.
- Performance: hashing every ergodite on every run is cheap (microseconds per file) but verifying signatures is slower. Cache verification results per-process? Per-install? At what granularity?

### D. Authorship certificate — tamper resistance

This is the most novel surface. Several sub-problems, each with a different prior-art body to consult before locking design:

**D.1. What does the certificate assert?**
- "This corpus content has hash H at time T."
- "This author signature S over hash H, verifiable against public key P."
- "These analysis results R were produced by ErgodixDocs version V over content hash H."
- "All three of the above are bound together — any of (content, results, signature) modified breaks verification."

**D.2. Where does it live?**

The user's first instinct: embed it in the `.md` itself, possibly via steganography in an embedded image, with an "embedded viewer" rendering verification status.

Honest assessment:
- Markdown is plain text. There's no "embedded viewer" surface — Pandoc / GitHub / VS Code render markdown declaratively. Steganography in a referenced image works but requires a verifier tool to run; the tool can't auto-execute when the markdown is rendered.
- A *YAML frontmatter block* with the certificate fields is the cleanest in-band carrier. Trivially readable; trivially verifiable by re-running the hash.
- Alternative: a sidecar file (`<chapter>.md.cert.json` or `<chapter>.md.sig`) like git's commit-signing pattern. Detached signatures are well-understood (PGP, minisign, Sigstore).

Lean: **YAML frontmatter for the public certificate (hash + author signature + ergodix-version), sidecar file for the encrypted teacher-only payload**. Steganography is fun but adds a verification dependency the rest of the toolchain doesn't otherwise need.

**D.3. Tamper resistance — what does the threat model assume?**

The student is the threat actor. They can:
- Edit the .md content after Ergodix ran its analyses.
- Edit the certificate / frontmatter to claim a clean bill of health.
- Replace Ergodix on their machine with a fake binary that always emits "no AI detected."
- Copy a known-good certificate from a sibling and swap content.

What protects against each:
- Content edit: the certificate is over a hash of the content; re-running the hash detects the swap.
- Certificate edit: the certificate is signed by ErgodixDocs (with a key the student can't forge — *that's the hard part*).
- Fake binary: only Ergodix-with-the-real-signing-key can emit valid certificates. The student running a fake locally produces certificates that don't verify against the public key chain.
- Swapped certificate: certificate must include the content hash; mismatched hash invalidates.

**The load-bearing question is "who holds the signing key?"** If it's a key on the student's machine, the student can extract it and forge whatever they want. So either:
- (a) The signing happens server-side (a verification service Ergodix calls), or
- (b) The signing happens in a hardware-backed enclave (TPM / Secure Enclave) the student can't extract from, or
- (c) The certificate is co-signed by a teacher-held key, so a student forgery without the teacher key is detectable.

Option (c) is the most realistic for a desktop tool. The teacher is in the loop anyway.

**D.4. Encrypted teacher-only payload.**

The user's instinct is right: the analysis results (which findings were detected) should be encrypted such that only the teacher can decrypt — preventing the student from reading "plagiarism detected page 3, paragraph 2" and then specifically rewording that paragraph to evade.

Standard pattern: hybrid encryption.
- Generate a one-time symmetric key (AES-256-GCM).
- Encrypt the findings payload with the symmetric key.
- Encrypt the symmetric key with the teacher's RSA / Curve25519 public key.
- Store both in the sidecar.
- Teacher decrypts the symmetric key with their private key, then decrypts the payload.

**D.5. Key distribution — the hardest sub-problem.**

"Teacher has the private key of every student" is the wrong direction. Teachers should hold *their own* private key, and the certificate flow should encrypt findings to the teacher's *public* key (which can be distributed openly).

For student authorship attribution, the student has their own keypair; their public key is registered with the teacher / school once at enrollment. (Not during writing; that's a one-time onboarding action.)

Prior art:
- X.509 PKI (overkill for this)
- PGP / GPG (proven; ugly UX but the model is right)
- minisign / signify (lightweight Ed25519 signatures; OpenBSD genealogy)
- Sigstore / cosign (modern; gitops-friendly; ephemeral keys)
- Identity-based encryption (IBE — encrypt to "alice@school.edu" without her public key in advance; hard to deploy)
- Signal's double ratchet (overkill for non-real-time docs)

Lean: **Ed25519 keypairs per student and per teacher, generated at onboarding, public keys exchanged once, private keys stay local in the OS keychain (the same `keyring` package ergodix already uses).** Minisign-style detached signatures over the certificate payload; libsodium-style sealed-box for the encrypted teacher payload.

**Open question.** What happens when a teacher leaves and a new teacher takes over? Re-encryption flow? Key rotation policy? Park.

### E. Education extension — student=writer, teacher=editor

ADR 0005's existing role model maps cleanly:
- Student → `--writer` floater. Their commits go on `develop`-style branches; can't push to `main`.
- Teacher → `--editor` floater. Reads student's repo via the slice-repo pattern from ADR 0006; uses comments via Pandoc CriticMarkup or VS Code review tools.

This is a happy fit because **no new role concept needs inventing**. The product surfaces are the same; the deployment topology is different (school-managed Drive, teacher's machine, student's machine).

**Open questions.**
- Drive ownership: school owns the corpus folder; student writes there; teacher reads from there. Need to map this to ADR 0014's sync transport modes (drive-mirror is the natural fit).
- Provisioning: school IT admin runs `ergodix opus init --school-mode`? Generates student keypairs? Park.
- "In-progress" visibility (the Big Brother concern raised in the source message): teachers seeing keystroke-level data crosses an ethical line. Lean: teachers see what the student commits; they don't see the writing-in-progress unless explicitly opted-in by the student. Capture this as a hard constraint.

### F. GUI surface

ErgodixDocs is a CLI today. A GUI for the education product is a substantial new surface — enough to deserve its own ADR.

**The user's GUI concept (paraphrased):**
- Side panel showing live style score per paragraph
- Red box around paragraphs that don't match the author's style profile
- Red persists until the paragraph is rewritten enough to match the profile
- Green flash on success, fade after 10s

**Implementation paths:**
- (a) VS Code extension. Reuses the editor the student is already in; LSP-style integration; no new GUI tech. Reaches the existing-user audience plus students whose schools deploy VS Code.
- (b) Electron / Tauri standalone app. More UX control; heavier distribution; more infra.
- (c) Browser-based editor (Codespaces-style). Zero install; needs a backend.

Lean: **(a) VS Code extension** for v1. ADR 0001 already mentions VS Code as a supported editor; D1 prereq installs VS Code tasks. The student's environment is already a VS Code surface in school deployments. Keep the GUI scope tight: status panel + paragraph decoration. Defer Electron / browser editors to a later ADR if (a) hits clear limits.

**Open question.** Does the existing CLI consume the same analyses the VS Code extension does? Probably yes — the extension is a thin layer over the analysis registry results.

### G. Copyright / paraphrase threshold

The user's `InfringementThreatLevelWords: 4` setting is a good shape: configurable per-instance, lives in the settings cascade (per ADR 0014), defaults set by school policy, can be tightened or loosened per opus.

**Open questions.**
- What does the threshold actually count? "Every Nth word different" is ambiguous — different at fixed positions? Different in any positions? Sliding-window edit distance?
- Does it apply to direct quotes vs. paraphrase differently? A direct quote with attribution is fine; a paraphrase that's too close is the problem.
- Real legal thresholds vary by jurisdiction and use case (fair use, academic citation rules). Recommend: treat the setting as a school-policy variable, not a legal claim; surface a disclaimer.

### H. ADR 0013 boundary check

All threads are read-only analysis. None mutates the corpus. They fit cleanly under ADR 0013 §3 ("structural analysis," gated by Spike 0010 author preferences):
- Style sentinel = author-encoded preferences (their own style is the reference).
- AI detection = ergodite output, never auto-replacement.
- Plagiarism check = ergodite output, never auto-rewrite.
- Certificate = artifact written next to / inside the corpus, but the certificate itself is not corpus content.
- Ergodite integrity check = self-protection on tooling, no corpus contact.

The closed list survives. **No ADR 0013 conflict** — but Spike 0010's interview will need extension to capture education-mode preferences (which ergodites run, what the threshold is, what the teacher sees).

The certificate-writing flow does technically write a new file (sidecar `.cert.json`); the ergodite integrity manifest is also a tooling-emitted file (`ergodix/ergodites/.lock.json`). Neither is "AI editing the corpus" — both are tooling artifacts of the same kind as the `_archive/` folder migrate creates. Worth one sentence in the eventual ADR clarifying that.

## Open questions to resolve in follow-on ADRs

Grouped by likely ADR boundaries:

**ADR-X1 (ergodite registry + integrity):**
1. ~~Naming.~~ **Resolved:** "ergodites" (per Message 1 addendum). Package: `ergodix/ergodites/`.
2. Does an ergodite declare relevant floaters/personas, so the CLI surfaces only relevant ones per role?
3. How do ergodites access OAuth-scoped Drive/Docs services?
4. Standalone-binary build path: now or later? (Lean: later.)
5. **Integrity manifest format**: `.lock.json` with salted SHA-256 per ergodite — what salt strategy (release-version, per-install random, both)?
6. **Manifest trust anchor**: Approach 1 (plain hash dictionary) or Approach 2 (detached signatures, shared with §D certificate signing)? Lean: 1 first, promote to 2 alongside §D.
7. **Custom / user-authored ergodites**: separate trust namespace, content-hash allowlist, or refuse-in-school-mode-only? Pick one in the ADR.
8. **Verification cadence**: hash every ergodite on every run (cheap), or cache per-process / per-install / per-release with invalidation rules?

**ADR-X2 (authorship certificate format + key distribution):**
9. In-band frontmatter vs. sidecar file: which carries which fields?
10. Signing-key custody: student-only, teacher-cosign, or server-side?
11. Asymmetric primitives: Ed25519 / X25519 (libsodium) vs. RSA vs. PGP?
12. Onboarding flow: who generates student keys, when, and how are public keys published?
13. Key rotation when a teacher changes / a student transfers schools?

**ADR-X3 (education-mode product surface):**
14. School-managed Drive deployment topology: mapping to ADR 0014 sync modes.
15. Big-brother boundary: teachers see commits, not keystrokes. Is this a hard constraint or a configurable default?
16. GUI strategy: VS Code extension first; defer Electron/web. Confirm.
17. CLI surface: `ergodix opus init --school-mode`? Separate `ergodix-school` package?
18. `InfringementThreatLevelWords` (and friends) — full settings vocabulary.

**Cross-cutting:**
19. Spike 0010 interview extension for education-mode preferences.
20. Spike 0014+ for "AI-detector training corpus" — which AI-generated books / essays do we use? Licensing for training data?

## Cross-references

- [ADR 0013 — AI permitted-actions boundary](../adrs/0013-ai-permitted-actions-boundary.md): the closed list this work runs against.
- [Spike 0010 — UserWritingPreferencesInterview](0010-user-writing-preferences-interview.md): structural analysis is gated by interview preferences; education mode extends the interview.
- [ADR 0005 — Roles as floaters and opus naming](../adrs/0005-roles-as-floaters-and-opus-naming.md): student=writer, teacher=editor mapping.
- [ADR 0006 — Editor collaboration via sliced repos](../adrs/0006-editor-collaboration-sliced-repos.md): teacher reads student's slice; signed-commit topology.
- [ADR 0014 — Sync transport and settings cascade](../adrs/0014-sync-transport-and-settings-cascade.md): drive-mirror mode for school-managed Drive folders; settings cascade for `InfringementThreatLevelWords` and friends.
- [Devil's Toolbox parking-lot story](../stories/SprintLog.md): pattern detection (anaphora, near-rhyme topography) — related analysis surface, same registry.
- [Fibonacci writing prompt — TBD]: the user's chapter-arc prompt for ChatGPT, referenced in Message 1. Not yet captured in the repo. Action: add `docs/fibonacci-writing-prompt.md` (or wherever the user wants it) before the climax-detection analysis is designed.

## Why we're not implementing today

The migrate arc (Story 0.2, ADR 0015, chunks 1-7) is mid-flight. Sprint 1 features (Plot-Planner, Continuity-Engine) are gated on migrate landing. This spike is the *capture* of a planning conversation so the design surface survives the session — not a green light to start coding. ADRs land first; implementation lands behind tests after.

**Next pass on this spike**: when the migrate arc closes and Sprint 1 priorities are next-up, revisit the open questions, split into ADR drafts, and re-evaluate against whatever has changed in the project's understanding.
