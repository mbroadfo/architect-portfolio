# Tech Stack Decisions — U1 contracts

**Inputs:**
- functional-spec, rules and entities: `../functional-design/`;
- requirements (NFR1 to NFR17);
- contract-summary (C1 to C11);
- team-practices (Testing Posture, Code Style, Deployment);
- `bolt-plan.md`, Bolts B01 and B02;
- the walking slice's `tech-stack-decisions.md` (U0), which this file stays consistent with;
- `nfr-requirements-questions.md`.

U1 is a specification unit with no runtime. Its stack is the set of tools that read the specs, generate types, validate messages and run the contract tests. **No version is claimed here.** Exact versions are chosen at code-generation time (B01 and B02), recorded in the lockfiles, and entered in the table under "Dependencies recorded at code generation". Where this file names candidates, it states the criteria; the choice at code generation must meet all of them or it is not made.

## Decisions fixed by approved records

| Area | Choice | Rationale |
|---|---|---|
| Spec formats | JSON Schema 2020-12 for C2 to C6; OpenAPI 3.1 for C1 (with C10); Python `typing.Protocol` for the C7 ports; TypeScript types for C11 | The approved contracts fix these (contract-summary C1 to C11) |
| Spec authoring | Specs are kept as the files in `contracts/` (the placeholder folder from S0), written in YAML or JSON as in the contract summary, and loaded with safe loaders only | Contract Ownership Rule 1 (one source); the S0 layout |
| Python | 3.12, the version pinned in `.python-version` | Same as U0; charter §6; team practice (Ruff, mypy, pytest) |
| Node and TypeScript | Node 22 as pinned in `.nvmrc` and the workspace `engines`; TypeScript in strict mode | Same as U0 |
| Test tools | pytest with pytest-cov; Vitest with its coverage provider; Playwright with its Chromium, Firefox and WebKit engines for the browser run of the fixtures (NFR12.1) | Same as U0 for the tools; the extra engines cover the four browsers of NFR12 (Chrome and Edge are Chromium, Safari is WebKit) |
| Lint, format, types | Ruff and mypy (strict) for Python; ESLint, Prettier and `tsc --noEmit` (strict) for TypeScript | Team practice, Code Style |
| Dependencies and audit | Python locked with hashes and installed with `--require-hashes`; `npm ci` from the committed lockfile; `pip-audit` and `npm audit` fail on high or critical findings; Dependabot; gitleaks; CodeQL | Team practice, Code Style (checks before merge) |
| CI | The S0 aggregate check; U1 adds no workflow | U0 BR5.1; NFR13.2 |
| Cost | $0: open-source tools run locally; no paid service | NFR4 |

## Decisions made by criteria, versions pinned at code generation

