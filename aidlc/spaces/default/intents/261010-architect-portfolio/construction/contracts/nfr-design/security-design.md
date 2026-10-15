# Security Design — U1 contracts

**Inputs:**
- U1 NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- contract-summary (C1 to C11, R-07, R-08, R-18);
- team-practices (Testing Posture, Code Style, Deployment);
- `bolt-plan.md`, Bolts B01 and B02;
- `nfr-design-questions.md`.

U1 is a specification unit with no runtime and no deployment. This design describes how the generation pipeline, the shared validator wrapper, the contract-test harness and their checks meet the NFR rows, and what U1 hands to the units that implement the boundaries. It is a design, not code: snippets are pseudocode of at most 15 lines. Folder names are logical (`spec/`, `register/`, `generated/`, `fixtures/`, `harness/` under the existing `contracts/` folder); exact paths are fixed at code generation. Performance, scalability, reliability and observability designs are not produced for a `spec` unit (Q1); the figures U1 owns are designed here.

## Generation Pipeline (NFR13.4, NFR13.5, NFR13.1; BR1.1, BR1.2, BR1.11, BR9.1, BR9.2)

**Single source of truth.** The files in `spec/` (C1 OpenAPI, C2 to C6 JSON Schemas, the C7 ports module, the C8 and C9 rule tables, the C11 types) and the `register/` files (versions, consumer acceptance, allow-list, constants, address-field register, evidence ledger) are the only sources. Nothing under `generated/` is edited by hand, and no value that the register owns is typed into a spec (BR1.11).

**Pipeline, run by one entry point, in this order:**
1. **Load.** Read the sources with a safe loader and the strict parse step (below). A key with a null value, a duplicate key, or an unknown file type stops the run (BR1.2).
2. **Lint.** Run the schema lint: meta-schema validation, OpenAPI 3.1 validation, null-key rule, closed request bodies (BR1.10), the portable `pattern` subset, the format set, pattern bounds, and the address-field candidate predicate (NFR13.10 to NFR13.12; BR4.9).
3. **Materialize.** Copy the register's constants into the schemas (`maxItems` 200, the 5 MB bound, the prefix list) so a schema never restates them (BR1.11).
4. **Derive.** Produce the tolerant view of each lenient contract from the strict schema by two transforms only: unknown fields allowed, and `schemaVersion` widened from the constant to the same-major pattern (BR1.6, BR1.9).
5. **Generate.** Write the Python models, the TypeScript types, the TypeScript standalone validators (if chosen, see below) and the C1 API types.
6. **Format and mark.** Run the pinned Ruff and Prettier over the output. Every file starts with a generated-file marker. Output is UTF-8 with LF line endings.
7. **Write.** Replace the contents of `generated/` in one step.

**Determinism (NFR13.4).** The generator reads no clock, no environment variable other than a fixed `PYTHONHASHSEED`, and no absolute path; it sorts every map and list it emits, and it normalises path separators to `/`. Tool versions come from the lockfiles, so they cannot change between runs. The generation check runs the pipeline twice into two temporary folders and requires them to be byte-identical (a determinism failure), then compares one of them with the committed `generated/` folder (the drift check, BR9.2). A difference fails the check and prints the first differing file.

**Generated-file exclusion (NFR13.1).** The coverage configuration omits `generated/**` from the denominator of both pytest-cov and the Vitest coverage provider. Generated files are not exempt from checks: mypy strict and `tsc --noEmit` strict run over them (BR9.1), and the drift check pins their content. Hand-authored code (the wrapper, the parser, the harness, the key and path functions, the lints, the ledger tool) carries the 80% floor.

**Where the validators come from (NFR15.1; BR9.3).** One standalone TypeScript validator build is the design: the same generated validator code is imported by Node tests, by U8 and by the U11 bundle, so Node and browser run identical code. It is produced in step 5, committed under `generated/`, and covered by the drift check. If the CSP test (NFR15.1) or the determinism check fails for it, the fallback is an interpreting validator, which needs no generated validator code.

