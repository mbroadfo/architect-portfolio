# NFR Requirements Questions — U1 contracts

**Inputs:**
- functional-spec, rules and entities: `../functional-design/`;
- requirements (NFR1 to NFR17);
- contract-summary (C1 to C11; errors, timeouts and retries; R-07, R-08, R-18);
- team-practices (Testing Posture, Code Style, Deployment);
- `bolt-plan.md`, Bolts B01 `u1-contract-schemas` and B02 `u1-api-and-ports`;
- the walking slice's `tech-stack-decisions.md` (U0), which U1 stays consistent with.

U1 is a specification unit (kind `spec`). It has no runtime and no deployment. It delivers specs, generated Python and TypeScript types, validators, fixtures and a shared contract-test harness with a test-only reference host. Every requirement row carries its inception NFR ID with a sub-number.

Every answer comes from approved records, under Michael's instruction to handle routine decisions from the approved charter, recorded decisions and sensible defaults, and to escalate only important decisions or mandatory approval gates (P-05, P-08). None of these is such a decision.

## Questions

### Q1. Which NFR documents does U1 produce?

A. `security-requirements.md` (which also carries the quality-gate, supply-chain, browser-compatibility and cost rows) and `tech-stack-decisions.md`, plus `traceability.json`. The performance, scalability, reliability and observability documents are not produced.
B. All six documents, as for U0.
X. Other (please specify)

[Answer]: A. The stage file limits the performance, scalability, reliability and observability documents to units of kind `service` or `ui` (`produces_kinds`), and `unit-of-work.md` classes U1 as `spec`. The performance figures U1 needs (validating a maximum-size snapshot in Python and in the browser) are rows in `security-requirements.md` (NFR6.1, NFR6.2), as U0 kept its non-security rows in the same file.

### Q2. What coverage floor and CI budget apply?

A. At least 80% line coverage for the Python and TypeScript code U1 authors (the harness, the reference host, the validator wrappers, the key, path and download-name functions, the generator glue). Generated files are excluded from the denominator and are checked by the strict type checks and the drift check instead. Every S0 CI gate applies, and the whole pull-request CI finishes within 10 minutes. U1's checks are entries in the verification registry, and their summed time through `scripts/verify.py`, with dependencies installed and browsers downloaded, is allotted 3 minutes.
X. Other (please specify)

[Answer]: A. Team practice, Testing Posture (80% floor, never lowered) and Code Style (the checks before merge; "CI should finish within 10 minutes"). The 3-minute allotment is this stage's share of that approved total.

### Q3. How are the schema, OpenAPI and type-generation tools chosen?

A. By criteria, from a named candidate list, with exact versions pinned in the lockfiles at code-generation time. The criteria are: JSON Schema 2020-12 and OpenAPI 3.1 support; fully offline operation (no network reference resolution); deterministic output; a permissive licence; active maintenance; a clean `pip-audit` and `npm audit`; and, for the browser validators, no runtime code generation. No version is claimed here.
X. Other (please specify)

[Answer]: A. Team practice, Code Style ("Dependencies: pinned through committed lockfiles", Dependabot, audit gates); NFR4 (free tools only); the approved contracts, which fix JSON Schema 2020-12 and OpenAPI 3.1; project rules (NEVER commit copyrighted material the project has no rights to use), which is why only permissive licences are accepted.

### Q4. Must the TypeScript validators run in the browser under the Studio's security policy?

A. Yes. U11 validates the C4 payload and the snapshot in the browser before rendering, and the Studio carries the NFR15 policy with `default-src 'self'` and no `unsafe-eval`. The browser validators therefore use no runtime code generation (pre-generated standalone code and an interpreting validator both conform). The fixtures run in Node 22 and in the Chromium, Firefox and WebKit engines, which cover the four browsers of NFR12.
X. Other (please specify)

