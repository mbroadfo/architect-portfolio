# Units of Work

**Inputs:**
- components — `../domain-design/components.md` (12 components);
- decisions — `../domain-design/decisions.md` (ADR-001 to ADR-012);
- requirements — `../requirements-analysis/requirements.md`;
- the plan Michael approved on 2026-10-11 (`units-generation-questions.md`): 11 units, with a React and TypeScript renderer and the clarifications recorded under Q6;
- Amendment D1 (2026-10-11), which adds the delivery-only unit U0, making 12 units in total. U0 is classed `service` because its slice runs as a service locally, but its S1 to S3 output is never deployed.

The dependency graph is in `unit-of-work-dependency.md`, and the mapping from requirements to units is in `unit-of-work-story-map.md`.

Units are **units of construction work**: code ownership and design scope. Delivery Planning splits each unit into one or more Bolts of one to two days (team practice). Units are not a promise of separate databases or separate processes. Several units deploy into the same Python back-end package (see Deployment model). The plan declares `skeleton: off`, so no unit is shaped as a walking skeleton. This document describes topology only; Delivery Planning chooses the order.

## Unit Summary

| Unit ID | Directory | Name | Kind | Components | Deployment model | Size |
|---|---|---|---|---|---|---|
| U0 | u0-walking-slice | walking-slice | service | — (delivery-only; owns no component) | S0 merges (CI baseline and repository layout); S1 to S3 run locally from a demonstration branch, never merged or deployed | L |
| U1 | u1-contracts | contracts | spec | — (contracts between units) | Embedded: consumed in place by U3 to U11 | M |
| U2 | u2-platform | platform | packaging | — (shared infrastructure) | Standalone Terraform roots | L |
| U3 | u3-studio-api | studio-api | service | StudioApi, OwnerAccess, Projects, RepositoryCatalog | Standalone: hosts the back-end Python package | L |
| U4 | u4-media-library | media-library | service | MediaLibrary | Shared: a module in the back-end package, plus a standalone isolated upload-processing function | L |
| U5 | u5-description-assistant | description-assistant | library | DescriptionAssistant | Embedded in the back-end package | M |
| U6 | u6-link-checker | link-checker | service | LinkChecker | Standalone isolated function | M |
| U7 | u7-site-renderer | site-renderer | library | SiteRenderer | Embedded in U8 (publication) and U11 (preview) | M |
| U8 | u8-site-publisher | site-publisher | service | PublicSiteExporter | Standalone Node function, invoked only by U9 | M |
| U9 | u9-publication | publication | service | Publication | Shared: a module in the back-end package, plus the sequence-runner and recovery entry points | XL |
| U10 | u10-content-backup | content-backup | service | ContentBackup | Shared: a scheduled entry point of the back-end package | S |
| U11 | u11-studio-web | studio-web | ui | StudioWeb | Standalone static assets on the CDN; all owner data and actions are gated by the API | L |

Every one of the 12 components belongs to exactly one of U1 to U11. U0 is a delivery-only unit added by Amendment D1 (2026-10-11, approved by Michael at the Delivery Planning gate). It owns no component and changes no boundary.

**Size scale** (relative effort, in one-to-two-day Bolts, confirmed by Delivery Planning):

| Size | Bolts |
|---|---|
| S | 1 |
| M | 2 |
| L | 3 to 4 |
| XL | 5 or more |

## Cross-Unit Constraints (owner clarifications at Plan Approval, 2026-10-11)

1. **Static public site.** React runs only at publication time to generate static files, never as request-time server rendering. Visitors are served only static CDN assets. No visitor-facing Node service exists, and public pages call no API (FR7.4, NFR7).
2. **U7 is one shared library.** It is the only renderer, used by publication (inside U8, on Node) and by the owner's authenticated preview (inside U11, in the browser) (FR6.1, ADR-008). It must therefore be **runtime-neutral**:
   - a pure function from a snapshot and an asset resolver to HTML strings and island assets;
   - no Node, DOM, network, clock or random-number use during rendering;
   - deterministic output.

   The asset resolver is the only difference between the two uses: publication maps an image reference to its public path, and preview maps it to an owner-only, short-lived address. A **parity test** renders the same fixture snapshots with the same resolver in Node and in a browser and requires identical HTML. That test, not the shared code alone, is what keeps preview and the live site from drifting.