## Shared Validator Wrapper (NFR13.10 to NFR13.13, NFR6.1, NFR6.2, NFR2.5; BR1.3, BR1.6, BR1.9, BR2.5, BR9.3)

One wrapper in each language is the only entry point U3, U8, U9 and U11 use. Its design:

```text
check(doc_bytes, contract, mode, accepted_versions, max_bytes) -> Verdict
  1. size: len(doc_bytes) > max_bytes            -> refuse TOO_LARGE
  2. depth pre-scan (iterative, no allocation of the tree):
       count open brackets outside strings       -> refuse TOO_DEEP when > 16
  3. strict parse (below)                         -> refuse NOT_JSON | DUPLICATE_KEY | BAD_NUMBER
  4. version: read only schemaVersion, compare with accepted_versions
       strict: exact; tolerant: same major and minor >= floor
                                                  -> refuse VERSION
  5. schema: strict or tolerant schema; stop after 20 errors
                                                  -> refuse SCHEMA
  6. semantic rules S1 to S7 (and none of S6a, S8 to S10)  -> refuse SEMANTIC
  7. return ok with the typed view
```

- **Order and cost.** The size and depth steps run before anything is built, so a hostile body costs a scan, not a tree. Validation work is linear in the input size, and error collection stops after 20 errors (NFR13.12).
- **Modes (BR1.6).** Strict mode is the default. Tolerant mode is selected only by the register's consumer-acceptance row for a lenient contract, never by the caller's argument alone, so a strict contract cannot be read tolerantly by mistake (NFR2.5).
- **Refusal reasons.** The wrapper returns a reason code from a fixed internal list and never any document content, so a refusal can be mapped without leaking a snapshot (BR3.2, NFR11.1). Mapping: U3 answers 422 `VALIDATION_FAILED`, with no new error code; U8 returns the C3 result `invalid` with the reason code; U9 fails the operation before invoking U8; U11 shows the error and no preview (BR4.6, BR5.1).
- **Strict JSON parse (NFR13.13).** Neither `json.loads` nor `JSON.parse` rejects duplicate keys, `NaN`, `Infinity` or integers beyond 2^53-1, so U1 supplies a small in-repo parser in each language. Python uses `json` with an object-pairs hook that rejects a repeated key, a constant hook that rejects `NaN` and `Infinity`, and an integer hook that enforces the range -(2^53-1) to 2^53-1, after the depth pre-scan. TypeScript uses an in-repo iterative tokenizer, because a `JSON.parse` reviver cannot see duplicates. Both are kept equal by the parsing-policy fixtures.
- **Portable `pattern` subset (NFR13.10).** The lint parses every pattern with a small grammar that accepts only literals, explicit ranges, groups, alternation, `?`, `+`, `*`, `{m,n}` and the anchors `^` and `$`, and rejects everything else. Both validators match the whole string, and a trailing newline never satisfies `$`: the Python side matches with a full-match call on the pattern with its anchors removed, and the TypeScript side with a sticky anchored expression, so neither relies on the engine's `$` rule. The edge fixtures (trailing newline, Arabic-Indic digits, non-BMP characters) prove the two agree.
- **ReDoS and pattern bounds (NFR13.12).** The same grammar computes the longest string a pattern can match. The lint passes a pattern only if that length is bounded and at most 2048, or the field declares `maxLength` of at most 2048; and it rejects a quantified group whose body can repeat (`(a+)+`) and an alternation under a quantifier whose branches can start with the same character. When a Rust-backed Python validator is chosen, its engine is also linear-time; the lint protects the interpreters regardless.
- **Format assertion policy (NFR13.11).** Library defaults differ, so U1 does not use them. The wrapper registers its own four checkers in each language and enables format assertion for exactly `uri` (absolute, no whitespace or control characters, valid percent-escapes), `date-time` (RFC 3339 with an offset), `email` (one `@`, a non-empty local part, a domain with at least one dot) and `uuid`. The lint rejects any other `format` keyword. The address scan reads the declared `format: uri` in the spec text, so it does not depend on whether a validator asserts it (BR4.9).
- **Typed view (BR9.3).** In Python the JSON Schema validator is the sole authority on verdicts. The generated pydantic models are built only from documents that already passed, so the models can never disagree with the validator. In TypeScript the generated types are compile-time only.
- **Semantic rules.** S1 to S7 are one shared function per language, driven by the same fixtures; S6a, S8, S9 and S10 are absent by design and are U9's (BR2.2, BR2.3).

