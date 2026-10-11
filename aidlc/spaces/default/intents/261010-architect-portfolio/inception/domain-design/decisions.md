# Domain Design — Architecture Decision Records

Status of every ADR: **Proposed**. They become accepted when Michael approves the Domain Design gate. They are then copied to `docs/decisions/`, as the project rule requires.

The component names are those in `components.md`. Sources:
- requirements: `../requirements-analysis/requirements.md`, with Amendment A1 to A1.2;
- team-practices: `../practices-discovery/team-practices.md` and the affirmed `team.md` and `project.md`;
- the decision log: D-01 to D-28 and P-01 to P-06;
- the approved Refined Mockups.

---

## ADR-001: Twelve domain components in one modular monolith

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

## ADR-002: Published versions are the only input to the public site

- **Context**
  - Nothing private may become public without the owner's approval of that exact content (charter §4, §5; D-22; NFR2).
  - The export may contain only allow-listed fields (FR4.10).
  - Re-exported pages must use the last published state of every exhibit (FR7.4).
  - At the 2026-10-11 Request Changes, the owner rejected a prototype in which unapproved data was loaded and merely hidden. The owner then approved an explicit approved-publication snapshot (Refined Mockups P4; P-06).
- **Decision** — Publication freezes a **PublishedVersion** at each confirmed Publish or Update. It is an immutable projection of one project revision containing only allow-listed public fields:
  - text;
  - images with alt text;
  - included attachments;
  - links;
  - derived badge labels;
  - the live URL, if included and authorized;
  - repositories confirmed public, with their licence;
  - primary category and featured flag.

  SiteRenderer and PublicSiteExporter receive only a public site model built from PublishedVersions and the published featured order. They have no access to Projects or to any private record. The evidence shown in the confirmation (check results, private repository names, attachment metadata) is kept in the PublicationOperation, never in the PublishedVersion.
- **Consequences**
  - Positive:
    - the boundary is structural, not a filter, so a mistake in rendering cannot leak a draft;
    - the export-scan invariant tests (NFR2) have one, small input type to reason about;
    - the prototype's approved model carries straight into the design.
  - Negative: content is stored twice (draft and published); this is a negligible cost at this scale.
- **Alternatives Rejected**
  - **Filtering the live project record at export time:** unapproved data would reach the export code path, which is exactly the failure the owner rejected.
  - **Copying public fields into the project record:** this mixes approved and draft state in one record with two writers.

## ADR-003: Project status is derived, not stored

- **Context**
  - FR3.2 defines four statuses and their allowed transitions.
  - FR7.5 and FR7.8 require two things:
    - an edit saved while a publication operation runs is excluded from it and leaves "Changes since last publish";
    - edits to a taken-down exhibit stay private.
  - A stored status would be written by both Projects (on save) and Publication (on publish and take-down).
- **Decision** — Projects keeps a draft revision that increments on every save. Publication keeps a PublicationRecord: state (never published, live, taken down) and the revision of its current PublishedVersion. Publication derives the status:

  | State | Revision | Status |
  |---|---|---|
  | never published | any | Draft |
  | live | draft = published | Published |
  | live | draft > published | Changes since last publish |
  | taken down | any | Taken down |
- **Consequences**
  - Positive:
    - one writer per fact;
    - FR3.2's transitions and FR7.8's concurrency rule hold by construction;
    - no cross-component transaction.
  - Negative: listing statuses needs both components, which StudioApi composes.
- **Alternatives Rejected**
  - **A stored status field updated by both components:** two writers, a race between save and publish, and a cross-component transaction.

## ADR-004: Publication operations run one at a time per exhibit and are idempotent

- **Context**
  - Publish, update and take-down for one exhibit must run in confirmation order, with the public state always equal to the last successful action (FR7.8).
  - They must be safe to repeat (FR7.6).
  - Featured order is published by its own confirmation (FR9.7).
  - Content must be public or removed within 5 minutes (FR7.4, FR8.2).
