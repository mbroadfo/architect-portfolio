# Domain Design — Architecture Decision Records

Status of every ADR: **Proposed** (ADR-001 to ADR-012). They become accepted when Michael approves the Domain Design gate. They are then copied to `docs/decisions/`, as the project rule requires.

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

  The candidate version is projected from the reviewed draft revision when the confirmation is prepared, and it is the version published if the confirmation is accepted (ADR-012).
  - **Public site model.** Publication is its only builder. The model contains:
    - the current PublishedVersion of every live exhibit;
    - the PublishedFeaturedOrder;
    - the categories derived from those versions.

    Each version freezes its primary category with slug, name and position, so the model never reads Projects' reference data. SiteRenderer and PublicSiteExporter receive only this model and have no access to Projects or to any private record.
  - **Repositories.** They reach a PublishedVersion only as repositories confirmed public at preparation, with their licence. A free-form link that points at a repository host blocks Publish (FR4.3).
  - **Confirmation evidence.** The check results, private repository names and attachment metadata the owner was shown are kept in the ConfirmationTicket, never in the PublishedVersion.
- **Consequences**
  - Positive:
    - the boundary is structural, not a filter, so a mistake in rendering cannot leak a draft;
    - the export-scan invariant tests (NFR2) have one, small input type to reason about;
    - the prototype's approved model carries straight into the design.
  - Negative:
    - content is stored twice (draft and published); this is a negligible cost at this scale;
    - renaming a category, a roadmap item, will need a site-wide republish, because names are frozen into versions.
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
    - status itself needs no cross-component transaction. The atomic acceptance and commit steps (ADR-012, ADR-004) exist for publication, not for status.
  - Negative: listing statuses needs both components, which StudioApi composes.
- **Alternatives Rejected**
  - **A stored status field updated by both components:** two writers, a race between save and publish, and a cross-component transaction.

## ADR-004: One site-wide, fenced sequence for every operation that changes public pages

- **Context**
  - Publish, update and take-down of any exhibit, and "Update featured order", all rewrite shared public pages: the home page, carousel, category pages and counts (FR7.4, FR8.2, FR9.7).
  - Operations for one exhibit must run in confirmation order, and the public state must always equal the last successful action (FR7.8).
  - Operations must be safe to repeat (FR7.6) and complete on the public site within 5 minutes (FR7.4, FR8.2).
  - The first draft serialized operations per exhibit only. The architecture review (R-02) showed that two exhibits' operations could then build shared pages from stale views, so a taken-down exhibit could reappear on the home page. The owner required every shared-page operation to be serialized across projects (Request Changes, 2026-10-11).
