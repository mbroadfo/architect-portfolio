# Entities — U1 contracts

**Inputs:**
- unit-of-work (U1);
- components;
- contract-summary (C1 to C11, errors and timeouts, model additions);
- requirements;
- `functional-design-questions.md`.

U1 owns no domain data. Its entities are **contract artifacts**: the specifications, rules and test assets that the other units build against, plus the versioning model that governs them. Domain entities (Project, MediaAsset, PublishedVersion and the rest) stay with their owning components; this file only records the shapes that cross a boundary. Shapes are design-level. The generated JSON Schemas, OpenAPI document and ports are produced from these definitions in Code Generation (B01, B02).

## Entity Model

```yaml
entities:
  # ---- Catalogue and versioning ----
  - name: ContractSpec
    description: One of the eleven contracts, as a catalogue entry. The single authoritative definition lives in U1 (BR1.1).
    attributes:
      - { name: contractId, type: enum, required: true, unique: true, allowed: [C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11] }
      - { name: title, type: text, required: true }
      - { name: kind, type: enum, required: true, allowed: [openapi, json-schema, port-interface, key-layout-rules, path-rules, typed-interface, http-surface] }
      - { name: strictness, type: enum, required: true, allowed: [strict, lenient, not-applicable], constraints: "C2, C3, C4 strict; C1 responses, C5, C6 lenient; C1 request bodies strict (BR1.9, BR1.10)" }
      - { name: providerUnit, type: text, required: true }
      - { name: consumerUnits, type: list, required: true }
      - { name: version, type: reference, required: true, references: ContractVersion }
      - { name: schemaId, type: text, required: false, constraints: "present for JSON Schemas; placeholder .invalid host until U1 assigns real identifiers" }
    instances:
      - { contractId: C1, kind: openapi, provider: "U3 host; routes from U4, U5, U9", consumers: [U11], artifact: "Studio API OpenAPI 3.1 document, with C10 health" }
      - { contractId: C2, kind: json-schema, provider: U9, consumers: [U8, U7, U11], artifact: "PublicSiteSnapshot schema" }
      - { contractId: C3, kind: json-schema, provider: U8, consumers: [U9], artifact: "PublishRequest and PublishResult schemas" }
      - { contractId: C4, kind: json-schema, provider: U9, consumers: [U11], artifact: "PreviewPayload schema (inside C1)" }
      - { contractId: C5, kind: json-schema, provider: U6, consumers: [U9], artifact: "LinkCheckRequest and LinkCheckResult schemas" }
      - { contractId: C6, kind: json-schema, provider: "U4 upload processor", consumers: ["U4 module"], artifact: "UploadResult schema" }
      - { contractId: C7, kind: port-interface, provider: "the providing module", consumers: [U3, U4, U5, U9, U10], artifact: "Python ports module" }
      - { contractId: C8, kind: key-layout-rules, provider: U4, consumers: [U9, U8, U7], artifact: "key builders and parsers, variant rule, file-type table" }
      - { contractId: C9, kind: path-rules, provider: "U7 for pages; U2 for headers", consumers: [U7, U8], artifact: "page-path to object-key mapping, public paths, download-name rule (headers are not defined here)" }
      - { contractId: C10, kind: http-surface, provider: U3, consumers: ["smoke checks"], artifact: "GET /health, defined inside C1" }
      - { contractId: C11, kind: typed-interface, provider: U7, consumers: [U8, U11], artifact: "TypeScript renderer types" }
    relationships:
      - { to: ContractVersion, cardinality: "1..*", direction: "a contract has a current version and may have superseded versions" }
      - { to: GeneratedTypesOutput, cardinality: "0..*", direction: "a JSON Schema, OpenAPI or typed-interface contract generates types" }
  - name: ContractVersion
    description: One semantic version of a contract, with the lifecycle that governs its rollout (state machine in functional-spec.md).
    attributes:
      - { name: contractId, type: reference, required: true, references: ContractSpec }
      - { name: version, type: text, required: true, constraints: "MAJOR.MINOR; strict contracts carry the same value as the schemaVersion constant (for example 1.0)" }
      - { name: change, type: enum, required: true, allowed: [initial, additive, breaking] }
      - { name: state, type: enum, required: true, allowed: [Proposed, Approved, Accepted, Current, Superseded], default: Proposed, constraints: "stored in the contract register; moves only in this order (BR1.11); Accepted needs every consumer to list the version; exactly one Current per contract" }
      - { name: pinsSnapshotId, type: text, required: false, constraints: "C3, C4 and the C11 input type pin the C2 $id of the version they use (BR1.7)" }
      - { name: reviewRecord, type: reference, required: false, constraints: "required for any version that adds a public snapshot field (BR1.5) and for a breaking change on C1 or C3 (BR1.8)" }
    relationships:
      - { to: ConsumerAcceptance, cardinality: "0..*", direction: "each consumer declares whether it accepts this version" }
  - name: ConsumerAcceptance
    description: The set of versions one consumer accepts for one contract. A message outside the set is refused whole (BR1.6).
    attributes:
      - { name: consumerUnit, type: text, required: true }
      - { name: contractId, type: reference, required: true, references: ContractSpec }
      - { name: mode, type: enum, required: true, allowed: [strict, tolerant], constraints: "tolerant only for the lenient contracts: the C5 result and C6 records (which carry schemaVersion), and C1 responses except the embedded C4 payload (which carry none, so tolerance there is only ignoring unknown fields; C1 is versioned by the OpenAPI document version, BR1.6)" }
      - { name: acceptedVersions, type: list, required: true, constraints: "strict mode: exact versions, and during a rollout the old and the new version; the producer emits exactly one" }
      - { name: minorFloor, type: integer, required: false, constraints: "tolerant mode only: the lowest minor of the contract's major that the consumer accepts; a different major is refused" }
    constraints: "(consumerUnit, contractId) is unique; stored in the contract register (ContractRegister)"
  - name: ContractRegister
    description: The one machine-readable data file in U1 that holds the data tests and other units read (BR1.11). Nothing in it is defined anywhere else.
    attributes:
      - { name: versions, type: list, required: true, constraints: "ContractVersion rows with their lifecycle state" }
      - { name: acceptance, type: list, required: true, constraints: "ConsumerAcceptance rows (mode and accepted versions)" }
      - { name: allowList, type: reference, required: true, references: ReviewedAllowList }
      - { name: constants, type: list, required: true, constraints: "ContractConstant rows" }
      - { name: addressFields, type: list, required: true, constraints: "AddressFieldEntry rows (BR4.9)" }
      - { name: evidenceLedger, type: list, required: true, constraints: "one row per C1 operation: evidence level none, reference or real, the Bolt that set it and the harness result it came from; updated by each unit's Bolt from the harness output (BR4.8, BR4.13)" }
    relationships:
      - { to: ContractVersion, cardinality: "1..*", direction: "stores" }
      - { to: ConsumerAcceptance, cardinality: "1..*", direction: "stores" }
      - { to: ReviewedAllowList, cardinality: "1", direction: "stores" }
      - { to: ContractConstant, cardinality: "1..*", direction: "stores" }
      - { to: AddressFieldEntry, cardinality: "1..*", direction: "stores" }
  - name: ReviewedAllowList
    description: The reviewed list of permitted snapshot field paths that the allow-list conformance test compares with the C2 schema (BR1.4, BR1.5).
    attributes:
      - { name: snapshotVersion, type: text, required: true }
      - { name: paths, type: list, required: true, constraints: "every permitted field path; changed only with a version change, an updated PB-02 test and a recorded security review" }
      - { name: reviewRecord, type: reference, required: true, constraints: "the independent security review of this exact content" }
  - name: ContractConstant
    description: A named limit shared by several units and the fixtures.
    attributes:
      - { name: name, type: text, required: true, unique: true, constraints: "for example MAX_EXHIBITS (200), MAX_REQUEST_BYTES (5 MB), U8_READABLE_PREFIXES (derivatives/, files/), DOWNLOAD_NAME_BUDGET (set in NFR Design)" }
      - { name: value, type: text, required: true }
      - { name: usedBy, type: list, required: true }
  - name: AddressFieldEntry
    description: One named field in the address-field register (BR4.9).
    attributes:
      - { name: fieldPath, type: text, required: true, unique: true }
      - { name: classification, type: enum, required: true, allowed: [storage-address, public-link, free-form-allowance, not-an-address] }
      - { name: channel, type: reference, required: false, references: StorageChannel, constraints: "required for storage-address" }
      - { name: owner, type: text, required: true }
    instances:
      - { fieldPath: "UploadAuthorization.uploadUrl", classification: storage-address, channel: upload }
      - { fieldPath: "UploadAuthorization.fields", classification: free-form-allowance, channel: upload, note: "form fields of the upload channel; object key must equal incoming/{assetRef}/upload" }
      - { fieldPath: "PreviewPayload.imageAddresses", classification: storage-address, channel: previewImages }
      - { fieldPath: "PreviewPayload.downloadAddresses", classification: storage-address, channel: previewDownloads }
      - { fieldPath: "Link.url", classification: public-link }
      - { fieldPath: "Exhibit.liveUrl", classification: public-link }
      - { fieldPath: "PublicRepository.url", classification: public-link }
      - { fieldPath: "SiteBlock.githubProfileUrl", classification: public-link }
      - { fieldPath: "POST /projects 303 Location header", classification: public-link }
      - { fieldPath: "Project, ProjectPatch, Ticket.inventory, UploadResult.documentMetadata", classification: free-form-allowance, note: "values must hold no address-like string" }
      - { fieldPath: "Exhibit.links", classification: not-an-address, note: "an array of Link objects; the name does not match the candidate predicate, and a test pins that" }
      - { fieldPath: "Repository.linkedProjectId", classification: not-an-address, note: "a project identifier; the name does not match the candidate predicate, and a test pins that" }
  - name: FenceRecord
    description: U8's site-wide fence in its private store (ADR-004), never deleted. Every write and deletion is conditional on it (BR3.1, BR3.8).
    attributes:
      - { name: highestToken, type: integer, required: true, constraints: "set to the higher of the stored value and the token of a request that passed validation; an invalid request never changes it" }
      - { name: lastOperationId, type: text, required: true, constraints: "an equal token is accepted only for this operation id" }
  - name: ReferenceHost
    description: A thin, test-only host in the harness that registers a spy route for every operation in the OpenAPI document and runs the pipeline contract (BR4.13). It is never shipped and is not evidence about any real host.
    attributes:
      - { name: routes, type: list, required: true, constraints: "one per (method, path) of the document" }
      - { name: spyCounts, type: map, required: true, constraints: "invocations per route" }
      - { name: brokenVariant, type: boolean, required: true, constraints: "a deliberately broken pipeline used as a negative control" }
      - { name: evidence, type: enum, required: true, allowed: [none, reference, real], constraints: "per operation; only real counts as agreement (BR4.8)" }
  - name: GeneratedTypesOutput
    description: Types produced from the specs for one language. Never edited by hand; must equal a fresh generation (BR9.1, BR9.2).
    attributes:
      - { name: language, type: enum, required: true, allowed: [python, typescript] }
      - { name: sourceContract, type: reference, required: true, references: ContractSpec }
      - { name: outputKind, type: enum, required: true, allowed: [snapshot-types, publish-types, preview-types, link-check-types, upload-result-types, api-types, ports-module, renderer-types] }
      - { name: strictCheck, type: enum, required: true, allowed: [mypy, tsc-noEmit], constraints: "python is checked with mypy, typescript with tsc --noEmit under strict settings" }
      - { name: marker, type: text, required: true, constraints: "carries a generated-file marker" }
    relationships:
      - { to: ContractSpec, cardinality: "1", direction: "each output belongs to one contract" }
  - name: ContractTestHarness
    description: The shared test assets U1 supplies so both sides of every contract run the same cases (BR9.5).
    attributes:
      - { name: harnessId, type: identifier, required: true, unique: true }
      - { name: stubHandlers, type: list, required: true, constraints: "one stub per registering-unit tag so the registry check runs before the real handlers exist (BR4.2)" }
      - { name: portFakes, type: list, required: true, constraints: "one fake per C7 port (BR6.2)" }
      - { name: runners, type: list, required: true, allowed: [python, typescript, node, browser] }
    relationships:
      - { to: ContractFixture, cardinality: "1..*", direction: "the harness holds the fixtures" }
      - { to: ContractTestCase, cardinality: "1..*", direction: "the harness runs the cases" }
  - name: ContractFixture
    description: A language-neutral sample message with its expected verdict, run by both language validators (BR9.3).
    attributes:
      - { name: fixtureId, type: identifier, required: true, unique: true }
      - { name: contractId, type: reference, required: true, references: ContractSpec }
      - { name: verdictStrict, type: enum, required: true, allowed: [accept, refuse], constraints: "expected verdict in strict mode (BR1.6)" }
      - { name: verdictTolerant, type: enum, required: true, allowed: [accept, refuse, not-applicable], constraints: "expected verdict in tolerant mode; not-applicable for a strict contract, where it always equals verdictStrict if given; both language validators must give each declared verdict (BR9.3)" }
      - { name: violates, type: text, required: false, constraints: "required when any verdict is refuse: the rule or test id it breaks (for example S3, C3-K6, BR2.4)" }
      - { name: content, type: document, required: true, constraints: "placeholders only; hosts on .invalid; no real project content, withheld value or secret (BR9.4)" }
  - name: ContractTestCase
    description: A named contract test that a provider or consumer must run.
    attributes:
      - { name: caseId, type: identifier, required: true, unique: true, constraints: "for C3: C3-K1 to C3-K18, C3-P1, C3-F1, C3-OK (approved), and C3-F2 to C3-F5 (added by U1, BR3.7, BR3.8)" }
      - { name: contractId, type: reference, required: true, references: ContractSpec }
      - { name: runBy, type: list, required: true, constraints: "the units on both sides of the contract" }
      - { name: expectation, type: text, required: true }
    instances:
      - { family: "C1", cases: ["registry equals document", "non-owner rejection with spy handlers (reference host at B02, real hosts later)", "negative control: a broken reference pipeline fails the tests", "closed request bodies", "error-body and shared-response lint", "OpenAPI/handler agreement against real handlers (R-18)", "three-channel and address-field scan with negative fixtures (R-18)"] }
      - { family: "C2", cases: ["allow-list conformance", "structural rules", "semantic rules S1 to S10 with fixtures"] }
      - { family: "C3", cases: ["C3-K1 to C3-K18", "C3-P1", "C3-F1", "C3-OK", "C3-F2 stalled attempt", "C3-F3 invalid request does not advance the fence", "C3-F4 equal token", "C3-F5 conditional write with a stale token"] }
      - { family: "C5", cases: ["NFR17 scenarios", "15 s U6 bound", "20 s invoke timeout gives Not reachable", "one URL per exhibit per preparation"] }
      - { family: "register", cases: ["valid lifecycle transitions", "skipped transition refused", "Current version not accepted by every consumer refused"] }
      - { family: "C4 and C11", cases: ["parity", "purity", "preview marking only in preview mode", "PREVIEW_BLOCKED", "PB-02 scan"] }
      - { family: "C6", cases: ["rejection cases"] }
      - { family: "U1 self-check", cases: ["every spec parses, declares $schema, has no null-valued key"] }

  # ---- C1 Studio API (with C10) ----
  - name: StudioApiDocument
    description: The OpenAPI 3.1 description of the owner-only API. One server entry; routes are registered into U3's host by U3, U4, U5 and U9 (R-08).
    attributes:
      - { name: openapiVersion, type: text, required: true, constraints: "3.1.0" }
      - { name: apiVersion, type: text, required: true }
      - { name: server, type: text, required: true, constraints: "exactly one entry; placeholder .invalid origin until Infrastructure Design" }
      - { name: security, type: text, required: true, constraints: "ownerBearer (JWT bearer) on every operation except GET /health" }
      - { name: tags, type: list, required: true, allowed: [U3-projects, U3-repositories, U4-media, U5-assistant, U9-publication] }
    relationships:
      - { to: ApiOperation, cardinality: "1..*", direction: "the document lists the operations" }
      - { to: ErrorBody, cardinality: "1", direction: "all error responses share one body" }
      - { to: StorageChannel, cardinality: "3", direction: "exactly three storage channels are described" }
  - name: ApiOperation
    description: One (method, path) pair of the document and its responses.
    attributes:
      - { name: method, type: enum, required: true, allowed: [GET, POST, PUT, PATCH] }
      - { name: path, type: text, required: true }
      - { name: tag, type: enum, required: true, allowed: [U3-projects, U3-repositories, U4-media, U5-assistant, U9-publication], constraints: "names the registering unit" }
      - { name: requiresOwner, type: boolean, required: true, constraints: "false only for GET /health" }
      - { name: requiresIfMatch, type: boolean, required: true, constraints: "true for PATCH /projects/{projectId}, POST /projects/{projectId}/repositories, /images, /attachments and PUT /featured-lineup (BR4.10)" }
      - { name: responses, type: list, required: true, constraints: "each response names its status and either the Error schema (every 4xx and 5xx), a success schema, or a NoBodyException entry (the six approved bodyless 2xx responses and the 303) (BR4.5)" }
      - { name: requestBody, type: reference, required: false, constraints: "a closed schema (BR1.10)" }
    constraints: "(method, path) is unique and equals a registry entry at runtime (BR4.2)"
    relationships:
      - { to: ErrorBody, cardinality: "1..*", direction: "every non-2xx response except the exception uses it" }
  - name: PipelineStage
    description: One step of the request pipeline every registered route runs (BR4.3).
    attributes:
      - { name: order, type: integer, required: true, unique: true, constraints: "1 to 4" }
      - { name: stage, type: enum, required: true, allowed: [OwnerAccess, RateLimit, RequestIdAndErrorMapping, Handler] }
      - { name: skippableBy, type: text, required: true, constraints: "only GET /health may skip OwnerAccess; nothing may skip the others" }
  - name: ErrorBody
    description: The shared body of every error response the host produces (BR4.5).
    attributes:
      - { name: code, type: enum, required: true, references: ErrorCodeEntry, allowed: [UNAUTHENTICATED, NOT_OWNER, RATE_LIMITED, VALIDATION_FAILED, NOT_FOUND, REVISION_REQUIRED, STALE_REVISION, SLUG_TAKEN, LINEUP_CHANGED, TICKET_USED, TICKET_MISMATCH, TICKET_EXPIRED, BASIS_CHANGED, SUPERSEDED, PREVIEW_BLOCKED, NO_LINKED_REPOSITORY, AI_SPEND_NOT_APPROVED, PROVIDER_NOT_APPROVED, GITHUB_UNAVAILABLE, SUGGESTION_UNAVAILABLE, INTERNAL] }
      - { name: message, type: text, required: true, constraints: "no secret or personal data (NFR11)" }
      - { name: requestId, type: text, required: true, constraints: "set by the pipeline" }
      - { name: blockers, type: list, required: false, constraints: "list of text; used by PREVIEW_BLOCKED" }
  - name: ErrorCodeEntry
    description: One closed (status, code) pair (BR4.6).
    attributes:
      - { name: status, type: integer, required: true, allowed: [401, 403, 404, 409, 410, 422, 428, 429, 500, 503, 504] }
      - { name: code, type: text, required: true, unique: true }
    instances:
      - { status: 401, codes: [UNAUTHENTICATED] }
      - { status: 403, codes: [NOT_OWNER, AI_SPEND_NOT_APPROVED, PROVIDER_NOT_APPROVED] }
      - { status: 404, codes: [NOT_FOUND] }
      - { status: 409, codes: [STALE_REVISION, SLUG_TAKEN, LINEUP_CHANGED, TICKET_USED, TICKET_MISMATCH, BASIS_CHANGED, SUPERSEDED] }
      - { status: 410, codes: [TICKET_EXPIRED] }
      - { status: 422, codes: [VALIDATION_FAILED, PREVIEW_BLOCKED, NO_LINKED_REPOSITORY] }
      - { status: 428, codes: [REVISION_REQUIRED] }
      - { status: 429, codes: [RATE_LIMITED] }
      - { status: 500, codes: [INTERNAL] }
      - { status: 503, codes: [GITHUB_UNAVAILABLE] }
      - { status: 504, codes: [SUGGESTION_UNAVAILABLE] }
  - name: NoBodyException
    description: A documented response that intentionally has no body, recorded instead of inventing one (R-18). Covers the approved bodyless 2xx responses and the 303 redirect. No error (4xx, 5xx) response may be listed here.
    attributes:
      - { name: operation, type: reference, required: true, references: ApiOperation }
      - { name: status, type: integer, required: true, allowed: [200, 202, 303] }
      - { name: kind, type: enum, required: true, allowed: [success-no-body, redirect] }
      - { name: reason, type: text, required: true }
      - { name: header, type: text, required: false, constraints: "ETag for the PATCH 200; Location for the 303" }
    instances:
      - { operation: "PATCH /projects/{projectId}", status: 200, kind: success-no-body, header: "ETag", reason: "Saved; the revision is in the ETag header" }
      - { operation: "POST /projects/{projectId}/repositories", status: 200, kind: success-no-body, reason: "Linked" }
      - { operation: "POST /projects/{projectId}/images", status: 200, kind: success-no-body, reason: "Attached" }
      - { operation: "POST /projects/{projectId}/attachments", status: 200, kind: success-no-body, reason: "Attached" }
      - { operation: "PUT /featured-lineup", status: 200, kind: success-no-body, reason: "Saved" }
      - { operation: "POST /publication/operations/{operationId}/retry", status: 202, kind: success-no-body, reason: "Retry scheduled" }
      - { operation: "POST /projects", status: 303, kind: redirect, header: "Location", reason: "redirect to the project already linked to the repository; not an error (FR2.3)" }
  - name: StorageChannel
    description: One of the three authorized direct-to-storage channels (R-18 point 1; BR4.9).
    attributes:
      - { name: channelId, type: enum, required: true, unique: true, allowed: [upload, previewImages, previewDownloads] }
      - { name: issuedBy, type: text, required: true, constraints: "an owner-authenticated route: POST /projects/{projectId}/uploads (U4) or GET /projects/{projectId}/preview (U9)" }
      - { name: carriedIn, type: text, required: true, constraints: "named fields only (the address-field register): UploadAuthorization.uploadUrl and fields; PreviewPayload.imageAddresses values; PreviewPayload.downloadAddresses values. Public-link fields of C2 are exempt by name (BR4.9)" }
      - { name: lifetime, type: text, required: true, constraints: "short-lived; upload is single-use, bound to project, size and type" }
      - { name: target, type: text, required: true, constraints: "upload: one object under incoming/; previews: read of the previewed exhibit's derivatives or attachments" }

  # ---- C2 Public site snapshot ----
  - name: PublicSiteSnapshot
    description: The only input to the public site (ADR-002). Strict, versioned, produced by U9, validated by U9 before sending and by U8 and U11 on receipt.
    attributes:
      - { name: schemaVersion, type: text, required: true, allowed: ["1.0"], constraints: "constant" }
      - { name: generation, type: integer, required: true, constraints: "minimum 0; the site generation public storage will be at once the snapshot is applied" }
      - { name: site, type: reference, required: true, references: SiteBlock }
      - { name: exhibits, type: list, required: true, constraints: "at most 200; slugs unique (S3)" }
      - { name: featuredOrder, type: list, required: true, constraints: "at most 5 slugs; each a live exhibit with featured true; no duplicates (S1)" }
      - { name: categories, type: list, required: true, constraints: "at most 4 CategoryWithCount; equals the set derived from the exhibits (S2)" }
    constraints: "additionalProperties false at every level (BR1.3); no field for an address, draft, ticket, operation, link-check, private-repository or access-metadata value (BR2.4); the permitted field paths equal the reviewed FR4.10 allow-list (BR1.4)"
    relationships:
      - { to: SiteBlock, cardinality: "1", direction: "embedded" }
      - { to: Exhibit, cardinality: "0..200", direction: "embedded" }
      - { to: CategoryWithCount, cardinality: "0..4", direction: "embedded" }
  - name: SiteBlock
    description: Reviewed site settings (owner name, profile, contact), a configuration owned by U9 and not an entity.
    attributes:
      - { name: ownerName, type: text, required: true, constraints: "up to 120 characters" }
      - { name: githubProfileUrl, type: text, required: true, constraints: "https://github.com/ plus an owner name" }
      - { name: contactEmail, type: text, required: false, constraints: "a valid email or null; null until the owner supplies it (FR9.4)" }
  - name: Exhibit
    description: One live exhibit, frozen from a PublishedVersion. Field names follow the Model Additions mapping (publishedAt is the version's confirmation time).
    attributes:
      - { name: slug, type: text, required: true, unique: true, constraints: "lowercase words joined by hyphens, up to 60 characters" }
      - { name: title, type: text, required: true, constraints: "1 to 120 characters" }
      - { name: summary, type: text, required: true, constraints: "up to 1200 characters" }
      - { name: sections, type: reference, required: true, references: Sections }
      - { name: leadImage, type: reference, required: true, references: Image }
      - { name: images, type: list, required: true, constraints: "at most 40" }
      - { name: attachments, type: list, required: true, constraints: "at most 20" }
      - { name: links, type: list, required: true, constraints: "at most 10; https only; never a repository host (BR2.1)" }
      - { name: liveUrl, type: text, required: false, constraints: "https only; never a repository host; present only if included at Publish and authorized (S9)" }
      - { name: badges, type: list, required: true, constraints: "at most 6; derived only from the FR4.10 table (S10)" }
      - { name: publicRepositories, type: list, required: true, constraints: "at most 10; only repositories confirmed public (S8)" }
      - { name: primaryCategory, type: reference, required: false, references: Category }
      - { name: featured, type: boolean, required: true }
      - { name: publishedAt, type: timestamp, required: true }
    relationships:
      - { to: Image, cardinality: "1..41", direction: "one lead image plus up to 40 images; each assetRef once (S7)" }
      - { to: Attachment, cardinality: "0..20", direction: "embedded" }
      - { to: Link, cardinality: "0..10", direction: "embedded" }
      - { to: Badge, cardinality: "0..6", direction: "embedded" }
      - { to: PublicRepository, cardinality: "0..10", direction: "embedded" }
  - name: Sections
    description: The six narrative sections, each optional text (summary is on the exhibit).
    attributes:
      - { name: inspiration, type: text, required: false, constraints: "up to 8000 characters" }
      - { name: designChallenges, type: text, required: false, constraints: "up to 8000 characters" }
      - { name: architecturalDecisions, type: text, required: false, constraints: "up to 8000 characters" }
      - { name: implementation, type: text, required: false, constraints: "up to 8000 characters" }
      - { name: outcomes, type: text, required: false, constraints: "up to 8000 characters" }
      - { name: lessonsLearned, type: text, required: false, constraints: "up to 8000 characters" }
  - name: Image
    description: A published image, identified only by assetRef (never by an address).
    attributes:
      - { name: assetRef, type: identifier, required: true, constraints: "^ast_[A-Za-z0-9]{16,32}$; equals the MediaAsset assetId" }
      - { name: altText, type: text, required: true, constraints: "1 to 300 characters (NFR8)" }
      - { name: caption, type: text, required: false, constraints: "up to 300 characters" }
      - { name: width, type: integer, required: true, constraints: "at least 1; pixel width of the metadata-free primary image; drives the variant rule" }
      - { name: height, type: integer, required: true, constraints: "at least 1" }
  - name: Attachment
    description: A published download, identified only by assetRef.
    attributes:
      - { name: assetRef, type: identifier, required: true }
      - { name: label, type: text, required: true, constraints: "up to 120 characters" }
      - { name: fileType, type: enum, required: true, allowed: [PDF, SKP, FCStd, DXF, STL, ZIP, VSDX] }
      - { name: byteSize, type: integer, required: true, constraints: "1 to 52428800" }
  - name: Link
    description: A free-form public link; never a repository (FR4.3).
    attributes:
      - { name: kind, type: enum, required: true, allowed: [demo, documentation, other] }
      - { name: label, type: text, required: true, constraints: "up to 80 characters" }
      - { name: url, type: text, required: true, constraints: "https; up to 2048 characters; host not github.com, githubusercontent.com, gitlab.com or bitbucket.org (any subdomain)" }
  - name: Badge
    description: A public badge derived only from the FR4.10 table.
    attributes:
      - { name: kind, type: enum, required: true, allowed: [inBrowser, signInRequired, byInvitation, bestOnDesktop, openSource, sourceAvailable, sourcePrivate] }
      - { name: spdx, type: text, required: false, constraints: "^[A-Za-z0-9.+-]{1,40}$; only with kind openSource (S4)" }
  - name: PublicRepository
    description: A repository confirmed public at preparation, with its licence (fail closed).
    attributes:
      - { name: name, type: text, required: true, constraints: "up to 100 characters" }
      - { name: url, type: text, required: true, constraints: "https://github.com/{owner}/{name}" }
      - { name: licence, type: text, required: false, constraints: "an SPDX identifier pattern" }
  - name: Category
    description: A primary category frozen into an exhibit.
    attributes:
      - { name: slug, type: enum, required: true, allowed: [games, astronomy, woodworking, software] }
      - { name: name, type: text, required: true, constraints: "up to 60 characters" }
      - { name: position, type: integer, required: true, constraints: "minimum 0" }
  - name: CategoryWithCount
    description: A category that has at least one live exhibit, with its count.
    attributes:
      - { name: slug, type: enum, required: true, allowed: [games, astronomy, woodworking, software] }
      - { name: name, type: text, required: true }
      - { name: position, type: integer, required: true }
      - { name: count, type: integer, required: true, constraints: "at least 1" }
  - name: SemanticRule
    description: A snapshot rule the schema cannot express, with its checkers (BR2.2, BR2.3).
    attributes:
      - { name: ruleId, type: enum, required: true, unique: true, allowed: [S1, S2, S3, S4, S5, S6, S6a, S7, S8, S9, S10] }
      - { name: statement, type: text, required: true }
      - { name: checkedBy, type: list, required: true, allowed: [U9, U8], constraints: "S6a, S8, S9, S10 list U9 only" }
    instances:
      - { ruleId: S1, checkedBy: [U9, U8] }
      - { ruleId: S2, checkedBy: [U9, U8] }
      - { ruleId: S3, checkedBy: [U9, U8] }
      - { ruleId: S4, checkedBy: [U9, U8] }
      - { ruleId: S5, checkedBy: [U9, U8] }
      - { ruleId: S6, checkedBy: [U9, U8] }
      - { ruleId: S6a, checkedBy: [U9] }
      - { ruleId: S7, checkedBy: [U9, U8] }
      - { ruleId: S8, checkedBy: [U9] }
      - { ruleId: S9, checkedBy: [U9] }
      - { ruleId: S10, checkedBy: [U9] }

  # ---- C3 Publish request and result ----
  - name: PublishRequest
    description: One invoke per attempt from U9 to U8. Every request means "make public storage equal this snapshot".
    attributes:
      - { name: schemaVersion, type: text, required: true, allowed: ["1.0"] }
      - { name: operationId, type: text, required: true }
      - { name: attemptToken, type: integer, required: true, constraints: "at least 1; strictly increasing per attempt; the fencing token (ADR-004)" }
      - { name: purpose, type: enum, required: true, allowed: [operation, restore, recovery], constraints: "used only for logging" }
      - { name: snapshot, type: reference, required: true, references: PublicSiteSnapshot }
      - { name: assetManifest, type: list, required: true, constraints: "one AssetManifestEntry per referenced asset (BR3.3)" }
    constraints: "closed (BR1.3); no field for an address map or a preview slug (BR5.6); serialized size at most 5 MB (BR2.5)"
    relationships:
      - { to: PublicSiteSnapshot, cardinality: "1", direction: "embedded; pinned by $id" }
      - { to: AssetManifestEntry, cardinality: "0..*", direction: "embedded" }
      - { to: PublishResult, cardinality: "1", direction: "each request gets one result" }
  - name: AssetManifestEntry
    description: The private source keys U8 may read for one asset.
    attributes:
      - { name: assetRef, type: identifier, required: true, unique: true, constraints: "unique within a request" }
      - { name: kind, type: enum, required: true, allowed: [imageDerivatives, file] }
      - { name: sourceKeys, type: list, required: true, constraints: "1 to 6 unique keys of at most 200 characters; exactly the C8 keys for the assetRef, kind and snapshot width or file type, compared byte for byte (BR3.4)" }
  - name: PublishResult
    description: U8's answer. U8 decides nothing beyond the status.
    attributes:
      - { name: schemaVersion, type: text, required: true, allowed: ["1.0"] }
      - { name: operationId, type: text, required: true }
      - { name: attemptToken, type: integer, required: true }
      - { name: status, type: enum, required: true, allowed: [completed, fenced, invalid, failed] }
      - { name: generation, type: integer, required: false, constraints: "echo of snapshot.generation when completed" }
      - { name: objectsWritten, type: integer, required: false }
      - { name: objectsDeleted, type: integer, required: false }
      - { name: invalidationId, type: text, required: false }
      - { name: error, type: text, required: false, constraints: "up to 500 characters; a reason code and object keys only, never snapshot content" }

  # ---- C4 Preview payload ----
  - name: PreviewPayload
    description: What U9 returns through the preview route. A strict contract inside lenient C1.
    attributes:
      - { name: schemaVersion, type: text, required: true, allowed: ["1.0"] }
      - { name: snapshot, type: reference, required: true, references: PublicSiteSnapshot, constraints: "the last committed snapshot with this exhibit replaced by its candidate version" }
      - { name: previewSlug, type: text, required: true, constraints: "slug pattern; names the previewed exhibit in the snapshot (its draft slug before first publish)" }
      - { name: imageAddresses, type: map, required: true, constraints: "keys {assetRef}/{variant}.{format} with variant w480, w960 or w1600 and format webp or jpg; values URIs; owner-only and short-lived" }
      - { name: downloadAddresses, type: map, required: true, constraints: "keys assetRef; values URIs; owner-only, short-lived; served as an attachment, never rendered" }
      - { name: expiresAt, type: timestamp, required: true }
    constraints: "the addresses never appear in the snapshot (BR2.4); the payload never reaches U8 or public storage (BR5.6)"
    relationships:
      - { to: PublicSiteSnapshot, cardinality: "1", direction: "embedded; same version" }
      - { to: StorageChannel, cardinality: "2", direction: "imageAddresses and downloadAddresses are two of the three channels" }

  # ---- C5 Link check ----
  - name: LinkCheckRequest
    description: U9's request to U6 for one URL.
    attributes:
      - { name: schemaVersion, type: text, required: true, allowed: ["1.0"] }
      - { name: requestId, type: text, required: true }
      - { name: url, type: text, required: true, constraints: "up to 2048 characters; not trusted to be canonical" }
  - name: LinkCheckResult
    description: U6's answer. U6 stores nothing; U9 keeps a LinkCheckRecord. No field enters C2.
    attributes:
      - { name: schemaVersion, type: text, required: true, allowed: ["1.0"] }
      - { name: requestId, type: text, required: true }
      - { name: label, type: enum, required: true, allowed: ["Reachable", "Not reachable", "Refused (non-public address)"] }
      - { name: finalAddress, type: text, required: false, constraints: "no userinfo, query or fragment" }
      - { name: signInDetected, type: boolean, required: false }
      - { name: crossDomainRedirect, type: boolean, required: false }
      - { name: checkedAt, type: timestamp, required: true }
      - { name: reason, type: text, required: true, constraints: "up to 200 characters" }
    relationships:
      - { to: LinkCheckRequest, cardinality: "1", direction: "answers one request by requestId" }

  # ---- C6 Upload result ----
  - name: UploadResult
    description: The record the isolated processor writes at results/{assetRef}.json for U4's module to ingest.
    attributes:
      - { name: schemaVersion, type: text, required: true, allowed: ["1.0"] }
      - { name: assetRef, type: identifier, required: true, constraints: "equals the assetRef in the object key" }
      - { name: projectId, type: text, required: true }
      - { name: status, type: enum, required: true, allowed: [valid, rejected] }
      - { name: reason, type: text, required: false, constraints: "up to 200 characters; required when rejected" }
      - { name: detectedType, type: enum, required: false, allowed: [jpeg, png, webp, heic, pdf, skp, fcstd, dxf, stl, zip, vsdx] }
      - { name: byteSize, type: integer, required: false }
      - { name: width, type: integer, required: false }
      - { name: height, type: integer, required: false }
      - { name: derivatives, type: list, required: false, constraints: "exactly the variant rule's set for an image; none when rejected" }
      - { name: fileKey, type: text, required: false, constraints: "files/{assetRef}/file.{ext} for a validated attachment; none when rejected" }
      - { name: documentMetadata, type: document, required: false, constraints: "extracted under FR4.4 limits; shown at Publish" }
      - { name: archiveEntries, type: list, required: false, constraints: "at most 2000" }
      - { name: metadataReadable, type: boolean, required: false }
      - { name: processedAt, type: timestamp, required: true }
    relationships:
      - { to: DerivativeEntry, cardinality: "0..6", direction: "embedded" }
  - name: DerivativeEntry
    description: One derivative the processor wrote.
    attributes:
      - { name: variant, type: enum, required: true, allowed: [w480, w960, w1600] }
      - { name: format, type: enum, required: true, allowed: [webp, jpg] }
      - { name: key, type: text, required: true, constraints: "derivatives/{assetRef}/{variant}.{format}" }
      - { name: width, type: integer, required: true }
      - { name: height, type: integer, required: true }

  # ---- C7 Ports ----
  - name: PortInterface
    description: One in-process Python interface (Protocol) through which back-end modules call each other (BR6.1, BR6.2).
    attributes:
      - { name: portName, type: text, required: true, unique: true }
      - { name: providerUnit, type: text, required: true, constraints: "exactly one" }
      - { name: consumerUnits, type: list, required: true }
      - { name: defaultImplementation, type: text, required: false, constraints: "AttachCheckPort has a fail-closed default shipped by U3 (BR6.4)" }
      - { name: fake, type: reference, required: true, constraints: "U1 ships a conforming fake checked by mypy (BR6.2)" }
      - { name: version, type: text, required: true, constraints: "1.0" }
    instances:
      - { portName: UnitOfWork, provider: "U3 host (transaction)", consumers: [U3, U9], members: ["__enter__", "__exit__"] }
      - { portName: RouteRegistry, provider: U3, consumers: [U4, U5, U9], members: ["register(method, path, handler, rate_limit)"] }
      - { portName: RepositoryCatalogPort, provider: U3, consumers: [U3, U5, U9], members: [list_repositories, access_facts, documentation] }
      - { portName: LinkCheckClientPort, provider: "U9 adapter around C5", consumers: [U9], members: [check] }
      - { portName: ProjectsPort, provider: U3, consumers: [U5, U9, U10], members: [get_draft, read_lineup, revision_guard, lineup_guard, release_featured_slot, record_provenance, export_records] }
      - { portName: AttachCheckPort, provider: "declared for U3; implemented by U4", consumers: [U3], members: [check_attachable], default: "U3 refuses every attachment" }
      - { portName: MediaPort, provider: U4, consumers: [U9, U10], members: [issue_upload_authorization, asset_status, attachment_inventory, manifest_keys, image_facts, preview_address, preview_download_address, export_records] }
      - { portName: AssistantPort, provider: U5, consumers: [U10], members: [suggestion_provenance, export_records], note: "no U3 call: the approved call-direction table has none" }
      - { portName: PublicationPort, provider: U9, consumers: [U3, U10], members: [statuses, export_records], default: "U3 reads statuses only when U9 is registered; with no U9 every project reports the derived status Draft (ADR-003)" }
    relationships:
      - { to: ContractSpec, cardinality: "1", direction: "all ports are C7" }

  # ---- C8 Key layout, variants, file types ----
  - name: StorageKeyPattern
    description: One private-storage key pattern (BR7.1). Built and parsed only by U1's functions.
    attributes:
      - { name: prefix, type: enum, required: true, unique: true, allowed: [incoming, originals, derivatives, files, results] }
      - { name: pattern, type: text, required: true }
      - { name: writtenBy, type: text, required: true }
      - { name: readBy, type: list, required: true }
      - { name: content, type: text, required: true }
    instances:
      - { prefix: incoming, pattern: "incoming/{assetRef}/upload", writtenBy: "owner's browser (single-use authorization)", readBy: ["U4 processor"], content: "raw upload; deleted after processing" }
      - { prefix: originals, pattern: "originals/{assetRef}/original.{ext}", writtenBy: "U4 processor", readBy: ["restore and backup only"], content: "original image with metadata; never public" }
      - { prefix: derivatives, pattern: "derivatives/{assetRef}/{variant}.{format}", writtenBy: "U4 processor", readBy: ["U8", "U4 preview addresses"], content: "metadata-free image derivatives" }
      - { prefix: files, pattern: "files/{assetRef}/file.{ext}", writtenBy: "U4 processor", readBy: ["U8"], content: "validated attachment, published unchanged" }
      - { prefix: results, pattern: "results/{assetRef}.json", writtenBy: "U4 processor", readBy: ["U4 module"], content: "C6 result record" }
  - name: VariantRule
    description: The single definition of which image variants exist (BR7.2).
    attributes:
      - { name: widths, type: list, required: true, allowed: [480, 960, 1600] }
      - { name: formats, type: list, required: true, allowed: [webp, jpg] }
      - { name: belowSmallest, type: text, required: true, constraints: "if the pixel width is below 480, only w480, encoded at the pixel width with no upscaling" }
      - { name: keyCount, type: list, required: true, allowed: [2, 4, 6] }
  - name: FileTypeMapping
    description: One row of the total mapping between C6 detectedType, C2 fileType and the extension (BR7.3).
    attributes:
      - { name: detectedType, type: enum, required: true, unique: true, allowed: [pdf, skp, fcstd, dxf, stl, zip, vsdx] }
      - { name: fileType, type: enum, required: true, unique: true, allowed: [PDF, SKP, FCStd, DXF, STL, ZIP, VSDX] }
      - { name: ext, type: text, required: true, unique: true }
      - { name: publicContentType, type: text, required: true, default: "application/octet-stream" }
    constraints: "image types jpeg, png, webp and heic never appear here"

  # ---- C9 Paths and names ----
  - name: PageObjectMapping
    description: One public page path and its stored object key (BR7.4).
    attributes:
      - { name: pagePath, type: text, required: true, unique: true, allowed: ["/", "/work/", "/work/{slug}", "/category/{slug}", "/404.html", "/category-404.html"] }
      - { name: objectKey, type: text, required: true, unique: true, allowed: ["index.html", "work/index.html", "work/{slug}/index.html", "category/{slug}/index.html", "404.html", "category-404.html"] }
      - { name: contentType, type: text, required: true, default: "text/html; charset=utf-8" }
  - name: PublicRoute
    description: One public route of the static site (BR7.5).
    attributes:
      - { name: path, type: text, required: true, unique: true }
      - { name: status, type: enum, required: true, allowed: [200, 404] }
      - { name: content, type: text, required: true }
    instances:
      - { path: "/", status: 200, content: "home, or the empty-site message" }
      - { path: "/work/", status: 200, content: "catalog" }
      - { path: "/work/{slug}", status: 200, content: "exhibit page" }
      - { path: "/category/{games|astronomy|woodworking|software}", status: "200 or 404", content: "category page; 404 when the category is empty" }
      - { path: "any unknown path, or a taken-down exhibit", status: 404, content: "This exhibit isn't on display (404.html)" }
      - { path: "/media/{assetRef}/{variant}.{format}", status: 200, content: "image derivative" }
      - { path: "/files/{assetRef}/{downloadName}", status: 200, content: "download (headers defined by U2 and U7)" }
      - { path: "/assets/{name}.{hash}.{ext}", status: 200, content: "U7 build-time bundle: CSS, fonts, small island scripts" }
  - name: DownloadNameRule
    description: The single, deterministic, linear-time rule for a download's file name (BR7.6).
    attributes:
      - { name: input, type: text, required: true, constraints: "attachment label (up to 120 characters in C2, but the rule accepts any length)" }
      - { name: ext, type: text, required: true, constraints: "from FileTypeMapping" }
      - { name: output, type: text, required: true, constraints: "slug + '.' + ext; characters only [a-z0-9-] and one '.'; slug at most 60 characters; empty slug becomes 'download'" }

  # ---- C11 Renderer interface ----
  - name: RenderOptions
    description: Options of the renderer call.
    attributes:
      - { name: mode, type: enum, required: true, allowed: [public, preview], constraints: "preview adds the permanent 'Preview — not public' marking and noindex" }
      - { name: resolveAsset, type: reference, required: true, references: AssetResolver }
      - { name: previewSlug, type: text, required: false, constraints: "required when mode is preview, and must name an exhibit in the snapshot (BR8.2)" }
  - name: AssetResolver
    description: A pure, synchronous lookup from an asset reference to an address (BR8.4).
    attributes:
      - { name: imageRef, type: document, required: true, constraints: "kind image, assetRef, variant, format" }
      - { name: downloadRef, type: document, required: true, constraints: "kind download, assetRef, downloadName" }
      - { name: unresolved, type: text, required: true, constraints: "throws RenderInputError" }
    constraints: "publication uses the C9 public paths; preview uses the two C4 address maps"
  - name: RenderedPage
    description: One static page the renderer produces.
    attributes:
      - { name: path, type: text, required: true, references: PageObjectMapping }
      - { name: status, type: enum, required: true, allowed: [200, 404] }
      - { name: html, type: text, required: true, constraints: "complete static HTML; references only static assets and resolver output; no inline scripts or styles; all text escaped" }
  - name: RenderOutput
    description: Everything a render call returns.
    attributes:
      - { name: contractVersion, type: text, required: true, allowed: ["1.0"] }
      - { name: pages, type: list, required: true }
      - { name: requiredImages, type: list, required: true, constraints: "exactly the variant rule's set (BR8.3)" }
      - { name: requiredDownloads, type: list, required: true, constraints: "one entry per attachment (BR8.3)" }
      - { name: staticAssets, type: list, required: true, constraints: "hashed paths under /assets/ that the pages reference" }
    relationships:
      - { to: RenderedPage, cardinality: "1..*", direction: "embedded" }
```

