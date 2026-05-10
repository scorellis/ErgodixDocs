# IP strategy — trademark "ErgodixDocs" + patent decision

- **Status**: parking-lot (activate via attorney consultation, not when convenient)
- **Origin**: extracted from monolithic [SprintLog.md](../SprintLog.md) parking-lot section on 2026-05-10.
- **Hard deadline**: ~2027-05-02 (US patent grace-period filing deadline; see Key dates below).

## As / So that

As a publisher, so that the name, brand, and any patentable architecture decisions are protected before commercial launch — without over-spending on IP before the product has a real audience.

## Value

Trademarks protect the user-facing brand cheaply and durably; patents protect novel architecture but cost real money and have hard deadlines that started ticking when the repo went public; doing both right before commercialization is the difference between a defensible launch and a launch that gets copied by someone with a bigger budget.

## Risk

NOT consulting a real IP attorney is the biggest risk — software patent strategy in particular is non-DIY territory; the US 12-month grace period on first public disclosure (started ~2026-05-02 when this repo was first made public) caps when you can still file a US utility application that claims novelty; most non-US jurisdictions require absolute novelty so the public-disclosure window has likely already foreclosed those countries; spending $5K–$25K on a patent that gets rejected for prior art (decades of installer / configuration tools — Chef, Puppet, Ansible, Nix, Homebrew formulae, MacPorts, dpkg, etc. — set a high prior-art bar for "multi-phase orchestrator with consent gate") is real money wasted.

## Assumptions

The author has the financial position to pursue real IP protection; an IP attorney is the right next step; trademark protection is high-value-low-cost (good ROI) regardless of whether patents make sense; the architecture-level concepts (cantilever orchestrator, configure phase, preamble cascade) are novel-feeling but face real prior-art questions that a search would surface.

## Tasks (when activated — talk to an IP attorney first)

- [ ] **Trademark "ErgodixDocs"** (and potentially "Ergodix" and any related marks) at USPTO via TEAS — ~$350 filing fee + attorney costs; protects the brand which is what users actually associate with the product. High value, low cost, fast.
- [ ] **Provisional patent application** if patenting is pursued — ~$65 USPTO fee + ~$1.5K attorney for drafting. Locks in priority for 12 months while deciding whether to commit to a full non-provisional application. **Hard deadline: ~2027-05-02 to file in the US** (12-month grace period from first public disclosure ~2026-05-02; outside US is likely already too late).
- [ ] **Prior-art search** before any non-provisional commitment — patent attorney runs this. Architecture-level patents face decades of installer / configuration / build-tool prior art. Likely candidates: cantilever's 5-phase orchestrator + needs-interactive configure phase; ergodic-typesetting preamble cascade; AI-prose-boundary enforcement model.
- [ ] **Non-provisional patent application** if the prior-art search clears it and the business case justifies $5K–$25K + 18–36 months of prosecution. Otherwise drop the patent path.
- [ ] **Domain name protection** — register `ergodix.com` / `ergodix.app` / `ergodixdocs.com` / etc. before someone else does (cheap, ~$15/yr each).
- [ ] **Copyright** — already automatic on every commit; nothing to file. The PolyForm Strict license already establishes copyright posture.

## Key dates

- ~2026-05-02 — first public disclosure (repo went public). US patent grace period clock started.
- ~2027-05-02 — US patent application deadline if pursuing the grace-period filing.

## Key counsel question

"Given decades of installer / configuration-management prior art, is there a defensible novel claim worth filing on the multi-phase orchestrator + configure-phase pattern, or should we focus on trademark + brand + the actual product instead?"