- **Decision**
  - **One sequence.** Every accepted publication operation gets the next number in one site-wide sequence. Operations run one at a time in that order, whatever exhibit they concern. This also keeps each exhibit's operations in confirmation order.
  - **Fresh start for each run.** Each run starts from the last committed public state (its base generation), applies its own change, builds the complete public site model, and exports the exhibit's objects and every shared page the change affects.
  - **Run-time basis check.** When an operation starts, every operation accepted before it has committed or failed. It re-checks its state-dependent preconditions against that committed state, and if any no longer holds it fails as "basis changed — review again", with no public change:
    - the action is legal for the exhibit's publication state;
    - the carousel limit holds;
    - for "Update featured order", the published order version and the set of live featured exhibits equal its basis.

    The acceptance check of the ticket's basis (ADR-012) refuses early; this check is the guarantee.
  - **Attempts, leases and fencing.** Every attempt (first run, automatic retry or manual retry) takes a lease on the sequence and a new token from a strictly increasing site-wide counter.
    - The lease outlasts the attempt's maximum execution time, and an attempt starts only after the previous lease has expired or been released, so two attempts never run at once.
    - PublicSiteExporter records the highest accepted token in a site-wide fence that is never deleted, and refuses any write with a lower token, so a stalled attempt cannot overwrite newer state or recreate a withdrawn object. The fence and the exporter's other records live in a private store, never in public storage.
    - Because each manual retry gets a fresh token, tokens used by later operations never block it.
  - **Commit.** After a successful export, one transaction commits, only if the attempt's token still holds the lease and the site generation still equals its base generation:
    - the new publication records and featured order;
    - the next site generation;
    - the ActivityEntry;
    - for a take-down, the release of the draft featured slot through Projects.
  - **Idempotency.** A repeated confirmation of the same ticket returns the operation already accepted. A retry re-runs that same operation, and only when no later operation for the same exhibit has succeeded; otherwise it is marked superseded.
  - **Failure.** A failed operation restores public storage to the last committed generation and is shown with a retry.
  - **Abandoned attempts.** An attempt can stop without reporting (a crash, or a timeout past its lease). When its lease expires without a commit or a completed restore, a recovery attempt runs before anything else. Lease expiry triggers it, backed by a periodic check, so it never waits for a later operation. The recovery attempt takes a new lease and a higher token, marks the abandoned attempt failed, and restores public storage to the last committed model. An abandoned attempt counts as one of its operation's attempts, including against a take-down's automatic-attempt budget.
  - **Retry window.** A manual retry of a Publish, Update or featured-order operation is allowed only while its ticket is unexpired; after that the owner prepares again. A take-down retry is always allowed. A failed take-down that a later Publish or Update supersedes is marked superseded. That confirmation warns that the exhibit stays public. A failed take-down is retried automatically, ahead of later operations, a bounded number of times. Once those attempts are exhausted it is marked failed, releases the lease and the sequence moves on, so the queue is never blocked. The Studio then shows a persistent "Take-down failed — still public" alert with a manual retry (FR8.1).
  - **Five minutes.** NFR Design sets the per-attempt time budget and the number of automatic take-down attempts so that an operation, the work queued ahead of it and its automatic attempts finish within 5 minutes. With a single owner the queue stays short. An operation that still fails is restored and reported as failed, never as complete.
  - **Mechanism.** The queue, lease and fencing implementation are chosen in NFR Design. The properties above are fixed here.
- **Consequences**
  - Positive:
    - no shared page can be built from a stale view;
    - no stale run can overwrite newer state;
    - every completed state equals the last successful operation;
    - preconditions that depend on public state are re-checked against the state the operation actually runs on;
    - retries and double clicks are harmless;
    - the activity log and the site generation come from the same commit.
  - Negative:
    - unrelated exhibits wait for each other, which is acceptable for one owner;
    - each operation re-exports shared pages, a few small static files.
- **Alternatives Rejected**
  - **Per-exhibit queues (the first draft):** shared pages could be written from stale views (review R-02).
  - **The sequence number as the fencing token (the second draft):** a retry could not be told apart from the stalled attempt it replaced, and a retry after later operations would have been blocked. Tokens are therefore per attempt.
  - **Concurrent operations with last-writer-wins:** violates FR7.8.
  - **Per-exhibit queues plus a lock only around shared-page writes:** this also works, but it needs two coordination mechanisms. The order in which shared pages are written would then differ from the order in which operations were accepted. One sequence is simpler and gives a single, auditable order.

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
  - **Projects** owns ExhibitImage and ExhibitAttachment: which assets, order, lead, alt text, captions and labels. It accepts an asset only after MediaLibrary confirms it passed validation and was uploaded for the same project; an asset from another project is refused.
  - **StudioApi** requests an upload authorization from MediaLibrary only for a project that Projects confirms exists. The authorization binds the project, size and type.
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
  - **Publication** owns PublishedFeaturedOrder, the ordered list of published featured exhibits.
    - Publishing or updating an exhibit as featured, when it is not already listed, appends it at the end.
    - Publishing or updating it as not featured removes it.
    - Take-down removes it from the published order. Through Projects, it also removes the exhibit from the draft line-up and clears its featured flag, so the slot is not restored on a later publish.
    - "Update featured order" publishes exactly the candidate order frozen in its ticket (ADR-012). The ticket is taken from the draft line-up, restricted to exhibits that are live and published as featured, and its run-time basis check must pass (ADR-004).
    - In every case the other entries keep their relative order.
    - Publish is blocked if it would put more than five exhibits in the published carousel.
    - A featured-order confirmation binds to the line-up revision and the published order version that were shown (ADR-012).
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
  - **Health endpoint.** The single unauthenticated route is `GET /health`. It is rate-limited, reads no domain data, and returns a fixed status body with no version, configuration, project or owner information. Every other route requires the owner.
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

