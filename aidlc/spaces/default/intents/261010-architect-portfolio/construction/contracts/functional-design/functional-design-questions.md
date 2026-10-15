# Functional Design Questions — U1 contracts

**Inputs:**
- unit-of-work (U1; constraints 1 to 7; "Call Direction Inside the Back End");
- unit-of-work-story-map (U1 owns no FR directly and supports FR4.10 and every integration contract);
- unit-of-work-dependency;
- requirements;
- components;
- contract-summary (C1 to C11, errors and timeouts, model additions, ownership rules, R-07, R-08, R-18);
- decisions (ADR-002, ADR-004, ADR-006, ADR-008, ADR-011, ADR-012);
- the approved `bolt-plan.md`, revision 6, Bolts B01 `u1-contract-schemas` and B02 `u1-api-and-ports`.

Every answer below comes from those approved records. Michael's standing instruction is to handle routine decisions from the approved charter, recorded decisions and sensible defaults, and to return only for a required approval gate or a genuinely consequential decision (P-05, P-08). No question needs his judgement, so no question is put to him. U1 reopens no decision: it formalises the contracts that Contract Design approved.

## Questions

### Q1. What does U1 own, and how is it split across its two Bolts?

A. Eleven contract artifacts, formalised as the single authoritative definitions: C1 to C11. B01 `u1-contract-schemas` covers the C2 to C6 JSON Schemas, the generated Python and TypeScript types, and a self-check. B02 `u1-api-and-ports` covers the C1 OpenAPI document, the C7 ports, the C8 key-layout and variant rules, the C9 path and download-name rules, the C11 types, and the shared contract-test harness. The C10 health response is part of C1.
B. Only the schemas, leaving the API description to U3.
X. Other (please specify)

[Answer]: A. `unit-of-work.md` U1 "Owns" and "Delivers"; `bolt-plan.md` B01 and B02; contract-summary "Contract Ownership Rules" 1 (U1 holds every spec).

### Q2. How are contract versions expressed, and what happens to a message with a version a consumer does not know?

A. Each contract has its own semantic version. A major version breaks consumers and a minor version adds. Strict contracts (C2, C3, C4) carry `schemaVersion` as a constant, and a consumer refuses the whole message for an unknown version or an unknown field. C3 and C4 pin the snapshot by its `$id`, so a new snapshot version also gives new C3, C4 and C11 input versions. Consumers (U8, U11) accept a new version first, then U9 starts emitting it.
B. One version for all contracts.
X. Other (please specify)

[Answer]: A. Contract-summary "Contract Ownership Rules" 2 and 3; C2, C3 and C4 `schemaVersion` constants; C3-K10 (unsupported `schemaVersion` is `invalid`).

### Q3. Which contracts are strict and which are lenient?

A. Strict: C2 (snapshot), C3 (publish request and result) and C4 (preview payload), plus every C1 request body. Lenient: C1 responses (except the embedded C4 payload, which stays strict), C5 results and C6 records. Additive response fields are safe, and consumers ignore unknown response fields. The published schemas stay closed so that producers and fixtures are checked against exactly the fields of the version.
B. Everything strict.
X. Other (please specify)

[Answer]: A. Contract-summary "Contract Ownership Rules" 3 and 4 and the C1 notes "Strict request bodies" and "Unknown fields".

### Q4. What is the shared error body, and which responses have none?

A. Every error response the API host produces carries the shared `Error` body (`code` from the closed `ErrorCode` list, `message`, `requestId`, optional `blockers`). The one response that intentionally has no body is the `303` from `POST /projects`, which is a redirect and not an error: it carries a `Location` header and no body. The 404, 410, 428 and 504 responses that the first OpenAPI draft left without a body carry `Error`.
B. Leave the body-less responses undocumented.
X. Other (please specify)

[Answer]: A. R-18 point 2 (P-08): "specify the shared Error response body for all applicable API error responses; where a protocol response intentionally has no body, document that exception rather than inventing one"; contract-summary C1 (`POST /projects` 303) and "Errors, Timeouts and Retries".