**Summary.** The model has 51 entities in eight groups:
- **Catalogue and versioning:** ContractSpec (the eleven contracts), ContractVersion with its lifecycle, ConsumerAcceptance (mode and accepted versions), the ContractRegister that stores them with the ReviewedAllowList, the ContractConstants and the AddressFieldEntry rows, GeneratedTypesOutput (Python and TypeScript), and the contract-test assets (ContractTestHarness, ReferenceHost, ContractFixture with a verdict per mode, ContractTestCase). FenceRecord is U8's private fence, described here because C3 depends on it.
- **C1 and C10, the Studio API:** the OpenAPI document, its operations, the four-step pipeline, the shared ErrorBody with the closed (status, code) table, the single no-body exception, and the three storage channels (upload, preview images, preview downloads).
- **C2, the snapshot:** PublicSiteSnapshot and its embedded shapes, and the semantic-rule catalogue with who checks each rule.
- **C3, the publish request:** the request (with the operation id and fencing token), the manifest entry and the result.
- **C4 to C6:** the preview payload with its two address maps, the link-check request and result, and the upload result with its derivative entries.
- **C7, the ports:** nine port interfaces, each with one provider, named consumers and a conforming fake.
- **C8 and C9, keys, variants, paths and names:** key patterns, the variant rule, the file-type mapping, the page-to-object mapping, the public routes and the download-name rule.
- **C11, the renderer:** options, resolver, page and output.

Ownership of meaning stays where the approved records put it: U9 for the snapshot and preview, U8 for the publish behaviour, U4 for keys and uploads, U7 for pages and the renderer, U6 for link checks, and U3 for the API host and the error model. U1 owns the specification of each, and the tests that keep both sides equal.

## Assumptions & Open Questions

- **Data, not code.** Attribute types are logical. The JSON Schema, OpenAPI and Python/TypeScript forms are produced in Code Generation from these definitions and from the approved contract text.
- **Draft shapes.** The full `Project`, `ProjectPatch`, inventory and ticket shapes are not U1 entities. They are fixed by the Functional Design of U3, U9 and U11, and the C1 document carries them as placeholders until then.
- **Instances.** The `instances` lists restate approved tables (contract catalogue, error pairs, key layout, routes, ports). They add no value of their own.