- **Decision** — Each confirmation creates a PublicationOperation with an idempotency key. Operations are processed one at a time:
  - per exhibit for publish, update and take-down;
  - one at a time overall for featured-order changes and the shared pages they touch.

  A repeated confirmation with the same key returns the original operation. A failed operation leaves the previous public state and is shown with a retry. Every completed operation writes an ActivityEntry (FR7.7). The queueing mechanism is chosen in NFR Design.
- **Consequences**
  - Positive: no mixed public state; retries and double clicks are harmless; the activity log comes from the same record.
  - Negative: a burst of confirmations is processed sequentially, which is acceptable for a single owner.
- **Alternatives Rejected**
  - **Concurrent operations with last-writer-wins:** this violates FR7.8.
  - **A global lock across all exhibits:** it is simpler but would block unrelated exhibits for no benefit.

## ADR-005: The link checker is stateless and isolated; Publication keeps its results

- **Context** — NFR17 requires the check to run where a bypass reaches no private network, AWS-internal endpoint, secret or database, "under an execution identity with no other permissions". FR10.5 requires the result to be recorded with its time and shown in the Publish confirmation.
- **Decision** — LinkChecker has no dependencies, no storage and no secrets: a URL goes in and one labelled result comes out. Publication calls it while preparing a confirmation, one live URL per exhibit, and stores the result as a LinkCheckRecord. The record is never exported (FR4.10 allow-list).
- **Consequences**
  - Positive: the component can be deployed on a zero-permission identity with public-only egress, and a successful SSRF bypass finds nothing of value.
  - Negative: the result has to travel back to Publication instead of being written in place.
- **Alternatives Rejected**
  - **The checker stores its own results:** it would need database credentials, contrary to NFR17.
  - **Running the check inside Publication:** Publication's identity has database access.

## ADR-006: MediaLibrary owns the bytes; Projects owns how an exhibit uses them

- **Context**
  - Uploads are untrusted and security-sensitive:
    - content checks by file signature;
    - HEIC conversion;
    - pixel and decode limits;
    - ZIP ratio limits and XXE protection;
    - single-use upload authorizations (FR4.2, FR4.4, FR4.8).
  - Alt text, lead image and image order are exhibit content: they are checked at Publish (FR7.3, D-19) and versioned with the draft.
  - Published images must be metadata-free derivatives; originals stay private (FR4.2, FR4.9, NFR2).
- **Decision**
  - **MediaLibrary** owns MediaAsset and UploadAuthorization:
    - validation and conversion;
    - private originals;
    - attachment metadata and entry listing;
    - public derivatives, produced only on request from the exporter.
  - **Projects** owns ExhibitImage and ExhibitAttachment: which assets, order, lead, alt text, captions and labels. It accepts an asset only after MediaLibrary confirms it passed validation.
- **Consequences**
  - Positive:
    - one component, and one review target, touches untrusted bytes;
    - exhibit edits never re-process files;
    - its decoding can later get its own execution identity without touching Projects.
  - Negative: attaching an image needs a cross-component check.
- **Alternatives Rejected**
  - **Projects owns files completely:** this would mix untrusted-file processing into the most frequently changed component.
  - **MediaLibrary owns alt text:** alt text is exhibit content, and it would then escape draft versioning.

## ADR-007: A provider-independent description assistant; provider chosen later

- **Context**
  - FR5.4 requires a provider-independent interface with server-side adapters on an open framework.
  - Spending needs the owner's approval and a monthly limit (FR5.8).
  - Private repository content may go only to a provider approved for it (FR5.9).
  - The Publish confirmation must show AI-originated text and the private repositories that informed it (FR7.2).
  - The provider choice depends on its cost per call, which NFR Design establishes before the owner approves spending.
- **Decision** — DescriptionAssistant owns:
  - the provider port and its adapters;
  - AiSpendPolicy, AiProviderApproval and AiUsageMonth;
  - Suggestion records with source files, source repositories and provider.

  When the owner inserts a suggestion, StudioApi passes the suggestion's recorded provenance to Projects, which stores a TextProvenance record with the edited field. The provider and framework are chosen in NFR Design.
