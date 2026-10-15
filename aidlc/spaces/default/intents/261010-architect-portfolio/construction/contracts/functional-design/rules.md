# Business Rules — U1 contracts

**Inputs:** unit-of-work (U1; constraints 1 to 7); unit-of-work-story-map; requirements; components; contract-summary (C1 to C11, R-07, R-08, R-18); decisions (ADR-002, ADR-004, ADR-006, ADR-008, ADR-011, ADR-012); `entities.md`; `functional-design-questions.md`.

These rules make the contracts testable. U1 contains no business behaviour of its own: each rule states what a conforming definition, producer or consumer must do, and the contract test that fails when it does not. Rules about behaviour that another unit implements (for example how U8 fences or how U4 decodes) are stated as the contract that unit's tests must prove, with the fixtures and the harness supplied by U1.

## Rules

```yaml
rules:
  - id: BR1.1
    statement: Every contract has exactly one authoritative definition, held in U1, and no unit hand-copies it.
    category: policy
    applies_to: C1 to C11 and every Python or TypeScript type generated from them
    trigger: every change to a contract; every CI run
    logic: >
      The specs in U1 are the only source.
      Generated Python and TypeScript types are produced from them, never written by hand.
      A definition outside U1 that carries the same contract identifier ($id, OpenAPI info, port module name, or renderer contractVersion) is a duplicate.
    violation: CI fails and names the duplicate or hand-edited file
    source: contract-summary Contract Ownership Rules 1; unit-of-work U1 Owns
  - id: BR1.2
    statement: U1's own specs are well-formed.
    category: validation
    applies_to: every JSON Schema, the OpenAPI document and every port module in U1
    trigger: every CI run (the U1 self-check)
    logic: >
      Every JSON Schema parses, declares $schema (JSON Schema 2020-12) and $id, and validates against the 2020-12 meta-schema.
      The OpenAPI document validates as OpenAPI 3.1.
      No spec document contains a key whose value is null.
      (A type list that names "null" as a permitted type, such as contactEmail, is a string value and is allowed.)
    violation: the self-check fails; no types are generated
    source: contract-summary Contract Ownership Rules 6 (U1 itself); bolt-plan B01 DoD, B02 DoD
  - id: BR1.3
    statement: Strict contracts are closed at every level.
    category: validation
    applies_to: C2 snapshot, C3 publish request and result, C4 preview payload
    trigger: every validation of a message or fixture
    logic: >
      additionalProperties is false on every object in these schemas, including every $defs object.
      A message with any unknown property at any depth is refused whole.
      A required property that is absent, or a key whose value is null where the schema does not permit null, is refused.
    violation: the message is refused (C3 status invalid, including test C3-K9; C2 and C4 refused by the validating consumer); nothing is used or written
    source: contract-summary C2, Contract Ownership Rules 3; unit-of-work constraint 6; FR4.10
  - id: BR1.4
    statement: The snapshot allow-list mirrors the FR4.10 allow-list exactly.
    category: constraint
    applies_to: C2 PublicSiteSnapshot
    trigger: every change to the C2 schema; every CI run (the allow-list conformance test)
    logic: >
      The set of field paths the C2 schema permits equals the set of public fields in the approved allow-list: text, images with alt text, included attachments, links, derived badge kinds, the owner-included live URL, repositories confirmed public with name, URL and licence, primary category and featured flag, plus the site block and the structural fields.
      The conformance test enumerates the schema's permitted paths and compares them with a reviewed list kept in U1.
      A path in the schema and not in the list, or the reverse, fails.
      Access metadata (reachability results, final addresses, sign-in detection, check times, private repository names, URLs or IDs) has no path.
    violation: the test fails; the change cannot merge
    source: FR4.10; NFR2; ADR-002; unit-of-work U1 constraints; contract-summary C2
  - id: BR1.5
    statement: Adding a public field is a schema version change that needs review.
    category: policy
    applies_to: C2, and through the cascade C3, C4 and C11
    trigger: any pull request that adds, widens or renames a permitted path of the snapshot
    logic: >
      The pull request must raise the snapshot version (BR1.7), update the reviewed allow-list and the PB-02 export-scan allow-list test, and carry an independent security review recorded for its exact content.
      Narrowing a permitted path is a breaking change (BR1.8).
    violation: the allow-list conformance test or the review check fails; the change cannot merge
    source: contract-summary Contract Ownership Rules 3; unit-of-work U1 constraints; team practice (independent security review for publication boundaries)
  - id: BR1.6
    statement: Every message is validated in one of two defined modes, and a version outside the mode's acceptance is refused.
    category: validation
    applies_to: U8 (C2, C3), U11 (C2, C4), U6 (C5 request), U9 (C5 result), U4 module (C6), and field tolerance for U11 reading C1 responses
    trigger: receipt of a message; validation of a fixture
    logic: >
      Strict mode is used by producers, by fixtures, and by consumers of strict contracts (C2, C3, C4, C1 request bodies, the C5 request).
      The schema is the published closed schema, and its schemaVersion is the constant of the current version (for example "1.0").
      A message with any other schemaVersion, or any unknown field, is refused whole before any other field is read.
      Tolerant mode is used only by consumers of the lenient contracts (the C5 result, C6 records, and C1 responses except the embedded C4 payload).
      C1 responses carry no schemaVersion in the approved document. C1 is versioned by the OpenAPI document's info.version (semantic, Ownership rule 2), so for C1 responses tolerant mode means only that unknown fields are ignored, with no per-message version check; a change of the document's major version follows BR1.8.
      U1 generates the tolerant schema from the same spec by two changes only: unknown fields are ignored, and schemaVersion is accepted when its major part equals the contract's and its minor part is at least the lowest minor the consumer lists as accepted.
      Every other constraint (required fields, types, patterns, limits) still applies, and a different major version is refused.
      Each consumer's mode and accepted versions are recorded in the contract register (BR1.11).
      No version is guessed or defaulted.
    violation: C3 returns invalid (test C3-K10) and writes nothing; U11 shows no preview; a C5 or C6 consumer records a failure; nothing is acted on
    source: contract-summary C3-K10, Contract Ownership Rules 3 and 4
  - id: BR1.7
    statement: A new snapshot version cascades, and consumers accept it before the producer emits it.
    category: constraint
    applies_to: C2, C3, C4, C11 input type
    trigger: a new C2 version
    logic: >
      C3 and C4 pin the snapshot by its $id, so a new snapshot version also yields new C3 and C4 versions and a new C11 input type.
      Rollout order: U8 and U11 accept the new versions (their accepted sets hold the old and the new), then U9 starts emitting the new ones.
      A contract test holds a consumer fixture that accepts both versions and a producer fixture that emits exactly one.
    violation: the cascade test fails when C3, C4 or the C11 input type still pins the old snapshot $id
    source: contract-summary Contract Ownership Rules 3
  - id: BR1.8
    statement: Contract versions are semantic, and a breaking change follows a fixed process.
    category: policy
    applies_to: every contract
    trigger: any change to a contract
    logic: >
      A major version breaks consumers and a minor version only adds.
      A breaking change is agreed in one pull request that updates U1, both sides' contract tests and the contract summary.
      A breaking change on C1 or C3 also needs the owner's review, because those contracts carry authorization or publication.
    violation: the pull request cannot merge; both sides' contract tests fail against the old version
    source: contract-summary Contract Ownership Rules 2 and 5; project rules (owner approval for significant architecture and security policy changes)
  - id: BR1.9
    statement: Lenient contracts tolerate additive response fields; requests stay strict.
    category: constraint
    applies_to: C1 responses (except the embedded C4 payload), C5 results, C6 records
    trigger: a consumer reads a response or record
    logic: >
      The published schema is closed (strict mode, BR1.6) and is what producers and fixtures are checked against: a producer that emits a field outside it fails, and the closed schema accepts only its own schemaVersion constant.
      A consumer of a lenient contract validates in tolerant mode (BR1.6).
      So a later 1.1 C5 result or C6 record that adds a field is refused by the closed 1.0 schema, which is correct for a producer, and accepted by a 1.0 consumer in tolerant mode, with the extra field ignored. A C1 response that adds a field is accepted by tolerant mode and has no message version.
      A message with a different major version, or with a missing or mistyped known field, is refused in both modes.
      Every C1 request body stays strict (BR1.10), and the embedded C4 payload stays strict (BR1.3).
    violation: a consumer test fails if tolerant mode rejects a fixture that adds an unknown field and a same-major later minor version to a lenient message; a producer test fails if strict mode accepts it
    source: contract-summary Contract Ownership Rules 4; C1 notes "Unknown fields"
  - id: BR1.10
    statement: Every request body in the Studio API is closed.
    category: validation
    applies_to: C1 OpenAPI request bodies
    trigger: every CI run
    logic: >
      Every schema reachable from a requestBody has additionalProperties false at every object level.
      The U1 generator enforces this across the whole document, and the contract test fails on any request schema that is not closed.
      Draft and patch shapes whose full fields are fixed by U3's Functional Design are closed in the same way once defined; until then the document marks them as placeholders and the test lists them as pending.
    violation: the C1 contract test fails and names the open schema
    source: contract-summary C1 notes "Strict request bodies"; bolt-plan B02 DoD
  - id: BR1.11
    statement: One contract register holds the data that tests and other units read, and version states change only in order.
    category: constraint
    applies_to: the U1 contract register (a machine-readable data file in U1) and ContractVersion states
    trigger: every CI run; every change to a version state
    logic: >
      The register holds: each contract's versions and states; each consumer's mode and accepted versions (BR1.6, BR1.7); the reviewed allow-list of snapshot field paths (BR1.4); the named constants (the 200-exhibit cap, the 5 MB request bound, the readable-prefix scope of BR3.5); and the address-field register (BR4.9).
      States move only in this order: Proposed, Approved, Accepted, Current, Superseded.
      Approved needs the self-check, the contract tests on both sides and any required review (BR1.5, BR1.8) recorded.
      Accepted needs every consumer row of the contract to list the version.
      Current needs the version to be Accepted, and a contract has exactly one Current version.
      Superseded needs a later version to be Current.
      Source and direction: the register is the single source for named constants, the prefix list and the allow-list paths. A value that a schema must carry (for example maxItems 200 or the 5 MB bound) is generated into the schema from the register at generation time; the hand-written spec never restates it. The drift check (BR9.2) compares the generated schema with the register, so a schema value that differs from the register fails, and the register fails only when the same value is defined by hand in a second place.
      The register also holds the evidence ledger, one row per C1 operation (BR4.8, BR4.13).
      The first values in the register are copied from the approved contract summary (200 exhibits, 5 MB, derivatives/ and files/).
    violation: the register check fails and names the skipped transition, the consumer that does not accept the version, or the duplicate definition
    source: contract-summary Contract Ownership Rules 1 and 3 (deployment order); unit-of-work U1 constraints; R-07

  - id: BR2.1
    statement: The snapshot's structural rules are enforced by the schema itself.
    category: validation
    applies_to: C2 PublicSiteSnapshot
    trigger: every validation of a snapshot
    logic: >
      The schema enforces: the required top-level fields; the size caps (200 exhibits, 5 featured slugs, 4 categories, 40 images, 20 attachments, 10 links, 6 badges, 10 public repositories per exhibit); the slug pattern; the assetRef pattern; the closed fileType, badge kind and category slug lists.
      Links and the live URL accept https only, and never a repository host: github.com, githubusercontent.com, gitlab.com and bitbucket.org, with any subdomain.
      A public repository is accepted only as a github.com owner/name URL.
      The site block takes an owner name, a github.com profile URL and a contact email that is a valid email or null.
    violation: the snapshot is refused whole
    source: FR4.3; FR4.10; contract-summary C2 structural rules
  - id: BR2.2
    statement: The snapshot's semantic rules S1 to S7 are checked by both U9 and U8 from the same shared check.
    category: validation
    applies_to: C2 snapshot semantic rules S1 to S7
    trigger: U9 before sending; U8 on receipt; the renderer on entry (BR8.2)
    logic: >
      U1 provides one conformance check and its fixtures for S1 to S7.
      S1 featured slugs are live featured exhibits, without duplicates.
      S2 categories equal the set derived from primary categories, with correct counts.
      S3 slugs are unique.
      S4 spdx appears only with openSource.
      S5 at most one of inBrowser, signInRequired, byInvitation, and only with a liveUrl.
      S6 openSource, sourceAvailable and sourcePrivate agree with the listed public repositories.
      S7 within one exhibit, each assetRef appears once among leadImage and images together (a lead image repeated in images is a violation), and once among attachments.
    violation: U9 does not send; U8 returns invalid and writes nothing (test C3-K18)
    source: contract-summary C2 semantic rules S1 to S7; unit-of-work constraint 6
  - id: BR2.3
    statement: Semantic rules that depend on facts outside the snapshot are U9's alone and are never claimed by U1 or U8.
    category: constraint
    applies_to: S6a, S8, S9, S10
    trigger: U9 builds a snapshot
    logic: >
      S6a (OSI-approved licence), S8 (repositories confirmed public at preparation), S9 (live URL included and authorized) and S10 (badges derived from the FR4.10 table) rely on GitHub reads, the pinned SPDX/OSI list and Studio data.
      U1 records them in the rule table with checkedBy set to U9 only.
      U1's fixtures for them test U9's builder, and no U1 or U8 check claims to prove them.
    violation: a rule catalogue test fails if any of these rules lists U8 or U1 as its checker
    source: contract-summary C2 semantic rules table; unit-of-work constraints 3 and 4; FR4.10; FR10.7
  - id: BR2.4
    statement: The snapshot never carries a private address or private data.
    category: constraint
    applies_to: C2 PublicSiteSnapshot
    trigger: every change to the schema; every fixture run
    logic: >
      The schema has no field intended to hold a storage key, a preview or owner-only image or download address, an upload authorization, or any draft, ticket, operation, link-check, private-repository or access-metadata value.
      Images and attachments are identified only by assetRef.
      The schema cannot tell an owner-entered public https URL from a storage address: links.url, liveUrl, publicRepositories.url and site.githubProfileUrl accept any https URL that passes BR2.1, and they are exempt from the address scan by name only (BR4.9). They are the owner's reviewed content, shown at Publish. This rule does not claim more than that.
      Negative fixtures that add imageAddresses, downloadAddresses, an image address field, a derivative key, a ticket id or a link-check field to a snapshot are refused.
    violation: the schema test fails if a negative fixture is accepted
    source: "unit-of-work U1 (preview payload: the snapshot never carries a private address); FR6.2; NFR2; ADR-002; contract-summary C2 closing paragraph"
  - id: BR2.5
    statement: A snapshot request over the size bound is refused by U9 before U8 is invoked, and by U8 if it arrives anyway.
    category: constraint
    applies_to: C2 and C3
    trigger: U9 prepares a publish request; U8 receives a request
    logic: >
      exhibits is capped at 200 by the schema.
      IF the serialized publish request is over 5 MB THEN U9 does not invoke U8 and the operation fails with the reason SNAPSHOT_TOO_LARGE.
      U8 applies the same bound on receipt as one of its snapshot checks: a request over the bound, or over the 200-exhibit cap, is invalid and nothing is written (the over-size part of approved test C3-K18).
      The two limits are named constants in the contract register (BR1.11), shared by U9, U8 and the fixtures.
    violation: U9 fails the operation with SNAPSHOT_TOO_LARGE and writes nothing; U8 returns invalid and writes nothing
    source: contract-summary C2 "Size bound"

  - id: BR3.1
    statement: A publish request carries the operation id and the per-attempt fencing token, and U8 refuses any write with a lower token than the highest it has accepted.
    category: constraint
    applies_to: C3 PublishRequest and U8's site-wide fence
    trigger: U9 invokes U8; every write or deletion U8 makes
    logic: >
      The request has schemaVersion, operationId, attemptToken (an integer of at least 1, strictly increasing per attempt, issued only by U9), purpose (operation, restore or recovery), the snapshot and the asset manifest.
      purpose is used only for logging; every request means "make public storage equal this snapshot".
      When the token is recorded: U8 validates the whole request first (version, schema, semantic rules, manifest). Only a request that passes validation records its token, as a conditional update of the site-wide fence in U8's private store that sets it to the higher of the stored value and the token. The fence is never deleted.
      Order, one for every case: (1) validate the request; (2) compare the token with the fence; (3) record it; (4) write.
      An invalid request is answered invalid whatever its token, higher or lower than the fence, and never advances the fence (test C3-F3 covers both).
      A valid request whose token is lower than the recorded fence is answered fenced after step 1, with nothing written (test C3-F1).
      An equal token is an allowance for duplicate delivery of the same operationId (a repeat of the same attempt that rewrites the same set); an equal token with another operationId is refused as fenced (test C3-F4). ADR-004 tokens are strictly increasing per attempt, so this allowance covers only redelivery, not a new attempt.
      Every write and every deletion in the publish sequence is conditional on the fence still equalling this request's token at that write (BR3.8).
    violation: status fenced, nothing written; for a fence that advances during the run, no further write happens (BR3.8)
    source: contract-summary C3; ADR-004 ("refuses any write with a lower token")
  - id: BR3.2
    statement: The publish result reports one of four statuses, and only U9 decides what follows.
    category: policy
    applies_to: C3 PublishResult
    trigger: U8 returns
    logic: >
      completed only after every write and deletion succeeded and the CDN invalidation was submitted.
      fenced: a higher token is already recorded, or became recorded before one of this request's writes (BR3.1, BR3.8).
      invalid: schema, semantic or manifest-key validation failed, and nothing was written.
      failed: anything else.
      The error text holds a reason code and object keys only, never snapshot content.
      U8 never retries and never reads Studio data.
      U9 treats any status other than completed, or a timeout, as a failed attempt, then restores or recovers.
    violation: a result with another status, or with snapshot content in error, fails the result-schema test
    source: contract-summary C3 behaviour and authority; ADR-004; unit-of-work constraint 4
  - id: BR3.3
    statement: The asset manifest lists exactly the assets the snapshot references.
    category: validation
    applies_to: C3 assetManifest (check (a))
    trigger: U8 validates a request before any read; U9 builds a manifest
    logic: >
      Each assetRef is referenced by the snapshot itself: an image or lead image of an exhibit for imageDerivatives, or an attachment for file.
      There is exactly one entry per referenced asset, with none missing, none extra and no duplicate assetRef.
    violation: the request is invalid and nothing is written (tests C3-K3, C3-K4, C3-K15)
    source: contract-summary C3 R-07 layer 2 (a); R-07
  - id: BR3.4
    statement: Manifest source keys are exactly the keys the key rules require, compared byte for byte.
    category: validation
    applies_to: C3 assetManifest sourceKeys (checks (b) and (c))
    trigger: U8 validates a request before any read
    logic: >
      For an image the keys are derivatives/{assetRef}/{variant}.{format} for every variant the variant rule (BR7.2) gives from the snapshot width, in both formats.
      For a file the key is files/{assetRef}/file.{ext}, where ext comes from the file type table (BR7.3) for the snapshot fileType.
      The set must match exactly, with no missing key, no extra key and no duplicate.
      Keys are compared byte for byte with the generated expected keys, with no normalisation.
      A key containing "..", "//", a leading "/", "%", "\", an uppercase character in a prefix, whitespace or a control character never matches.
    violation: the request is invalid and nothing is written (tests C3-K1, K2, K5 to K8, K11 to K14, K16, K17; K9 belongs to BR1.3)
    source: contract-summary C3 R-07 layer 2 (b), (c); C8; R-07
  - id: BR3.5
    statement: The publisher's storage scope is limited by prefix, and the limit is held in U1 as data.
    category: authorization
    applies_to: U8's execution role (implemented by U2) and U8's validator
    trigger: every CI run; Infrastructure Design review
    logic: >
      U1 lists the readable private prefixes for U8 as derivatives/ and files/ only, in the contract register (BR1.11).
      U8 can never read incoming/, originals/, results/, backups/ or any database.
      It may write and delete only in the public bucket, and read and write only its own private state store.
      Because IAM limits only by prefix, the application check (BR3.3, BR3.4) is also required.
      U2's IAM test reads the prefix list from U1 and confirms that U8's role is denied originals/, incoming/ and results/.
    violation: the IAM test or the K tests fail; the change cannot merge
    source: contract-summary C3 R-07 layer 1; R-07; NFR2; NFR3
  - id: BR3.6
    statement: Public object paths come from the snapshot and the path rules, never from the request.
    category: constraint
    applies_to: U8 (check (d)); C3 test C3-P1
    trigger: U8 writes after a valid request
    logic: >
      U8 computes every public object path from the snapshot and the C9 path rules (BR7.4, BR7.5).
      It writes exactly that set, plus the static assets listed by the renderer output.
      IF a derivative the variant rule requires is missing from the manifest THEN the result is invalid, so a live page never references a missing image.
    violation: invalid, or test C3-P1 fails when the written set differs from the computed set
    source: contract-summary C3 R-07 layer 2 (d), C3-P1; FR7.4
  - id: BR3.7
    statement: The R-07 test matrix is mandatory and shared by both sides.
    category: policy
    applies_to: C3 contract tests C3-K1 to C3-K18, C3-P1, C3-F1, C3-OK
    trigger: every CI run of U1, U8 and U9
    logic: >
      U1 holds each case as a fixture with its expected status.
      Every K case must return invalid with nothing written.
      U8 runs the cases against its validator and writer; U9 runs them against its manifest builder, which must never produce a request that a K case would reject.
      A case that is removed or weakened fails the matrix-completeness check.
      U1 adds four fence cases to the approved list, as a disclosed addition: C3-F2 (a stalled attempt, BR3.8), C3-F3 (an invalid request with a higher token does not advance the fence), C3-F4 (an equal token), and C3-F5 (a write conditional on the fence is refused after a higher token is recorded).
    violation: the matrix-completeness check or a case fails; the change cannot merge
    source: contract-summary C3 contract tests; R-07; Contract Ownership Rules 6; ADR-004
  - id: BR3.8
    statement: A stalled older attempt cannot overwrite newer state, and this is proved at the conditional write.
    category: constraint
    applies_to: U8's write and deletion path and its fence store
    trigger: every write or deletion U8 makes during one publish sequence
    logic: >
      Each write and each deletion is a conditional operation that succeeds only if the fence in U8's private store still equals this request's token.
      A check made once at receipt is not enough, because the attempt may stall after it.
      IF the fence has advanced (a request with a higher token was accepted meanwhile) THEN the operation is refused, U8 stops at once, makes no further write or deletion, and returns fenced.
      Residual window, stated explicitly: the fence lives in U8's private store and the objects live in the public bucket, so U1 cannot make the fence check and the public write one atomic step. A write that passed the check just before a higher token was accepted can still land. The contract promises only that no new write starts once the fence has advanced and that every write re-checks the fence; the window is at most the write in flight, and ADR-004's restore of public storage to the last committed generation after a failed or superseded attempt covers what lands in it.
      The mechanism that narrows the window (for example conditional or versioned writes, or write ordering) is left to NFR Design and Infrastructure Design.
      The scenario test (C3-F2) uses a fake store with atomic conditional writes and an injectable pause. It proves the contract (every write re-checks the fence), not the residual window. Attempt A (token 5) passes validation and records 5; B (token 6) is accepted and completes; A resumes and attempts each write and deletion kind; every one is refused, the public set equals B's, and A's result is fenced.
      Test C3-F5 calls the conditional write directly with a stale token, to prove the condition is in the write and not only in the receipt check.
    violation: the scenario test fails if any object of attempt A is present, or any object of B is changed or recreated
    source: ADR-004 ("refuses any write with a lower token, so a stalled attempt cannot overwrite newer state or recreate a withdrawn object"); contract-summary C3 (fenced)

  - id: BR4.1
    statement: The Studio API description is one valid OpenAPI 3.1 document with a closed error-code list.
    category: validation
    applies_to: C1
    trigger: every CI run
    logic: >
      The document validates as OpenAPI 3.1 and has one server entry.
      Every operation is tagged with exactly one of the registering-unit tags (U3-projects, U3-repositories, U4-media, U5-assistant, U9-publication).
      Every error code the contract uses is in the ErrorCode list, and every ErrorCode value is used by at least one documented response or by the shared pipeline responses.
    violation: the OpenAPI self-check fails
    source: contract-summary C1; bolt-plan B02 DoD
  - id: BR4.2
    statement: The routes actually registered equal the paths and methods in the OpenAPI document.
    category: constraint
    applies_to: the reference host at B02, then the route registry of each real host as it lands (BR4.13)
    trigger: every CI run that assembles a host
    logic: >
      The set of (method, path) pairs held by the host's route registry equals the set in the document.
      A registered route missing from the document fails the build.
      At B02 the registry is the reference host's, built from the document itself, so the check proves the harness and the document structure and nothing about U3, U4, U5 or U9.
      When U3's real registry exists (B06, B07), the same check runs against it; a documented route that no module registers fails once the assembly includes that module's tag (U4 at B10, U5 at B14, U9 at B21 to B25).
    violation: the build fails and names the route
    source: contract-summary C1 R-08 contract test (1); bolt-plan B02 Demo, B06, B07
  - id: BR4.3
    statement: Every registered route runs the same pipeline, in the same order, with no opt-out.
    category: authorization
    applies_to: every route registered through the route registry (the pipeline contract is U1's; the real pipeline is U3's, built at B06 and B07)
    trigger: every request
    logic: >
      The order is: OwnerAccess check (issuer plus subject), rate limits, request id and error mapping, then the handler.
      RouteRegistry.register has no parameter that skips a step.
      The only route outside the OwnerAccess step is GET /health, declared by U3 itself, which still has rate limiting and a request id.
      U1 states this order as the pipeline contract. The reference host implements it minimally so the conformance test has something to run against (BR4.13).
    violation: the pipeline conformance test fails; no handler is reached
    source: contract-summary C1 R-08; unit-of-work "Call Direction Inside the Back End"; ADR-011; FR1.2; NFR1; NFR16
  - id: BR4.4
    statement: A caller who is not the owner never reaches a handler.
    category: authorization
    applies_to: every registered route except GET /health
    trigger: every CI run (the R-08 tests (2) and (3))
    logic: >
      Each route is called four ways: with no token, with an expired token, with a token carrying the owner's email but another subject, and with a token from another issuer.
      Every call must answer 401 or 403 with the shared Error body.
      A spy handler registered for each route must record zero invocations.
      At B02 the test runs against the reference host's pipeline, which proves that the test cases discriminate (a deliberately broken reference pipeline must make them fail) and that the spy mechanism works.
      It is not evidence about U3's OwnerAccess. The same test re-runs against the real host at B07 and, for the routes each unit registers, at B10, B14 and B21 to B25.
    violation: the test fails and names the route and the case
    source: contract-summary C1 R-08 contract tests (2) and (3); R-08; FR1.1; FR1.2; NFR1
  - id: BR4.5
    statement: Every error response (4xx and 5xx) produced by the API host carries the shared Error body; success responses are not covered.
    category: validation
    applies_to: every 4xx and 5xx response in the C1 document
    trigger: every error response; every CI run
    logic: >
      The approved text is: "Every error body is `Error` with a code from the closed `ErrorCode` list" (Errors, Timeouts and Retries). R-18 point 2 extends it to the responses the first draft left without a body: 404, 410, 428, 504 and the 409, 410 answers of the retry route.
      The body is JSON with code (a value of the closed ErrorCode list), message, requestId and optionally blockers (a list of strings).
      The message contains no secret and no personal data, and the requestId is set by the pipeline.
      Pipeline responses (401, 403, 429, and 500 INTERNAL from the status table) and handler responses (404, 409, 410, 422, 428, 503, 504) all use this body.
      A 2xx response is outside this rule. The approved C1 documents several success responses without a body, recorded in the entities as NoBodyException entries, and they stay as approved: PATCH /projects/{projectId} 200 (revision in the ETag header), POST /projects/{projectId}/repositories 200 ("Linked"), POST /projects/{projectId}/images 200 and /attachments 200 ("Attached"), PUT /featured-lineup 200 ("Saved"), and POST /publication/operations/{operationId}/retry 202 ("Retry scheduled").
      The one documented no-body response that is neither an error nor a success body is the 303 from POST /projects, which carries a Location header naming the existing project.
      Responses generated by the API entry point before the host runs are outside this document.
      500 is declared once as a shared response although the approved note lists only 401, 403 and 429; this is a disclosed clarification, because the approved status table already gives 500 INTERNAL to every route.
    violation: the document lint fails if a 4xx or 5xx response lacks the Error schema and is not the documented 303; the agreement test (BR4.8) fails if an observed error has another shape
    source: R-18 point 2 (P-08); contract-summary C1 and "Errors, Timeouts and Retries"; NFR11
  - id: BR4.6
    statement: Each error code is used only with its documented status.
    category: constraint
    applies_to: the (status, code) table of C1
    trigger: every error response; every CI run
    logic: >
      The closed pairs are: 401 UNAUTHENTICATED; 403 NOT_OWNER, AI_SPEND_NOT_APPROVED, PROVIDER_NOT_APPROVED; 404 NOT_FOUND; 409 STALE_REVISION, SLUG_TAKEN, LINEUP_CHANGED, TICKET_USED, TICKET_MISMATCH, BASIS_CHANGED, SUPERSEDED; 410 TICKET_EXPIRED; 422 VALIDATION_FAILED, PREVIEW_BLOCKED, NO_LINKED_REPOSITORY; 428 REVISION_REQUIRED; 429 RATE_LIMITED; 500 INTERNAL; 503 GITHUB_UNAVAILABLE; 504 SUGGESTION_UNAVAILABLE.
      A handler response whose status and code are not a pair in this table is a violation.
    violation: the agreement test (BR4.8) fails and names the route and the pair
    source: contract-summary "Errors, Timeouts and Retries"; R-18
  - id: BR4.7
    statement: Pipeline responses are declared once and apply to every operation.
    category: constraint
    applies_to: every operation except GET /health
    trigger: every CI run
    logic: >
      The shared responses 401 (Unauthenticated), 403 (Forbidden), 429 (RateLimited) and 500 (Internal) are declared once in the document's components and attached to every operation by reference or by a single document-wide rule, so no operation can omit one.
      GET /health has 200, 429 and 500 only (it "keeps rate limiting and the request id", C10).
      Same status, same Error shape, and the code distinguishes: a route may restate a shared status when C1 documents it, using the same Error schema and a code from that status's row of the BR4.6 table. It never gives the status another meaning or another body shape.
      The approved examples stay as approved: the 403 on POST /projects/{projectId}/suggestions with codes AI_SPEND_NOT_APPROVED and PROVIDER_NOT_APPROVED (FR5.8, FR5.9), next to the shared 403 NOT_OWNER; and the 429 RATE_LIMITED on POST /projects/{projectId}/uploads, which is the shared 429.
    violation: the OpenAPI lint fails and names the operation; a restated shared status with a different body schema or a code outside its row fails
    source: "contract-summary C1 notes \"Shared pipeline responses\" (every route except /health may also answer 401, 403 and 429, declared once and not repeated per route), C1 suggestions and uploads responses; R-18"
  - id: BR4.8
    statement: The OpenAPI responses and the registered handlers agree, and a test proves it.
    category: policy
    applies_to: every operation in C1, against the real handlers of the unit that registers it
    trigger: every CI run of each unit that registers routes (B10, B14, B21 to B25 for U4, U5, U9; B07 and B08 and B09 for U3)
    logic: >
      For every operation and every documented response status, the harness drives the unit's real registered handler into that response.
      It checks that the observed status, content type and body validate against the documented schema, or against the documented no-body response (BR4.5).
      It also checks that no status, code pair or body shape occurs that the document does not list.
      Every documented status must be provoked by at least one case; an unprovoked status is reported as untested and fails.
      The harness records evidence per operation as none, reference or real, in the evidence ledger of the contract register (BR1.11, BR4.13). A stub handler driven into its documented response proves only that the harness can build that response; it is evidence "reference" and is never counted as agreement. An operation counts as agreeing only with evidence "real".
      At B02 the document-only checks run (structure, BR4.1, the error-body and shared-response lint, BR4.5 and BR4.7). The agreement check is built, tested against the reference host, and reports every operation as "reference" until its unit lands.
      When a unit's last route-owning Bolt lands, any of its operations still not "real" fails that unit's CI; the build and test stage confirms that no operation remains below "real".
    violation: the test fails and names the operation, status and difference
    source: R-18 point 3 (P-08); bolt-plan B02 R-18; contract-summary Contract Ownership Rules 6
  - id: BR4.9
    statement: There are exactly three direct-to-storage channels, and each is issued only to the authenticated owner.
    category: authorization
    applies_to: every field of C1, C2 and C4 that could carry an address
    trigger: every CI run (the channel scan); every issue of an address
    logic: >
      The channels are: the single-use upload authorization (U4 route POST /projects/{projectId}/uploads), used once for one object under incoming/; the owner-only short-lived preview image addresses; and the owner-only short-lived preview download addresses (both in the preview payload from the U9 route GET /projects/{projectId}/preview).
      Each is issued only by an owner-authenticated route, is short-lived, and is single-purpose.
      The address-field register (BR1.11) names the fields, so the scan does not guess from a format.
      Storage-address fields, exactly: UploadAuthorization.uploadUrl and UploadAuthorization.fields (channel upload); PreviewPayload.imageAddresses values (channel preview images); PreviewPayload.downloadAddresses values (channel preview downloads).
      Public-link fields, exempt by name because they hold owner-entered public https URLs and no storage address: C2 Link.url, Exhibit.liveUrl, PublicRepository.url, SiteBlock.githubProfileUrl; and the Location header of the 303 on POST /projects, which names a project path.
      The scan walks every property in C1, C2 and C4. A property is a candidate if it has a uri or uri-reference format; or its name contains url, uri, address, href, location, endpoint or signature, or ends in Key or Keys; or it is a free-form object or a map with additionalProperties. The word "link" alone is not a trigger, so Exhibit.links (an array of Link objects) and Repository.linkedProjectId (a project identifier) are not candidates; the register lists both as not-an-address and a test pins that, so the predicate cannot drift back to capturing them.
      Every candidate must be on the storage-address list or the exempt list. Anything else fails.
      Enumeration for the approved schemas (the "approved schemas pass" fixture asserts exactly this set): C1 has UploadAuthorization.uploadUrl (storage address), UploadAuthorization.fields, Project, ProjectPatch and Ticket.inventory (free-form allowances); C2 has SiteBlock.githubProfileUrl, Link.url, Exhibit.liveUrl and PublicRepository.url (public links); C4 has PreviewPayload.imageAddresses and downloadAddresses (storage addresses), and its embedded snapshot is scanned as C2. No other property of the approved C1, C2 or C4 matches. C6's documentMetadata is a free-form allowance of the C6 record, outside the scan's three documents.
      Free-form and placeholder objects (Project, ProjectPatch, Ticket.inventory, UploadAuthorization.fields, UploadResult.documentMetadata) are listed in the register with their owner. Their values must not contain an address-like string (a URL with a scheme, a storage key under a private prefix, or a signed-address parameter such as a signature or expiry query), except that UploadAuthorization.fields may carry the form fields of the upload channel, whose object key must equal incoming/{assetRef}/upload. The handler agreement test (BR4.8) applies this value check to every observed response.
      Positive fixture: the approved C1, C2 and C4 as defined pass the scan with no exemption beyond the two lists.
      Negative fixtures (each must fail): a response property with a uri format that is not listed; an innocuously named property (for example ref) with a uri format; a listed free-form object holding a signed address; and a hidden fourth channel such as a download URL added to the attachment-attach response.
      U11 reaches no other storage or service.
    violation: the scan fails when a candidate is on neither list or a free-form value holds an address-like string; a negative fixture that passes fails the scan's own test
    source: R-18 point 1 (P-08); contract-summary C1 R-08, C4; FR6.2; FR4.8
  - id: BR4.10
    statement: Every operation that edits a draft or the line-up requires the revision it is based on.
    category: constraint
    applies_to: PATCH /projects/{projectId}, POST /projects/{projectId}/repositories, POST /projects/{projectId}/images, POST /projects/{projectId}/attachments, PUT /featured-lineup
    trigger: every CI run; every request
    logic: >
      Each of these operations declares the required If-Match header and documents 409 and 428.
      A request without the header answers 428 REVISION_REQUIRED, and one based on an older revision answers 409 STALE_REVISION or LINEUP_CHANGED, changing nothing.
      The revision is returned in the ETag header of the matching reads.
    violation: the OpenAPI lint fails if an operation on the list lacks the header or either response
    source: FR3.3; FR3.4; contract-summary C1 notes "Concurrency"
  - id: BR4.11
    statement: The health route returns a fixed body and nothing else.
    category: policy
    applies_to: GET /health
    trigger: every request; smoke checks
    logic: >
      The route answers 200 with exactly {"status":"ok"}.
      It declares no security requirement, reads no domain data and returns no version, configuration, project or owner information.
      No other operation declares an empty security list.
    violation: the schema test or the security-list lint fails
    source: contract-summary C10 and C1 Health schema; NFR11
  - id: BR4.12
    statement: U11 reaches U4, U5 and U9 only through U3's host.
    category: authorization
    applies_to: C1 and the back-end package
    trigger: every CI run
    logic: >
      The document has a single server entry.
      U4, U5 and U9 register routes and handlers into U3's host through the route-registration port, and expose no endpoint of their own.
      The set of deployables with an HTTP API entry equals the U3 host.
      Every route of those units inherits the pipeline of BR4.3.
    violation: the build fails when a module declares its own listener or a second server entry appears
    source: R-08; contract-summary C1; unit-of-work "Call Direction Inside the Back End"; ADR-011

  - id: BR4.13
    statement: B02 builds and tests a reference host inside the harness, and defers the same tests to the real hosts.
    category: policy
    applies_to: the shared contract-test harness (B02) and the hosts of U3 (B06, B07, B08, B09), U4 (B10), U5 (B14), U9 (B21 to B25)
    trigger: every CI run
    logic: >
      U1 is a specification unit, and the real route registry and OwnerAccess pipeline arrive in U3's Bolts after B02.
      B02 therefore builds a thin, test-only reference host in the harness. It registers a route for every (method, path) in the OpenAPI document, with spy handlers, and runs the pipeline of BR4.3 using the owner-access contract (issuer plus subject match, FR1.1) defined from U1's port definitions.
      The reference host ships nowhere. It cannot be imported by a production package, and a boundary test enforces that.
      Verified at B02: document structure (BR4.1); the error-body and shared-response lint on the document (BR4.5, BR4.6, BR4.7); the write-header lint (BR4.10, BR4.11); the three-channel scan on the document and schemas (BR4.9); registry equality against the reference host (BR4.2); non-owner calls rejected by the reference pipeline with spy counts of zero (BR4.4); and negative controls that must each make the matching check fail: a broken reference pipeline that lets a non-owner reach a handler (non-owner test), an extra undocumented registered route (registry check), a handler that returns an undocumented status or code pair (agreement check), and a handler that returns a wrong body shape for a documented status (agreement check).
      The four non-owner token fixtures come from a token issuer in the harness that creates its signing key in memory, never stored or committed: no token, an expired token, a token carrying the owner's email on another subject, and a token from another issuer. The verifier expects exactly 401 for no token, expired and other issuer, and 403 for the other subject (the U0 BR1.1 split; the approved C1 text says 401 or 403), the shared Error body, and a spy count of zero.
      Evidence is recorded in the evidence ledger of the contract register (BR1.11): one row per C1 operation with the level none, reference or real, the Bolt that set it and the harness result it came from. Each unit's Bolt updates its operations' rows from the harness output, CI fails if a row claims real without a passing real-handler result, and Build and Test reads the ledger to confirm that no operation is below real.
      Deferred and re-run against the real hosts: registry equality and the non-owner test at B06 and B07; agreement of every operation with its real handler (BR4.8) as each unit lands; the value check of BR4.9 on real responses.
      A stub or reference handler driven into its documented response is not evidence of agreement (BR4.8).
    violation: B02 does not pass without the negative control failing as designed; a unit's CI fails if it does not run the shared cases against its real host
    source: R-08; R-18 point 3 (P-08); bolt-plan B02 (Demo "harness runs green against stub implementations"), B06, B07; unit-of-work U1 Delivers (contract tests that both sides run)
  - id: BR5.1
    statement: The preview payload is a strict composition of the candidate snapshot and separate address maps.
    category: validation
    applies_to: C4 PreviewPayload
    trigger: U9 builds the payload; U11 receives it
    logic: >
      The payload has schemaVersion, snapshot (valid against C2 at the same version), previewSlug (the slug of the previewed exhibit inside the candidate snapshot), imageAddresses, downloadAddresses and expiresAt.
      U11 validates the payload against C4 and the snapshot against C2 before rendering, even though C1 responses are otherwise lenient.
      The candidate snapshot is the last committed snapshot with this exhibit replaced by its candidate version, from the same projection as publication.
    violation: U11 shows the error and no preview; nothing is rendered
    source: contract-summary C4; ADR-008; FR6.1
  - id: BR5.2
    statement: Private addresses live only in the two address maps, with exact key forms.
    category: constraint
    applies_to: C4 imageAddresses and downloadAddresses
    trigger: U9 builds the payload; U11 resolves an asset
    logic: >
      imageAddresses keys have the form {assetRef}/{variant}.{format} with the variants and formats of the variant rule; downloadAddresses keys are an assetRef; all values are URIs.
      The snapshot carries no address (BR2.4).
      The preview resolver looks up images and downloads in these maps.
      IF a reference the renderer requires is missing THEN the resolver throws RenderInputError and no preview is shown.
    violation: the key-pattern test fails; a missing entry shows no preview
    source: contract-summary C4 "Use of the payload"; FR6.2; PB-12
  - id: BR5.3
    statement: A candidate that cannot project to a valid snapshot answers PREVIEW_BLOCKED with its blockers.
    category: validation
    applies_to: GET /projects/{projectId}/preview
    trigger: preview request
    logic: >
      IF the candidate does not project to a valid C2 snapshot (for example no title, no lead image, an image without alt text, no slug) THEN answer 422 PREVIEW_BLOCKED with the blockers in the Error body.
      Rights, live-URL and publication approvals do not block preview, because preview is private.
    violation: the fixtures for the blocked and unblocked cases fail the contract test
    source: contract-summary C4 "When preview is available"; FR7.3; FR6.2
  - id: BR5.4
    statement: The link-check request and result are fixed, and no link-check field enters the snapshot.
    category: validation
    applies_to: C5 LinkCheckRequest and LinkCheckResult
    trigger: U9 invokes U6
    logic: >
      The request is schemaVersion, requestId and a url of up to 2048 characters; U6 parses the URL itself and does not trust it to be canonical.
      The result label is one of "Reachable", "Not reachable", "Refused (non-public address)".
      finalAddress, when present, has no userinfo, query or fragment.
      reason is up to 200 characters.
      U6 finishes within 15 seconds and U9's invoke timeout is 20 seconds; an invoke error or timeout is recorded as "Not reachable" with the reason.
      U9 sends at most one URL per exhibit per preparation.
      No field name of C5 appears in C2.
      Tests, with an injectable clock and a fake U6: (1) a fake U6 that takes longer than 15 seconds is treated by the contract test as a violation of U6's bound; (2) a fake invoke that errors or exceeds 20 seconds makes U9's client return "Not reachable" with a reason of up to 200 characters; (3) an exhibit fixture with several candidate URLs produces exactly one invoke in one preparation, and none when it has no live URL.
    violation: a result with another label, or a finalAddress with userinfo, query or fragment, fails the conformance check; a C5 field found in C2 fails the allow-list test; any of the three timing and count tests fails
    source: FR10.5; NFR17; NFR16; contract-summary C5, Errors, Timeouts and Retries
  - id: BR5.5
    statement: An upload processing result is consistent with the key layout.
    category: validation
    applies_to: C6 UploadResult (results/{assetRef}.json)
    trigger: the isolated processor writes a result; U4's module ingests it
    logic: >
      The record's assetRef equals the assetRef in its key.
      status valid with an image has exactly the derivatives the variant rule requires from the width, each with a key matching the C8 pattern, and no fileKey.
      status valid with an attachment has a fileKey matching the C8 pattern and the extension for its detected type, and no derivative.
      status rejected has a reason and no derivative and no fileKey.
      detectedType is from the closed list.
      The raw object under incoming/ is deleted after processing and the original image is kept under originals/.
    violation: U4's module treats the record as rejected; the conformance fixtures fail
    source: FR4.2; FR4.4; contract-summary C6, C8
  - id: BR5.6
    statement: Preview data can never be part of a publish request.
    category: constraint
    applies_to: C3 and C4
    trigger: every validation of a publish request
    logic: >
      C3 has no field for an address map, a preview slug or a candidate marker.
      Negative fixtures that add imageAddresses, downloadAddresses or previewSlug to a publish request are refused as unknown properties.
      The candidate never reaches U8 or public storage.
    violation: the negative fixture is accepted, so the schema test fails
    source: FR6.2; PB-12; unit-of-work constraint 3; ADR-008

  - id: BR6.1
    statement: Modules in the back-end package interact only through the U1 ports.
    category: constraint
    applies_to: U3, U4, U5, U9, U10 modules and the U1 ports module
    trigger: every CI run (the boundary test)
    logic: >
      No module reads another module's collections or private state directly; only the ports cross between modules.
      The U1 ports module imports nothing from U3 to U11.
      A reverse call (a lower-level unit calling a unit that depends on it) goes through a U1 port, with the implementation supplied by the depending unit.
    violation: the boundary test fails and names the import or the collection
    source: contract-summary C7 Rules "No database sharing"; unit-of-work constraint 7 and "Call Direction Inside the Back End"; ADR-012
  - id: BR6.2
    statement: Each port has one provider, named consumers, and a conforming fake.
    category: constraint
    applies_to: UnitOfWork, RouteRegistry, RepositoryCatalogPort, LinkCheckClientPort, ProjectsPort, AttachCheckPort, MediaPort, AssistantPort, PublicationPort
    trigger: every CI run
    logic: >
      Provider and consumers are as in the port catalogue of entities.md, which follows the approved "Call Direction Inside the Back End" table and the C7 consumer notes (for example: AttachCheckPort is declared for U3 and implemented by U4; ProjectsPort is provided by U3 and consumed by U5, U9, U10; RepositoryCatalogPort is consumed by U5 and U9).
      The approved table has no call from U3 to U5 or U9 beyond route registration, so AssistantPort lists only U10 (through export_records) as a consumer. PublicationPort lists U10 and, for one read only, U3. That read is the derived status in the project list (C1 "status composed from U9"), the one place U3 needs a publication fact; there U3 reads PublicationPort.statuses only when U9 has registered it, and with no U9 every project reports the derived status Draft, which is what ADR-003 gives when no publication record exists.
      U1 ships a fake of each port that satisfies the Protocol under the strict type check.
      ContentBackup (U10) reads other modules only through export_records of ProjectsPort, MediaPort, AssistantPort and PublicationPort.
    violation: the type check or the port-catalogue test fails
    source: contract-summary C7; unit-of-work "Call Direction Inside the Back End"; ADR-009
  - id: BR6.3
    statement: Guard methods work inside the caller's transaction.
    category: constraint
    applies_to: ProjectsPort.revision_guard, lineup_guard, release_featured_slot
    trigger: ADR-012 acceptance; ADR-004 commit; take-down
    logic: >
      Each guard takes the caller's UnitOfWork and performs its read or write only through it, never through its own connection or transaction.
      Acceptance and commit each run inside one transaction.
      Each module writes only its own records.
      The fake unit of work used in the contract test records every write and rejects a write made outside it.
      If a later step of the acceptance or the commit fails after a guard has written, the unit of work rolls back, and none of the guard's writes remains (ADR-012: the acceptance steps are atomic).
      Rollback test: a guard succeeds, a later step raises, and the fake reports zero committed writes; the same sequence without the failure commits all of them.
    violation: the guard test fails when a write happens outside the supplied unit of work, or when a write survives a failed later step
    source: contract-summary C7 Rules "Transactions"; ADR-012; ADR-004; unit-of-work constraint 7
  - id: BR6.4
    statement: Until U4 provides the attach check, every attachment is refused.
    category: authorization
    applies_to: AttachCheckPort (declared for U3, implemented by U4)
    trigger: U3 attaches an image or file before U4 is registered
    logic: >
      U3 ships a default AttachCheckPort that refuses every attachment for any asset, project and kind.
      A decision is accepted only when it is an explicit "attachable" result; a missing implementation or an unrecognised decision is a refusal.
      U4's implementation accepts only an asset that is validated and was uploaded for the same project.
    violation: the default-refusal test fails if any attachment is accepted without U4
    source: contract-summary C7 Rules "Fail-closed attach"; unit-of-work "Call Direction Inside the Back End"; FR4.8
  - id: BR6.5
    statement: Repository facts fail closed.
    category: constraint
    applies_to: RepositoryCatalogPort.access_facts
    trigger: U9 prepares a ticket
    logic: >
      Visibility is one of public, PRIVATE or unconfirmed.
      Any GitHub error, rate limit or rename yields unconfirmed, with no name, URL or licence in the facts.
      Only a repository confirmed public carries a name, URL and licence.
      The facts that U9 freezes into a ticket come only from access_facts, LinkCheckClientPort.check and MediaPort.attachment_inventory, called during preparation.
    violation: the fixture test fails if an unconfirmed fact carries a name, URL or licence
    source: FR4.10 (fail closed); contract-summary C7 Rules "Facts frozen at preparation"; ADR-012
  - id: BR6.6
    statement: The host works without the modules that register into it.
    category: constraint
    applies_to: U3 host assembly
    trigger: every CI run
    logic: >
      U3 does not import U4, U5 or U9.
      An assembly with no module registered serves GET /health and U3's own routes, its attach check refuses (BR6.4), and the project list reports the derived status Draft (BR6.2).
      Registering a module adds its documented routes and nothing else.
    violation: the assembly test fails if the host needs another module to start
    source: unit-of-work "Call Direction Inside the Back End"; unit-of-work-dependency (graph acyclic)

  - id: BR7.1
    statement: Private storage keys follow one layout, built and parsed by one set of functions.
    category: constraint
    applies_to: C8 key layout
    trigger: any code that names a private storage key
    logic: >
      The prefixes are incoming/{assetRef}/upload, originals/{assetRef}/original.{ext}, derivatives/{assetRef}/{variant}.{format}, files/{assetRef}/file.{ext} and results/{assetRef}.json.
      assetRef matches ^ast_[A-Za-z0-9]{16,32}$ and equals the MediaAsset assetId.
      U1 provides the builders and parsers; every unit builds and reads keys through them.
      Parsing a built key returns the same parts, and a string that is not a built key does not parse.
      Writers and readers are as in the layout table: nobody but restore and backup reads originals/.
    violation: the round-trip and rejection tests fail
    source: contract-summary C8; R-07
  - id: BR7.2
    statement: The variant rule has one definition.
    category: calculation
    applies_to: image derivatives (U4 produces, U9 lists, U8 validates and writes, U7 writes srcset)
    trigger: any use of an image width
    logic: >
      Given the primary image's pixel width W, the variants are every width in {480, 960, 1600} that is at most W.
      IF W is below 480 THEN the only variant is w480, encoded at width W with no upscaling.
      Each variant exists in both webp and jpg, so an image has 2, 4 or 6 derivative keys.
      The boundary fixtures cover W of 1, 479, 480, 481, 959, 960, 961, 1599, 1600 and 1601.
    violation: the boundary test fails in either language
    source: contract-summary C8 "Variant rule"; FR4.2
  - id: BR7.3
    statement: The file-type table is a single total mapping.
    category: constraint
    applies_to: C6 detectedType, C2 fileType, C8/C9 ext, public content type
    trigger: any conversion between those values
    logic: >
      pdf to PDF to pdf, skp to SKP to skp, fcstd to FCStd to fcstd, dxf to DXF to dxf, stl to STL to stl, zip to ZIP to zip, vsdx to VSDX to vsdx.
      Every file type has the public content type application/octet-stream unless NFR Design fixes another.
      The image types jpeg, png, webp and heic produce derivatives only and never appear as a fileType.
    violation: the table test fails if a value maps to none or to two, or an image type maps to a fileType
    source: contract-summary C8 "File types"; FR4.4; FR4.9
  - id: BR7.4
    statement: Each public page path maps to exactly one stored object key.
    category: constraint
    applies_to: C9 page paths
    trigger: U7 emits a page; U8 writes it
    logic: >
      "/" maps to index.html; "/work/" to work/index.html; "/work/{slug}" to work/{slug}/index.html; "/category/{slug}" to category/{slug}/index.html; "/404.html" to 404.html; "/category-404.html" to category-404.html.
      Pages are stored with content type text/html; charset=utf-8.
      No other page path is valid.
    violation: the path test fails on an unmapped or doubly mapped path
    source: contract-summary C9 "Page paths and stored objects"; FR9.1 to FR9.3; FR7.4
  - id: BR7.5
    statement: The public routes and the public paths of images and downloads are fixed.
    category: constraint
    applies_to: C9 public routes; the publication asset resolver
    trigger: U7 emits a link target; U8 computes object paths
    logic: >
      The public routes are /, /work/, /work/{slug}, /category/{games|astronomy|woodworking|software}, any unknown path (404), /media/{assetRef}/{variant}.{format}, /files/{assetRef}/{downloadName} and /assets/{name}.{hash}.{ext}.
      The category page is 404 when the category has no live exhibit.
      The publication resolver maps an image reference to /media/{assetRef}/{variant}.{format} and a download reference to /files/{assetRef}/{downloadName}.
      Header requirements (NFR15) belong to U2 and U7 and are not defined here.
    violation: the path test fails if U7's link targets and U8's computed paths differ for the same fixture
    source: contract-summary C9; FR9.1 to FR9.5; FR10.3
  - id: BR7.6
    statement: The download name is one deterministic, linear-time rule.
    category: calculation
    applies_to: C9 downloadName used by U7 (link targets) and U8 (object keys and headers)
    trigger: any computation of a download name
    logic: >
      downloadName is slug(label) + "." + ext.
      slug folds ASCII upper-case letters to lower case, replaces every run of characters outside [a-z0-9] with one "-", trims "-" from both ends, cuts to 60 characters, and trims "-" from the end again.
      An empty result becomes "download".
      ext comes from the file-type table (BR7.3).
      The rule is a single pass over the input with no backtracking pattern that can grow faster than linear, and works on any length of label.
      The result contains only [a-z0-9-] and one ".", so it is safe in a Content-Disposition header, an object key and a path.
      The same fixtures run in Python and TypeScript with identical results, including non-ASCII letters (which become "-").
      The shared fixtures include the inputs where Unicode lower-casing differs from the ASCII fold: U+0130 (capital I with dot above) and U+212A (Kelvin sign) must each become "-", not "i" or "k".
      The slice's variants.ts uses Unicode toLowerCase, so it differs on those two inputs. This rule supersedes the slice's behaviour (BR9.6); it does not keep it.
      Timing: the test is written against a named constant DOWNLOAD_NAME_BUDGET in the contract register. The approved requirements give no figure for this function, so the value is set by NFR Design; until then the test asserts scaling instead: it times inputs of 25,000 and 100,000 characters (a factor of four), takes the median of five runs each, and requires the 100,000-character time to be at most eight times the 25,000-character time plus a 5 millisecond floor. A quadratic implementation would take about sixteen times as long and fail.
    violation: the fixture test fails on a differing result; the timing test fails if the run time over a label of 200,000 characters (all hyphens, and alternating hyphens and letters) exceeds DOWNLOAD_NAME_BUDGET, or the scaling check fails
    source: contract-summary C9 "Download name"; FR4.4; FR4.9

  - id: BR8.1
    statement: The renderer interface is exactly the approved surface.
    category: constraint
    applies_to: C11 (generated TypeScript types)
    trigger: every change to C11; every CI run
    logic: >
      The public surface is render(snapshot, options) returning RenderOutput, with RenderOptions (mode public or preview, resolveAsset, previewSlug), RenderedPage (path, status 200 or 404, html), RenderOutput (contractVersion "1.0", pages, requiredImages, requiredDownloads, staticAssets), AssetResolver and RenderInputError.
      The input type is the C2 type of the same version.
      Nothing else is exported as part of the contract.
    violation: the type-surface test fails on an added or removed export
    source: contract-summary C11; unit-of-work constraint 2
  - id: BR8.2
    statement: The renderer validates its input before producing any output.
    category: validation
    applies_to: render()
    trigger: every call
    logic: >
      The snapshot is validated against C2 and the semantic rules S1 to S7 (BR2.2).
      mode preview requires a previewSlug that names an exhibit in the snapshot.
      IF anything is invalid THEN throw RenderInputError before any output.
      U8 maps the error to invalid, and U11 shows the error instead of a preview.
    violation: the negative fixtures fail the contract test if any output is produced
    source: contract-summary C11 "Errors"; C4
  - id: BR8.3
    statement: The renderer's required-asset lists equal what the manifest rules compute.
    category: constraint
    applies_to: RenderOutput requiredImages and requiredDownloads
    trigger: U8 compares after rendering
    logic: >
      requiredImages is exactly the variant rule's set for every image in the snapshot, in both formats.
      requiredDownloads is exactly one entry per attachment with its downloadName.
      Both equal what C3 check (d) computes.
    violation: U8 returns invalid on any mismatch (test C3-K17 and the consistency fixture)
    source: contract-summary C11 "Consistency"; C3 (d)
  - id: BR8.4
    statement: The asset resolver is pure and synchronous, and the two uses differ only in the resolver.
    category: constraint
    applies_to: AssetResolver
    trigger: every render
    logic: >
      The resolver maps an image reference (assetRef, variant, format) or a download reference (assetRef, downloadName) to an address string, with no input or output.
      Publication uses the C9 public paths (BR7.5).
      Preview uses the two maps of C4 (BR5.2).
      A resolver that cannot resolve a reference throws RenderInputError.
    violation: the resolver conformance test fails
    source: contract-summary C11, C4; unit-of-work constraint 2; ADR-008
  - id: BR8.5
    statement: U1 supplies the renderer's conformance fixtures; U7, U8 and U11 run them.
    category: policy
    applies_to: C11 and the C2 fixtures
    trigger: every CI run of U7, U8 and U11
    logic: >
      The shared fixtures cover: Node and headless-browser parity (identical RenderOutput for the same fixtures and resolver); purity (network, timers and storage stubbed to throw); the preview marking present only in preview mode; and the PB-02 scan of public output.
      U1 holds the fixtures and expected results; the runners belong to U7, U8 and U11.
    violation: a runner that omits a shared fixture fails the fixture-completeness check
    source: contract-summary C11 contract tests; unit-of-work constraint 2; FR6.1

  - id: BR9.1
    statement: Python and TypeScript types are generated from the specs and must compile.
    category: policy
    applies_to: generated types and the U1 generators
    trigger: every CI run; every change to a spec
    logic: >
      One generator run produces the Python types and the TypeScript types from the same specs.
      Generated files are marked as generated and are never edited by hand.
      The Python output passes mypy and the TypeScript output passes tsc --noEmit under strict settings.
    violation: CI fails and names the file that does not compile
    source: bolt-plan B01 DoD; contract-summary Contract Ownership Rules 1; team practice (Code Style)
  - id: BR9.2
    statement: Generated output must equal a fresh generation, and no duplicate definition may exist.
    category: validation
    applies_to: generated types and every file outside U1
    trigger: every CI run
    logic: >
      Regenerating from the specs gives byte-identical output to what the repository holds (the drift check).
      No JSON Schema or OpenAPI document outside U1 carries a U1 $id or title.
    violation: CI fails and shows the drift or the duplicate
    source: contract-summary Contract Ownership Rules 1; Q9
  - id: BR9.3
    statement: The Python and TypeScript validators give the same verdict on every fixture.
    category: validation
    applies_to: C2 to C6 validators in both languages
    trigger: every CI run
    logic: >
      Each fixture file in U1 declares one expected verdict per validation mode (BR1.6): strict (accept or refuse) and tolerant (accept or refuse, or not applicable for a strict contract), and, for a refusal, the rule or test id it violates.
      For a strict contract the two verdicts are always equal. For a lenient contract they may differ: a message that adds a field is refused in strict mode and accepted in tolerant mode.
      Both language validators must give the declared verdict in each mode, so the one-verdict-per-fixture comparison holds per mode and per language.
      An invalid snapshot (an extra field, or a GitHub link in links) is refused by both, in strict mode.
    violation: CI fails and names the fixture, the language and the verdict
    source: bolt-plan B01 DoD and Demo; Contract Ownership Rules 6
  - id: BR9.4
    statement: Fixtures and specs contain placeholders only.
    category: policy
    applies_to: every fixture and spec in U1
    trigger: every CI run
    logic: >
      Text is placeholder text, hosts use the reserved .invalid domain, and identifiers are generated.
      No real project content, no withheld value (including the withheld live URL) and no secret, token or key appears.
      The fixtures' image data is a tiny synthetic image.
    violation: the repository secret scan or the withheld-value check fails
    source: FR10.7; NFR3; project rules (no secrets, no private material); Q10
  - id: BR9.5
    statement: One shared contract-test harness runs for both sides of every contract.
    category: policy
    applies_to: the U1 harness and each unit's CI
    trigger: every CI run
    logic: >
      The harness runs from a clean checkout with only the documented prerequisites.
      It holds the fixtures, the expected verdicts, the reference host with its spy handlers (BR4.13), and the fakes of the ports.
      Each unit runs the cases for every contract it provides and every contract it consumes.
      The harness uses no live paid service and no production system.
    violation: a unit's CI fails when a contract it provides or consumes has no case run
    source: "contract-summary Contract Ownership Rules 6; team practice (Testing Posture: runnable, no live paid services); bolt-plan B02 Demo"
  - id: BR9.6
    statement: The local definitions in U0 are replaced by U1's, not extended.
    category: policy
    applies_to: U0's slice C2 schema, variant and download-name helpers, output scan and snapshot validator
    trigger: the owning units' Bolts (U3, U7, U8, U9, U11)
    logic: >
      U1 is the only definition (BR1.1).
      When an owning unit takes over slice code, it imports the U1 generated type or helper and deletes the local copy.
      The U1 conformance fixtures also run against the U0 local versions while they exist, so any difference in verdict is found at once.
      S1 to S3 stay on the slice branch and are never merged (Amendment D1).
    violation: the duplicate-definition check (BR9.2) fails once a local copy remains in merged code
    source: contract-summary preamble (Amendment D1); unit-of-work U0 constraints; Q8
```

