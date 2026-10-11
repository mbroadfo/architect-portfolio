# Bolt Plan

**Inputs:**
- requirements;
- mockups (the approved Refined Mockups and prototype);
- components and ADR-001 to ADR-012;
- unit-of-work, unit-of-work-dependency and unit-of-work-story-map;
- contract-summary (C1 to C11);
- team-practices.

A **Bolt** is one build pass over part of a unit of work. It ends in working, tested code merged through one pull request, normally within one to two days, as one squash commit named by the Bolt's slug (team practice, Way of Working).

**How Construction runs.** Construction builds one unit at a time:
- **unit-major:** each unit's design stages and code finish before the next unit starts;
- **serial:** one Bolt at a time.

The engine walks the units in the order of the approved dependency graph (`unit-of-work-dependency.md`). This plan follows the same order, so the two do not disagree. The plan declares `skeleton: off`, so no Bolt is a formal walking skeleton (a first slice built and approved through every layer before anything else). Instead, the thinnest piece that runs end to end comes first inside each unit, and the four early proofs from team practice are flagged where they land.

## Definition of Done for Every Bolt

This baseline applies to every Bolt. Each Bolt below adds its own items.

1. **Code and tests.** The code is complete, and the tests for each layer are written and run after it (team practice, test-after). Test names cite the acceptance-criteria or contract IDs they verify.
2. **CI gates pass on the pull request:**
   - format, lint and type check;
   - tests, with 80% line coverage for the front end and the Python API;
   - build;
   - gitleaks;
   - dependency audit;
   - CodeQL.
3. **Contract tests.** The U1 contract tests for every contract the Bolt touches pass on both sides.
4. **Security review where required.** Some Bolts touch authentication, authorization, private material or publication boundaries; they are marked 🔒. Each needs an independent AI security review (from a session that did not write the change), recorded on the pull request with its blocking findings fixed.
5. **Preview verification where required.** Some Bolts change authentication, APIs, publication, take-down or infrastructure; they are marked 🧪. Each needs preview deployment and its smoke and end-to-end checks passing before merge. This depends on `preview` existing (external dependency E2). Until then, such a Bolt can be built and reviewed but not merged.
6. **Approval and merge.** Michael approves the Bolt at its AI-DLC checkpoint. Merging follows team practice, but only once Michael has authorized Construction merges (E10).

## Sequence