## Performance Figures and Validator Selection (NFR6.1, NFR6.2, NFR13.8, NFR4.1)

**Validator selection decision (settles the delegation from NFR Requirements).**
- **Python.** First choice: a compiled, Rust-backed validator (`jsonschema-rs`). Second: pure-Python `jsonschema` with `referencing`, only if it passes the same gate. The choice is made in B01 by a **candidate-qualification checklist**, each item pass or fail, plus the speed gate: JSON Schema 2020-12 conformance on the U1 schemas; offline reference resolution with a retriever that refuses remote URLs; format assertion switchable to the set of NFR13.11 with the in-repo checkers; the portable pattern subset giving identical verdicts to the TypeScript side on the edge fixtures; deterministic error ordering; permissive licence on the NFR13.7 allow-list; clean `pip-audit`; last release recent enough to be maintained. The speed gate is the benchmark below.
- **TypeScript.** First choice: Ajv's 2020 build generating standalone code, with formats supplied by the in-repo checkers. Fallback: an interpreting validator (`@cfworker/json-schema`), if the CSP test, the determinism check or the drift check fails for standalone output. A runtime-compiling validator is allowed only in Node-side tests.
- **If no Python candidate passes the speed gate:** the NFR6.1 remedy applies. The lead architect for U1 first looks for a faster candidate that meets the checklist; failing that, records a revised allocation with the measured data in the pull request. A change that would need NFR6 itself to move goes to Michael.

**Benchmark design (NFR6.1, NFR6.2).**
- **Fixture.** A deterministic builder creates the maximum snapshot: 200 exhibits, filled to about 5 MB when serialized (about 25 KB per exhibit, so text sections are shorter than their 8000-character limits), valid in every field. The builder, not a stored file, makes the fixture, so it carries no real content (NFR3.2).
- **Python (NFR6.1).** Parse once outside the timing, warm up once, time five validations of the parsed object, require the median at most 250 ms. Parsing is timed separately and reported, because U3 and U9 count it in their own operation.
- **Browser (NFR6.2).** The same fixture is validated in headless Chromium, median of five at most 1 second. This is a ceiling for pathological validators; U11's NFR replaces it if tighter.
- **Runner noise.** The benchmark runs alone in its check (`contracts-bench`), after a warm-up, and a failure is re-run once before it is reported, so one slow shared-runner sample does not fail a pull request while a consistently slow validator does.

**`DOWNLOAD_NAME_BUDGET` (NFR13.8; BR7.6) — value and derivation.**
- **Value: 250 milliseconds** for one call on a 200,000-character label, median of five runs, in each language.
- **Derivation.** The approved C2 limits a label to 120 characters, so real inputs are tiny and a linear rule costs microseconds. The 200,000-character label is a robustness case 1,700 times larger. The budget equals the NFR6.1 allocation, because no single helper should cost more than a whole maximum-size validation. A quadratic implementation would perform about 4 x 10^10 steps on that input and fail by a wide margin; a single pass of 200,000 steps finishes in a small fraction of the budget.
- **Scaling test stays.** The test of NFR13.8 (25,000 and 100,000 characters, median of five, at most eight times plus 5 ms) remains the main discriminator and is not replaced by the ceiling. The constant lives in the register (BR1.11).
- **Design of the rule.** One pass over the input with two pieces of state: the output so far and a pending-hyphen flag. An ASCII letter is folded to lower case and kept; a digit is kept; any other character sets the pending-hyphen flag (so runs collapse). Before a kept character, a pending hyphen is written only if the output is non-empty and writing it plus the character stays within 60; the pass stops when the output reaches 60. This yields the trimmed, cut and re-trimmed result of BR7.6 without ever creating a leading or trailing hyphen. A property test compares it with a slow three-step reference on random inputs (including U+0130 and U+212A, which become `-`).

