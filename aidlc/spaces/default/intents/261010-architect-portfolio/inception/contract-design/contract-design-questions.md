# Contract Design — Questions

**Inputs:**
- unit-of-work — `../units-generation/unit-of-work.md`;
- unit-of-work-dependency — `../units-generation/unit-of-work-dependency.md`;
- components — `../domain-design/components.md`;
- requirements — `../requirements-analysis/requirements.md`;
- ADR-001 to ADR-012;
- Michael's Units Generation gate conditions (P-07: R-07 and R-08 are required corrections).

Each answer comes from those approved records, under Michael's standing instruction to "handle routine decisions autonomously using the approved charter, recorded decisions, and sensible defaults". No question is left open for the owner.

## Questions

### Q1. Which units expose an API consumed outside the system?

A. Two:
- the **public web**: static pages, assets and downloads served by the CDN to visitors;
- the **health endpoint**, used by smoke checks.

The Studio API is consumed only by the owner's Studio web client (U11), and is treated as an inter-unit contract with an owner-only security boundary.
B. The Studio API is a public API for third parties.
X. Other (please specify)

[Answer]: A — Requirements FR9 and NFR7 define the public site as static files with no visitor-facing API. Charter §4 makes the Studio owner-only, and FR1.2 requires every Studio operation to be the owner's.

### Q2. Integration mechanism per boundary

A.
- **Studio API:** HTTPS with JSON (OpenAPI).
- **U9 → U8 and U9 → U6:** synchronous function invocation with a JSON request and response, validated by JSON Schema.
- **U4 upload processor:** a storage upload event in, a result record object out.
- **Inside the back-end package:** Python module interfaces.
- **Public web:** static HTTP.
B. Events everywhere.
X. Other (please specify)

[Answer]: A — This follows `unit-of-work-dependency.md` (Integration Points) and ADR-004: U9 drives each attempt and needs U8's outcome before it commits. The isolation of U4 and U6 rules out shared database access (ADR-005, ADR-006).

### Q3. Contract ownership

A. U1 (contracts) holds every spec. The owner of a contract's *meaning* is the providing unit, except for these:
- the public site snapshot, owned by U9 as the publication authority;
- the snapshot schema, enforced by U1 for U7, U8 and U11.
B. Each consumer owns its own copy.
X. Other (please specify)

[Answer]: A — This is set by `unit-of-work.md` (U1 Owns; constraints 3, 4 and 6).

### Q4. Versioning and breaking changes

A. Semantic versions per contract. For the Studio API, additive changes are safe and clients ignore unknown fields. The **public site snapshot** and the **publish request** are strict: no unknown properties, and U8 refuses any version it does not support. Adding a public field therefore needs a schema version change, and U8 and U11 are deployed first.
B. The same lenient rule everywhere.
X. Other (please specify)

[Answer]: A — The snapshot is the publication boundary. It enforces the FR4.10 allow-list structurally (owner clarification: "versioned and schema-validated"), so silently accepted unknown fields would defeat it.

### Q5. Errors, timeouts and retries

A. Each boundary states its error model, and the caller decides on retries:
- **U9** decides every publication retry, and treats any non-success from U8 as a failed attempt followed by a restore (ADR-004).
- **U6 timeouts** become "Not reachable".
- **Studio API errors:**
  - 401/403 for authentication;
  - 409 for stale revisions, tickets or basis;
  - 422 for validation;
  - 429 for rate limits;
  - 503 for upstream unavailability.
B. Retries inside every callee.
X. Other (please specify)

[Answer]: A — This follows ADR-004 (U9 is authoritative), FR10.5, NFR16, FR3.4 and ADR-012.

### Q6. How are R-07 and R-08 carried into the contracts?

A.
- **R-07:**
  - the IAM read scope for U8 is limited to two private prefixes: image derivatives and validated files;
  - U8 checks every manifest key at the application boundary, against the key layout and against the approved snapshot's asset references;
  - contract tests reject unauthorized keys.
- **R-08:** the Studio API contract records that U11 reaches U4, U5 and U9 only through U3's authenticated API host and route registration.
X. Other (please specify)

[Answer]: A — These are Michael's conditions on the Units Generation approval (P-07).

## Assumptions & Open Questions

None for the owner. Contract points that later stages settle are listed under "Open Questions" in `contract-summary.md`.