| Bolt | Unit | Slug | Scope | 🔒 | 🧪 |
|---|---|---|---|---|---|
| B01 | U1 contracts | `u1-contract-schemas` | C2 to C6 JSON Schemas; generated Python and TypeScript types; a U1 self-check (parse, `$schema`, no null keys) | | |
| B02 | U1 contracts | `u1-api-and-ports` | C1 OpenAPI; C7 ports; C8 key-layout and variant rules; C9 path and download-name rules; C11 types; shared contract-test harness | 🔒 | |
| B03 | U2 platform | `u2-foundation-modules` | Terraform modules and the `preview` and `production` roots, with no resources applied; `fmt`, `validate`, tflint | | |
| B04 | U2 platform | `u2-oidc-ci-plan` | CI job running `terraform plan` through the read-only OIDC role (**early proof: CI passes using OIDC; Terraform plan is clean**) | 🔒 | 🧪 |
| B05 | U2 platform | `u2-cdn-headers-dns-root` | CDN with the NFR15 headers, the FR4.4 download policy, 404 routing, the `noindex` gate for preview, and the separate DNS root (plan only) | 🔒 | 🧪 |
| B06 | U3 studio-api | `u3-api-host-health` | Python package host, route registry and pipeline, `GET /health` (**early proof: API answers a health check**) | | 🧪 |
| B07 | U3 studio-api | `u3-owner-access` | OwnerAccess (issuer plus subject), 401/403 on every route, R-08 registry tests with spy handlers, rate-limit hooks | 🔒 | 🧪 |
| B08 | U3 studio-api | `u3-projects-core` | Projects: title-only create, optimistic revisions, slug, categories, featured line-up, revision and line-up guards (C7) | 🔒 | 🧪 |
| B09 | U3 studio-api | `u3-repository-catalog` | RepositoryCatalog: read-only listing, fail-closed `access_facts`, untrusted documentation reads, Discover and linking | 🔒 | 🧪 |
| B10 | U4 media-library | `u4-upload-authorizations` | Single-use upload authorizations bound to project, size and type; asset status; fail-closed attach check (C1, C7) | 🔒 | 🧪 |
| B11 | U4 media-library | `u4-image-processor` | Isolated processor for images: signature checks, HEIC conversion, pixel limit before decode, metadata-free derivatives under the variant rule (C6, C8) | 🔒 | 🧪 |
| B12 | U4 media-library | `u4-file-processor` | Isolated processor for attachments: ZIP, XML and XXE limits, VSDX and FCStd checks, metadata and entry extraction (FR4.4, FR7.2) | 🔒 | 🧪 |
| B13 | U5 description-assistant | `u5-provider-port-fake` | Provider port, a fake provider, the spend gate and monthly limit, provider approval for private content, provenance (no paid calls) | 🔒 | |
| B14 | U5 description-assistant | `u5-suggestion-flow` | Suggestion endpoint: delimited untrusted input, 60-second timeout, "No suggestion this time", Insert, Edit or Discard provenance | 🔒 | 🧪 |
| B15 | U6 link-checker | `u6-url-and-address-policy` | Canonical parsing, the IANA special-purpose allow-list, IPv4-mapped normalisation, refusal labels (NFR17) | 🔒 | |
| B16 | U6 link-checker | `u6-pinned-fetch` | Pinned connection, TLS by hostname, redirect re-validation, limits, sign-in detection, zero-permission function | 🔒 | 🧪 |
| B17 | U7 site-renderer | `u7-pages-and-tokens` | Runtime-neutral `render()`; home, catalog, category, exhibit and 404 pages; crafted-studio tokens; escaping; fixtures from the approved prototype | | |
| B18 | U7 site-renderer | `u7-islands-and-parity` | Carousel and lightbox scripts; Node and browser parity test; purity test; accessibility checks (axe) | | |
| B19 | U8 site-publisher | `u8-validate-and-fence` | Validation of C3 and C2 and the semantic rules S1 to S7; manifest key enforcement (R-07, tests K1 to K18); fence store | 🔒 | |
| B20 | U8 site-publisher | `u8-write-delete-restore` | Rendering to public storage, ordered writes and deletions, restore, CDN invalidation; test P1 (**early proof: the public page builds and is served**, in preview) | 🔒 | 🧪 |
| B21 | U9 publication | `u9-status-and-tickets` | Derived status; preparation and inventory; blockers; ConfirmationTicket with the frozen candidate (ADR-003, ADR-012) | 🔒 | 🧪 |
| B22 | U9 publication | `u9-atomic-acceptance` | Acceptance transaction with the Projects guards; `confirmationId` idempotency; tests CS-01 to CS-04, CS-14, CS-15 and CS-18 | 🔒 | 🧪 |
| B23 | U9 publication | `u9-sequence-runner` | Site-wide sequence, leases and tokens, run-time basis check, invocation of U8, conditional commit; tests CS-05 to CS-08a, CS-11 and CS-13 | 🔒 | 🧪 |
| B24 | U9 publication | `u9-recovery-takedown` | Abandoned-attempt recovery, restore, take-down with its retries and alert, featured-order semantics; tests CS-09, CS-10, CS-12, CS-16, CS-17, CS-19 and CS-20 | 🔒 | 🧪 |
| B25 | U9 publication | `u9-snapshot-and-preview` | Public snapshot builder (semantic rules S8 to S10), preview payload, activity log; tests PB-01 to PB-12 | 🔒 | 🧪 |
| B26 | U10 content-backup | `u10-nightly-export-restore` | Nightly export through the owners' ports; documented and tested restore (NFR10) | 🔒 | 🧪 |
| B27 | U11 studio-web | `u11-shell-signin-projects` | Studio shell, sign-in with MFA, Projects list and empty state, statuses, take-down alert | | 🧪 |
| B28 | U11 studio-web | `u11-editor-uploads` | Editor with the leave guard and edit recovery, uploads through authorizations, images and alt text, attachments, suggestions | | 🧪 |
| B29 | U11 studio-web | `u11-preview-publish` | Preview through U7 in a sandboxed frame; Publish, Update and take-down confirmations; featured order; activity log | 🔒 | 🧪 |
| B30 | U11 studio-web | `u11-e2e-journeys` | Playwright journeys (team practice): gallery and exhibit; Studio from discover through preview, publish and take-down | | 🧪 |

