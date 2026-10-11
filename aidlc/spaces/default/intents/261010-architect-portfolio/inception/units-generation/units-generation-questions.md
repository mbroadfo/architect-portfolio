# Units Generation — Decomposition Plan and Questions

**Inputs:**
- components — `../domain-design/components.md` (12 components, approved 2026-10-11);
- decisions — `../domain-design/decisions.md` (ADR-001 to ADR-012);
- requirements — `../requirements-analysis/requirements.md`;
- the charter §6 constraints;
- the team practices in `aidlc/spaces/default/memory/team.md`.

User Stories is skipped in the approved plan, so units are traced to FR IDs. The plan declares `skeleton: off`, so no first-unit skeleton applies.

Q1 to Q5 are answered from approved records, under Michael's standing instruction to "handle routine decisions autonomously using the approved charter, recorded decisions, and sensible defaults". Q6 is a genuine architectural choice and is put to Michael at Plan Approval.

## Questions

### Q1. Unit boundary strategy

A. By domain component, grouped where components share one runtime and data store, and split where an ADR requires a separate execution identity or a different runtime.
B. One unit per component (12 units).
C. By deployment target only (front end, back end, infrastructure).
X. Other (please specify)

[Answer]: A — ADR-001 makes the components modules of one modular monolith, not deployables. Three things force separate deployables:
- ADR-005 and NFR17 require the link checker to run on a zero-permission identity;
- untrusted upload decoding needs memory and time limits (FR4.2, FR4.4);
- the publication sequence runs outside the request path (ADR-004).

Option B would create units too small to deliver on their own, and option C would hide those security boundaries.

### Q2. Granularity

A. Medium: about ten units, each deliverable and testable on its own, none larger than XL.
B. Coarse: three or four units.
X. Other (please specify)

[Answer]: A — Units map to Bolts, and each Bolt is one pull request merged within one to two days (team practice, Way of Working).

### Q3. Dependencies and parallelism

A. A strict acyclic graph that allows parallel work between independent units, built against agreed contracts.
B. Strictly sequential.
X. Other (please specify)

[Answer]: A — Team practice allows parallel coding agents on isolated branches. A contracts unit lets the front end, the renderer and the back end proceed in parallel. Delivery Planning chooses the order.

### Q4. Integration between units

A. Explicit contracts, owned by a contracts unit:
- the Studio API (OpenAPI);
- the public site model (JSON Schema);
- the publish and preview render request;
- the link-check request and result;
- upload processing results.

Calls inside the back-end package go through module interfaces.
B. Shared database access between units.
X. Other (please specify)

[Answer]: A — Charter §6 asks for clean contracts. ADR-002 makes the public site model the only input to the public site, so its schema must be explicit. Contract Design formalises the shapes.

### Q5. Deployment model

A. Hybrid:
- one Python back-end package deployed as the Studio API function, with separate entry points for the publication runner, the recovery check and the nightly backup;
- standalone isolated functions for the link checker and upload processing;
- the public-site publisher;
- the Studio web client as static assets;
- shared infrastructure as a platform unit.
B. Everything in one function.
C. Every unit independently deployed.
X. Other (please specify)

[Answer]: A — This follows from charter §6 (Python API on AWS Lambda, S3 and CloudFront, Terraform) and from the isolation required by ADR-005 and NFR17. It stays on pay-per-use serverless services, so no new paid service is introduced (NFR4). Infrastructure Design confirms the exact resources and costs.

### Q6. Public-site rendering technology (owner decision at Plan Approval)

The renderer (SiteRenderer, ADR-008) produces the static public pages at publish time, and the owner-only preview.

A. **React and TypeScript renderer, run in a small Node publisher function** (recommended).
   - Public pages are prerendered to static HTML with React and TypeScript. The same component library builds the client assets (carousel, lightbox).
   - The Python back end hands each export or preview to the publisher, which renders and writes public storage.
   - Pros:
     - keeps charter §6 ("React, TypeScript and Vite front end") for every user-facing page;
     - one UI toolchain;
     - preview and export share one renderer.
   - Cons: a second runtime (Node) on the back end, and a cross-language contract for the site model. Contract Design defines that contract anyway.
B. **Python templates in the back end, with TypeScript only for client assets.**
   - Pros: simplest, with one back-end runtime and no cross-language call.
   - Cons: public pages would not use React, a departure from charter §6 that needs Michael's agreement, and there would be two template systems (React in the Studio, Python templates for the public site).
X. Other (please specify)

[Answer]: A — Michael approved the 11-unit plan with the React and TypeScript renderer at Plan Approval (2026-10-11), with these clarifications:
- **Static generation only.** React runs only at publication time, never as request-time server rendering. Public pages remain static CDN assets, with no visitor-facing Node service and no dependency on a public API.
- **U7 (site-renderer)** is a reusable rendering library, shared by authenticated preview and publication.
- **U8 (site-publisher)** consumes only the explicitly approved, allow-listed public snapshot.
- **U9 (publication, Python)** stays authoritative for:
  - publication sequencing;
  - atomic confirmation;
  - fencing;
  - recovery;
  - take-down.

  The Node publisher makes no publication or authorization decision of its own.
- **Minimal public JavaScript.** Carousel and gallery interactivity must not require hydrating the whole site.
- **Versioned contract.** The Python-to-TypeScript contract is versioned and schema-validated.
- **Atomicity.** Unit boundaries must not compromise the cross-component atomicity that ADR-012 requires.

## Assumptions & Open Questions

- **Q6** is decided: option A, with Michael's clarifications above.
- **Service and runtime choices** follow the charter; NFR Design and Infrastructure Design confirm them:
  - API Gateway HTTP API;
  - EventBridge or SQS for sequencing;
  - S3 events for uploads.