| Area | Selection criteria | Candidates (not a version claim) | Notes |
|---|---|---|---|
| Python JSON Schema validator | Full 2020-12 support; offline reference resolution only (remote `$ref` disabled); format assertion switchable to exactly the set in NFR13.11; ECMA-262-compatible pattern behaviour for the portable subset of NFR13.10, or a documented wrapper that gives it; speed: validates the 200-exhibit, 5 MB snapshot in at most 250 ms (NFR6.1), which a pure-Python implementation may not meet, so a compiled or Rust-backed candidate is preferred; permissive licence; maintained; clean audit; deterministic error ordering for fixtures | `jsonschema-rs` (Rust-backed); `jsonschema` with its `referencing` library (pure Python), accepted only if the B01 benchmark meets NFR6.1 | Strict mode uses the published closed schemas; the tolerant mode is generated from the same spec (BR1.6). If no candidate meets every criterion, NFR6.1's remedy applies |
| TypeScript JSON Schema validator | Same criteria as the Python validator (format set, pattern subset, offline), plus: no runtime code generation in code the Studio loads (NFR15.1), meaning either validators pre-generated as standalone code or an interpreting validator; identical verdicts in Node 22 and in the Chromium, Firefox and WebKit engines (NFR12.1); validates the maximum snapshot within the browser ceiling of NFR6.2 | Ajv (2020 build) with standalone code generation; an interpreting validator such as `@cfworker/json-schema`. A runtime-compiling validator is accepted only for Node-side tests, never for code U11 imports | If pre-generated code is chosen, it is made by the same generator step as the types and is covered by the drift check (BR9.2) |
| OpenAPI 3.1 validator | Validates 3.1 documents; works offline; permissive licence | `openapi-spec-validator` (Python); `@apidevtools/swagger-parser` or `@redocly/openapi-core` (TypeScript) | Used by the self-check (BR1.2) and the document lint (BR4.1, BR4.5, BR4.7, BR4.10) |
| Python type generation | Output passes mypy strict; closed objects reject unknown fields in strict mode and ignore them in the generated tolerant view; byte-identical output on a repeated run; no network; a permissive licence | `datamodel-code-generator` producing pydantic v2 models (the slice's `snapshot.py` already uses pydantic models); a small in-repo generator if no candidate meets every criterion | Generated files carry a generated-file marker (BR9.1) |
| TypeScript type generation | Output passes `tsc --noEmit` strict; preserves `additionalProperties: false`; deterministic; offline | `json-schema-to-typescript`; `openapi-typescript` for C1 | Output formatted by the pinned Prettier so the drift check is stable |
| Reference host | In-process, no network and no port; registers a spy route for every operation in the OpenAPI document; can run the pipeline contract and a deliberately broken variant | Starlette (ASGI) with its in-process test client; FastAPI with its test client (the U0 API host choice) if the extra OpenAPI generation helps the registry check | Test-only (NFR1.3). U3 confirms the real framework in its own NFR Design |
| Harness token issuer | RS256 or ES256 signing; key generated in memory per session; short-lived tokens (NFR1.2); permissive licence | PyJWT with the `cryptography` package (the U0 token-verification choice) | Test-only, outside every deployable target |
| Fixture format | Language-neutral JSON files, each with its expected verdict per mode and the rule or test id it violates | JSON files read by both runners | Placeholders only (NFR3.2) |
| Strict JSON parser and depth pre-scan | Neither Python's `json.loads` nor `JSON.parse` rejects duplicate object keys, integers beyond 2^53-1 or very deep nesting, so U1 provides a small in-repo strict parse step used by every caller of the validator wrapper (NFR13.12, NFR13.13). It rejects `NaN`, `Infinity`, duplicate keys, integers outside -(2^53-1) to 2^53-1, a document deeper than 16 levels and a document larger than the caller's `max_bytes`, checking depth and size before building the full structure, and it is iterative so it cannot overflow the stack. It runs offline with no dependency beyond the standard library of each language where possible | An in-repo implementation in Python and in TypeScript, kept equal by the shared parsing-policy fixtures; a vetted strict-parsing library only if it meets every criterion in NFR13.6 and NFR13.7 | A refusal returns the closed-table code `VALIDATION_FAILED` (422) from the Studio API, and no new code is added. At U8 it is the C3 result `invalid`, at U9 the operation fails before U8 is invoked, and at U11 the error is shown instead of a preview. The calling unit counts the parse time in its own operation; it is outside the NFR6.1 figure |
| Schema lint | Rejects patterns outside the portable subset (NFR13.10), formats outside the asserted set (NFR13.11), unbounded patterns and ReDoS shapes (NFR13.12), null-valued keys (BR1.2), and open request bodies (BR1.10) | A small in-repo script over the spec files, run by both runners' CI jobs | Runs offline; its rules are the NFR rows it cites |
| Verify registry | U1's generation, drift, offline, benchmark, lint, harness and licence-report steps are `[[check]]` entries in `scripts/verify-checks.toml` with ids beginning `contracts-`, gated by `applies_when` on the contracts folder, each with a timeout | The existing `scripts/verify.py` registry | NFR13.2. U1 adds no workflow |
| Benchmark and scaling tests | Median of 5 runs; no external service; runs in the CI budget | pytest and Vitest timing helpers written in-repo | NFR6.1, NFR13.8 |
| Licence report | Reads the Python and npm lockfile metadata from U1's own dependency groups (a `contracts` requirements group and the contracts npm workspace) so U0's tools are separated out; classifies shipped and bundled dependencies against the explicit SPDX allow-list of NFR13.7; lists dev-only tools without gating them; reads a reviewed exceptions file | A small in-repo script using the package managers' own metadata commands | NFR13.7. A recorded report and an optional (`required = false`) verify-check entry; making it a required gate is a tracked proposal for Michael through the CI Pipeline stage |

**Selection process.** A direct dependency is added only if it meets its row's criteria and is recorded below with its exact version, licence, last release date and audit result. The choice is routine engineering within these criteria. A dependency that is paid or needs network access at generation or test time is not accepted, and a shipped or bundled dependency whose licence is not on the SPDX allow-list needs an entry in the reviewed exceptions file (NFR13.7). One that would be a new paid or recurring service needs Michael's approval (project rules).

**Dependencies recorded at code generation.**

| Name | Exact version | Licence | Last release | Audit result | Used for |
|---|---|---|---|---|---|
| (filled in by B01 and B02 from the lockfiles) | | | | | |

No new paid service is introduced (NFR4).

## Assumptions & Open Questions

- **Versions are not claimed.** No approved record gives a version for any generator or validator, so none is stated here. The lockfiles are the record of what was chosen, and the table above is completed from them.
- **Consistent with U0.** Python 3.12, Node 22, pytest, Vitest, Playwright, Ruff, mypy, ESLint, Prettier, hash-locked Python requirements and `npm ci` are the S0 baseline, unchanged.
- **Layout.** The contract summary's indicative paths (`u1-contracts/python`, `u1-contracts/ts`) map to folders under the repository's `contracts/` directory; the exact layout is set at code generation.