3. **U8 sees only approved snapshots.** It receives nothing but the explicitly approved, allow-listed public snapshot, which U9 builds from accepted PublishedVersions (ADR-002). It never receives drafts, preview candidates, confirmation evidence or private data. Because of this, preview is rendered in U11, not in U8 (see Preview below).
4. **Python is authoritative for publication.** U9 owns sequencing, atomic confirmation, run-time basis checks, leases, fencing-token issue, conditional commit, recovery and take-down. U8 makes no publication or authorization decision. It executes the export U9 hands it and enforces the token U9 issued. When it refuses a write or fails, the operation fails and U9 decides what happens next (ADR-004).
5. **Minimal public JavaScript.** Pages are complete static HTML that reads and navigates without JavaScript. The carousel, gallery lightbox and similar behaviour are small, separately loaded scripts attached only where needed ("islands"). The site is never hydrated as a whole. NFR Design sets the payload budget, and the Lighthouse check (NFR5) enforces it.
6. **Versioned, schema-validated contract.** U1 owns a versioned JSON Schema for the public site snapshot and for the publish request. The schema enforces the allow-list structurally, with no additional properties. U9 validates every snapshot before sending it, and U8 validates it again on receipt, refusing an unknown version or any field outside the schema.
7. **ADR-012 atomicity is preserved.** These units share one Python package and one database, so the cross-component atomic steps run in one process and one database transaction, each module writing only its own records:
   - U3: Projects, with its revision and line-up guards;
   - U9: Publication, acceptance and commit;
   - U5 and U10.

   They must stay in that package and database. A split that moved Projects or Publication into another process or store would break ADR-012 and is out of bounds.

## Unit Definitions

### U0 — walking-slice (service, L; delivery-only, Amendment D1)

- **Owns:** no component.
- **Delivers:**
  - **S0:** the repository layout and the baseline CI. This includes the aggregate required check, gitleaks, the dependency audit, CodeQL, the content-bound security-review check, and a build-time guard against shipping a fake identity provider. It merges to `main`.
  - **S1 to S3:** a thin, local, end-to-end walking slice. A project is created, saved, previewed and published as a static page, using a local fake identity provider, a MongoDB container and the local filesystem.
- **Constraints:**
  - S1 to S3 stay on the `slice/walking-slice` branch as a reference implementation and are never merged or deployed. Their code reaches `main` only through the owning units' own reviewed Bolts (U3, U7, U8, U9, U11).
  - Placeholder data only.
  - The published output is validated against the approved C2 schema.
  - The branch is archived once U9 lands.

### U1 — contracts (spec, M)

- **Owns:**
  - the Studio API description (OpenAPI), used by U11 and implemented by U3, U4, U5 and U9;
  - the **public site snapshot schema** (JSON Schema, versioned with `schemaVersion`), the allow-listed model that U9 produces and U8 and U7 consume;
  - the **publish request** U9 → U8: snapshot, asset-copy manifest, fencing token, operation id, and restore or export mode;
  - the **preview payload** U9 → U11: a candidate snapshot under the same schema and version, plus a separate image-address map (image reference → owner-only, short-lived address). The map is kept outside the snapshot, so the snapshot schema never carries a private address;
  - the **back-end module interfaces** (Python ports) between U3 and U4, U5, U9 and U10. These cover the Projects attach check and guards, the MediaLibrary queries, the Publication and DescriptionAssistant services, and the route registration described in "Call direction inside the back end";
  - the **link-check request and result** U9 → U6;
  - the **upload processing result** U4, a record object the isolated processor writes for U4's module to ingest;
  - the **private derivative key layout**, so U9 can name derivatives in the asset-copy manifest and U8 can read only those keys.
- **Delivers:** schemas, generated types for Python and TypeScript, and contract tests that both sides run.
- **Constraints:**
  - The snapshot schema mirrors the FR4.10 allow-list exactly. Adding a public field is a schema version change that needs review.
  - Contract Design formalises the shapes.

### U2 — platform (packaging, L)

- **Owns:** the shared Terraform foundation for `preview` and `production`:
  - the state backend;
  - the GitHub OIDC provider and roles;
  - public and private storage;
  - the CDN distribution with the security headers (NFR15) and the download response policy (FR4.4);
  - the API entry point;
  - the database project;
  - the SSM parameter namespace;
  - the scheduler and queue resources;
  - the separate DNS root (FR10.2, FR10.4; team practice, Deployment).
- **Delivers:** Terraform roots and modules, and the bootstrap procedure.
- **Constraints:**
  - It creates nothing without Michael's approval: the preview environment, new paid services, production runs and DNS (project rules).
  - Each other unit's own functions and roles are specified in that unit's Infrastructure Design, inside this foundation.

### U3 — studio-api (service, L)