## Rules Summary

| Rule | Summary | Source |
|---|---|---|
| BR1.1 | One authoritative definition per contract; no hand copies | Ownership rule 1 |
| BR1.2 | Specs parse, declare `$schema`/`$id`, validate, and hold no null-valued key | Ownership rule 6 |
| BR1.3 | C2, C3, C4 closed at every level | C2; constraint 6 |
| BR1.4 | Snapshot allow-list equals the FR4.10 allow-list | FR4.10; ADR-002 |
| BR1.5 | A public field addition is a version change with review | Ownership rule 3 |
| BR1.6 | Strict and tolerant validation modes; unknown version refused | C3-K10; Ownership rules 3, 4 |
| BR1.7 | New snapshot version cascades; consumers accept first | Ownership rule 3 |
| BR1.8 | Semantic versions; breaking-change process | Ownership rules 2, 5 |
| BR1.9 | Lenient contracts ignore additive response fields | Ownership rule 4 |
| BR1.10 | Every request body is closed | C1 notes |
| BR1.11 | One contract register; version states change in order | Ownership rules 1, 3 |
| BR2.1 | Structural rules enforced by the schema | FR4.3; FR4.10 |
| BR2.2 | Semantic rules S1 to S7 from one shared check | C2 S1 to S7 |
| BR2.3 | S6a, S8, S9, S10 are U9's alone | C2 table |
| BR2.4 | Snapshot never carries a private address | unit-of-work U1; FR6.2 |
| BR2.5 | 5 MB request bound; SNAPSHOT_TOO_LARGE | C2 size bound |
| BR3.1 | Operation id and fencing token; when the fence is recorded; equal and invalid cases | C3; ADR-004 |
| BR3.2 | Four result statuses; U9 decides | C3 |
| BR3.3 | Manifest lists exactly the referenced assets | R-07 (a) |
| BR3.4 | Manifest keys equal the required keys byte for byte | R-07 (b), (c) |
| BR3.5 | IAM prefix limits held in U1 as data | R-07 layer 1 |
| BR3.6 | Public paths computed from the snapshot, not the request | R-07 (d) |
| BR3.7 | R-07 test matrix is mandatory; fence cases added | C3 tests |
| BR3.8 | A stalled attempt is refused at the conditional write | ADR-004 |
| BR4.1 | One valid OpenAPI 3.1 document; closed code list | C1 |
| BR4.2 | Registry equals document | R-08 test (1) |
| BR4.3 | One pipeline, no opt-out | R-08; FR1.2 |
| BR4.4 | Non-owner never reaches a handler | R-08 tests (2), (3) |
| BR4.5 | Shared Error body; documented no-body exception | R-18 point 2 |
| BR4.6 | Closed (status, code) table | Errors table |
| BR4.7 | Pipeline responses declared once | C1 notes |
| BR4.8 | OpenAPI/handler agreement test | R-18 point 3 |
| BR4.9 | Exactly three storage channels | R-18 point 1 |
| BR4.10 | If-Match on draft and line-up edits | FR3.4 |
| BR4.11 | Fixed health body | C10 |
| BR4.12 | U11 reaches U4, U5, U9 only through U3 | R-08 |
| BR4.13 | B02 reference host; checks deferred to the real hosts | R-08; R-18 |
| BR5.1 | Preview payload composition, strict | C4 |
| BR5.2 | Addresses only in the two maps; missing means no preview | C4 |
| BR5.3 | PREVIEW_BLOCKED with blockers | C4 |
| BR5.4 | Link-check request and result | C5; FR10.5 |
| BR5.5 | Upload result consistent with key layout | C6 |
| BR5.6 | Preview data never in a publish request | FR6.2 |
| BR6.1 | Modules interact only through ports | C7 |
| BR6.2 | Port catalogue with provider, consumers, fakes | C7 |
| BR6.3 | Guards work in the caller's transaction | ADR-012 |
| BR6.4 | Attach check refuses until U4 provides it | C7 |
| BR6.5 | Repository facts fail closed | FR4.10 |
| BR6.6 | Host works without registering modules | unit-of-work |
| BR7.1 | Key layout with one builder/parser | C8 |
| BR7.2 | One variant rule | C8 |
| BR7.3 | Total file-type table | C8 |
| BR7.4 | Page path to object key | C9 |
| BR7.5 | Public routes and resolver paths | C9 |
| BR7.6 | Deterministic linear-time download name | C9 |
| BR8.1 | Renderer surface exactly as approved | C11 |
| BR8.2 | Validate before output; RenderInputError | C11 |
| BR8.3 | Required lists equal manifest computation | C11; C3 (d) |
| BR8.4 | Pure resolver; two uses differ only by resolver | C11; C4 |
| BR8.5 | Shared renderer fixtures run by U7, U8, U11 | C11 tests |
| BR9.1 | Generated types compile | B01 DoD |
| BR9.2 | No drift, no duplicate definition | Ownership rule 1 |
| BR9.3 | Both validators agree on every fixture | B01 Demo |
| BR9.4 | Placeholders only | FR10.7; NFR3 |
| BR9.5 | One harness for both sides | Ownership rule 6 |
| BR9.6 | U0's local definitions are replaced | Amendment D1 |