Thirty Bolts in total, matching the size scale: U1 M (2), U2 L (3), U3 L (4), U4 L (3), U5 M (2), U6 M (2), U7 M (2), U8 M (2), U9 XL (5), U10 S (1), U11 L (4).

## Bolt Details

Each entry gives the Definition of Done items beyond the baseline (**DoD**), what shipping the Bolt will tell us (**Proves**) and the expected demonstration (**Demo**). Every Bolt is owned by aidlc-developer-agent (`team-allocation.md`).

### U1 — contracts

- **B01 `u1-contract-schemas`**
  - **DoD:** every C2 to C6 schema validates against the 2020-12 meta-schema; fixtures pass and are rejected exactly as the C2 and C3 tables state; generated types compile in Python and TypeScript.
  - **Proves:** the allow-list can be enforced structurally, in both languages.
  - **Demo:** an invalid snapshot (an extra field, or a GitHub link) is rejected by both the Python and the TypeScript validators.
- **B02 `u1-api-and-ports`**
  - **DoD:** the OpenAPI 3.1 document validates; every request body is closed; the `ErrorCode` list is complete.
  - **R-18 (mandatory Functional Design correction, P-08):**
    - preview downloads are named as the third direct-to-storage channel;
    - the shared `Error` body is on every applicable error response, and responses that intentionally have no body are documented;
    - a test proves the OpenAPI responses and the registered handlers agree.
  - **Proves:** the back-end units and U11 can build in parallel against fixed interfaces.
  - **Demo:** the contract-test harness runs green against stub implementations.

### U2 — platform

- **B03 `u2-foundation-modules`**
  - **DoD:** `terraform fmt -check`, `validate` and tflint pass; no resource is applied; the modules have no paid resources beyond those team practice lists.
  - **Proves:** both environments come from one set of modules.
  - **Demo:** a clean `validate` and tflint run in CI.
- **B04 `u2-oidc-ci-plan`**
  - **DoD:** CI gets read-only credentials through GitHub OIDC, with no stored AWS keys, and `terraform plan` is clean. Needs E1.
  - **Proves:** the OIDC trust and the state backend work, with no long-lived keys.
  - **Demo:** the CI plan output on a pull request.
- **B05 `u2-cdn-headers-dns-root`**
  - **DoD:**
    - the plan shows the NFR15 headers, the download policy, 404 routing to `404.html` and `category-404.html`, and the preview gate with `noindex`;
    - the DNS root is a separate state;
    - nothing is applied without Michael's approval.
  - **Proves:** the C9 contract is achievable at the CDN.
  - **Demo:** the plan diff, then the preview smoke check after E2.

### U3 — studio-api

- **B06 `u3-api-host-health`**
  - **DoD:** `/health` returns only `{"status":"ok"}`; the route registry is in place; the request id is logged with no secrets.
  - **Proves:** the API package deploys and answers.
  - **Demo:** the smoke check against preview.
- **B07 `u3-owner-access`**
  - **DoD:**
    - FR1.1 to FR1.3 acceptance criteria pass, including the look-alike email and foreign-issuer cases;
    - the R-08 registry and spy-handler tests pass;
    - the security review is recorded.
  - **Proves:** nothing in the Studio is reachable except by the owner.
  - **Demo:** a non-owner token gets 403 on every route.