- **Owns:** StudioApi, OwnerAccess, Projects and RepositoryCatalog. It hosts the back-end Python package that U4, U5, U9 and U10 add modules to.
- **Delivers:**
  - the owner-only API: issuer plus subject match, and 401/403 on every route except the data-free `GET /health`;
  - rate limits (NFR16);
  - projects with optimistic concurrency, revision and line-up guards, categories and the featured line-up;
  - Discover, through a read-only GitHub credential that fails closed on visibility.
- **Constraints:**
  - OwnerAccess and the guards are security-sensitive and need the independent security review (team practice).
  - The package must host U9's acceptance and commit transactions (constraint 7).

### U4 — media-library (service, L)

- **Owns:** MediaLibrary.
- **Delivers:**
  - single-use upload authorizations bound to project, size and type;
  - an isolated **upload-processing function** with memory and time limits, and with no database, secret or network access beyond its storage prefixes. It covers signature checks, HEIC conversion, the pixel limit before decode, safe ZIP and XML reading, metadata extraction, and metadata-free derivatives (FR4.2, FR4.4). It writes its validation result as a record object to a private results prefix. U4's module, running in the back-end package, takes that record into the database when the asset's status is read or an attach is checked, so the isolated function never needs database access;
  - the attach check (validated, and uploaded for the same project).
- **Derivatives:** they are produced at upload time, so untrusted decoding happens only in the isolated function. They stay in private storage, and they become public only when U9 names them in a publish request and U8 copies them. This realises "public derivatives only on request from export" in `components.md`: making them public, not encoding them, is what happens on request.
- **Constraints:** untrusted bytes are handled only in the isolated function. This is a security-sensitive path that needs the independent review.

### U5 — description-assistant (library, M)

- **Owns:** DescriptionAssistant.
- **Delivers:**
  - the provider-independent port and its adapters;
  - the spend gate and monthly limit;
  - provider approval for private content;
  - Suggestion records with their provenance.
- **Constraints:**
  - It is embedded in the back-end package, and its credentials come from SSM through the API role (FR5.5).
  - The provider is chosen in NFR Design, and no paid call is made before Michael approves spending (FR5.8).

### U6 — link-checker (service, M)

- **Owns:** LinkChecker.
- **Delivers:** the NFR17 check as a standalone function on an execution identity with no other permissions, no VPC, no database and no secrets. It returns one of three labels (FR10.5).
- **Constraints:** invoked only by U9. It is security-sensitive and needs the independent review and invariant tests.

### U7 — site-renderer (library, M)

- **Owns:** SiteRenderer.
- **Delivers:**
  - React and TypeScript components and templates for every public page: home, catalog, category, exhibit, and the two "isn't on display" pages;
  - static generation to HTML;
  - the island scripts for the carousel and lightbox;
  - the crafted-studio tokens (FR9.6);
  - accessibility (NFR8).

  It runs as a pure function, from a schema-valid snapshot to files.
- **Constraints:**
  - It makes no network or storage calls.
  - It loads no third-party origin and emits no inline scripts (FR9.5, NFR15).
  - It escapes all text (FR4.5).
  - In preview mode it adds the permanent "Preview — not public" marking.

### U8 — site-publisher (service, M)

- **Owns:** PublicSiteExporter.
- **Delivers:** a Node function, invoked only by U9's identity, that:
  1. validates the publish request and snapshot against U1;
  2. renders through U7;
  3. copies the listed metadata-free derivatives and included files;
  4. writes and deletes public objects in the safe order;
  5. enforces the fence (refusing a lower token than the highest accepted);
  6. invalidates the CDN;
  7. restores a given committed snapshot on request.
- **Constraints:**
  - It has no visitor-facing endpoint, no access to Studio data or the database, and no publication or authorization logic (constraints 3 and 4).
  - Its fence and object-set records are kept in a private store.
  - Its role can write public storage, read only the derivative and file objects named in the manifest, and use its private state store.

### U9 — publication (service, XL)

- **Owns:** Publication.
- **Delivers:**
  - preparation, blockers and inventories;
  - confirmation tickets with frozen candidates;
  - atomic acceptance with the Projects guards (ADR-012);
  - status derivation;
  - preview candidates for U11;
  - the site-wide sequence runner: run-time basis check, per-attempt lease and token, the U8 invocation, conditional commit;
  - abandoned-attempt recovery;
  - bounded retries and the take-down failure alert;
  - featured-order semantics;
  - the public site snapshot builder;
  - the activity log.
- **Constraints:**
  - It is the publication boundary (NFR2) and needs the independent security review and the approval and privacy invariant tests (CS-01 to CS-20 and PB-01 to PB-12 in `components.md`).
  - Its acceptance and commit transactions run in the shared back-end package and database (constraint 7).

