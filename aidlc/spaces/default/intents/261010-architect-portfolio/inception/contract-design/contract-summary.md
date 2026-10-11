# Contract Summary

**Inputs:**
- unit-of-work — `../units-generation/unit-of-work.md` (11 units and cross-unit constraints 1 to 7);
- unit-of-work-dependency — `../units-generation/unit-of-work-dependency.md` (edges and integration points);
- components — `../domain-design/components.md` (entities, behaviour, scenarios CS and PB);
- decisions — ADR-001 to ADR-012 in `../domain-design/decisions.md`;
- requirements — `../requirements-analysis/requirements.md`;
- answers — `contract-design-questions.md`.

**Required corrections from the Units Generation approval (P-07):**
- **R-07** is resolved in C3 and C8: IAM limited to prefixes, manifest keys enforced by U8 against the approved snapshot, and contract tests that reject unauthorized keys.
- **R-08** is resolved in C1: U11 reaches U4, U5 and U9 only through U3's authenticated API host and route registration.

Every spec below lives in U1 (`u1-contracts`) as the source of truth. These blocks are its first version. Shared error, timeout and retry rules are under "Errors, Timeouts and Retries". The fields this stage adds to the domain model, and its renames, are under "Model Additions and Mappings".

## Contracts

| # | Provider Unit | Consumer | Mechanism | Owner |
|---|---|---|---|---|
| C1 | U3 studio-api (host), with routes registered by U4, U5 and U9 | U11 studio-web | HTTPS + JSON, owner bearer token (OpenAPI) | Each route: its registering unit. Host, security and error model: U3 |
| C2 | U9 publication (producer) | U8 site-publisher, U7 site-renderer, U11 studio-web (preview) | Shared schema (JSON Schema, strict, versioned) | U9 for meaning; U1 for the schema |
| C3 | U8 site-publisher | U9 publication | Function invoke, JSON request and response (JSON Schema) | U8 for behaviour; U9 for authority over when to call |
| C4 | U9 publication | U11 studio-web | Part of C1: the preview payload (JSON Schema) | U9 |
| C5 | U6 link-checker | U9 publication | Function invoke, JSON request and response (JSON Schema) | U6 |
| C6 | U4 upload processor (isolated function) | U4 media-library module | Storage upload event in; result record object out (JSON Schema) | U4 |
| C7 | U3, U4, U5, U9 (back-end modules) | Each other, and U10 | In-process Python interfaces (ports) | Providing module |
| C8 | U4 media-library | U9 (manifest builder), U8 (reader) | Shared key layout for private storage | U4 |
| C9 | Public site (output of U8 on U2's CDN) | External: public web (visitors, search engines) | Static HTTP: routes, status codes, headers | U7 for pages; U2 for headers and CDN |
| C10 | U3 studio-api | External: smoke checks | HTTPS `GET /health` | U3 |
| C11 | U7 site-renderer | U8 site-publisher (Node), U11 studio-web (browser preview) | In-process TypeScript library call (typed interface) | U7 |

## C1 — Studio API (U3 host; routes from U3, U4, U5 and U9 → U11)

**R-08: how U11 reaches U4, U5 and U9.** U11 calls only U3's API host, one HTTPS origin behind the API entry point.
- U4, U5 and U9 do not expose their own endpoints. Each registers its routes and handlers into U3's host through the route-registration interface (C7).
- Every registered route inherits U3's request pipeline, in this order:
  1. OwnerAccess check (issuer plus subject);
  2. rate limits (NFR16);
  3. request id and error mapping;
  4. the handler.
- A route cannot opt out of this pipeline. The only exception, `GET /health` (C10), is declared by U3 itself. It skips the OwnerAccess check, but keeps rate limiting and the request id.
- **Two deliberate storage-origin channels.** Each is short-lived and single-purpose, and each is issued only by an owner-authenticated U3 route:
  - **upload:** the single-use upload authorization from `POST /projects/{projectId}/uploads` (U4 route), used once for one object under `incoming/` (C6);
  - **preview images:** the owner-only, short-lived image addresses in the preview payload from `GET /projects/{projectId}/preview` (U9 route; C4).

  U11 reaches no other storage or service.
- **R-08 contract tests:**
  - **(1)** The set of routes actually held by the route registry at runtime must equal the paths and methods in this OpenAPI document. An undocumented registered route fails the build.
  - **(2)** Every registered route except `/health` is called with no token, an expired token, a token with the owner's email but another subject, and a token from another issuer. Each call must answer 401 or 403.
  - **(3)** A spy handler registered for each route proves the handler was never invoked for those calls.

```yaml
openapi: 3.1.0
info:
  title: Architect Portfolio Studio API
  version: 1.0.0
  description: >
    Owner-only API. Hosted by U3; routes tagged by registering unit. All routes except
    /health require the owner (issuer + subject match, FR1.1, FR1.2).
servers:
  - url: https://studio-api.example.invalid   # real origin fixed in Infrastructure Design
security:
  - ownerBearer: []
tags:
  - name: U3-projects
  - name: U3-repositories
  - name: U4-media
  - name: U5-assistant
  - name: U9-publication
paths:
  /health:
    get:
      tags: [U3-projects]
      security: []
      summary: "Data-free health check (C10); no OwnerAccess, rate-limited"
      responses:
        "200": { description: OK, content: { application/json: { schema: { $ref: "#/components/schemas/Health" } } } }
  /projects:
    get:
      tags: [U3-projects]
      summary: List projects with derived status (status composed from U9)
      responses:
        "200": { description: Projects, content: { application/json: { schema: { type: array, items: { $ref: "#/components/schemas/ProjectSummary" } } } } }
    post:
      tags: [U3-projects]
      summary: Create a project from a title, or from a repository (FR3.1, FR2.3)
      requestBody: { content: { application/json: { schema: { $ref: "#/components/schemas/NewProject" } } } }
      responses:
        "201": { description: Created, content: { application/json: { schema: { $ref: "#/components/schemas/Project" } } } }
        "303": { description: Repository already linked; Location names the existing project }
  /projects/{projectId}:
    parameters: [ { $ref: "#/components/parameters/ProjectId" } ]
    get:
      tags: [U3-projects]
      responses:
        "200": { description: Project draft, headers: { ETag: { $ref: "#/components/headers/Revision" } }, content: { application/json: { schema: { $ref: "#/components/schemas/Project" } } } }
    patch:
      tags: [U3-projects]
      summary: Save draft changes; increments the revision (FR3.3, FR3.4)
      parameters: [ { $ref: "#/components/parameters/IfMatchRevision" } ]
      requestBody: { content: { application/json: { schema: { $ref: "#/components/schemas/ProjectPatch" } } } }
      responses:
        "200": { description: Saved, headers: { ETag: { $ref: "#/components/headers/Revision" } } }
        "409": { $ref: "#/components/responses/Conflict" }
        "428": { description: If-Match revision required }
  /projects/{projectId}/repositories:
    parameters: [ { $ref: "#/components/parameters/ProjectId" } ]
    post:
      tags: [U3-repositories]
      summary: Link a repository (FR3.1, FR2.3, FR2.5)
      parameters: [ { $ref: "#/components/parameters/IfMatchRevision" } ]
      requestBody: { content: { application/json: { schema: { type: object, additionalProperties: false, required: [githubRepositoryId], properties: { githubRepositoryId: { type: string } } } } } }
      responses: { "200": { description: Linked }, "409": { $ref: "#/components/responses/Conflict" } }
  /projects/{projectId}/images:
    parameters: [ { $ref: "#/components/parameters/ProjectId" } ]
    post:
      tags: [U3-projects]
      summary: Attach a validated image asset (attach check via C7; same-project only, FR4.8)
      parameters: [ { $ref: "#/components/parameters/IfMatchRevision" } ]
      requestBody: { content: { application/json: { schema: { $ref: "#/components/schemas/AttachImage" } } } }
      responses: { "200": { description: Attached }, "409": { $ref: "#/components/responses/Conflict" }, "422": { $ref: "#/components/responses/Invalid" } }
  /projects/{projectId}/attachments:
    parameters: [ { $ref: "#/components/parameters/ProjectId" } ]
    post:
      tags: [U3-projects]
      summary: Attach a validated file asset (same-project only)
      parameters: [ { $ref: "#/components/parameters/IfMatchRevision" } ]
      requestBody: { content: { application/json: { schema: { type: object, additionalProperties: false, required: [assetId, label], properties: { assetId: { $ref: "#/components/schemas/AssetId" }, label: { type: string, minLength: 1, maxLength: 120 } } } } } }
      responses: { "200": { description: Attached }, "409": { $ref: "#/components/responses/Conflict" }, "422": { $ref: "#/components/responses/Invalid" } }
  /categories:
    get:
      tags: [U3-projects]
      responses: { "200": { description: "The four fixed categories (FR9.8)", content: { application/json: { schema: { type: array, items: { $ref: "#/components/schemas/Category" } } } } } }
  /featured-lineup:
    get:
      tags: [U3-projects]
      responses: { "200": { description: "Draft line-up with revision", headers: { ETag: { $ref: "#/components/headers/Revision" } }, content: { application/json: { schema: { $ref: "#/components/schemas/Lineup" } } } } }
    put:
      tags: [U3-projects]
      summary: Reorder the draft line-up (at most 5, drafts included; FR9.7)
      parameters: [ { $ref: "#/components/parameters/IfMatchRevision" } ]
      requestBody: { content: { application/json: { schema: { type: object, additionalProperties: false, required: [orderedProjectIds], properties: { orderedProjectIds: { type: array, maxItems: 5, uniqueItems: true, items: { type: string } } } } } } }
      responses: { "200": { description: Saved }, "409": { $ref: "#/components/responses/Conflict" } }
  /repositories:
    get:
      tags: [U3-repositories]
      summary: Discover the owner's repositories (FR2.1, FR2.4)
      parameters: [ { name: q, in: query, schema: { type: string, maxLength: 100 } } ]
      responses:
        "200": { description: Repositories, content: { application/json: { schema: { type: array, items: { $ref: "#/components/schemas/Repository" } } } } }
        "503": { $ref: "#/components/responses/GitHubUnavailable" }
  /projects/{projectId}/uploads:
    parameters: [ { $ref: "#/components/parameters/ProjectId" } ]
    post:
      tags: [U4-media]
      summary: Issue a single-use upload authorization (FR4.8; rate-limited, NFR16)
      requestBody: { content: { application/json: { schema: { $ref: "#/components/schemas/UploadRequest" } } } }
      responses:
        "201": { description: Authorization, content: { application/json: { schema: { $ref: "#/components/schemas/UploadAuthorization" } } } }
        "404": { description: Project does not exist }
        "422": { $ref: "#/components/responses/Invalid" }
        "429": { $ref: "#/components/responses/RateLimited" }
  /assets/{assetId}:
    get:
      tags: [U4-media]
      summary: Validation status of an uploaded asset (ingests the C6 result record)
      parameters: [ { name: assetId, in: path, required: true, schema: { $ref: "#/components/schemas/AssetId" } } ]
      responses: { "200": { description: Asset status, content: { application/json: { schema: { $ref: "#/components/schemas/AssetStatus" } } } } }
  /projects/{projectId}/suggestions:
    parameters: [ { $ref: "#/components/parameters/ProjectId" } ]
    post:
      tags: [U5-assistant]
      summary: Request a description suggestion (FR5; spend and provider gates; rate-limited)
      requestBody: { content: { application/json: { schema: { type: object, additionalProperties: false, required: [field], properties: { field: { $ref: "#/components/schemas/TextField" } } } } } }
      responses:
        "200": { description: Suggestion, content: { application/json: { schema: { $ref: "#/components/schemas/Suggestion" } } } }
        "403": { description: "AI spending or private-content provider not approved (FR5.8, FR5.9); codes AI_SPEND_NOT_APPROVED, PROVIDER_NOT_APPROVED" }
        "422": { description: No linked repository (FR5.1) }
        "429": { $ref: "#/components/responses/RateLimited" }
        "504": { description: "No suggestion this time (FR5.7)" }
  /ai/settings:
    get:
      tags: [U5-assistant]
      responses: { "200": { description: "Spend approval, monthly limit, provider approvals and usage", content: { application/json: { schema: { $ref: "#/components/schemas/AiSettings" } } } } }
    put:
      tags: [U5-assistant]
      summary: Owner records spend approval, monthly limit and provider approvals
      requestBody: { content: { application/json: { schema: { $ref: "#/components/schemas/AiSettingsUpdate" } } } }
      responses: { "200": { description: Saved, content: { application/json: { schema: { $ref: "#/components/schemas/AiSettings" } } } }, "422": { $ref: "#/components/responses/Invalid" } }
  /projects/{projectId}/publication:
    parameters: [ { $ref: "#/components/parameters/ProjectId" } ]
    get:
      tags: [U9-publication]
      summary: Publication state, derived status, failed take-down alert
      responses: { "200": { description: State, content: { application/json: { schema: { $ref: "#/components/schemas/PublicationState" } } } } }
  /projects/{projectId}/publication/tickets:
    parameters: [ { $ref: "#/components/parameters/ProjectId" } ]
    post:
      tags: [U9-publication]
      summary: Prepare Publish, Update or Take down; runs link check and visibility read (ADR-012)
      requestBody: { content: { application/json: { schema: { type: object, additionalProperties: false, required: [action], properties: { action: { enum: [publish, update, takedown] }, includeLiveUrl: { type: boolean }, includeAttachmentIds: { type: array, uniqueItems: true, items: { $ref: "#/components/schemas/AssetId" } } } } } } }
      responses:
        "201": { description: Ticket, content: { application/json: { schema: { $ref: "#/components/schemas/Ticket" } } } }
        "429": { $ref: "#/components/responses/RateLimited" }
  /featured-order/tickets:
    post:
      tags: [U9-publication]
      summary: Prepare "Update featured order" (frozen candidate order)
      responses: { "201": { description: Ticket, content: { application/json: { schema: { $ref: "#/components/schemas/Ticket" } } } } }
  /publication/confirmations:
    post:
      tags: [U9-publication]
      summary: Confirm a ticket; atomic acceptance (ADR-012). Idempotent per confirmationId.
      requestBody: { content: { application/json: { schema: { $ref: "#/components/schemas/Confirmation" } } } }
      responses:
        "202": { description: Accepted, content: { application/json: { schema: { $ref: "#/components/schemas/OperationRef" } } } }
        "409": { $ref: "#/components/responses/Conflict" }
        "410": { description: Ticket expired; prepare again }
  /publication/operations/{operationId}:
    get:
      tags: [U9-publication]
      parameters: [ { name: operationId, in: path, required: true, schema: { type: string } } ]
      responses: { "200": { description: Operation, content: { application/json: { schema: { $ref: "#/components/schemas/Operation" } } } } }
  /publication/operations/{operationId}/retry:
    post:
      tags: [U9-publication]
      summary: Manual retry (Publish/Update/featured-order only while the ticket is unexpired; take-down always)
      parameters: [ { name: operationId, in: path, required: true, schema: { type: string } } ]
      responses: { "202": { description: Retry scheduled }, "409": { description: Superseded }, "410": { description: Ticket expired; prepare again } }
  /projects/{projectId}/preview:
    parameters: [ { $ref: "#/components/parameters/ProjectId" } ]
    get:
      tags: [U9-publication]
      summary: "Preview payload (C4); only when the candidate projects to a valid C2 snapshot"
      responses:
        "200": { description: Preview, content: { application/json: { schema: { $ref: "#/components/schemas/PreviewPayload" } } } }
        "422": { description: "Not previewable yet (code PREVIEW_BLOCKED); lists blockers such as missing title, lead image, alt text or slug", content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
  /activity:
    get:
      tags: [U9-publication]
      responses: { "200": { description: "Activity log (FR7.7)", content: { application/json: { schema: { type: array, items: { $ref: "#/components/schemas/ActivityEntry" } } } } } }
components:
  securitySchemes:
    ownerBearer: { type: http, scheme: bearer, bearerFormat: JWT }
  parameters:
    ProjectId: { name: projectId, in: path, required: true, schema: { type: string, pattern: "^[A-Za-z0-9_-]{8,40}$" } }
    IfMatchRevision: { name: If-Match, in: header, required: true, schema: { type: string }, description: Draft revision the edit is based on }
  headers:
    Revision: { schema: { type: string }, description: Current draft or line-up revision }
  responses:
    Conflict: { description: "Stale revision, used or changed ticket, or changed basis; review again", content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
    Invalid: { description: Validation failed, content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
    RateLimited: { description: "Rate limit exceeded; no provider call, authorization or outbound request was made (code RATE_LIMITED)", content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
    Unauthenticated: { description: "No valid owner token (code UNAUTHENTICATED); returned by the pipeline before any handler", content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
    Forbidden: { description: "Valid token that is not the owner (code NOT_OWNER); returned by the pipeline before any handler", content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
    GitHubUnavailable: { description: "Can't reach GitHub right now (code GITHUB_UNAVAILABLE)", content: { application/json: { schema: { $ref: "#/components/schemas/Error" } } } }
  schemas:
    Health: { type: object, additionalProperties: false, required: [status], properties: { status: { const: ok } } }
    Error: { type: object, required: [code, message, requestId], properties: { code: { $ref: "#/components/schemas/ErrorCode" }, message: { type: string }, requestId: { type: string }, blockers: { type: array, items: { type: string } } } }
    ErrorCode:
      enum: [UNAUTHENTICATED, NOT_OWNER, RATE_LIMITED, VALIDATION_FAILED, NOT_FOUND, REVISION_REQUIRED,
             STALE_REVISION, SLUG_TAKEN, LINEUP_CHANGED, TICKET_USED, TICKET_MISMATCH, TICKET_EXPIRED, BASIS_CHANGED,
             SUPERSEDED, PREVIEW_BLOCKED, NO_LINKED_REPOSITORY, AI_SPEND_NOT_APPROVED, PROVIDER_NOT_APPROVED,
             GITHUB_UNAVAILABLE, SUGGESTION_UNAVAILABLE, INTERNAL]
    Category: { type: object, required: [categoryId, slug, name, position], properties: { categoryId: { type: string }, slug: { enum: [games, astronomy, woodworking, software] }, name: { type: string }, position: { type: integer } } }
    Lineup: { type: object, required: [revision, orderedProjectIds], properties: { revision: { type: integer }, orderedProjectIds: { type: array, maxItems: 5, items: { type: string } } } }
    AiSettings: { type: object, required: [spendApproved, providers, usageThisMonth], properties: { spendApproved: { type: boolean }, monthlyLimit: { type: [integer, "null"], minimum: 0 }, providers: { type: array, items: { type: object, required: [providerId, approvedForPrivateContent], properties: { providerId: { type: string }, approvedForPrivateContent: { type: boolean }, dataUseTermsReference: { type: string } } } }, usageThisMonth: { type: integer, minimum: 0 } } }
    AiSettingsUpdate: { type: object, additionalProperties: false, properties: { spendApproved: { type: boolean }, monthlyLimit: { type: integer, minimum: 0 }, providerApprovals: { type: array, items: { type: object, additionalProperties: false, required: [providerId, approvedForPrivateContent], properties: { providerId: { type: string }, approvedForPrivateContent: { type: boolean }, dataUseTermsReference: { type: string } } } } } }
    ActivityEntry: { type: object, required: [entryId, at, action, outcome], properties: { entryId: { type: string }, at: { type: string, format: date-time }, projectId: { type: [string, "null"] }, action: { enum: [publish, update, takedown, featuredOrder] }, outcome: { enum: [committed, failed, superseded] }, operationId: { type: string } } }
    AssetId: { type: string, pattern: "^ast_[A-Za-z0-9]{16,32}$", description: "The MediaAsset assetId; the same value is called assetRef in C2, C3, C6 and C8" }
    TextField: { enum: [summary, inspiration, designChallenges, architecturalDecisions, implementation, outcomes, lessonsLearned] }
    NewProject: { type: object, additionalProperties: false, oneOf: [ { required: [title] }, { required: [githubRepositoryId] } ], properties: { title: { type: string, minLength: 1, maxLength: 120 }, githubRepositoryId: { type: string } } }
    ProjectSummary: { type: object, required: [projectId, title, status], properties: { projectId: { type: string }, title: { type: string }, status: { enum: [Draft, Published, Changes since last publish, Taken down] }, takeDownFailed: { type: boolean } } }
    Project: { type: object, description: Draft fields owned by Projects (full shape in Functional Design) }
    ProjectPatch: { type: object, description: Partial draft update; unknown fields rejected }
    AttachImage: { type: object, additionalProperties: false, required: [assetId, altText], properties: { assetId: { $ref: "#/components/schemas/AssetId" }, altText: { type: string, minLength: 1, maxLength: 300 }, caption: { type: string, maxLength: 300 }, isLead: { type: boolean } } }
    Repository: { type: object, required: [githubRepositoryId, name, visibility, updatedAt], properties: { githubRepositoryId: { type: string }, name: { type: string }, visibility: { enum: [PRIVATE, public, unconfirmed] }, updatedAt: { type: string, format: date-time }, linkedProjectId: { type: [string, "null"] } } }
    UploadRequest: { type: object, additionalProperties: false, required: [kind, declaredType, byteSize], properties: { kind: { enum: [image, file] }, declaredType: { type: string }, byteSize: { type: integer, minimum: 1 } } }
    UploadAuthorization: { type: object, required: [assetId, uploadUrl, fields, expiresAt], properties: { assetId: { $ref: "#/components/schemas/AssetId" }, uploadUrl: { type: string, format: uri }, fields: { type: object }, expiresAt: { type: string, format: date-time } } }
    AssetStatus: { type: object, required: [assetId, status], properties: { assetId: { $ref: "#/components/schemas/AssetId" }, status: { enum: [pending, valid, rejected] }, reason: { type: string } } }
    Suggestion: { type: object, required: [suggestionId, providerId, sourceFiles, text], properties: { suggestionId: { type: string }, providerId: { type: string }, sourceFiles: { type: array, items: { type: string } }, text: { type: string } } }
    PublicationState: { type: object, required: [status], properties: { status: { $ref: "#/components/schemas/ProjectSummary/properties/status" }, takeDownFailed: { type: boolean }, lastOperation: { $ref: "#/components/schemas/OperationRef" } } }
    Ticket: { type: object, required: [ticketId, kind, inventory, inventoryDigest, blockers, expiresAt], properties: { ticketId: { type: string }, kind: { enum: [publish, update, takedown, featuredOrder] }, inventory: { type: object, description: Full FR7.2 inventory for display }, inventoryDigest: { type: string }, blockers: { type: array, items: { type: string } }, expiresAt: { type: string, format: date-time } } }
    Confirmation: { type: object, additionalProperties: false, required: [ticketId, inventoryDigest, confirmationId], properties: { ticketId: { type: string }, inventoryDigest: { type: string }, confirmationId: { type: string, format: uuid } } }
    OperationRef: { type: object, required: [operationId, sequence], properties: { operationId: { type: string }, sequence: { type: integer } } }
    Operation: { type: object, required: [operationId, kind, status], properties: { operationId: { type: string }, kind: { enum: [publish, update, takedown, featuredOrder] }, status: { enum: [accepted, running, committed, failed, superseded] }, failureReason: { type: string } } }
    PreviewPayload: { $ref: "https://contracts.invalid/preview-payload/1.0.json" }
```

Notes:
- **Shared pipeline responses.** Every route except `/health` may also answer `401` (Unauthenticated), `403` (Forbidden) and `429` (RateLimited), from the pipeline, before any handler. These are declared once here and are not repeated per route.
- **Strict request bodies.** Every request body is closed (`additionalProperties: false`). The U1 generator enforces this OpenAPI-wide, and a C1 contract test fails on any request schema that is not closed.
- **Concurrency.** `If-Match` carries the draft or line-up revision (FR3.4). A save based on an older revision gets 409 and changes nothing.
- **Unknown fields.** Additive response fields are safe, and clients ignore fields they don't know. Request bodies reject unknown fields.
- **Full shapes.** Functional Design pins the full draft shape (`Project`, `ProjectPatch`) and the inventory shape.

## C2 — Public Site Snapshot (U9 → U8, U7; U11 for preview)

This is the only input to the public site (ADR-002). It is strict: `additionalProperties: false` at every level, so the FR4.10 allow-list is enforced structurally. U9 validates every snapshot before sending it, and U8 and U11 validate it again on receipt. A snapshot that fails validation is refused whole.

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: https://contracts.invalid/public-site-snapshot/1.0.json
title: PublicSiteSnapshot
type: object
additionalProperties: false
required: [schemaVersion, generation, site, exhibits, featuredOrder, categories]
properties:
  schemaVersion: { const: "1.0" }
  generation: { type: integer, minimum: 0, description: "The site generation public storage will be at once this snapshot is applied: base plus one for an operation; the committed generation itself for a restore or recovery" }
  site:
    type: object
    additionalProperties: false
    required: [ownerName, githubProfileUrl]
    properties:
      ownerName: { type: string, maxLength: 120 }
      githubProfileUrl: { type: string, format: uri, pattern: "^https://github\\.com/[A-Za-z0-9-]+$" }
      contactEmail: { type: [string, "null"], format: email, description: "null until the owner supplies it (FR9.4)" }
  exhibits:
    type: array
    maxItems: 200
    items: { $ref: "#/$defs/Exhibit" }
  featuredOrder:
    type: array
    maxItems: 5
    items: { $ref: "#/$defs/Slug" }
    description: Slugs of featured live exhibits, in published order; each must be in exhibits with featured=true
  categories:
    type: array
    maxItems: 4
    items: { $ref: "#/$defs/CategoryWithCount" }
    description: Only categories with at least one live exhibit
$defs:
  Slug: { type: string, pattern: "^[a-z0-9]+(-[a-z0-9]+)*$", maxLength: 60 }
  AssetRef: { type: string, pattern: "^ast_[A-Za-z0-9]{16,32}$" }
  Category:
    type: object
    additionalProperties: false
    required: [slug, name, position]
    properties:
      slug: { enum: [games, astronomy, woodworking, software] }
      name: { type: string, maxLength: 60 }
      position: { type: integer, minimum: 0 }
  CategoryWithCount:
    type: object
    additionalProperties: false
    required: [slug, name, position, count]
    properties:
      slug: { enum: [games, astronomy, woodworking, software] }
      name: { type: string, maxLength: 60 }
      position: { type: integer, minimum: 0 }
      count: { type: integer, minimum: 1 }
  Image:
    type: object
    additionalProperties: false
    required: [assetRef, altText, width, height]
    properties:
      assetRef: { $ref: "#/$defs/AssetRef" }
      altText: { type: string, minLength: 1, maxLength: 300 }
      caption: { type: string, maxLength: 300 }
      width: { type: integer, minimum: 1, description: "Pixel width of the metadata-free primary image; drives the variant rule in C8" }
      height: { type: integer, minimum: 1 }
  Attachment:
    type: object
    additionalProperties: false
    required: [assetRef, label, fileType, byteSize]
    properties:
      assetRef: { $ref: "#/$defs/AssetRef" }
      label: { type: string, maxLength: 120 }
      fileType: { enum: [PDF, SKP, FCStd, DXF, STL, ZIP, VSDX] }
      byteSize: { type: integer, minimum: 1, maximum: 52428800 }
  Link:
    type: object
    additionalProperties: false
    required: [kind, label, url]
    properties:
      kind: { enum: [demo, documentation, other] }
      label: { type: string, maxLength: 80 }
      url: { $ref: "#/$defs/NonRepositoryHttpsUrl" }
  NonRepositoryHttpsUrl:
    type: string
    format: uri
    maxLength: 2048
    pattern: "^https://"
    not: { pattern: "^https://([A-Za-z0-9-]+\\.)*(github\\.com|githubusercontent\\.com|gitlab\\.com|bitbucket\\.org)(:[0-9]+)?(/|$)" }
    description: "Repository hosts are never allowed here; repositories are published only through publicRepositories (ADR-002, FR4.3)"
  Badge:
    type: object
    additionalProperties: false
    required: [kind]
    properties:
      kind: { enum: [inBrowser, signInRequired, byInvitation, bestOnDesktop, openSource, sourceAvailable, sourcePrivate] }
      spdx: { type: string, pattern: "^[A-Za-z0-9.+-]{1,40}$", description: Only with kind openSource }
  PublicRepository:
    type: object
    additionalProperties: false
    required: [name, url]
    properties:
      name: { type: string, maxLength: 100 }
      url: { type: string, pattern: "^https://github\\.com/[A-Za-z0-9-]+/[A-Za-z0-9._-]+$" }
      licence: { type: string, pattern: "^[A-Za-z0-9.+-]{1,40}$" }
  Sections:
    type: object
    additionalProperties: false
    properties:
      inspiration: { type: string, maxLength: 8000 }
      designChallenges: { type: string, maxLength: 8000 }
      architecturalDecisions: { type: string, maxLength: 8000 }
      implementation: { type: string, maxLength: 8000 }
      outcomes: { type: string, maxLength: 8000 }
      lessonsLearned: { type: string, maxLength: 8000 }
  Exhibit:
    type: object
    additionalProperties: false
    required: [slug, title, summary, sections, leadImage, images, attachments, links, badges, publicRepositories, featured, publishedAt]
    properties:
      slug: { $ref: "#/$defs/Slug" }
      title: { type: string, minLength: 1, maxLength: 120 }
      summary: { type: string, maxLength: 1200 }
      sections: { $ref: "#/$defs/Sections" }
      leadImage: { $ref: "#/$defs/Image" }
      images: { type: array, maxItems: 40, items: { $ref: "#/$defs/Image" } }
      attachments: { type: array, maxItems: 20, items: { $ref: "#/$defs/Attachment" } }
      links: { type: array, maxItems: 10, items: { $ref: "#/$defs/Link" } }
      liveUrl: { $ref: "#/$defs/NonRepositoryHttpsUrl", description: "Present only if included at Publish and authorized where required (FR10.7)" }
      badges: { type: array, maxItems: 6, items: { $ref: "#/$defs/Badge" } }
      publicRepositories: { type: array, maxItems: 10, items: { $ref: "#/$defs/PublicRepository" } }
      primaryCategory: { $ref: "#/$defs/Category" }
      featured: { type: boolean }
      publishedAt: { type: string, format: date-time }
```

**Structural rules.** The schema enforces these itself:
- the allow-list, with no unknown fields;
- `https` only;
- **repository hosts:** `links[].url` and `liveUrl` may never point at a repository host. The hosts are `github.com`, `githubusercontent.com`, `gitlab.com` and `bitbucket.org`, with any subdomain.

**Semantic rules.** The schema cannot express these. Each has a C2 conformance test, and the "Checked by" column says who enforces it. U8 cannot verify facts held only in Studio data (constraints 3 and 4), so those rules are U9's alone. U8 re-checks the rules that can be decided from the snapshot itself.

| # | Rule | Checked by |
|---|---|---|
| S1 | Every `featuredOrder` slug is an exhibit with `featured: true`; no duplicates | U9 and U8 |
| S2 | `categories` equal the set derived from the exhibits' `primaryCategory`, with correct counts | U9 and U8 |
| S3 | Exhibit `slug`s are unique | U9 and U8 |
| S4 | `spdx` appears only with `kind: openSource` | U9 and U8 |
| S5 | `inBrowser`, `signInRequired`, `byInvitation`: at most one, and only when `liveUrl` is present | U9 and U8 |
| S6 | `openSource` only when `publicRepositories` has a repository whose `licence` is that SPDX id; `sourceAvailable` only when it has a repository; `sourcePrivate` only when no repository is listed | U9 and U8 (presence and consistency) |
| S6a | Whether a licence is OSI-approved, which decides `openSource` versus `sourceAvailable`, uses U9's pinned SPDX/OSI list | U9 only |
| S7 | Within one exhibit, each `assetRef` appears once among `leadImage` and `images`, and once among `attachments` | U9 and U8 |
| S8 | `publicRepositories` holds only repositories confirmed public at preparation (fail closed, FR4.10) | U9 only |
| S9 | `liveUrl` is present only if the owner included it at Publish and, where required, "Live URL authorized" is set; excluded by default for a project with a private repository (FR10.7) | U9 only |
| S10 | Badges are derived only from the FR4.10 table, never typed by hand | U9 only |

The snapshot carries no draft, ticket, operation, link-check, private-repository or access-metadata field beyond these, so the PB-02 export scan has one small input type to check.

**Slugs.**
- Slugs are public addresses (`/work/{slug}`). Projects owns a `slug` draft attribute. It is proposed from the title when the project is created, can be edited until the first publish, and is fixed after that.
- Projects enforces uniqueness on save: a duplicate gets 409 with code `SLUG_TAKEN`.
- A candidate snapshot for a project never published before carries its draft slug.

The other additions are listed under "Model Additions and Mappings".

**Size bound.** `exhibits` is capped at 200. Before invoking U8, U9 refuses a request whose serialized size is over 5 MB, below the 6 MB limit on synchronous invokes. The operation then fails with the reason `SNAPSHOT_TOO_LARGE`, and nothing is written.

## C3 — Publish Request (U9 → U8), including R-07

One invoke per attempt (ADR-004). Every request means "make public storage equal this snapshot". Export, restore and recovery are therefore the same operation with a different `purpose`, which is used only for logging. U8 works out writes and deletions from its own ExportedObjectSet records.

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: https://contracts.invalid/publish-request/1.0.json
title: PublishRequest
type: object
additionalProperties: false
required: [schemaVersion, operationId, attemptToken, purpose, snapshot, assetManifest]
properties:
  schemaVersion: { const: "1.0" }
  operationId: { type: string }
  attemptToken: { type: integer, minimum: 1, description: Strictly increasing per attempt (ADR-004) }
  purpose: { enum: [operation, restore, recovery] }
  snapshot: { $ref: "https://contracts.invalid/public-site-snapshot/1.0.json" }
  assetManifest:
    type: array
    items:
      type: object
      additionalProperties: false
      required: [assetRef, kind, sourceKeys]
      properties:
        assetRef: { type: string, pattern: "^ast_[A-Za-z0-9]{16,32}$" }
        kind: { enum: [imageDerivatives, file] }
        sourceKeys:
          type: array
          minItems: 1
          maxItems: 6
          uniqueItems: true
          items: { type: string, maxLength: 200 }
```

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: https://contracts.invalid/publish-result/1.0.json
title: PublishResult
type: object
additionalProperties: false
required: [schemaVersion, operationId, attemptToken, status]
properties:
  schemaVersion: { const: "1.0" }
  operationId: { type: string }
  attemptToken: { type: integer }
  status: { enum: [completed, fenced, invalid, failed] }
  generation: { type: integer, description: Echo of snapshot.generation when completed }
  objectsWritten: { type: integer }
  objectsDeleted: { type: integer }
  invalidationId: { type: string }
  error: { type: string, maxLength: 500, description: "Reason code and object keys only; never snapshot content" }
```

**Behaviour and authority:**
- **Status.** U8 returns `completed` only after every write and deletion succeeded and the CDN invalidation was submitted. The other results:
  - `fenced`: a higher token is already recorded;
  - `invalid`: schema, semantic or manifest-key validation failed, and nothing was written;
  - `failed`: anything else.
- **U8 does not decide.** It never retries on its own, chooses nothing about publication, and never reads Studio data. U9 treats any status other than `completed`, or a timeout, as a failed attempt. It then restores (ADR-004) or recovers.
- **Invocation and timeout.** Only U9's runner role may invoke U8 (resource policy; Infrastructure Design). The invoke timeout is the per-attempt budget set in NFR Design.

**R-07: the authorized storage scope, enforced in two layers.**

1. **IAM (Infrastructure Design implements this; the contract fixes it).** U8's role may read only two private prefixes:
   - `derivatives/` (metadata-free image derivatives);
   - `files/` (validated attachments).

   It can never read `incoming/` (raw uploads), `originals/` (images with metadata), `results/`, `backups/` or any database. It may write and delete only in the public bucket, and read and write its own private state store. IAM can only limit by prefix, so layer 2 is required.

2. **The application boundary (U8, before any read).** U8 rejects the whole request, with `invalid` and nothing written, unless every manifest entry passes all of these checks:
   - **(a)** `assetRef` is referenced by the snapshot itself: an image or lead image of a live exhibit for `imageDerivatives`, or an attachment for `file`. The manifest has exactly one entry per referenced asset, with none missing and none extra.
   - **(b)** The `sourceKeys` exactly match the keys the C8 rules require for that `assetRef` and `kind`, with no missing key, no extra key and no duplicate:
     - for an image, `derivatives/{assetRef}/{variant}.{format}`, for every variant the C8 variant rule gives from the snapshot `width`, in both formats;
     - for a file, `files/{assetRef}/file.{ext}`, where `ext` is the C8 extension for the snapshot's `fileType`.
   - **(c)** Keys are compared byte for byte with the generated expected keys, with no normalisation. Any key containing any of these never matches:
     - `..`, `//`, or a leading `/`;
     - `%` or `\`;
     - uppercase characters in a prefix;
     - whitespace or control characters.
   - **(d)** Public object paths are computed by U8 from the snapshot and the C9 path rules, never taken from the request. U8 writes exactly that set of paths, plus the static assets listed by C11. If a required derivative is missing from the manifest, the result is `invalid`, so a live page never references a missing image.

**C3 contract tests (in U1, run by U8 and U9).** Every K case must return `invalid` and write nothing:

| Test | Request | Expected |
|---|---|---|
| C3-K1 | `sourceKey` under `originals/` for a valid assetRef | `invalid` |
| C3-K2 | `sourceKey` under `incoming/` or `results/` | `invalid` |
| C3-K3 | Manifest entry for an assetRef not in the snapshot | `invalid` |
| C3-K4 | A snapshot image whose assetRef has no manifest entry | `invalid` |
| C3-K5 | Key for another asset's derivative (`derivatives/ast_B/...` under `assetRef: ast_A`) | `invalid` |
| C3-K6 | Path traversal or encoding (`derivatives/ast_A/../../originals/x`, `%2e%2e`) | `invalid` |
| C3-K7 | `kind: file` pointing at `derivatives/` (or the reverse) | `invalid` |
| C3-K8 | File extension not matching the snapshot `fileType` | `invalid` |
| C3-K9 | Extra unknown property anywhere in request or snapshot | `invalid` |
| C3-K10 | Unsupported `schemaVersion` | `invalid` |
| C3-K11 | Uppercase reserved prefix (`Derivatives/...`, `FILES/...`) | `invalid` |
| C3-K12 | Double slash (`derivatives//ast_A/w480.webp`) | `invalid` |
| C3-K13 | Leading slash (`/derivatives/ast_A/w480.webp`) | `invalid` |
| C3-K14 | Control character, whitespace or backslash in a key | `invalid` |
| C3-K15 | Two manifest entries for the same `assetRef`, or a duplicate key within an entry | `invalid` |
| C3-K16 | Variant or format outside the allowed set (`w2000.webp`, `w480.png`) | `invalid` |
| C3-K17 | A variant required by the C8 rule for the image's `width` is missing | `invalid` |
| C3-K18 | A snapshot that violates a U8-checked semantic rule (S1 to S7), or is over the size bound | `invalid` |
| C3-P1 | Valid request | The public paths written equal exactly the set computed from the snapshot by the C9 rules, plus the C11 static assets |
| C3-F1 | Valid request with a token lower than the fence | `fenced`, nothing written |
| C3-OK | Valid request, valid keys | `completed` |

An IAM-level test in Infrastructure Design confirms that U8's role is denied `originals/`, `incoming/` and `results/`.

## C4 — Preview Payload (U9 → U11, inside C1)

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: https://contracts.invalid/preview-payload/1.0.json
title: PreviewPayload
type: object
additionalProperties: false
required: [schemaVersion, snapshot, previewSlug, imageAddresses, downloadAddresses, expiresAt]
properties:
  schemaVersion: { const: "1.0" }
  snapshot:
    $ref: "https://contracts.invalid/public-site-snapshot/1.0.json"
    description: >
      Candidate site = the last committed snapshot with this exhibit replaced by its candidate
      version (same projection as publication), so card, carousel slide and category page preview too (FR6.1).
  previewSlug: { type: string, pattern: "^[a-z0-9]+(-[a-z0-9]+)*$", description: "Slug of the exhibit being previewed inside the candidate snapshot (its draft slug before first publish)" }
  imageAddresses:
    type: object
    description: "assetRef + variant + format -> owner-only, short-lived address; kept outside the snapshot (never part of C2)"
    additionalProperties: { type: string, format: uri }
    propertyNames: { pattern: "^ast_[A-Za-z0-9]{16,32}/w(480|960|1600)\\.(webp|jpg)$" }
  downloadAddresses:
    type: object
    description: "assetRef -> owner-only, short-lived download address for each attachment in the previewed exhibit; served as an attachment, never rendered"
    additionalProperties: { type: string, format: uri }
    propertyNames: { pattern: "^ast_[A-Za-z0-9]{16,32}$" }
  expiresAt: { type: string, format: date-time }
```

**Use of the payload.**
- **Rendering.** U11 renders `snapshot` through C11 with `mode: "preview"`, and a resolver that looks up images in `imageAddresses` by `assetRef/variant.format` and downloads in `downloadAddresses` by `assetRef`. If a reference is missing, the resolver throws `RenderInputError` and no preview is shown. Publication uses the C9 resolver instead.
- **Isolation.** The output goes into a sandboxed frame marked "Preview — not public" and is never written anywhere.
- **Fidelity.** The parity test (unit-of-work constraint 2; C11) runs the same fixtures through Node and a browser.
- **Strict even inside C1.** C4 is a strict contract: U11 validates it against this schema, and the snapshot against C2, before rendering.

**When preview is available.** Preview needs a candidate that projects to a valid C2 snapshot. Otherwise the endpoint answers 422 `PREVIEW_BLOCKED` with the blockers, such as no title, no lead image, an image without alt text, or no slug. These are the content blockers of FR7.3. Rights, live-URL and publication approvals do not block preview, because preview is private (FR6.2).

## C5 — Link Check (U9 → U6)

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: https://contracts.invalid/link-check-request/1.0.json
title: LinkCheckRequest
type: object
additionalProperties: false
required: [schemaVersion, requestId, url]
properties:
  schemaVersion: { const: "1.0" }
  requestId: { type: string }
  url: { type: string, maxLength: 2048 }
```

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: https://contracts.invalid/link-check-result/1.0.json
title: LinkCheckResult
type: object
additionalProperties: false
required: [schemaVersion, requestId, label, checkedAt, reason]
properties:
  schemaVersion: { const: "1.0" }
  requestId: { type: string }
  label: { enum: ["Reachable", "Not reachable", "Refused (non-public address)"] }
  finalAddress: { type: string, description: "Sanitized: no userinfo, query or fragment" }
  signInDetected: { type: boolean }
  crossDomainRedirect: { type: boolean }
  checkedAt: { type: string, format: date-time }
  reason: { type: string, maxLength: 200 }
```

**Behaviour:**
- U6 applies NFR17 in full. It parses the URL itself; the request is not trusted to be canonical.
- U6 finishes within 15 seconds. U9's invoke timeout is 20 seconds, and an invoke error or timeout is recorded as "Not reachable" with the reason.
- U9 sends at most one URL per exhibit per preparation, and rate limits are applied before the invoke (NFR16).
- U6 stores nothing; U9 stores the result as a LinkCheckRecord.
- No field of C5 enters C2.

## C6 — Upload Processing (storage event → U4 processor → result record → U4 module)

- **Input.** An object created under `incoming/{assetRef}/upload`, through a single-use upload authorization bound to project, size and type.
- **Output.** A result record at `results/{assetRef}.json`. The processor has no database or network access beyond its prefixes. U4's module ingests the record into MediaAsset when the status is read or an attach is checked.

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: https://contracts.invalid/upload-result/1.0.json
title: UploadResult
type: object
additionalProperties: false
required: [schemaVersion, assetRef, projectId, status, processedAt]
properties:
  schemaVersion: { const: "1.0" }
  assetRef: { type: string, pattern: "^ast_[A-Za-z0-9]{16,32}$" }
  projectId: { type: string }
  status: { enum: [valid, rejected] }
  reason: { type: string, maxLength: 200, description: "e.g. 'This photo could not be converted' (FR4.2)" }
  detectedType: { enum: [jpeg, png, webp, heic, pdf, skp, fcstd, dxf, stl, zip, vsdx] }
  byteSize: { type: integer }
  width: { type: integer }
  height: { type: integer }
  derivatives:
    type: array
    items:
      type: object
      additionalProperties: false
      required: [variant, format, key, width, height]
      properties:
        variant: { type: string, enum: [w480, w960, w1600] }
        format: { type: string, enum: [webp, jpg] }
        key: { type: string, pattern: "^derivatives/ast_[A-Za-z0-9]{16,32}/w(480|960|1600)\\.(webp|jpg)$" }
        width: { type: integer }
        height: { type: integer }
  fileKey: { type: string, pattern: "^files/ast_[A-Za-z0-9]{16,32}/file\\.(pdf|skp|fcstd|dxf|stl|zip|vsdx)$", description: "Validated attachment (C8)" }
  documentMetadata: { type: object, description: "Extracted under FR4.4 limits; shown at Publish (FR7.2)" }
  archiveEntries: { type: array, items: { type: string }, maxItems: 2000 }
  metadataReadable: { type: boolean, description: "false means the confirmation shows 'Metadata could not be read'" }
  processedAt: { type: string, format: date-time }
```

On success the processor writes, under the C8 layout, exactly the derivatives the C8 variant rule requires, or the validated file. A rejected upload leaves no derivative or file. The raw object under `incoming/` is deleted after processing, and the original image is kept under `originals/` (FR4.2).

## C7 — Back-End Module Interfaces (in-process, Python)

These are the only ways the modules in the back-end package call each other. Reverse calls go through these ports, and the implementation is supplied by the depending unit (unit-of-work: "Call Direction Inside the Back End"). Signatures are indicative; Functional Design fixes the types.

```python
# u1-contracts/python/ports.py  (version 1.0)
from typing import Protocol, Callable, Sequence
from contextlib import AbstractContextManager

class UnitOfWork(Protocol):                      # one database transaction; ADR-012 / ADR-004
    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, *exc) -> bool | None: ...

class RouteRegistry(Protocol):                   # R-08: U4/U5/U9 register into U3's host
    def register(self, method: str, path: str, handler: Callable, *, rate_limit: str | None = None) -> None: ...
    # every registered route runs: OwnerAccess -> rate limit -> request id -> handler (no opt-out)

class RepositoryCatalogPort(Protocol):           # provided by U3; consumed by U3 routes, U5 and U9
    def list_repositories(self, query: str | None) -> Sequence["RepositorySummary"]: ...         # Discover (U3)
    def access_facts(self, github_repository_ids: Sequence[str]) -> dict[str, "RepositoryAccessFacts"]: ...
    # U9 at preparation: name, url, visibility in {"public","PRIVATE","unconfirmed"}, licence SPDX or None.
    # Any GitHub error, rate limit or rename yields "unconfirmed" with no name, url or licence (fail closed, FR4.10).
    def documentation(self, github_repository_id: str, max_bytes: int) -> "UntrustedDocuments": ...
    # U5: README and documentation text, marked untrusted (FR5.6); raises GitHubUnavailable (FR2.4)

class LinkCheckClientPort(Protocol):             # provided by U9's adapter around C5; consumed by U9 preparation
    def check(self, url: str) -> "LinkCheckResult": ...   # invoke error or 20 s timeout -> "Not reachable"

class ProjectsPort(Protocol):                    # provided by U3; consumed by U5, U9, U10
    def get_draft(self, project_id: str) -> "Draft": ...
    def read_lineup(self) -> "Lineup": ...       # revision + ordered project ids; U9 builds featured-order tickets
    def revision_guard(self, uow: UnitOfWork, project_id: str, expected_revision: int, operation_id: str) -> None: ...
    def lineup_guard(self, uow: UnitOfWork, expected_revision: int, operation_id: str) -> None: ...
    def release_featured_slot(self, uow: UnitOfWork, project_id: str) -> None: ...   # bumps line-up revision
    def record_provenance(self, project_id: str, field: str, suggestion_id: str, provider_id: str,
                          source_repository_ids: Sequence[str], expected_revision: int) -> int: ...
    def export_records(self) -> bytes: ...       # ContentBackup

class AttachCheckPort(Protocol):                 # declared for U3; implemented by U4; U3 default refuses all
    def check_attachable(self, asset_id: str, project_id: str, kind: str) -> "AttachDecision": ...

class MediaPort(Protocol):                       # provided by U4
    def issue_upload_authorization(self, project_id: str, kind: str, declared_type: str, byte_size: int) -> "UploadAuthorization": ...
    def asset_status(self, asset_id: str) -> "AssetStatus": ...
    def attachment_inventory(self, asset_id: str) -> "AttachmentInventory": ...   # FR7.2
    def manifest_keys(self, asset_id: str) -> Sequence[str]: ...                   # C8 keys for C3
    def image_facts(self, asset_id: str) -> "ImageFacts": ...                       # pixel width/height for C2 Image + C8 variant rule
    def preview_address(self, asset_id: str, variant: str, fmt: str, ttl_seconds: int) -> str: ...
    def preview_download_address(self, asset_id: str, ttl_seconds: int) -> str: ...
    def export_records(self) -> bytes: ...

class AssistantPort(Protocol):                   # provided by U5
    def suggestion_provenance(self, suggestion_id: str) -> "Provenance": ...
    def export_records(self) -> bytes: ...

class PublicationPort(Protocol):                 # provided by U9
    def statuses(self, project_ids: Sequence[str]) -> dict[str, "DerivedStatus"]: ...
    def export_records(self) -> bytes: ...
```

**Rules:**
- **Transactions.** The guard methods take the caller's `UnitOfWork`. ADR-012 acceptance and ADR-004 commit each run inside one transaction, and each module writes only its own records (constraint 7).
- **Fail-closed attach.** U3's default `AttachCheckPort` refuses every attachment until U4 provides the implementation.
- **No database sharing.** No module reads another module's collections directly; only these ports cross between modules.
- **Consumers.** These ports are the U3 → U5 and U3 → U9 edges of `unit-of-work-dependency.md`:
  - `RepositoryCatalogPort.access_facts` and `ProjectsPort.read_lineup` are consumed by U9;
  - `RepositoryCatalogPort.documentation` and `ProjectsPort.get_draft` are consumed by U5.
- **Facts frozen at preparation.** The repository facts and the link-check result that U9 freezes into a ticket come only from `access_facts` and `LinkCheckClientPort.check`, called during preparation. The attachment facts come from `MediaPort.attachment_inventory`.

## C8 — Private Storage Key Layout (U4)

| Prefix | Written by | Read by | Content |
|---|---|---|---|
| `incoming/{assetRef}/upload` | Owner's browser (single-use authorization) | U4 processor | Raw upload; deleted after processing |
| `originals/{assetRef}/original.{ext}` | U4 processor | Nobody but restore and backup | Original image, with metadata. Never public |
| `derivatives/{assetRef}/{variant}.{format}` | U4 processor | U8 (R-07), U4 preview addresses | Metadata-free image derivatives, per the variant rule below |
| `files/{assetRef}/file.{ext}` | U4 processor | U8 (R-07) | Validated attachment, published unchanged (FR7.2). `ext` per the table below |
| `results/{assetRef}.json` | U4 processor | U4 module | C6 result record |

`assetRef` matches `^ast_[A-Za-z0-9]{16,32}$` and **is the MediaAsset `assetId`**: one value, called `assetId` in C1 and C7 and `assetRef` in C2, C3, C6 and C8. U4 generates it, and it reveals nothing about the project or its content.

**Variant rule.** This is the only definition. U4 implements it when producing derivatives, U9 when building the manifest, U8 when validating keys and writing paths, and U7 when writing `srcset`.
- **Widths:** given the image's pixel width `W`, the variants are every width in {480, 960, 1600} that is at most `W`. If `W` is below 480, the only variant is `w480`, encoded at width `W` with no upscaling.
- **Formats:** each variant exists in both `webp` and `jpg`.
- **Size:** an image therefore has 2, 4 or 6 derivative keys.

**File types.**

| C6 `detectedType` | C2 `fileType` | C8/C9 `ext` | Public content type |
|---|---|---|---|
| pdf | PDF | pdf | `application/octet-stream` (NFR Design may fix a specific type) |
| skp | SKP | skp | `application/octet-stream` |
| fcstd | FCStd | fcstd | `application/octet-stream` |
| dxf | DXF | dxf | `application/octet-stream` |
| stl | STL | stl | `application/octet-stream` |
| zip | ZIP | zip | `application/octet-stream` |
| vsdx | VSDX | vsdx | `application/octet-stream` |

Image `detectedType`s (jpeg, png, webp, heic) produce derivatives only and never appear as a `fileType`.

## C9 — Public Web (static site → visitors)

Public routes (built by U7, written by U8, served by U2's CDN):

| Path | Status | Content |
|---|---|---|
| `/` | 200 | Home: carousel (only if any featured), categories with counts, gallery; or "New work is being installed." |
| `/work/` | 200 | Catalog of all live exhibits |
| `/work/{slug}` | 200 | Exhibit page |
| `/category/{games\|astronomy\|woodworking\|software}` | 200 or 404 | Category page; 404 "This category isn't on display" when empty |
| any unknown path, a taken-down exhibit | 404 | "This exhibit isn't on display", with a link to all work (object `404.html`) |
| `/media/{assetRef}/{variant}.{format}` | 200 | Image derivative per the C8 variant rule, immutable cache |
| `/files/{assetRef}/{downloadName}` | 200 | Download: content type from the C8 table, `Content-Disposition: attachment; filename="{downloadName}"`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy: sandbox; default-src 'none'` (FR4.4) |
| `/assets/{name}.{hash}.{ext}` | 200 | U7's build-time bundle (C11 `staticAssets`): CSS, fonts, small island scripts only (constraint 5); immutable cache |

**Page paths and stored objects.** U8 writes each C11 `RenderedPage` with content type `text/html; charset=utf-8`, to an object key derived from its path. C3 rule (d) and test C3-P1 use this mapping:

| Page path | Object key |
|---|---|
| `/` | `index.html` |
| `/work/` | `work/index.html` |
| `/work/{slug}` | `work/{slug}/index.html` |
| `/category/{slug}` | `category/{slug}/index.html` |
| `/404.html` | `404.html` |
| `/category-404.html` | `category-404.html` |

The CDN (U2; Infrastructure Design) resolves directory paths to `index.html`. When an object is missing, it answers 404: with `category-404.html` under `/category/`, and with `404.html` everywhere else.

**Download name.** `downloadName = slug(label) + "." + ext`, where:
- `slug` lowercases the label, replaces every run of characters outside `[a-z0-9]` with `-`, trims `-` from both ends, and cuts to 60 characters;
- an empty result becomes `download`;
- `ext` comes from the C8 table.

U7 (link targets) and U8 (object keys and headers) both use this one rule from U1.

Headers on every response (NFR15):
- `Content-Security-Policy` with `default-src 'self'`, `frame-ancestors 'none'`, and no inline scripts. Downloads under `/files/` override it with the stricter `sandbox; default-src 'none'` policy;
- HSTS with a max-age of at least one year;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: strict-origin-when-cross-origin`.

HTML pages use `no-cache` and hashed assets are immutable. The site sets no cookies and makes no third-party requests (FR9.5). The CDN keeps no access logging for the public site (NFR9). Production is indexable, while preview sends `noindex` and is gated (FR10.3). `mike.broadfoot.consulting` answers with a 301 to `michael.broadfoot.consulting` that preserves the path and query (FR10.2).

## C10 — Health (U3 → smoke checks)

`GET /health` → `200 {"status":"ok"}`, exactly as in C1's `Health` schema. It skips the OwnerAccess step of the pipeline but keeps rate limiting and the request id (C1). It reads no domain data. It returns no version, configuration, project or owner information. Post-deploy smoke checks in preview and production use it (team practice, Deployment).

## C11 — Renderer Interface (U7 → U8 on Node, U11 in the browser)

U7 is one runtime-neutral TypeScript library (unit-of-work constraint 2). This is its whole public surface, version 1.0, generated into U1 with the C2 types:

```typescript
// u1-contracts/ts/renderer.ts  (contract version 1.0; input type = C2 PublicSiteSnapshot 1.0)
import type { PublicSiteSnapshot } from "./public-site-snapshot";

export type Variant = "w480" | "w960" | "w1600";
export type ImageFormat = "webp" | "jpg";

/** Pure, synchronous lookup. Publication: C9 public paths. Preview: C4 imageAddresses. */
export type AssetResolver =
  | ((ref: { kind: "image"; assetRef: string; variant: Variant; format: ImageFormat }) => string)
  & ((ref: { kind: "download"; assetRef: string; downloadName: string }) => string);

export interface RenderOptions {
  mode: "public" | "preview";          // "preview" adds the permanent "Preview — not public" marking and noindex
  resolveAsset: AssetResolver;
  previewSlug?: string;                // required when mode === "preview"
}

export interface RenderedPage {
  path: string;                        // public path per C9: "/", "/work/", "/work/{slug}", "/category/{slug}", "/404.html", "/category-404.html"
  status: 200 | 404;
  html: string;                        // complete static HTML; references only static assets and resolver output
}

export interface RenderOutput {
  contractVersion: "1.0";
  pages: RenderedPage[];
  requiredImages: { assetRef: string; variant: Variant; format: ImageFormat }[];  // exactly the C8 variant rule's set
  requiredDownloads: { assetRef: string; downloadName: string }[];
  staticAssets: string[];              // hashed paths ("/assets/{name}.{hash}.{ext}") from U7's build-time bundle that the pages reference
}

export class RenderInputError extends Error {}  // thrown before any output when the snapshot or options are invalid

/** Validates the snapshot against C2 and the U8-checked semantic rules, then renders. */
export function render(snapshot: PublicSiteSnapshot, options: RenderOptions): RenderOutput;
```

**Rules:**
- **Pure and deterministic.** No Node or DOM API, network, storage, clock, random number or environment variable is read while rendering. The same input and resolver always give byte-identical output.
- **Static assets.** The CSS, fonts and island scripts (carousel, lightbox) are produced when U7 is built, with content-hashed names. They are shipped inside U7's package. U8 uploads the files in `staticAssets` from that package; U11 serves the same bundle from its own origin for preview. No page is hydrated as a whole (constraint 5).
- **No inline scripts or styles, and no third-party origins** (FR9.5, NFR15). All text is escaped (FR4.5).
- **Consistency.** `requiredImages` and `requiredDownloads` must equal what C3 rule (d) computes. U8 checks this and returns `invalid` on any mismatch.
- **Errors.** An invalid snapshot or options value throws `RenderInputError`. U8 maps it to `invalid`, and U11 shows the error instead of a preview.
- **Contract tests:**
  - **parity:** the same fixtures in Node and a headless browser give identical `RenderOutput`;
  - **purity:** a test runs the renderer with network, timers and storage stubbed to throw;
  - the preview marking is present only in `preview` mode;
  - the PB-02 scan of `public` output.

## Errors, Timeouts and Retries

**Studio API status codes (C1).** Every error body is `Error` with a code from the closed `ErrorCode` list:

| Status | Codes | Meaning |
|---|---|---|
| 401 | `UNAUTHENTICATED` | No valid owner token (pipeline) |
| 403 | `NOT_OWNER`, `AI_SPEND_NOT_APPROVED`, `PROVIDER_NOT_APPROVED` | Not the owner (pipeline); AI gates (FR5.8, FR5.9) |
| 404 | `NOT_FOUND` | Unknown project, asset or operation |
| 409 | `STALE_REVISION`, `SLUG_TAKEN`, `LINEUP_CHANGED`, `TICKET_USED`, `TICKET_MISMATCH`, `BASIS_CHANGED`, `SUPERSEDED` | The owner reviews again: a draft saved elsewhere, a slug in use, a line-up changed, a ticket already used by another confirmation, a digest mismatch, a public-state basis that changed (ADR-012), or a retry superseded (ADR-004) |
| 410 | `TICKET_EXPIRED` | Prepare again |
| 422 | `VALIDATION_FAILED`, `PREVIEW_BLOCKED`, `NO_LINKED_REPOSITORY` | Invalid input; not previewable yet; no repository for a suggestion |
| 428 | `REVISION_REQUIRED` | An edit was sent without `If-Match` |
| 429 | `RATE_LIMITED` | NFR16 |
| 503 | `GITHUB_UNAVAILABLE` | "Can't reach GitHub right now" (FR2.4) |
| 504 | `SUGGESTION_UNAVAILABLE` | "No suggestion this time" (FR5.7) |
| 500 | `INTERNAL` | Logged with the request id; no secrets or personal data (NFR11) |

`POST /projects` answers 303 to an existing project when the repository is already linked (FR2.3).

**Timeouts and who retries:**

| Call | Timeout | Retry |
|---|---|---|
| U11 → C1 | Browser default | U11 may resend a confirmation with the same `confirmationId`, which is idempotent (ADR-012). It never retries any other write automatically |
| U3 → GitHub (C7 `RepositoryCatalogPort`) | Set in NFR Design | No automatic retry; the owner retries (FR2.4). Visibility errors fail closed |
| U5 → AI provider | 60 s overall (FR5.7) | No automatic retry; the owner retries |
| U9 → U6 (C5) | 20 s invoke (U6 itself 15 s) | No retry; an error or timeout is "Not reachable" |
| U9 → U8 (C3) | Per-attempt budget (NFR Design) | Only U9 retries, as new attempts with new tokens (ADR-004). U8 never retries |
| Storage event → U4 processor (C6) | Function limit (NFR Design) | Bounded event retries. A final failure writes a `rejected` record |

## Model Additions and Mappings

The contracts add or rename these items against the approved entities in `components.md`. Functional Design adds them to the entity definitions.

| Item | Where | Owner | Note |
|---|---|---|---|
| `slug` | New attribute of Project | Projects (U3) | Proposed from the title; editable until first publish; unique (`SLUG_TAKEN`); frozen into PublishedVersion |
| Site settings: `ownerName`, `githubProfileUrl`, `contactEmail` | New configuration, not an entity | Publication (U9) | Reviewed configuration changed by pull request in v1 (Open Questions). `contactEmail` stays `null` until Michael supplies it |
| `publishedAt` | Snapshot name for PublishedVersion `confirmedAt` | Publication (U9) | Rename in projection only |
| Image `width`, `height` | Snapshot fields from MediaAsset `pixelWidth`, `pixelHeight` | MediaLibrary (U4) → Publication | Width drives the C8 variant rule |
| `assetRef` | Same value as MediaAsset `assetId` | MediaLibrary (U4) | Format `ast_` plus 16 to 32 characters |
| Derivative and file keys | MediaAsset `derivativeKeys` follow C8 (the validated file key included) | MediaLibrary (U4) | Generated from the C8 rules only |
| `generation` | Snapshot field from PublicSiteState `generation` | Publication (U9) | Base plus one for an operation; the committed value for a restore or recovery |

## Contract Ownership Rules

1. **Single source.** U1 holds every spec above. Generated Python and TypeScript types come from it, and no unit hand-copies a schema.
2. **Semantic versions per contract.** A major version breaks consumers; a minor version adds.
3. **Strict contracts: C2 (snapshot), C3 (publish request and result), C4 (preview payload).** These use `additionalProperties: false`, and consumers refuse unknown versions or fields.
   - Any new public field is a change to the publication boundary. It needs a schema version change, an update to the PB-02 allow-list test, and the independent security review (team practice).
   - **Versions cascade.** C3 and C4 pin the snapshot by its `$id`, so a new snapshot version also produces new versions of C3 and C4, and of C11's input type.
   - **Deployment order:** U8 and U11 accept the new versions first, then U9 starts emitting them.
4. **Lenient contracts: C1 responses (except the embedded C4 payload, which stays strict), C5 results and C6 records.** Additive fields are safe, and consumers ignore unknown response fields. Request bodies stay strict.
5. **Breaking changes** are agreed in a pull request that updates U1, both sides' contract tests and this summary. A breaking change on C1 or C3 needs the owner's review, because those contracts carry authorization or publication.
6. **Contract tests run in CI for both sides** of every contract:
   - C1: registry-equals-document, every route rejects non-owner calls, and spy handlers are never invoked (R-08); every request schema is closed;
   - C2: allow-list conformance, structural rules, and semantic rules S1 to S10, with fixtures;
   - C3: K1 to K18, F1, P1 and OK (R-07);
   - C4 and C11: parity fixtures, the preview marking, `PREVIEW_BLOCKED`;
   - U1 itself: every fenced spec parses, has `$schema` (for JSON Schemas), and contains no null-valued key;
   - C5: the NFR17 scenarios;
   - C6: rejection cases.

## Open Questions

| Contract | Question | Blocks |
|---|---|---|
| C1 | Full `Project`, `ProjectPatch` and inventory shapes | U3, U9, U11 Functional Design (not this stage) |
| C2 | Where the site settings (owner name, GitHub profile URL, contact email) are edited. Proposed for v1: reviewed configuration in U9, changed through a pull request; the email stays `null` until Michael supplies it | U9, U7 Functional Design |
| C3 | Per-attempt time budget, and how the CDN invalidation completion is confirmed within 5 minutes | U8, U9 NFR Design |
| C5 | Exact rate limits (NFR16) | U3, U6 NFR Design |
| C6 | Pixel limit confirmed, and the variant widths checked against NFR5 | U4 NFR Design |
| C9 | Public JavaScript budget | U7 NFR Design |
| C1, C9 | Real origins and domain for the Studio API and Studio web (no public DNS change without approval) | U2 Infrastructure Design |

None of these blocks Contract Design's approval. Each is owned by the stage named.

## Assumptions & Open Questions

- The `.invalid` URLs in `$id` and `servers` are placeholders. U1 assigns its real identifiers.
- The open contract points are listed in the Open Questions table above. No owner decision is needed in this stage.