## ADR-012: A confirmation is bound to the exact reviewed revision and inventory

- **Context**
  - Nothing may become public except through the owner's explicit confirmation of exactly what the confirmation listed (FR7.1, FR7.2, D-22).
  - Preparation and confirmation happen at different moments, and the owner may have the editor open in another tab (FR3.4).
  - The architecture review (R-01) found the first draft did not tie the confirmation to what was reviewed. The owner required three things (Request Changes, 2026-10-11):
    - the confirmation is bound to the exact reviewed revision and inventory;
    - a stale confirmation is rejected and the owner reviews again;
    - the revision check is atomic with accepting the operation.
- **Decision**
  - **Preparation.** Preparing Publish or Update reads draft revision N and freezes, at that moment, two things:
    - the candidate PublishedVersion projected from revision N;
    - the complete inventory shown to the owner, including check results, visibility and attachment entries.

    Both go into a single-use ConfirmationTicket with an expiry and a digest of the inventory. Every ticket records its basis, the public state it was prepared against:
    - the exhibit's last accepted operation, counting operations accepted but not yet run;
    - for featured changes, the published featured order version and the set of live featured exhibits.

    A featured-order ticket also freezes the exact candidate order shown and binds to the draft line-up revision. Every line-up change increments that revision, including a slot released by take-down.
  - **Acceptance.** The confirmation sends the ticket id, the inventory digest that was displayed, and a confirmation id generated once per confirmation. A repeat of the same confirmation returns the accepted operation, while a different confirmation presenting a used ticket is refused. In one atomic step, Publication:
    1. checks that the ticket is unused, unexpired and of the right kind, that the digest matches, and that the exhibit's last accepted operation still equals the ticket's basis;
    2. calls the Projects revision guard. The guard succeeds only if the draft revision is still N. It records the accepted operation by a conditional write to the project record, without changing the revision, so a concurrent save conflicts with it. Publishing then shows "Published", and a later save shows "Changes since last publish". Every saved draft change, including images, attachments, category, featured flag and rights flags, increments the revision;
    3. for a featured-order ticket, calls the Projects line-up guard in place of the revision guard. The guard succeeds only if the line-up revision is unchanged, and records the acceptance in the line-up's `publicationGuard` by a conditional write that does not change the revision;
    4. marks the ticket used;
    5. takes the next sequence number and records the PublicationOperation.

    If any check fails, nothing is accepted. The owner sees that the exhibit changed since review and prepares again.
  - **What is published.** The operation publishes the ticket's frozen candidate version (its `sourceRevision` always equals N), or for a featured-order ticket its frozen candidate order. Preconditions that depend on public state are re-checked when the operation runs (ADR-004).
  - **Mechanism.** NFR Design chooses it, for example one database transaction spanning the guard and the operation insert, with each component writing only its own records.
- **Consequences**
  - Positive:
    - a stale confirmation is always refused;
    - because the candidate is frozen at preparation, even a mechanism failure could not publish content the owner did not see;
    - an edit that lands just after acceptance stays private, and the status correctly becomes "Changes since last publish" (ADR-003);
    - repeated confirmations of one ticket are idempotent (ADR-004).
  - Negative:
    - the owner must re-prepare after any edit, which is intended;
    - tickets and frozen candidates add stored records;
    - the atomic step spans two components' records, so their persistence must support it.
- **Alternatives Rejected**
  - **Re-project the draft at confirmation time:** content edited after review could be published.
  - **Check the revision only, without freezing the candidate:** this relies wholly on the atomic check, with no second line of defence.
  - **Lock the project against edits while a confirmation is open:** the owner could be locked out by an abandoned tab. Optimistic refusal with re-review is simpler and never blocks editing.
