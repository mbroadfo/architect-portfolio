# ADR-008: One shared renderer for export and preview, separate from the exporter

- **Status:** Accepted — approved by Michael Broadfoot at the Domain Design gate, 2026-10-11.
- **Source of record:** `aidlc/spaces/default/intents/261010-architect-portfolio/inception/domain-design/decisions.md`. Component names refer to `components.md` in the same folder.

- **Context**
  - Preview must look exactly as visitors will see the exhibit (FR6.1) but must never be reachable by visitors (FR6.2).
  - The public site is a static export that never calls the API or database (Q3, FR7.4, NFR7).
  - The visual identity changes independently of the workflow rules (FR9.6).
- **Decision**
  - **SiteRenderer** is a pure transformation from a public site model to pages. It has no storage access and no Studio data access.
  - **Preview:** Publication builds a candidate version through the same projection as ADR-002 and renders it, marked "Preview — not public", for the owner only, through StudioApi.
  - **PublicSiteExporter** is the only writer to public storage and the CDN. It renders through SiteRenderer.
- **Consequences**
  - Positive: preview and export cannot drift apart, and the renderer can be tested with plain fixtures, including the export-scan invariant tests.
  - Negative: preview images need owner-only addresses from MediaLibrary.
- **Alternatives Rejected**
  - **Separate preview templates:** they would drift from the public pages.
  - **The exporter renders and writes in one component:** it would mix infrastructure side effects into template code, and preview would then need storage access.