### Q5. Which channels let the owner's browser reach storage directly?

A. Exactly three, each short-lived, single-purpose and issued only by an owner-authenticated route: the single-use upload authorization (U4 route), the owner-only preview image addresses, and the owner-only preview download addresses (both in the C4 payload from the U9 preview route). U11 reaches no other storage or service.
B. Two channels, as in the first Contract Design text.
X. Other (please specify)

[Answer]: A. R-18 point 1 (P-08): name preview downloads as the third authorized direct-to-storage channel; contract-summary C1 R-08 and C4 (`downloadAddresses`).

### Q6. How is agreement between the OpenAPI document and the handlers proved?

A. Contract tests in the shared harness. They show the registry equals the document, every documented response status can be provoked and has the documented body, no undocumented status or body shape is returned, and each route rejects non-owner callers without invoking its handler. U1 supplies the harness and stub handlers. Each unit's CI runs it as its real handlers land.
B. Manual review of the document.
X. Other (please specify)

[Answer]: A. R-18 point 3 (P-08); contract-summary C1 "R-08 contract tests" (1) to (3) and "Contract Ownership Rules" 6; `bolt-plan.md` B02 ("a test proves the OpenAPI responses and the registered handlers agree"; Demo: "the contract-test harness runs green against stub implementations").

### Q7. How is the authorized storage scope of the publisher enforced (R-07)?

A. In two layers. IAM limits U8's role by prefix (read only `derivatives/` and `files/`; write and delete only the public bucket and its own private state store). U8 then rejects the whole request unless every manifest entry passes checks (a) to (d) of C3, and the K1 to K18 tests plus P1, F1 and OK prove it. U1 holds the prefix scope and the key rules as data that U2's IAM test and U8's validator both use.
B. IAM alone.
X. Other (please specify)

[Answer]: A. Contract-summary C3 "R-07: the authorized storage scope, enforced in two layers" and the C3 contract tests; required correction R-07.

### Q8. How does U0's local work relate to U1's definitions?

A. U1 formalises the single authoritative definitions of C2 (schema), C8 (variant rule), C9 (download name) and C11 (types). U0's local versions (the slice's C2 schema, its variant and download-name helpers, its output scan and its snapshot validator) are thin local stand-ins that the owning units replace by U1's generated definitions in their own Bolts. U0 adds no contract (Amendment D1).
B. Treat U0's files as the contract.
X. Other (please specify)

[Answer]: A. Contract-summary preamble ("Amendment D1 … U0 adds no contract"); `unit-of-work.md` U0 constraints (S1 to S3 reach `main` only through the owning units' Bolts); U0 `entities.md` and `rules.md` (thin forms).

### Q9. How are generated types kept from drifting away from the specs?

A. The Python and TypeScript types come only from the U1 specs. A check fails when regenerating from the specs gives output different from what the repository holds, and when a duplicate definition of a contract (the same `$id`) exists outside U1. Generated types must compile under the strict type checks the team already runs (mypy and `tsc --noEmit`).
B. Hand-maintain both sets of types.
X. Other (please specify)

[Answer]: A. Contract-summary "Contract Ownership Rules" 1 ("Generated Python and TypeScript types come from it, and no unit hand-copies a schema"); `bolt-plan.md` B01 DoD ("generated types compile in Python and TypeScript"); team practice, Code Style (mypy on the API package; `tsc --noEmit` in CI).

### Q10. What test data do the fixtures use?

A. Placeholder text and generated identifiers only. Hosts use the reserved `.invalid` domain or well-known placeholders. No real project content, no withheld value and no secret appears in a fixture or in a spec.
X. Other (please specify)

[Answer]: A. FR10.7 (withheld values never in this repository); NFR3; project rules (NEVER commit secrets); contract-summary preamble note that `.invalid` URLs are placeholders.

## Assumptions & Open Questions

None for the owner.
