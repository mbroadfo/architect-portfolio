# Unit Story Map

**Inputs:**
- the units in `unit-of-work.md`;
- the components and ADRs from `../domain-design/`;
- the requirements in `../requirements-analysis/requirements.md`.

User Stories is skipped in the approved plan, so each row is keyed by an FR ID: the ten FR groups and their 62 sub-requirements. Each row names the implementing unit, by ID and construction directory, and any supporting units.

## Requirement-to-Unit Map

| ID | Requirement | Unit ID | Directory | Supporting units |
|---|---|---|---|---|
| FR1 | Studio access (owner only) | U3 | u3-studio-api | U11, U2 |
| FR2 | Repository discovery | U3 | u3-studio-api | U11 |
| FR3 | Projects | U3 | u3-studio-api | U9, U11 |
| FR4 | Exhibit content | U4 | u4-media-library | U3, U7, U8, U9 |
| FR5 | AI description suggestion | U5 | u5-description-assistant | U3, U11 |
| FR6 | Preview | U7 | u7-site-renderer | U9, U11 |
| FR7 | Publication | U9 | u9-publication | U8, U11 |
| FR8 | Take down | U9 | u9-publication | U8, U11 |
| FR9 | Public site | U7 | u7-site-renderer | U8, U2 |
| FR10 | Launch content and launch | U9 | u9-publication | U2, U6, U3 |
| FR1.1 | Owner matched on issuer and subject; sign-up disabled | U3 | u3-studio-api | U2 |
| FR1.2 | Server-side owner check on every operation | U3 | u3-studio-api | — |
| FR1.3 | MFA (identity-provider configuration and token check) | U3 | u3-studio-api | U2 |
| FR1.4 | Unsaved edits survive re-authentication | U11 | u11-studio-web | — |
| FR2.1 | List and search repositories | U3 | u3-studio-api | U11 |
| FR2.2 | Read-only GitHub credential | U3 | u3-studio-api | U2 |
| FR2.3 | Linked repository opens its project | U3 | u3-studio-api | — |
| FR2.4 | GitHub unreachable message and retry | U3 | u3-studio-api | U11 |
| FR2.5 | Discovery never changes or publishes anything | U3 | u3-studio-api | — |
| FR3.1 | Title-only projects; optional repositories | U3 | u3-studio-api | U11 |
| FR3.2 | Status derived from revision and publication record | U9 | u9-publication | U3 |
| FR3.3 | Saved changes persist | U3 | u3-studio-api | — |
| FR3.4 | Conflicting save refused | U3 | u3-studio-api | U11 |
| FR3.5 | Empty state with both actions | U11 | u11-studio-web | — |
| FR4.1 | Title, summary, six sections | U3 | u3-studio-api | U7 |
| FR4.2 | Image upload, validation, HEIC, metadata-free derivatives | U4 | u4-media-library | U8 |
| FR4.3 | Private repository links never public | U9 | u9-publication | U3 |
| FR4.4 | Attachment types, safe checks, sandboxed downloads | U4 | u4-media-library | U8, U2 |
| FR4.5 | Text escaped everywhere | U7 | u7-site-renderer | U11 |
| FR4.6 | Leave guard | U11 | u11-studio-web | — |
| FR4.7 | No topic tags | U3 | u3-studio-api | — |
| FR4.8 | Single-use upload authorizations; attach check | U4 | u4-media-library | U3 |
| FR4.9 | Attachments private until included; downloads only | U4 | u4-media-library | U9, U8 |
| FR4.10 | Access metadata, badges, fail-closed, allow-list | U9 | u9-publication | U1, U7 |
| FR5.1 | Suggestions only with a linked repository | U5 | u5-description-assistant | U11 |
| FR5.2 | Sources listed; Insert, Edit or Discard; provenance | U5 | u5-description-assistant | U3, U11 |
| FR5.3 | Owner-only suggestion endpoint | U3 | u3-studio-api | U5 |
| FR5.4 | Provider-independent port | U5 | u5-description-assistant | — |
| FR5.5 | Provider credentials in SSM, API role only | U5 | u5-description-assistant | U2 |
| FR5.6 | Repository content treated as untrusted | U5 | u5-description-assistant | — |
| FR5.7 | Failure leaves text unchanged | U5 | u5-description-assistant | U11 |
| FR5.8 | Spend approval and monthly limit | U5 | u5-description-assistant | U11 |
| FR5.9 | Provider approval for private content | U5 | u5-description-assistant | U11 |
| FR6.1 | Preview identical to public pages, marked | U7 | u7-site-renderer | U9, U11 |
| FR6.2 | Preview never reachable by visitors | U11 | u11-studio-web | U3, U9 |
| FR7.1 | Nothing public without explicit confirmation | U9 | u9-publication | — |
| FR7.2 | Confirmation inventory | U9 | u9-publication | U4, U6, U11 |
| FR7.3 | Publish blockers | U9 | u9-publication | U11 |
| FR7.4 | Static export of the exhibit and affected pages | U8 | u8-site-publisher | U9, U7 |
| FR7.5 | Edits private until Update | U9 | u9-publication | — |
| FR7.6 | Idempotent publishing | U9 | u9-publication | U8 |
| FR7.7 | Activity log | U9 | u9-publication | U11 |
| FR7.8 | One site-wide fenced sequence; atomic acceptance | U9 | u9-publication | U8, U3 |
| FR8.1 | Take-down with confirmation; failure alert | U9 | u9-publication | U11 |
| FR8.2 | Removal from storage, cache, carousel and categories | U8 | u8-site-publisher | U9 |
| FR8.3 | Taken-down exhibit keeps Studio content | U9 | u9-publication | U3 |
| FR8.4 | Notice that external copies cannot be withdrawn | U11 | u11-studio-web | — |
| FR9.1 | Home: carousel, categories, gallery | U7 | u7-site-renderer | — |
| FR9.2 | Exhibit page | U7 | u7-site-renderer | — |
| FR9.3 | Not-on-display page with 404 | U7 | u7-site-renderer | U8 |
| FR9.4 | Footer | U7 | u7-site-renderer | — |
| FR9.5 | No tracking; no third-party origins | U7 | u7-site-renderer | U2 |
| FR9.6 | Crafted studio identity tokens | U7 | u7-site-renderer | U11 |
| FR9.7 | Featured carousel and published order | U9 | u9-publication | U3, U7, U11 |
| FR9.8 | Four fixed categories as a relationship | U3 | u3-studio-api | U9, U7 |
| FR10.1 | Candidates published individually after approvals | U9 | u9-publication | U3 |
| FR10.2 | HTTPS and the 301 redirect | U2 | u2-platform | — |
| FR10.3 | Production indexable; preview noindex and gated | U2 | u2-platform | — |
| FR10.4 | Go-live and DNS only after owner approval (separate DNS root) | U2 | u2-platform | — |
| FR10.5 | Link check with three labels | U6 | u6-link-checker | U9 |
| FR10.6 | Rights-review flag blocks Publish | U3 | u3-studio-api | U9 |
| FR10.7 | Live URL withheld; withheld values kept out of the repository (CI check designed in CI Pipeline) | U9 | u9-publication | U3 |