## Assumptions & Open Questions

- **Lenient versus closed schemas.** The approved C5 and C6 schemas are closed (`additionalProperties: false`) with a constant `schemaVersion`, while Contract Ownership Rule 4 calls those contracts lenient. BR1.6 and BR1.9 reconcile them without changing either: strict mode (the published closed schema) is for producers, fixtures and strict contracts, and a tolerant view generated from the same spec is for consumers of lenient contracts.
- **Download name edge cases.** The approved text says the label is "lowercased", runs are replaced, hyphens are trimmed and the result is cut to 60 characters. BR7.6 states this precisely so that Python and TypeScript agree byte for byte: lower-casing is ASCII-only, and hyphens are trimmed again after the cut so a name never ends in "-". The slice's `variants.ts` also trims after the cut, but it lower-cases with Unicode `toLowerCase`, which differs from the ASCII fold on U+0130 and U+212A. U1's rule supersedes the slice there, and both inputs are in the shared fixtures.
- **Disclosed tightenings.** These go beyond the approved text, are testable, and change no approved boundary: the two validation modes (BR1.6); an invalid request never advances the fence and is answered invalid whatever its token, and every write is conditional on the fence (the equal-token case is not a tightening: it is an allowance for duplicate delivery of the same operation id), with test cases C3-F2 to C3-F5 added to the approved list (BR3.1, BR3.7, BR3.8); U8 also refuses an over-size request (BR2.5); 500 is declared once as a shared response (BR4.5); the reference host and the evidence levels of the agreement test (BR4.8, BR4.13); the address-field register (BR4.9); and the contract register with its lifecycle check (BR1.11).
- **Tracked clarification owed to the contract summary.** The approved C9 "Download name" text says the label is lowercased and the slug is trimmed and then cut to 60 characters. BR7.6 needs one line added to `contract-summary.md` at its next change: lower-casing is an ASCII-only fold, and hyphens are trimmed again after the cut. This design does not edit the approved summary; until the line is added, BR7.6 is a disclosed, testable tightening of that text.
- **Residual fence window.** BR3.8 states that the fence check and the public write cannot be one atomic step across two stores. NFR Design and Infrastructure Design choose the mechanism that narrows the window.
- **Project list status.** The approved C1 composes project status from U9, but the approved call-direction table has no U3 to U9 call. BR6.2 resolves this without a new edge: U3 reads `PublicationPort.statuses` only when U9 is registered, and reports Draft otherwise, as ADR-003 derives when no publication record exists.
- **Draft and patch shapes.** The full `Project`, `ProjectPatch` and inventory shapes are fixed in the Functional Design of U3, U9 and U11. BR1.10 closes them once they exist and lists them as pending until then.
- **Thresholds.** The timing budget in BR7.6, the address lifetimes and the per-attempt budget are set in NFR Design and test configuration, not here.
