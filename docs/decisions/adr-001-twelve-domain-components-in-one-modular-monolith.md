# ADR-001: Twelve domain components in one modular monolith

- **Status:** Accepted — approved by Michael Broadfoot at the Domain Design gate, 2026-10-11.
- **Source of record:** `aidlc/spaces/default/intents/261010-architect-portfolio/inception/domain-design/decisions.md`. Component names refer to `components.md` in the same folder.

- **Context**
  - Charter §6 asks for "a modular monolith with clean contracts; public and administrative security boundaries kept separate".
  - The requirements concentrate risk in four places, each needing its own invariant tests and an independent security review (team practice):
    - owner-only access (FR1, NFR1);
    - untrusted uploads (FR4.2, FR4.4, FR4.8);
    - SSRF-safe link checks (NFR17);
    - the publication boundary (FR7, FR4.10, NFR2).
  - Deployment topology belongs to Units Generation, not here.
- **Decision** — Decompose into twelve components:
  - StudioWeb, StudioApi, OwnerAccess;
  - Projects, MediaLibrary, RepositoryCatalog, DescriptionAssistant, LinkChecker;
  - Publication, SiteRenderer, PublicSiteExporter;
  - ContentBackup.

  Each security-critical rule has exactly one owning component, and every entity has exactly one owner. The components are modules with clean contracts, not deployables.
- **Consequences**
  - Positive:
    - each boundary is small enough to review and test on its own;
    - the link checker can be given a zero-permission identity;
    - drafts never share a record with approved content;
    - Units Generation can group modules freely.
  - Negative:
    - more modules to keep tidy;
    - some cross-component flows must be composed in StudioApi to keep the graph acyclic (ADR-011).
- **Alternatives Rejected**
  - **Three coarse components** (Studio back end, public site, Studio client): the four critical rules would share one component, so they could not be isolated or reviewed individually. It also cannot give the link checker a zero-permission identity, and it lets drafts and published content share a model.
  - **One component per screen or endpoint:** entity ownership would be ambiguous, and status and allow-list rules would be duplicated.