## Contract-Test Harness (NFR1.1 to NFR1.3, NFR2.2 to NFR2.4, NFR11.1, NFR13.3; BR4.2 to BR4.4, BR4.8, BR4.13, BR9.5)

**Components, all test-only and all under `harness/`:**
- **Reference host.** A minimal in-process ASGI app (Starlette, or FastAPI if its extra helpers prove useful) with an in-process test client, no port and no network. It reads the OpenAPI document and registers one route per (method, path), each with a spy handler that counts calls and returns a minimal documented response. It runs the pipeline contract: owner check, rate-limit hook, request id and error mapping, handler (BR4.3).
- **Harness issuer.** Creates an ES256 key pair in memory in a session-scoped fixture, signs tokens of at most 300 seconds, and hands the public key to the reference pipeline directly (no key fetch, no network). The key is never written, logged or printed (NFR1.2).
- **Token fixtures.** The issuer builds exactly four non-owner tokens: none, expired, the owner's email on another subject, and another issuer. The verifier expects 401, 401, 403 and 401, the shared Error body, and a spy count of 0 on every route except `/health` (NFR1.1; BR4.4).
- **Negative controls.** Four deliberately broken variants of the reference host, each of which must make its check fail, or the check itself is judged broken: a pipeline that skips the owner check; an extra undocumented route; a handler returning an undocumented status or (status, code) pair; a handler returning a wrong body shape for a documented status (BR4.13).
- **Error-message scan.** The agreement check scans every observed error message for secret shapes (bearer prefixes, JWT-like strings, PEM headers, email addresses) and requires 0 matches (NFR11.1).
- **Fence-store fake.** An in-memory store with atomic conditional operations and an injectable pause, used for the C3-F cases (below).

**Evidence ledger (NFR2.2, BR4.8).** One row per C1 operation in the register: level (`none`, `reference`, `real`), the Bolt that set it, and the id of the harness run. A small tool writes the rows from the harness output; people do not edit them. The `contracts-ledger` check recomputes the claim: a row marked `real` requires the unit's real host to be present in the checkout and its agreement run to pass for that operation in the current CI run; a `real` row with no real host present, or with a failing run, fails. At B02 every row is `reference`. If any of a unit's rows is not `real` at that unit's last route-owning Bolt, that unit's CI fails, and Build and Test reads the ledger (BR4.13).

**Package-content and import-boundary tests (NFR1.3).**
- After each build, list the files of every deployable output (the API package, the function packages, the site and Studio bundles) and fail if any path under `harness/`, any module named for the reference host or issuer, or the marker `AIDLC_LOCAL_ONLY_FAKE_IDP` appears. The harness files carry that marker, so the existing U0 guard also catches a leak into a non-local artifact.
- A static import check fails if any production module imports from `harness/`.
- A deployable's build configuration lists its sources explicitly, so `harness/` is never matched by a glob.

**Fixtures hygiene (NFR3.1, NFR3.2; BR9.4).**
- Fixtures are produced by builders and stored as JSON files, each with a header: id, contract, `verdictStrict`, `verdictTolerant`, and the rule or test id it violates.
- The register holds the placeholder-owner list (initially `example-owner`). A scan parses every string in every fixture, extracts URL-like values, and requires each host to be on the `.invalid` domain or `github.com` in the C2 profile or repository form with an owner from that list; contact emails must end in `@example.invalid`. Any other host fails (0 allowed).
- No binary file is stored. The fence and manifest cases use in-memory keys without object bytes.
- gitleaks runs over `contracts/` as part of the aggregate check; a test also greps the working tree and the captured test output after a run for PEM markers to prove the harness key never reached disk (NFR1.2).

## Offline and Network-Blocking Design (NFR13.5, NFR4.1)