[Answer]: A. Contract-summary C4 ("U11 validates it against this schema, and the snapshot against C2, before rendering"); NFR15 (the Studio's baseline policy); NFR12 (latest two versions of Chrome, Edge, Firefox and Safari).

### Q5. How are fixtures and the harness's token issuer kept safe?

A. Fixtures hold placeholder text, generated identifiers and hosts on the reserved `.invalid` domain only. The harness issuer creates its signing key in memory at the start of each test session and never writes, logs or commits it. Harness and reference-host code sit outside every deployable build target, and a package-content test proves it.
X. Other (please specify)

[Answer]: A. NFR3 and project rules (NEVER commit secrets); FR10.7 (withheld values never in this repository); U0 `rules.md` BR1.2 and U0 NFR1.3 (a fake issuer's key exists only in memory, and the S0 guard checks deployable artifacts); U1 `rules.md` BR4.13 (the reference host is never shipped) and BR9.4.

### Q6. What budget applies to validating a maximum-size snapshot?

A. In Python, validating an already-parsed snapshot at the contract limits (200 exhibits, 5 MB) takes at most 250 milliseconds (median of five runs on the CI runner), a quarter of the 1-second budget for Studio operations, because the preview route validates a snapshot inside the request. JSON parsing is counted separately by U3 and U9. The browser validator has its own 1-second ceiling, replaced by U11's figure if tighter. The Python candidate must meet its figure in the B01 benchmark, with a stated remedy and decision owner if not.
X. Other (please specify)

[Answer]: A. NFR6 (Studio API operations answer within 1 second at the 95th percentile) and contract-summary C2 "Size bound" (5 MB, 200 exhibits); C4 (the preview route and U11 validate). The one-quarter allocation and the browser ceiling are this stage's own allocations of an approved total and may be revised in NFR Design from measured data.

### Q7. How is the download-name performance budget set?

A. `DOWNLOAD_NAME_BUDGET` is a named constant whose value NFR Design sets. Until then the test checks scaling: it times inputs of 25,000 and 100,000 characters, takes the median of five runs each, and requires the larger time to be at most eight times the smaller plus 5 milliseconds.
X. Other (please specify)

[Answer]: A. U1 `rules.md` BR7.6 (as corrected at Functional Design review); the approved requirements give no figure for this function.

### Q8. What does U1 hand to the other units as NFR inputs?

A. A fixed list, in `security-requirements.md`: to U3 the pipeline contract, the four token fixtures and the error model; to U8 the C3 test matrix, the storage scope and the fence tests; to U9 the manifest and snapshot fixtures and the size bound; to U2 the storage-prefix data; to U7 the variant rule, download name and renderer fixtures; to U11 the browser validators; to U6 the C5 fixtures; and to the CI Pipeline stage the security-sensitive paths.
X. Other (please specify)

[Answer]: A. U1 Functional Design (`rules.md` BR3.5, BR3.7, BR3.8, BR4.4, BR4.13, BR8.5, BR9.5; `functional-spec.md` W3 to W7); unit-of-work (U1 "Delivers": schemas, generated types and contract tests that both sides run); bolt-plan (B02 marked as security-sensitive).

### Q9. How are dependency licences handled?

A. A recorded licence report, not a new required gate. It covers dependencies that ship or are bundled, against an explicit SPDX allow-list with a reviewed exceptions file; dev-only tools are listed but not gated; U1's dependencies are separated from U0's by their own groups. It is a `required = false` verify-check entry, and making it a required gate is a tracked proposal for Michael through the CI Pipeline stage.
X. Other (please specify)

[Answer]: A. A proposed supply-chain control on top of team practice (Dependabot and audits; the repository is public, charter §7). It is not based on the rule against committing copyrighted material, which concerns committed material, and it is not in the team's "checks before merge" list, which is why it is not a required gate.

### Q10. How do the two validators stay equal on untrusted input?

A. Through requirements NFR13.10 to NFR13.13: a portable regular-expression subset with a lint, an explicit set of asserted formats, bounded patterns with depth and size limits, and a strict JSON parsing policy (no NaN, Infinity, duplicate keys or unsafe integers). The shared fixtures prove identical verdicts.
X. Other (please specify)

[Answer]: A. Contract Ownership Rule 6 and BR9.3 (both language validators give the same verdict); BR1.3 (closed schemas); BR2.5 (the 5 MB bound); NFR6; NFR12.

## Assumptions & Open Questions

None for the owner.