- **B08 `u3-projects-core`**
  - **DoD:** FR3.1 to FR3.5; a stale save gets 409 `STALE_REVISION`; `SLUG_TAKEN`; the guards make a conditional write without changing the revision (CS-15); integration tests run against a throwaway MongoDB container.
  - **Proves:** the drafts model and the guards behave as ADR-003 and ADR-012 need.
  - **Demo:** two tabs saving, and one is refused.
- **B09 `u3-repository-catalog`**
  - **DoD:** FR2.1 to FR2.5; a GitHub error yields `unconfirmed` (PB-04); the credential is read-only (FR2.2); a fake GitHub is used in CI.
  - **Proves:** visibility fails closed.
  - **Demo:** Discover with a simulated GitHub outage.

### U4 — media-library

- **B10 `u4-upload-authorizations`**
  - **DoD:** FR4.8 criteria; expired, oversized and non-owner requests are refused; an asset from another project is refused (PB-10).
  - **Proves:** uploads cannot be abused or cross projects.
  - **Demo:** an upload to preview storage with a single-use authorization.
- **B11 `u4-image-processor`**
  - **DoD:**
    - FR4.2 criteria, including corrupt HEIC, the pixel-limit refusal before decode, and EXIF/GPS removal;
    - the variant rule;
    - the processor's role is denied the database.
  - **Proves:** untrusted images are contained.
  - **Demo:** a GPS-tagged photo yields clean derivatives.
- **B12 `u4-file-processor`**
  - **DoD:** FR4.4 criteria: renamed HTML, zip bomb, plain ZIP named `.vsdx`, XXE; "Metadata could not be read" on failure.
  - **Proves:** maker files are contained.
  - **Demo:** a zip bomb is rejected within the limits.

### U5 — description-assistant

- **B13 `u5-provider-port-fake`**
  - **DoD:** FR5.4, FR5.8 and FR5.9 with the fake provider; no provider call without spending approval (verified by a spy).
  - **Proves:** the AI gates hold before any money is spent.
  - **Demo:** the request is refused with "AI suggestions need approval".
- **B14 `u5-suggestion-flow`**
  - **DoD:** FR5.1, FR5.2, FR5.6 and FR5.7; a prompt-injection fixture cannot change the instructions; provenance is recorded.
  - **Proves:** suggestions never overwrite text or leak.
  - **Demo:** a suggestion inserted with its provenance shown.
  - **Note:** the real provider stays disabled until E6.

### U6 — link-checker

- **B15 `u6-url-and-address-policy`**
  - **DoD:** the NFR17 address and parsing criteria, including `169.254.169.254`, `::ffff:10.0.0.5` and `fd00:ec2::254`, and decimal and octal literals.
  - **Proves:** the allow-list policy is correct on its own.
  - **Demo:** a table-driven test run.
- **B16 `u6-pinned-fetch`**
  - **DoD:** the rebinding, redirect, TLS, size and time criteria; the function identity has no other permissions and no VPC; the security review is recorded.
  - **Proves:** SSRF is not possible.
  - **Demo:** a redirect to `127.0.0.1` is not followed.

### U7 — site-renderer

- **B17 `u7-pages-and-tokens`**
  - **DoD:** FR9.1 to FR9.6; the approved token contrast holds (FR9.6, NFR8); no inline script; the snapshot fixtures come from the approved prototype's STARS and Baduk data, with Monopoly and Risk absent.
  - **Proves:** the approved design is reproduced from the snapshot alone.
  - **Demo:** a rendered home page and exhibit, compared with the prototype.
- **B18 `u7-islands-and-parity`**
  - **DoD:** FR9.7 carousel behaviour (keyboard, no auto-advance, announcements, reduced motion); the parity and purity tests; no serious or critical axe violations; within the JavaScript budget from NFR Design.
  - **Proves:** preview and the live site cannot drift, and the JavaScript stays small.
  - **Demo:** identical output from Node and the browser.