The block is part of the checks, not of a workflow:
- **Python.** A shared pytest plugin, loaded by every `contracts-*` pytest run, replaces socket connect and name lookup with a function that raises, except for loopback addresses used by the in-process test client (which needs no real socket).
- **Node.** A preload module (`--import`) replaces the network entry points (`net`, `dns`, `http`, `https` and `fetch`) with ones that throw; Vitest loads it as a setup file.
- **Browsers.** The Playwright runs serve a local static page and abort every request whose target is not that local origin.
- **References.** Both validators get a retriever that resolves only files inside `spec/` and raises on any URL.
- **Canary.** The `contracts-offline` check runs one deliberate network call under each guard and requires it to fail, so a guard that silently stopped working is detected.
- **Generation and tests share the guard.** Every `contracts-*` check loads it, so generation and all tests run offline without a second full run (NFR13.5).

## Storage Scope and Manifest-Key Enforcement (R-07; NFR2.2; BR3.3 to BR3.7, BR7.1)

**Layer 1: prefix data.** The register holds `U8_READABLE_PREFIXES` as a data file (`derivatives/`, `files/`). U2's IAM test reads this file, builds the policy conditions from it, and checks that U8's role is denied `originals/`, `incoming/` and `results/`. U1 does not write IAM; it supplies the single list.

**Layer 2: manifest validation (U8, before any read).** The design, shared as one function per language and used by U8 (receipt) and U9 (manifest builder):

```text
expected = {}
for exhibit in snapshot.exhibits:
  for img in [exhibit.leadImage] + exhibit.images:
      expected[img.assetRef] = ("imageDerivatives", image_keys(img.assetRef, img.width))
  for att in exhibit.attachments:
      expected[att.assetRef] = ("file", [file_key(att.assetRef, att.fileType)])
reject if manifest has a duplicate assetRef, a missing one, or an extra one
for entry in manifest: reject unless set(entry.sourceKeys) == set(expected keys)
                        and len(entry.sourceKeys) == len(set(entry.sourceKeys))
keys are compared as exact strings: no decode, no trim, no case change
```

- **Cost.** Linear in the snapshot size using hash sets. Because the expected keys come only from the key builders, a key with `..`, `//`, a leading `/`, `%`, `\`, an uppercase prefix, whitespace or a control character can never equal an expected key (BR3.4).
- **Key layout and variant rule (BR7.1, BR7.2, BR7.3).** The key patterns, the widths {480, 960, 1600}, the formats {webp, jpg} and the file-type table are data in `spec/`. Each language has one small builder and one parser driven by that data (about 30 lines each), kept equal by the shared fixtures. The variant boundary widths (1, 479, 480, 481, 959, 960, 961, 1599, 1600, 1601) are in the shared fixtures. The parser accepts only built keys, so a string that was not built does not parse.
- **Test matrix.** The 18 K cases, P1, F1 and OK, and the added F cases, are table-driven fixtures: each row names the request, the expected status and the reason code. A completeness check compares the table with the list in the register, so a deleted row fails (BR3.7).

## Fence-Conditional Write Contract for U8 (NFR2.4; ADR-004; BR3.1, BR3.2, BR3.7, BR3.8)

U1 defines the contract that U8's implementation must meet, and supplies the conformance suite. U1 does not choose the store.

```text
FenceStore:
  record(token, operation_id) -> RECORDED | FENCED       # one atomic item update
     RECORDED if token > highest, or token == highest and operation_id == last_operation_id
     FENCED   otherwise
PublicWriter:
  put(key, body, token)    -> OK | FENCED  # succeeds only if highest == token at this write
  delete(key, token)       -> OK | FENCED
