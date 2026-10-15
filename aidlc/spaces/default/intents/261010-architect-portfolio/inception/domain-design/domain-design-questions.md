# Domain Design — Questions

Each question below has an answer derived from approved records: the charter, `requirements.md` (with Amendment A1 to A1.2), the affirmed team practices and the decision log. Michael's standing instruction is to "handle routine decisions autonomously using the approved charter, recorded decisions, and sensible defaults" and to batch only genuinely unresolved questions (P-03, P-05). Every answer cites its evidence.

The component decomposition is an architectural decision, so it is presented as an option block in `components.md` and is Michael's to confirm at the Domain Design gate. No question here is left open for the owner.

## Sources

- requirements — `../requirements-analysis/requirements.md` (FR1 to FR10, NFR1 to NFR17, Constraints, Open Questions).
- team-practices — `../practices-discovery/team-practices.md`, affirmed into `aidlc/spaces/default/memory/team.md` and `project.md`.
- Refined Mockups, approved 2026-10-11 (P-06):
  - `../refined-mockups/mockups.md` (P4, the approved-publication snapshot);
  - `../refined-mockups/interaction-spec.md`;
  - `../refined-mockups/prototype/`.
- Decision log D-01 to D-28 and P-01 to P-06 — `../../ideation/approval-handoff/decision-log.md`.
- Charter §6: "a modular monolith with clean contracts; public and administrative security boundaries kept separate".

User Stories is skipped in the approved plan (P-01), so no stories artifact is consumed.

## Questions

### Q1. What counts as a distinct building block?

A. One component per domain concern: owner access, projects, media, repositories, AI suggestions, link checks, publication, public-site rendering, export, backup, and the Studio API and web client.
B. Three coarse components: the Studio back end, the public site, and the Studio web client.
C. One component per screen or API endpoint.
X. Other (please specify)

[Answer]: A — The charter asks for a modular monolith with clean contracts (charter §6), and several concerns carry their own security invariants that must be independently testable:
- owner-only access (FR1, NFR1);
- untrusted file handling (FR4.2, FR4.4);
- SSRF-safe link checks (NFR17);
- the publication boundary (NFR2).

The trade-off against B is shown in `components.md` (Component-boundary options) for Michael to confirm at the gate.

### Q2. Which component owns what the public site may contain?

A. Publication owns an immutable **published version** of each exhibit. It holds only the allow-listed public fields (FR4.10) and is frozen at the owner's confirmation. Rendering and export read only published versions.
B. The exporter reads the live project record and filters it while writing pages.
X. Other (please specify)

[Answer]: A — This matches four approved sources:
- FR7.4: re-exported pages are built only from the last published state;
- FR4.10: the export allow-list;
- NFR2: the publication boundary;
- the approved-publication snapshot model in Refined Mockups P4, which the owner required at the 2026-10-11 Request Changes and approved on 2026-10-11.

Under option B, unapproved data reaches the export code path, which is the failure the owner rejected in the prototype.

### Q3. Who owns a project's status (Draft, Published, Changes since last publish, Taken down)?

A. Nobody stores it. It is derived from the project's draft revision and its publication record (state and published revision), so each fact has one writer.
B. A stored status field that both the editor and the publication workflow update.
X. Other (please specify)

[Answer]: A — Deriving the status makes every transition in FR3.2's table hold by construction:
- an edit that lands while a publication operation runs leaves the status at "Changes since last publish" (FR7.8);
- edits to a taken-down exhibit stay private.

Option B needs two components writing one field and a cross-component transaction.

### Q4. Who owns link-check results, given NFR17's isolation rule?

A. The link checker is stateless. It takes a URL and returns a result, and has no database or secret access. Publication stores the result with the confirmation it belongs to.
B. The link checker stores its own results.
X. Other (please specify)

[Answer]: A — NFR17 requires the check to run "under an execution identity with no other permissions" where a bypass reaches no database or secret. Storing results itself would give the checker database access.

### Q5. How is responsibility for images and files divided?

A. The media library owns the bytes. It covers upload authorization, content validation, HEIC conversion, metadata extraction, private originals and metadata-free public derivatives. Projects owns the exhibit's use of them: which images, order, lead image, alt text, and which attachments.
B. Projects owns images and files completely, including validation.
X. Other (please specify)

[Answer]: A — Upload processing is a security-sensitive path with its own limits (FR4.2, FR4.4, FR4.8). Alt text and lead image are exhibit content, versioned with the draft and checked at Publish (FR7.3, D-19).

### Q6. How is the AI integration bounded, and is the provider chosen here?

A. A description-assistant component behind a provider-independent port, holding the spend gate, monthly limit, provider approval for private content, and suggestion provenance. The provider and the open framework are chosen in NFR Design.
B. Choose the provider and framework now.
X. Other (please specify)

[Answer]: A — FR5.4 and FR5.8 require a provider-independent interface and an owner spending approval based on the provider's real cost per call. The requirements' Open Questions place the provider choice in "Domain Design and NFR Design". Domain Design fixes the boundary; NFR Design picks the provider once costs are known and Michael approves the spending.

### Q7. How is the user interface structured?

A. Two user-facing parts:
- a Studio web client (owner only, behind sign-in);
- a public-site renderer that turns a site model into static pages, used both for export and for owner-only preview.

The renderer has no access to Studio data.
B. One web application serving both the public site and the Studio.
X. Other (please specify)

[Answer]: A — Charter §6 keeps the public and administrative security boundaries separate. The public site is a static export that never calls the API or the database (Q3, FR7.4, NFR7). Preview must look exactly like the public site (FR6.1), which one shared renderer guarantees.

### Q8. Where do categories and featured order live?

A. Projects owns:
- the four fixed categories (as reference data);
- the project-to-category relationship with its primary flag;
- the draft featured line-up (at most five, drafts included).

Publication owns the published featured order, changed only by "Update featured order".
B. Categories and featured order are attributes of the public site only.
X. Other (please specify)

[Answer]: A — FR9.7 separates featured status, which is published with each exhibit, from carousel order, which is published by its own confirmation. FR9.8 models classification as a relationship, so more classifications need no migration later (D-27).

### Q9. How is the nightly content export (NFR10) bounded?

A. A content-backup component that reads each owning component's data through its export function, and writes to versioned private storage.
B. A database-level dump job outside the component model.
X. Other (please specify)

[Answer]: A — Entity ownership stays intact, and the export format does not depend on the storage layout. The physical mechanism (scheduling, tooling on the free database tier) is chosen in NFR Design and Infrastructure Design. Option B is recorded as the alternative in ADR-009.

## Assumptions & Open Questions

- **No new owner questions.** Each answer above follows from approved records. The decomposition itself (Q1) is confirmed at the gate.
- **Resolved later, as the requirements already schedule:**
  - the AI provider and framework (NFR Design);
  - the GitHub credential mechanism, fine-grained token or GitHub App (NFR Design);
  - secure edit recovery for FR1.4 (NFR Design);
  - rate values (NFR16) and the image pixel limit (FR4.2);
  - link-check isolation mechanics (NFR17);
  - deployment topology (Units Generation).