- **Consequences**
  - Positive:
    - providers can be swapped by configuration;
    - the approvals are checked in one place before any call;
    - provenance survives editing and reaches the Publish confirmation.
  - Negative: provenance is recorded per field, not per sentence. Text inserted and then rewritten is still reported as AI-originated, which is the conservative direction.
- **Alternatives Rejected**
  - **Choosing a provider now:** this needs cost data and owner spending approval that Domain Design cannot give.
  - **No provenance record:** FR7.2 could not be met.

## ADR-008: One shared renderer for export and preview, separate from the exporter

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

## ADR-009: Nightly content backup reads through the owning components

- **Context**
  - NFR10 requires a nightly export of Studio content to private, versioned, encrypted storage, with a tested restore.
  - The free database tier has no automated backups.
  - Uploaded files are already in versioned storage.
- **Decision** — ContentBackup asks Projects, MediaLibrary, DescriptionAssistant and Publication for their records and writes one export. The scheduling and tooling are chosen in NFR Design and Infrastructure Design.
- **Consequences**
  - Positive: entity ownership is preserved, and the export format does not depend on the storage layout.
  - Negative: each owner exposes an export function.
- **Alternatives Rejected**
  - **A database-level dump job outside the component model:** simpler, but it bypasses ownership and ties restore to the storage layout. NFR Design may still choose it as the mechanism, provided restore is tested; this ADR would then be revised.

## ADR-010: Categories as a relationship; featured line-up separate from the published order

- **Context**
  - FR9.8:
    - four fixed categories with fixed addresses;
    - at most one primary category in v1;
    - modelled as a relationship so several classifications need no migration later (D-27).
  - FR9.7:
    - up to five featured, drafts included;
    - featured status is published with each exhibit;
    - carousel order reaches the public site only through "Update featured order";
    - take-down releases the slot and it is not restored on republish (FR8.2).
- **Decision**
  - **Projects** owns:
    - Category, as reference data seeded with the four fixed categories;
    - CategoryAssignment, with a `primary` flag;
    - the draft FeaturedLineup;
    - the featured flag on Project.
  - **Publication** owns PublishedFeaturedOrder, changed only by a featured-order operation. Take-down removes the project from the line-up and clears its featured flag, through Projects.
- **Consequences**
  - Positive:
    - classification can grow without migration;
    - the draft order never leaks into the public carousel;
    - take-down semantics live in one operation.
  - Negative: two orderings exist (draft and published), by design.
- **Alternatives Rejected**
  - **A single `category` field on Project:** this contradicts FR9.8's model.
  - **One featured order applied immediately:** it would publish draft ordering without confirmation, contrary to FR9.7.

## ADR-011: StudioApi enforces ownership on every request and composes cross-component flows

- **Context**
  - Every Studio operation must be authorized on the server (FR1.2). Ownership is matched on issuer and subject, never email (FR1.1).
  - Some flows span components. Implemented as direct calls, they would create cycles:
    - Discover joins repositories with their project links (FR2.1, FR2.3);
    - inserting a suggestion records its provenance in Projects (FR5.2, FR7.2).
  - Rate limits apply to several endpoints (NFR16).
- **Decision**
  - **StudioApi** calls OwnerAccess before any operation and applies rate limits before any provider call, upload authorization or link check. It composes:
    - Discover, by listing from RepositoryCatalog and looking up links in Projects;
    - suggestion insertion, by reading provenance from DescriptionAssistant and saving it through Projects;
    - status listing, from Projects and Publication.
  - **OwnerAccess** is a small, separately reviewed component that holds no data.
- **Consequences**
  - Positive:
    - the dependency graph stays acyclic;
    - the owner-only invariant test has one place to target;
    - domain components stay free of HTTP and identity concerns.
  - Negative: StudioApi carries some orchestration logic, which must stay thin; business rules belong to the domain components.
- **Alternatives Rejected**
  - **Each component checks authorization itself:** the rule would be duplicated, and an endpoint could miss it.
  - **Direct calls between components:** Projects → DescriptionAssistant and RepositoryCatalog → Projects would form cycles.