### U8 — site-publisher

- **B19 `u8-validate-and-fence`**
  - **DoD:** C3 tests K1 to K18 and F1; semantic rules S1 to S7; the fence only ever increases.
  - **Proves:** R-07 holds at the application boundary.
  - **Demo:** an `originals/` key gets `invalid`, and nothing is written.
- **B20 `u8-write-delete-restore`**
  - **DoD:** test P1; ordered writes and deletions; restore; invalidation; the IAM test denies `originals/`, `incoming/` and `results/`.
  - **Proves:** public storage equals the snapshot.
  - **Demo:** a fixture snapshot published to preview, then restored.

### U9 — publication

- **B21 `u9-status-and-tickets`**
  - **DoD:** FR3.2, FR7.2, FR7.3, FR10.6 and FR10.7 preparation; the inventory digest; the frozen candidate.
  - **Proves:** the owner sees exactly what would be published.
  - **Demo:** the Monopoly fixture is blocked by its rights review.
- **B22 `u9-atomic-acceptance`**
  - **DoD:** tests CS-01 to CS-04, CS-14, CS-15 and CS-18, as deterministic interleaving tests.
  - **Proves:** content that was not reviewed can never be accepted.
  - **Demo:** an edit in another tab, then a refused confirmation.
- **B23 `u9-sequence-runner`**
  - **DoD:** tests CS-05 to CS-08a, CS-11 and CS-13.
  - **Proves:** no stale run can overwrite newer public state.
  - **Demo:** a take-down racing a publish ends in the correct home page.
- **B24 `u9-recovery-takedown`**
  - **DoD:** tests CS-09, CS-10, CS-12, CS-16, CS-17, CS-19 and CS-20; FR8.1 to FR8.4.
  - **Proves:** failures and crashes always converge on the committed state.
  - **Demo:** an export crashed partway, then recovered.
- **B25 `u9-snapshot-and-preview`**
  - **DoD:** tests PB-01 to PB-12; semantic rules S8 to S10; the PB-02 export scan finds no private identifiers or withheld values.
  - **Proves:** the publication boundary holds from end to end.
  - **Demo:** the export scan report.

### U10 — content-backup

- **B26 `u10-nightly-export-restore`**
  - **DoD:** NFR10; the restore is tested once against preview; the storage is private, versioned and encrypted.
  - **Proves:** at most 24 hours of edits can be lost.
  - **Demo:** a restore into an empty preview database.

### U11 — studio-web

- **B27 `u11-shell-signin-projects`**
  - **DoD:** FR1.3 and FR1.4 behaviour in the client; FR3.5; status words; the alert.
  - **Proves:** the Studio works against the real API.
  - **Demo:** sign-in to preview with the Auth0 development tenant.
- **B28 `u11-editor-uploads`**
  - **DoD:** FR4.1, FR4.6, FR4.8 and FR5.2 in the user interface; no secrets in the bundle.
  - **Proves:** curation takes little effort (intent).
  - **Demo:** an exhibit edited with images.
- **B29 `u11-preview-publish`**
  - **DoD:** FR6.1 and FR6.2; the C4 and C11 preview with download addresses; the confirmations show the full inventory; `PREVIEW_BLOCKED` is handled.
  - **Proves:** the owner can publish confidently.
  - **Demo:** a publish to preview, end to end.
- **B30 `u11-e2e-journeys`**
  - **DoD:** the team practice's Playwright journeys pass in preview.
  - **Proves:** the whole loop works in a non-production environment.
  - **Demo:** a recorded journey run.

## Assumptions & Open Questions

- **Engine order.** The engine walks units in the approved graph's order; this plan does not change that order.
- **Bolts that need preview.** 🧪 Bolts can be built and reviewed before `preview` exists, but cannot merge until E2 (`external-dependency-map.md`).
- **Merging.** No Bolt merges until Michael authorizes Construction merges (E10).