### U10 — content-backup (service, S)

- **Owns:** ContentBackup.
- **Delivers:** a scheduled nightly export that reads each owner's export function into private, versioned, encrypted storage, plus a documented and tested restore (NFR10).
- **Constraints:** it runs from the back-end package on a schedule, and its storage is never part of the public site.

### U11 — studio-web (ui, L)

- **Owns:** StudioWeb.
- **Delivers:**
  - the owner's Studio: sign-in with MFA, Projects, Discover, the editor with leave guard and edit recovery, publish, update, take-down and featured-order confirmations, and the activity log;
  - **preview**: renders the candidate snapshot from U9 with U7 into a sandboxed frame, marked "Preview — not public".
- **Constraints:**
  - It holds no secrets, no owner data in its bundle, and makes no authorization decision (FR1.2).
  - Its static assets are delivered separately from the public site, and every piece of owner data and every action is gated by the owner-only API. Preview content therefore reaches only the signed-in owner (FR6.2).

## Preview (realisation of the Publication → SiteRenderer preview edge)

In `components.md`, Publication renders the owner-only preview through SiteRenderer. With constraint 3, that edge is realised as follows:
1. U9 builds the candidate snapshot by the same projection used for publication.
2. U9 returns it, with owner-only image addresses, through the authenticated Studio API.
3. U11 renders it with U7 inside a sandboxed frame.

The renderer, the projection and the marking are unchanged; the rendering runs in the browser instead of on the server. Fidelity to the public pages (FR6.1) is guaranteed by U7's runtime-neutral constraint and its Node/browser parity test (constraint 2). Owner-only image addresses travel in the preview payload's separate map, never in the snapshot. The candidate never reaches U8 or public storage (FR6.2, PB-12).

## Call Direction Inside the Back End

The dependency graph records integration dependencies: a unit depends on the package, foundation or contract it needs. Inside the back-end package, runtime calls also run in the other direction, through U1's module interfaces:

| Runtime caller | Callee | Through | How the graph stays acyclic |
|---|---|---|---|
| StudioApi (U3) | MediaLibrary, DescriptionAssistant, Publication routes (U4, U5, U9) | Route registration | Each unit registers its own routes and handlers into U3's API host. U3 does not import them, and the host works without them |
| Projects (U3) | MediaLibrary attach check (U4) | Attach-check port in U1 | U3 ships a fail-closed default that refuses every attachment until U4 provides the implementation |
| Publication (U9) | Projects guards and slot release (U3) | Guard ports in U1 | Matches the graph: U9 depends on U3 |
| DescriptionAssistant (U5) | Projects, RepositoryCatalog (U3) | Ports in U1 | Matches the graph: U5 depends on U3 |
| ContentBackup (U10) | Export functions of U3, U4, U5 and U9 | Ports in U1 | Matches the graph |

So every reverse call goes through a U1 interface, with the implementation supplied by the depending unit. No unit needs another unit's code to build.

## Deployment Model

| Deployable | Units | Runtime | Reached by |
|---|---|---|---|
| Walking slice (S1 to S3) | U0 | Python and Node, local stack | Owner's machine only; never deployed |
| Studio API function | U3, U4 (module), U5, U9 (module) | Python | Owner, through the API entry point |
| Publication runner and recovery entry points | U9 (and U3 modules for guards and slot release) | Python, same package | Queue, lease expiry and schedule; never visitors |
| Nightly backup entry point | U10 | Python, same package | Schedule |
| Upload processor | U4 | Python, isolated function | Storage upload events |
| Link checker | U6 | Python, isolated function | Invoked by U9 only |
| Site publisher | U8 (+U7) | Node | Invoked by U9 only |
| Studio web | U11 (+U7) | Static assets | Owner's browser, behind sign-in |
| Public site | output of U8 | Static files on the CDN | Visitors |
| Infrastructure | U2 | Terraform | Approved pipeline runs |

The exact services (API Gateway HTTP API, the queue, the scheduler and storage events) are confirmed in NFR Design and Infrastructure Design, as are their costs (NFR4).

## Assumptions & Open Questions

- **Mechanisms:** the queue, lease and transaction mechanisms are fixed in NFR Design. The properties are fixed in ADR-004 and ADR-012, and constraint 7 keeps them achievable.
- **Public JavaScript budget:** set in NFR Design and enforced by the NFR5 Lighthouse check.
- **Infrastructure approvals:** creating preview, production runs and DNS each need Michael's approval (project rules). No unit here authorizes them.
