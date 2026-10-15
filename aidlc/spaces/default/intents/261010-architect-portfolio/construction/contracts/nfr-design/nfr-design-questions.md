# NFR Design Questions — U1 contracts

**Inputs:**
- U1 NFR requirements: `../nfr-requirements/` (NFR1 to NFR17, rows NFR1.1 to NFR17.1);
- functional design: `../functional-design/` (BR1.1 to BR9.6, AC1.1 to AC1.41);
- contract-summary (C1 to C11, R-07, R-08, R-18);
- team-practices (Testing Posture, Code Style, Deployment);
- `bolt-plan.md`, Bolts B01 and B02;
- `nfr-design-questions.md`.

U1 is a specification unit with no runtime and no deployment. Its NFR design describes how the generation pipeline, the shared validator wrapper, the contract-test harness and the checks that gate them meet the NFR rows, and what U1 hands to U3, U8, U9 and U2 as design inputs.

Every answer is derived from the approved records and the U1 NFR requirements, under Michael's instruction to handle routine decisions from the approved records and to escalate only important decisions or mandatory approval gates (P-05, P-08). None of these questions is an owner decision.

## Questions

### Q1. Which NFR design documents does U1 produce?

A. `security-design.md` and `traceability.json`. The performance, scalability, reliability and observability designs are not produced, and neither is `logical-components.md`.
B. All seven documents, as for U0.
X. Other (please specify)

[Answer]: A. The stage file limits the performance, scalability, reliability and observability designs to units of kind `service` (and `ui` for performance), and `logical-components.md` to `service`, `ui` and `library`. U1 is `spec`. The performance figures U1 owns (NFR6.1, NFR6.2) and the `DOWNLOAD_NAME_BUDGET` are designed in `security-design.md`, as U0 and U1 kept their non-security rows in the security file.

### Q2. How does generation keep one source of truth?

A. The spec files and the contract register are the only sources. A fixed pipeline lints them, materializes register values into the schemas, derives the tolerant view, generates Python and TypeScript output, formats it with the pinned formatters, and writes it to a generated folder. A drift check regenerates into a temporary folder and compares byte for byte, and generation runs twice to prove determinism.
X. Other (please specify)

[Answer]: A. BR1.1, BR1.11, BR9.1, BR9.2 and Contract Ownership Rule 1 (U1 holds every spec and no unit hand-copies a schema); NFR13.4; bolt-plan B01 DoD.

### Q3. Which validators are selected, and what gate must B01 pass?

A. Python: a compiled (Rust-backed) validator is the first choice, with pure-Python `jsonschema` accepted only if it passes the same gate. TypeScript: Ajv's 2020 build generating standalone code, used by both Node and the browser, with an interpreting validator as the fallback. The gate is a candidate-qualification checklist plus the B01 benchmark: the Python validator validates the maximum snapshot in at most 250 ms (median of 5). In Python the JSON Schema validator is the only authority for verdicts; the generated models are typed views built after validation.
X. Other (please specify)

[Answer]: A. NFR6.1 and its remedy; NFR13.10 to NFR13.13; NFR15.1 (either pre-generated or interpreting validators conform); `tech-stack-decisions.md` selection criteria; BR9.3.

### Q4. What value does `DOWNLOAD_NAME_BUDGET` take?

A. 250 milliseconds for a 200,000-character label, median of 5, in each language. It equals the NFR6.1 validation allocation: no single helper may cost more than a whole maximum-size validation. The scaling test of NFR13.8 stays as the main discriminator.
X. Other (please specify)

[Answer]: A. NFR13.8 left the value to NFR Design; the derivation is in `security-design.md`. Labels in the approved C2 are at most 120 characters, so the 200,000-character case is a robustness ceiling, not an expected input.

### Q5. What must the U8 implementation meet for fencing, and what happens to the residual window?

A. U8 must meet a fence-store contract (an atomic record-or-refuse on one fence item, and writes and deletions conditional on the fence), proved by a conformance suite that U1 supplies and that runs against any store implementation. The residual window between the fence check and the public write is stated, and the mitigation options are handed to Infrastructure Design without choosing one.
X. Other (please specify)

[Answer]: A. ADR-004; BR3.1, BR3.7, BR3.8; NFR2.4; the NFR Requirements rule that the mechanism is left to NFR Design and Infrastructure Design (BR3.8).

### Q6. How is the contract-test harness built, and how is it kept out of deployables?

A. A test-only reference host registers a spy route for every operation in the OpenAPI document and runs the owner-access pipeline contract against tokens signed by an in-memory harness issuer. Negative controls make the registry, non-owner, agreement and body-shape checks fail on purpose. An evidence ledger in the contract register records none, reference or real per operation. A package-content test and an import-boundary test prove the harness is in no deployable.
X. Other (please specify)

[Answer]: A. BR4.2 to BR4.4, BR4.8, BR4.13; NFR1.1 to NFR1.3; U0 BR1.2 and U0 NFR1.3 (a fake issuer's key lives only in memory, and the S0 guard checks deployable artifacts).

### Q7. How is "no network at generation or test time" enforced?

A. Inside each `contracts-*` check, not in a workflow: a socket guard for Python, a network-denying preload for Node, and request interception for the browser runs. A canary check proves a network call fails. Schema references resolve through a local retriever that refuses remote URLs.
X. Other (please specify)

[Answer]: A. NFR13.5 and NFR4.1; NFR13.2 (U1 adds no workflow).

### Q8. How is the licence report separated from U0's dependencies?

A. U1's Python runtime dependencies are compiled into their own hashed lock in the contracts folder, and its npm packages form a workspace whose tree is read on its own. The report covers the closure that ships or is bundled, lists dev-only tools without gating them, and reads a reviewed exceptions file. It is a `required = false` verify-check.
X. Other (please specify)

[Answer]: A. NFR13.6 and NFR13.7 (a proposed supply-chain control, not a required gate); team practice (hash-locked Python, `npm ci`).

### Q9. How is the 3-minute CI allocation divided?

A. Among eleven `contracts-*` verify-check entries with per-entry allocations that sum to 180 seconds, run through `scripts/verify.py` with dependencies installed and browsers downloaded. Each entry has a timeout of three times its allocation as a hang guard.
X. Other (please specify)

[Answer]: A. NFR13.2 (the 3-minute allotment inside the approved 10-minute CI total, registered as verify-check entries); team practice, Code Style ("CI should finish within 10 minutes").

## Assumptions & Open Questions

None for the owner.