## Cross-Cutting Rows

These requirements span several units. The unit in the table above owns the requirement; the supporting units each carry part of it.

| Concern | Units | How it is shared |
|---|---|---|
| Publication boundary (FR4.10, FR7.4, NFR2) | U9, U1, U8, U7 | U9 builds the allow-listed snapshot; U1's versioned schema enforces it structurally; U8 validates again and writes only what the snapshot names; U7 renders only the snapshot |
| Concurrency and atomicity (FR7.6, FR7.8, ADR-004, ADR-012) | U9, U3, U8 | U9 sequences, leases, fences and commits; U3 provides the revision and line-up guards in the same transaction; U8 enforces the token |
| Preview (FR6) | U9, U11, U7 | U9 builds the candidate; U11 renders it with U7 in a sandboxed frame |
| Security headers (NFR15) | U2, U7 | U2 sets the CDN response headers; U7 emits no inline or third-party scripts |
| Accessibility (NFR8) | U7, U11 | Public pages and the Studio |
| Secrets (NFR3) | U2, U3, U5 | U2 provides the SSM namespace and roles; U3 and U5 read only their own parameters |
| Rate limits (NFR16) | U3, U6 | U3 enforces endpoint rates; U6 checks one URL per exhibit |
| Observability (NFR11) | U3, U9 | Health endpoint, request ids, activity log |
| Durability (NFR10) | U10, U2 | Nightly export and versioned private storage |

## Implementation Order Within Each Unit

The order of work inside each unit only. It implies nothing about the order of units, which Delivery Planning decides.

| Unit | Order |
|---|---|
| U0 (u0-walking-slice) | No FR owned directly: delivery-only walking slice (S0 CI baseline merges; S1 to S3 are a local demonstration, Amendment D1) |
| U1 (u1-contracts) | Contracts consumed by every other unit (no FR owned directly) |
| U2 (u2-platform) | FR10.2, FR10.3, FR10.4 |
| U3 (u3-studio-api) | FR1.1, FR1.2, FR1.3, FR2.1, FR2.2, FR2.3, FR2.4, FR2.5, FR3.1, FR3.3, FR3.4, FR4.1, FR4.7, FR5.3, FR9.8, FR10.6 |
| U4 (u4-media-library) | FR4.2, FR4.4, FR4.8, FR4.9 |
| U5 (u5-description-assistant) | FR5.1, FR5.2, FR5.4, FR5.5, FR5.6, FR5.7, FR5.8, FR5.9 |
| U6 (u6-link-checker) | FR10.5 |
| U7 (u7-site-renderer) | FR4.5, FR6.1, FR9.1, FR9.2, FR9.3, FR9.4, FR9.5, FR9.6 |
| U8 (u8-site-publisher) | FR7.4, FR8.2 |
| U9 (u9-publication) | FR3.2, FR4.3, FR4.10, FR7.1, FR7.2, FR7.3, FR7.5, FR7.6, FR7.7, FR7.8, FR8.1, FR8.3, FR9.7, FR10.1, FR10.7 |
| U10 (u10-content-backup) | NFR10: nightly export, then restore procedure and its test (no FR owned directly) |
| U11 (u11-studio-web) | FR1.4, FR3.5, FR4.6, FR6.2, FR8.4 |

## Coverage Verification

- **FR IDs:** all 72 (10 groups and 62 sub-requirements) are assigned to exactly one implementing unit; there is no GAP.
- **Units:**
  - every unit other than U0 and U1 owns at least one row;
  - U0 (walking-slice) is delivery-only (Amendment D1): it owns no FR and supports CI and the early end-to-end demonstration;
  - U1 (contracts) owns no FR directly but supports FR4.10, and every integration contract;
  - U10 (content-backup) realizes NFR10 and supports the durability of every FR's data, so it carries the NFR10 row below.

| ID | Requirement | Unit ID | Directory | Supporting units |
|---|---|---|---|---|
| NFR10 | Nightly content export and tested restore | U10 | u10-content-backup | U2 |

## Assumptions & Open Questions

- The withheld-value CI check in FR10.7 is designed in the CI Pipeline stage. Its owning unit here is U9, which keeps withheld values out of every export.