```

**What U8 must do:**
1. Validate the whole request first. An invalid request returns `invalid` whatever its token, and calls nothing in the store (BR3.1).
2. Call `record` once, before the first write. `FENCED` returns the C3 result `fenced` with nothing written.
3. Pass the token to every `put` and `delete`. The first `FENCED` makes U8 stop and make no further write or deletion, and return `fenced` (BR3.8).
4. Return `completed` only after the last write, the last deletion and the CDN invalidation succeeded (BR3.2).

**Conformance suite.** The suite runs against a fake store (atomic, with an injectable pause) in U1, and against U8's real store implementation in B19 and B20:
- C3-F1 (a below-fence valid request), C3-F2 (the stalled attempt: A records 5, B records 6 and completes, A resumes and every `put` and `delete` is refused, the public set equals B's), C3-F3 (an invalid request never advances the fence, with a higher or a lower token), C3-F4 (an equal token with the same operation id, then with another), C3-F5 (a direct conditional write with a stale token).
- A concurrency case: two `record` calls issued together with tokens 5 and 6 end with a highest of 6 and exactly one of the two outcomes being `FENCED` if 6 was first, both `RECORDED` if 5 was first.

**Residual window (stated, not removed).** The fence is in one store and the public objects are in another, so a `put` that passed the token check just before a higher token was recorded can still land. The window is at most the write in flight, and only for an attempt that continues after a newer attempt was accepted. ADR-004's lease already serialises attempts, so the newer attempt exists only after the older lease expired or was released; the window therefore needs an attempt that runs beyond its lease. U9's restore of public storage to the last committed generation after a failed or superseded attempt covers what lands in it.

**Mitigation options handed to Infrastructure Design and U8's NFR Design (not chosen here):**
1. **Self-fencing by deadline.** U8 refuses to start a write after a deadline set below the lease length (lease minus a margin), so an attempt can never write past its lease.
2. **Conditional object writes.** Write each object with a precondition on its previous version or on an absent object, so a stalled write cannot replace a newer one.
3. **Versioned bucket with ordered writes.** Rely on object versioning so an overwritten newer object is recoverable, and order writes so the pages that make content visible are written last.
4. **Re-check immediately before each write.** Read the fence again just before each write, which narrows the window to the time between that read and the write.
Any of these can be combined. The choice, with its cost, belongs to Infrastructure Design (NFR4); none changes the contract above.

## Contract Register, Ledger and Constants (NFR13.9, NFR14.1; BR1.11)

- **Register contents.** Versions with states, consumer acceptance (mode, accepted versions, minor floor), the reviewed allow-list, the constants (`MAX_EXHIBITS`, `MAX_REQUEST_BYTES`, `U8_READABLE_PREFIXES`, `DOWNLOAD_NAME_BUDGET`, the placeholder-owner list), the address-field register and the evidence ledger.
- **State checks.** A check reads the register and enforces the order Proposed, Approved, Accepted, Current, Superseded, that Accepted needs every consumer row, and that a contract has exactly one Current version. Three fixture registers (valid, a skipped transition, a Current version not accepted by every consumer) test the check (AC1.41).
- **Address-field scan (BR4.9).** The scan walks the spec files for C1, C2 and C4 and applies the candidate predicate of BR4.9 (formats `uri` and `uri-reference`; names containing url, uri, address, href, location, endpoint or signature, or ending in Key or Keys; free-form objects and maps). Every candidate must be in the register as a storage address, a public link, a free-form allowance or a pinned non-address. A pinned-non-address test keeps `Exhibit.links` and `Repository.linkedProjectId` out of the candidate set. Free-form values in responses seen by the agreement run are scanned for address-like strings. The four negative fixtures and the positive fixture run in `contracts-lint`.
- **Security-sensitive paths proposed to the CI Pipeline stage (NFR13.9).** `contracts/spec/` for C1, C2, C3 and C4, the ports module, the key, path and download-name data and functions, `contracts/register/`, and the harness's pipeline contract. B02 is marked security-sensitive in the Bolt plan. U1 adds no workflow; any workflow change stays under the U0 rules.
- **Records (NFR14.1).** Specs, register and fixtures are committed. The one-line clarification owed to `contract-summary.md` (ASCII-only fold; hyphen trim again after the cut) is carried in the stage handoff as a tracked item.

## Dependencies, Licence Report and Supply Chain (NFR13.6, NFR13.7, NFR4.1)

- **Separation from U0.** U1's Python dependencies are declared in their own input file in the contracts folder and compiled to their own hashed lock, installed with `--require-hashes`. Tooling shared with U0 (pytest, Ruff, mypy, pip-audit) stays in the root lock. U1's npm packages form a workspace of the TypeScript project, and its tree is read on its own (`npm ls` for that workspace).
- **Report.** A small script reads the installed metadata for the closure of U1's runtime dependencies, which are the ones that ship (the Python validator in the API package) or are bundled (the standalone validator runtime in the U8 and U11 bundles), and prints each package with its SPDX id and the verdict allow-list, exception or unknown. Dev-only tools (generators, test tools) are listed, not gated. A reviewed exceptions file holds package, version, SPDX id, reason and reviewer.
- **Registration.** The report is the `contracts-licence-report` entry with `required = false`. Promoting it to a required gate is a tracked proposal for Michael through the CI Pipeline stage.
- **Audits and updates.** `pip-audit` and `npm audit` fail on high or critical findings; Dependabot proposes updates as pull requests; each new direct dependency is added to the "recorded at code generation" table in `tech-stack-decisions.md` (NFR13.6).

## CI Timing Allocation (NFR13.2)

U1 adds no workflow. Its steps are `[[check]]` entries in `scripts/verify-checks.toml`, gated by `applies_when` on the contracts folder. Allocations are the budget for the summed wall-clock time through `scripts/verify.py`, with dependencies installed and browsers downloaded (both cached); each entry's timeout is three times its allocation as a hang guard, not as the budget.

| Check id | Content | Allocation (s) |
|---|---|---|
| `contracts-lint` | Self-check, schema lint, address-field scan with its fixtures, fixture-host scan | 5 |
| `contracts-generate-drift` | Pipeline twice, determinism, drift against `generated/`, register-constant comparison | 30 |
| `contracts-types` | mypy strict and `tsc --noEmit` strict over authored and generated code | 20 |
| `contracts-test-py` | pytest with coverage: wrapper, parser, key and path functions, harness, K matrix, fence suite, ledger rules | 40 |
| `contracts-test-ts` | Vitest with coverage: wrapper, parser, key and path functions, fixtures | 20 |
| `contracts-browser` | Playwright in Chromium, Firefox and WebKit: fixture parity, CSP run, the browser benchmark | 30 |
| `contracts-bench` | Python benchmark, scaling test, `DOWNLOAD_NAME_BUDGET` | 10 |
| `contracts-offline` | Canary network calls under each guard | 5 |
| `contracts-package-content` | Package-content and import-boundary tests | 5 |
| `contracts-ledger` | Ledger recomputation and rule-to-test coverage (NFR13.3) | 5 |
| `contracts-licence-report` | Licence report (`required = false`) | 10 |
| **Total** | | **180** |

The whole pull-request CI stays within the approved 10 minutes, including a pull request that runs every component. If a measured sum exceeds 180 seconds, the Bolt's pull request reports it and the allocation is reviewed with the data, as the NFR Requirements note allows.

## Residual Risks

- **Fence window.** The window between the fence check and the public write remains until Infrastructure Design chooses a mitigation (above). The contract and the conformance suite do not depend on the choice.
- **Validator candidate may miss the speed gate.** The Python candidate must pass the B01 benchmark; the remedy and decision owner are fixed in NFR6.1 and above.
- **Browser versions.** The engines are covered; the previous browser version and the Studio journeys belong to U11's NFR and end-to-end suite (NFR12.1).
- **Shared-runner noise.** The benchmark is repeated once on failure; a persistent miss is treated as real.

## Assumptions & Open Questions

- **Logical folder names.** `spec/`, `register/`, `generated/`, `fixtures/` and `harness/` are logical; the paths are set at code generation under `contracts/`.
- **Standalone validator is a design preference.** One standalone TypeScript validator build for Node and the browser is chosen for parity; the fallback to an interpreting validator is designed, so no owner decision is involved.
- **Reference host framework.** Starlette or FastAPI is a test-tool choice made at code generation within the criteria; U3 confirms the real framework in its own NFR Design.
- **Allocations.** The 180-second split is this stage's allocation of the approved CI total, and the `DOWNLOAD_NAME_BUDGET` of 250 ms is derived from the NFR6.1 allocation. Both may be revised from measured data.
