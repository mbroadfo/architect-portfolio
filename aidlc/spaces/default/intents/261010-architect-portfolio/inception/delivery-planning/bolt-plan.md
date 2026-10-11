# Bolt Plan (revision 6)

**Inputs:**
- requirements;
- mockups (the approved Refined Mockups and prototype);
- components and ADR-001 to ADR-012;
- unit-of-work, unit-of-work-dependency and unit-of-work-story-map;
- contract-summary (C1 to C11);
- team-practices;
- Michael's Request Changes at the Delivery Planning gate (2026-10-11);
- the independent advisory reviews of revisions 2 to 5 (`reviews/`).

A **Bolt** is one build pass over part of a unit of work. It ends in working, tested code merged through one pull request, as one squash commit. A **walking slice** is the smallest piece of real code that runs end to end.

**What this revision does.** The 11 units, their contracts and the technical scope are unchanged. Only delivery changes, aiming for working software earlier with the same engineering discipline:

1. **A walking slice first.** U0, a delivery-only unit, shows a project being created, saved, previewed and published as a static page. It runs locally on fake or isolated dependencies (D1).
2. **CI from the first Bolt, and a real preview deploy path early.** S0 builds the baseline CI. B05a, in U2, builds the per-pull-request preview deploy path, so "verify in preview before merge" works from M2 instead of near the end.
3. **The Studio user interface early.** A minimal Studio page arrives in the slice. The full Studio (U11) moves from 11th to 6th in the build order.
4. **Every stop is a meaningful checkpoint.** Each unit's engine checkpoint presents its demonstration, progress, review recommendations and every Bolt of the unit, listed individually with its evidence. Michael's answer covers the whole unit: Approve, or Request Changes naming any Bolt he does not accept (D2-A). Options that cut the number of stops further are listed with their trade-offs, for Michael to choose (D2).
5. **Parallel engine execution was evaluated and is not recommended now.** The exact changes it would need are listed.
6. **Unchanged safeguards:**
   - independent security review for every 🔒 Bolt;
   - preview verification before merge for every 🧪 Bolt;
   - Michael's authorization for every merge;
   - separate approval for spending and deployment.

## Owner Decisions This Plan Needs

Approving revision 6 approves the plan. Each decision below then takes effect only as described, and nothing becomes effective by implication.

**D1 — Reopen Units Generation for a delivery-only amendment.**

The amendment makes these changes and no others:
- **(a)** Add U0 `walking-slice` (kind `service`), listed first.
- **(b)** Ordering-only edges U1 → U0 and U2 → U0, so the engine builds U0 first. The slice's real data flow runs the other way: it consumes the approved C2 schema.
- **(c)** Ordering-only edges U4 → U11, U5 → U11 and U6 → U11, so the Studio is built before those units.
- **(d)** The listing order follows the new sequence.
- **(e)** U0 rows are added to the story map as a supporting unit.

The components, contracts, boundaries and FR traceability targets are not changed.

**How the ordering-only edges are recorded.** The engine's edge block has only `depends_on`, so the five ordering-only edges appear there like any other edge. `unit-of-work-dependency.md` marks each of them **ordering-only** in its "Why Each Edge Exists" table, and its parallel-development sets are recomputed. Its definition of "depends on" gains one sentence: an edge marked ordering-only fixes build order only and carries no integration dependency.

- **Process cost:** Units Generation is reopened through the engine, reviewed and re-approved. If the engine also reopens the later Inception stages, Contract Design (unchanged; U0 adds no contract) and this plan are re-presented for approval. That is at most three extra gates, once.
- **If declined:** no early slice. The first end-to-end run comes after U9, about 24 Bolts in, and the Studio stays last.

**D2 — How Bolts are approved: the gate model.**

The engine's Construction settings stay unit-major and serial. At Construction entry the engine asks one question: continue automatically, or review each checkpoint. The answer decides how Michael approves Bolts.

| Option | How Bolts are approved | Stops (estimate) | Policy changes | Recommendation |
|---|---|---|---|---|
| **D2-A: "Review each checkpoint" (gated)** | At each unit's engine checkpoint, the presentation lists every Bolt of the unit with its evidence (pull request, CI, 🔒 review, 🧪 preview). The engine offers one answer per unit:<br>• **Approve** approves every listed Bolt. That approval receipt is the record that decides what may merge.<br>• **Request Changes**, naming any Bolt Michael does not accept, sends the whole unit back. The Bolt is fixed or removed from the unit, and the checkpoint is presented again.<br>There is no partial approval. This is exactly "Michael's own answer at an AI-DLC gate" (team practice; `project.md` Forbidden) | About 26: 12 Plan Approvals, 12 unit checkpoints, 1 verification command, plus D1's re-approvals | None | **Recommended.** It meets the request without weakening any approval: every stop carries a demonstration and the unit's decisions together, and stacks stay within one unit |
| D2-B: "Continue automatically" with milestone reviews | The engine approves verified units without a human. Michael decides Bolts at six milestone reviews: questions the conductor asks and records with `log decision` and `log answer`, one line per Bolt | About 20 | `team.md` ("Code pull requests") **and** `project.md` Forbidden ("never merge … before the owner has approved the AI-DLC gate it belongs to") must be amended to accept a recorded milestone answer | Not recommended. It is a weaker form of approval than an engine gate, and a stop would be enforced by the conductor rather than the engine |
| D2-C: either of the above, with the Plan Approval guard turned off (`guard.plan-approval off`) | Unchanged | About 14 under D2-A, or 8 under D2-B | Michael's request in his own words, per the guard rules | Not recommended. Plan Approval catches design drift before code is written |

## Parallel Execution: Evaluated, Not Recommended Now

Michael asked whether independent implementation work can run on isolated branches without harming atomicity or traceability.

**What holds.** ADR-012 atomicity is safe under any of these options. It is a runtime property of the shared Python package and database, U3 and U9 are never built at the same time, and U4 and U5 own separate modules.

**Engine swarm** (stage-major iteration with swarm execution) builds the units of a dependency batch in parallel worktrees, with one records owner. Its problems:
1. **Landing granularity.** Swarm lands each **unit** as one squash commit, while team practice needs one per **Bolt**.
2. **Merge target.** `org.md` fixes the worktree base and merge target as `main`, and an integration branch would also be long-lived.
3. **Throughput.** Preview deployments run one at a time, and each 🔒 Bolt needs its own independent review session, so parallel coding would mostly queue.

**Independent agents in other harnesses** (which team practice already permits) could build a later unit early on an isolated branch. But that unit's AI-DLC design stages, Plan Approval and checkpoint would come later, in engine order, so its code would run ahead of its own records. That is a traceability gap.

**Recommendation.** Stay with unit-major serial execution. This is offered as an explicit choice: approving this plan keeps the current engine settings (unit-major, serial). Grouped Plan Approval, which asks one question for several units, exists only with stage-major iteration, so it does not apply here. Michael can choose swarm later; it would need:
- the engine setters `set-construction-iteration stage-major` and `set-construction-execution swarm`;
- `org.md` and `team.md` wording that picks either per-unit pull requests or an integration branch reset to `main` after every batch.

## How Bolts Land (traceability)

1. **One Bolt, one branch.** Each Bolt gets its own branch, named by its slug, and its own pull request, labelled with the Bolt ID. Inside a unit, each Bolt's branch is stacked on the previous one, so a stack is never deeper than the unit's Bolts (at most five). Merge order is build order, which is stack order.
2. **Merging.** After the unit checkpoint approves the Bolts, and once merges are authorized (E10) and preview verification has passed where 🧪 requires it, the approved pull requests merge one by one as squash commits. After each merge the next pull request is rebased onto `main`, and CI runs again on the rebased commit.
3. **Review records and rebases.** Team practice requires "a recorded review for its latest commit". S0 implements that check so that a rebase of an already-reviewed Bolt is accepted only if the change is provably identical (the same `git patch-id`), and every content change needs a new review. This is a **provisional design**: the CI Pipeline stage confirms it, and until then the stricter reading (a new review after any rebase) applies if Michael prefers it.
4. **A Bolt Michael does not accept.** He answers Request Changes at the unit checkpoint, naming it (D2-A). The Bolt is fixed, or removed from the unit and replanned, and the checkpoint is presented again. Nothing in the unit merges until the unit is approved.
5. **Merge decisions.** Recommended: a standing merge authorization, decided once (E10). Under it, the Bolts of an approved unit merge as soon as their evidence is clean (CI, 🔒 review, 🧪 preview), with no separate merge stop. If Michael prefers to decide merges each time, that adds about 12 stops (see "Human Stops").
6. **Before preview exists** (until B05a works and E2 is approved), the U1 and U2 Bolts wait in their unit stacks. That is the plan's one temporary deviation from the one-to-two-day branch rule, and it ends at M2. The slice does not wait at all, because it never merges (Phase A).
7. **Traceable throughout:** Bolt ID → branch → pull request → CI run → security review (bound to content) → unit checkpoint decision → squash commit on `main`.

## Definition of Done for Every Bolt

1. **Code and tests.** The code is complete, and the tests for each layer are written and run after it. Test names cite the IDs they verify.
2. **CI gates pass on the Bolt's pull request.** These are the aggregate required check built in S0:
   - format, lint and type check;
   - tests, with 80% line coverage;
   - build;
   - gitleaks;
   - dependency audit;
   - CodeQL;
   - the check that a security review is recorded for security-sensitive paths.
3. **Contract tests.** The contract tests for the contracts the Bolt touches pass. Until U1 exists, the slice validates against the approved C2 schema.
4. **🔒 Security review.** An independent AI security review is recorded on the pull request, bound to its content, with its blocking findings fixed, before the unit checkpoint.
5. **🧪 Preview verification.** The preview deployment, smoke checks and end-to-end checks pass before merge, through the B05a path once `preview` exists (E2).
6. **Approval and merge.** Michael approves the Bolt at its unit checkpoint (D2). It merges only under the merge authorization (E10).

## Phase A — Walking Slice (U0, four Bolts)

| Bolt | Slug | Scope | 🔒 | 🧪 |
|---|---|---|---|---|
| S0 | `u0-repo-and-ci-baseline` | See S0 below | 🔒 | |
| S1 | `u0-slice-projects-and-owner-check` | See S1 below (demonstration; not merged) | 🔒 | |
| S2 | `u0-slice-render-and-publish` | See S2 below (demonstration; not merged) | 🔒 | |
| S3 | `u0-slice-studio-page` | See S3 below (demonstration; not merged) | 🔒 | |

**S0 `u0-repo-and-ci-baseline`** builds:
- the repository layout: the Python back-end package host, the TypeScript workspace, `.editorconfig`, and the lint and format configuration;
- the **baseline CI**:
  - one aggregate required check that runs on every pull request and runs or skips each component's checks by path;
  - format, lint, type and test with coverage;
  - gitleaks, the dependency audit and CodeQL;
  - the content-bound security-review check;
  - a build-time guard that fails any non-local artifact containing a fake identity provider or its configuration. It is in S0 so that it is enforced on `main` for every later unit.

  All of this is free for a public repository.
- the first, **provisional** list of **security-sensitive paths** and the location of the review records. The CI Pipeline stage finalizes both. The paths are named now from `unit-of-work.md`: OwnerAccess and the route registry; the Projects guards; the upload processor; the link checker; publication; the publisher; workflows; Terraform.

Michael registers the aggregate check as required in the `main` ruleset (E13); agents never edit rulesets.

**S1 `u0-slice-projects-and-owner-check`** builds:
- a local stack: a MongoDB container and a **local-only** fake identity provider;
- creating and saving a project with optimistic revisions;
- an owner check on issuer and subject.

Its tests:
- unauthenticated and non-owner calls are rejected;
- the S0 build-time guard, applied to the slice's own build.

**S2 `u0-slice-render-and-publish`** builds:
- a thin React static renderer;
- Publish only on explicit confirmation: the candidate is frozen, validated against the approved C2 schema, and the static files are written to a local public folder served locally.

Its tests:
- nothing is published without Publish;
- an allow-list scan finds no private material;
- the snapshot rejects fields outside the allow-list.

**S3 `u0-slice-studio-page`** builds:
- a minimal Studio page in React: create, edit title and summary, preview in a sandboxed frame using the same renderer, and Publish;
- `make slice-check`, a scripted end-to-end run.

**Slice boundaries.** The slice:
- is demonstrated locally at M1;
- uses placeholder data and a bundled fixture image only, with no withheld values;
- is never deployed anywhere: not to preview, and not to production.

**Only S0 merges.** S0 (the CI baseline and repository layout) merges to `main` after its unit checkpoint. S1 to S3 are **demonstration Bolts**: they stay on the branch `slice/walking-slice` as the reference implementation and are never merged or deployed. Their pull requests are opened as drafts labelled "demonstration, do not merge", so CI and the security reviews are recorded on them, and they are closed unmerged when the branch is archived at M5. This branch is deliberately long-lived, from M1 to M5. It is the one exception to the short-lived-branch rule; it is acceptable because it never merges. They therefore carry no 🧪 marker, and team practice's "verify in preview before merge" does not apply to them. Their 🔒 security review still runs before M1.

U3, U7, U8, U9 and U11 bring the slice's code into `main` only through their own Bolts. Each of those Bolts cites the slice commit it starts from, and passes its own review and preview verification. U0's own design stages run first and are deliberately light, with one Plan Approval.

**Retiring the slice.** The slice branch is archived at M5, once every part has a reviewed counterpart on `main`.

| Slice part | Replaced by | At |
|---|---|---|
| Projects and owner check | U3 | M3 |
| Renderer | U7 | M3 |
| Studio page | U11 | M3 |
| File writing | U8 | M5 |
| Publish | U9 | M5 |

No slice code reaches `main` except through these owning units' Bolts.

## Build Order and Milestones

The build order is the engine's dependency order after D1: U0, U1, U2, U3, U7, U11, U4, U5, U6, U8, U9, U10.

Under D2-A, every unit ends with its engine checkpoint. It carries the unit's demonstration, progress, review recommendations and every Bolt listed individually with its evidence, and Michael answers for the whole unit (Approve, or Request Changes naming a Bolt). The milestones below are the **reporting rhythm**: summary progress reports that group what the units have delivered, without extra approval stops.

| Milestone | Units | Bolts | What Michael can run or see |
|---|---|---|---|
| **M1 — Walking slice** | U0 | S0 to S3 | The slice locally, from its branch: create, save, preview, publish, open the static page. CI is in place on `main` (S0). **The verification command is chosen here** (below) |
| **M2 — Foundation and preview path** | U1, U2 | B01 to B05, B05a | The formal U1 contracts. Terraform plan through OIDC (needs E1). **The per-pull-request preview deploy path** (B05a; creating preview needs E2). From here, 🧪 Bolts are verified in preview and merged after their unit's approval |
| **M3 — Real core and Studio** | U3, U7, U11 | B06 to B09, B17 to B18, B27 to B29 | The real owner access, Projects, renderer (Node/browser parity) and **Studio user interface** against the real API, in preview. The Studio calls only real endpoints; upload, suggestion and publication show "not available yet" until their units land (see "Studio integration ownership") |
| **M4 — Content pipeline** | U4, U5, U6 | B10 to B16 | Isolated upload processing, suggestions with the fake provider, the SSRF-safe link checker; the Studio on the real endpoints |
| **M5 — Publication** | U8, U9 | B19 to B25 | The real publisher and publication, with tests CS-01 to CS-20 and PB-01 to PB-12. The slice is retired |
| **M6 — Release candidate** | U10 | B26 | Nightly export and a tested restore. The Build and Test stage then runs the end-to-end Playwright journeys (formerly B30) in preview |

**B05a `u2-preview-deploy-path`** (🔒 🧪, M2) builds:
- the GitHub Actions job that deploys each pull request's build to `preview` through the preview OIDC role: Terraform apply against the preview state, the site and the function deploy, and the smoke checks;
- serialization with a concurrency group (team practice).

Creating `preview` needs Michael's approval (E2). Whether agents may deploy pull-request builds there is part of the same decision. The CI Pipeline stage later consolidates this job with the rest of the pipeline.

**How B05a verifies itself and its unit.** B05a's own pull request is the first deployment it performs: its workflow applies the U2 stack (B03 to B05a) to the newly created `preview`.

At M2 no function or rendered site exists yet, so the smoke checks then cover only what U2 provides:
- the CDN serves a placeholder page with the NFR15 headers;
- the preview gate and `noindex` work;
- 404 routing to `404.html` and `category-404.html` works;
- the Terraform plan is clean after the apply.

That run is the 🧪 evidence for B04, B05 and B05a at U2's checkpoint. The function and site smoke checks join the same job when U3 (health, M3) and U7 and U8 (pages, M3 and M5) land.

**If E1 or E2 is not ready by U2's checkpoint.** U2's checkpoint presents B04 and B05a as "not yet verifiable". Michael can approve the unit so that Construction continues, with those Bolts' merges held until E1 and E2 make them verifiable, or he can wait. Construction is unit-major, so the next unit starts only after U2 is approved.

**Studio integration ownership.** U11 ships **no fakes in product code**. Its client always calls the real Studio API, and contract fakes (mock handlers built from the C1 OpenAPI) exist only in its tests. Ownership of the integration:
- **U11 (M3)** is verified in preview against the real U3. Its B28 and B29 Definitions of Done list the endpoints still pending.
- **U4, U5 and U9** each own the switch for their own endpoints. Each unit's last Bolt (B12, B14, B25) adds to its Definition of Done: "the U11 consumer contract tests for this unit's endpoints pass against the real implementation in preview, and the Studio flow that uses them is demonstrated".
- **B29's Studio publish flow** is security-reviewed again against the real U9 as part of B25's 🔒 review.
- The **Build and Test** end-to-end journeys confirm the whole loop.

**Verification command (proposed at M1).** The engine reuses one intent-wide command at every unit checkpoint, so it must cover every unit, not only the slice. Proposed: `make check`, which runs every present unit's test suites plus the slice check, and grows as units land. Michael approves it once, through the engine's command question.

**Critical path.**
- **E1 (AWS bootstrap)** is needed by B04 and B05a in M2. If it is not ready, B04 is delivered with local `terraform validate` and its plan job in place, and preview verification waits.
- **E2 (`preview`)** is needed before any 🧪 Bolt merges. Approving it at M2 lets merges start there.

## Bolt Sequence (B01 to B29 and B05a, with milestone)

Scope, 🔒 and 🧪 markers and early-proof labels are unchanged from revision 1. B05a is new: the preview deploy path. B30 (end-to-end journeys) moves to the Build and Test stage.

| Bolt | Unit | Slug | Scope | 🔒 | 🧪 | Milestone |
|---|---|---|---|---|---|---|
| B01 | U1 contracts | `u1-contract-schemas` | C2 to C6 JSON Schemas; generated Python and TypeScript types; a U1 self-check (parse, `$schema`, no null keys) |  |  | M2 |
| B02 | U1 contracts | `u1-api-and-ports` | C1 OpenAPI; C7 ports; C8 key-layout and variant rules; C9 path and download-name rules; C11 types; shared contract-test harness | 🔒 |  | M2 |
| B03 | U2 platform | `u2-foundation-modules` | Terraform modules and the `preview` and `production` roots, with no resources applied; `fmt`, `validate`, tflint |  |  | M2 |
| B04 | U2 platform | `u2-oidc-ci-plan` | CI job running `terraform plan` through the read-only OIDC role (**early proof: CI passes using OIDC; Terraform plan is clean**) | 🔒 | 🧪 | M2 |
| B05 | U2 platform | `u2-cdn-headers-dns-root` | CDN with the NFR15 headers, the FR4.4 download policy, 404 routing, the `noindex` gate for preview, and the separate DNS root (plan only) | 🔒 | 🧪 | M2 |
| B05a | U2 platform | `u2-preview-deploy-path` | Per-pull-request preview deploy through the preview OIDC role: Terraform apply to preview, site and function deploy, smoke checks; serialized (see M2) | 🔒 | 🧪 | M2 |
| B06 | U3 studio-api | `u3-api-host-health` | Python package host, route registry and pipeline, `GET /health` (**early proof: API answers a health check**) |  | 🧪 | M3 |
| B07 | U3 studio-api | `u3-owner-access` | OwnerAccess (issuer plus subject), 401/403 on every route, R-08 registry tests with spy handlers, rate-limit hooks | 🔒 | 🧪 | M3 |
| B08 | U3 studio-api | `u3-projects-core` | Projects: title-only create, optimistic revisions, slug, categories, featured line-up, revision and line-up guards (C7) | 🔒 | 🧪 | M3 |
| B09 | U3 studio-api | `u3-repository-catalog` | RepositoryCatalog: read-only listing, fail-closed `access_facts`, untrusted documentation reads, Discover and linking | 🔒 | 🧪 | M3 |
| B10 | U4 media-library | `u4-upload-authorizations` | Single-use upload authorizations bound to project, size and type; asset status; fail-closed attach check (C1, C7) | 🔒 | 🧪 | M4 |
| B11 | U4 media-library | `u4-image-processor` | Isolated processor for images: signature checks, HEIC conversion, pixel limit before decode, metadata-free derivatives under the variant rule (C6, C8) | 🔒 | 🧪 | M4 |
| B12 | U4 media-library | `u4-file-processor` | Isolated processor for attachments: ZIP, XML and XXE limits, VSDX and FCStd checks, metadata and entry extraction (FR4.4, FR7.2) | 🔒 | 🧪 | M4 |
| B13 | U5 description-assistant | `u5-provider-port-fake` | Provider port, a fake provider, the spend gate and monthly limit, provider approval for private content, provenance (no paid calls) | 🔒 |  | M4 |
| B14 | U5 description-assistant | `u5-suggestion-flow` | Suggestion endpoint: delimited untrusted input, 60-second timeout, "No suggestion this time", Insert, Edit or Discard provenance | 🔒 | 🧪 | M4 |
| B15 | U6 link-checker | `u6-url-and-address-policy` | Canonical parsing, the IANA special-purpose allow-list, IPv4-mapped normalisation, refusal labels (NFR17) | 🔒 |  | M4 |
| B16 | U6 link-checker | `u6-pinned-fetch` | Pinned connection, TLS by hostname, redirect re-validation, limits, sign-in detection, zero-permission function | 🔒 | 🧪 | M4 |
| B17 | U7 site-renderer | `u7-pages-and-tokens` | Runtime-neutral `render()`; home, catalog, category, exhibit and 404 pages; crafted-studio tokens; escaping; fixtures from the approved prototype |  |  | M3 |
| B18 | U7 site-renderer | `u7-islands-and-parity` | Carousel and lightbox scripts; Node and browser parity test; purity test; accessibility checks (axe) |  |  | M3 |
| B19 | U8 site-publisher | `u8-validate-and-fence` | Validation of C3 and C2 and the semantic rules S1 to S7; manifest key enforcement (R-07, tests K1 to K18); fence store | 🔒 |  | M5 |
| B20 | U8 site-publisher | `u8-write-delete-restore` | Rendering to public storage, ordered writes and deletions, restore, CDN invalidation; test P1 (**early proof: the public page builds and is served**, in preview) | 🔒 | 🧪 | M5 |
| B21 | U9 publication | `u9-status-and-tickets` | Derived status; preparation and inventory; blockers; ConfirmationTicket with the frozen candidate (ADR-003, ADR-012) | 🔒 | 🧪 | M5 |
| B22 | U9 publication | `u9-atomic-acceptance` | Acceptance transaction with the Projects guards; `confirmationId` idempotency; tests CS-01 to CS-04, CS-14, CS-15 and CS-18 | 🔒 | 🧪 | M5 |
| B23 | U9 publication | `u9-sequence-runner` | Site-wide sequence, leases and tokens, run-time basis check, invocation of U8, conditional commit; tests CS-05 to CS-08a, CS-11 and CS-13 | 🔒 | 🧪 | M5 |
| B24 | U9 publication | `u9-recovery-takedown` | Abandoned-attempt recovery, restore, take-down with its retries and alert, featured-order semantics; tests CS-09, CS-10, CS-12, CS-16, CS-17, CS-19 and CS-20 | 🔒 | 🧪 | M5 |
| B25 | U9 publication | `u9-snapshot-and-preview` | Public snapshot builder (semantic rules S8 to S10), preview payload, activity log; tests PB-01 to PB-12 | 🔒 | 🧪 | M5 |
| B26 | U10 content-backup | `u10-nightly-export-restore` | Nightly export through the owners' ports; documented and tested restore (NFR10) | 🔒 | 🧪 | M6 |
| B27 | U11 studio-web | `u11-shell-signin-projects` | Studio shell, sign-in with MFA, Projects list and empty state, statuses, take-down alert |  | 🧪 | M3 |
| B28 | U11 studio-web | `u11-editor-uploads` | Editor with the leave guard and edit recovery, uploads through authorizations, images and alt text, attachments, suggestions |  | 🧪 | M3 |
| B29 | U11 studio-web | `u11-preview-publish` | Preview through U7 in a sandboxed frame; Publish, Update and take-down confirmations; featured order; activity log | 🔒 | 🧪 | M3 |

## Bolt Details (B01 to B29 and B05a)

Each entry gives the Definition of Done items beyond the baseline (**DoD**), what shipping the Bolt will tell us (**Proves**) and the expected demonstration (**Demo**). The entries are carried over from revision 1, and their demonstrations are shown at each unit checkpoint. Every Bolt is owned by aidlc-developer-agent (`team-allocation.md`).

### U1 — contracts

- **B01 `u1-contract-schemas`**
  - **DoD:** every C2 to C6 schema validates against the 2020-12 meta-schema; fixtures pass and are rejected exactly as the C2 and C3 tables state; generated types compile in Python and TypeScript.
  - **Proves:** the allow-list can be enforced structurally, in both languages.
  - **Demo:** an invalid snapshot (an extra field, or a GitHub link) is rejected by both the Python and the TypeScript validators.
- **B02 `u1-api-and-ports`**
  - **DoD:** the OpenAPI 3.1 document validates; every request body is closed; the `ErrorCode` list is complete.
  - **R-18 (mandatory Functional Design correction, P-08):**
    - preview downloads are named as the third direct-to-storage channel;
    - the shared `Error` body is on every applicable error response, and responses that intentionally have no body are documented;
    - a test proves the OpenAPI responses and the registered handlers agree.
  - **Proves:** the back-end units and U11 can build in parallel against fixed interfaces.
  - **Demo:** the contract-test harness runs green against stub implementations.

### U2 — platform

- **B03 `u2-foundation-modules`**
  - **DoD:** `terraform fmt -check`, `validate` and tflint pass; no resource is applied; the modules have no paid resources beyond those team practice lists.
  - **Proves:** both environments come from one set of modules.
  - **Demo:** a clean `validate` and tflint run in CI.
- **B04 `u2-oidc-ci-plan`**
  - **DoD:** CI gets read-only credentials through GitHub OIDC, with no stored AWS keys, and `terraform plan` is clean. Needs E1.
  - **Proves:** the OIDC trust and the state backend work, with no long-lived keys.
  - **Demo:** the CI plan output on a pull request.
- **B05 `u2-cdn-headers-dns-root`**
  - **DoD:**
    - the plan shows the NFR15 headers, the download policy, 404 routing to `404.html` and `category-404.html`, and the preview gate with `noindex`;
    - the DNS root is a separate state;
    - nothing is applied without Michael's approval.
  - **Proves:** the C9 contract is achievable at the CDN.
  - **Demo:** the plan diff, then the preview smoke check after E2.

- **B05a `u2-preview-deploy-path`**
  - **DoD:** a pull request's build deploys to `preview` through the preview OIDC role only; deployments are serialized; smoke checks run; there is no production permission and no stored keys. Needs E1 and E2.
  - **Proves:** "verify in preview before merge" works.
  - **Demo:** a pull request's preview deployment with green smoke checks.

### U3 — studio-api

- **B06 `u3-api-host-health`**
  - **DoD:** `/health` returns only `{"status":"ok"}`; the route registry is in place; the request id is logged with no secrets.
  - **Proves:** the API package deploys and answers.
  - **Demo:** the smoke check against preview.
- **B07 `u3-owner-access`**
  - **DoD:**
    - FR1.1 to FR1.3 acceptance criteria pass, including the look-alike email and foreign-issuer cases;
    - the R-08 registry and spy-handler tests pass;
    - the security review is recorded.
  - **Proves:** nothing in the Studio is reachable except by the owner.
  - **Demo:** a non-owner token gets 403 on every route.
- **B08 `u3-projects-core`**
  - **DoD:** FR3.1 to FR3.5; a stale save gets 409 `STALE_REVISION`; `SLUG_TAKEN`; the guards make a conditional write without changing the revision (CS-15); integration tests run against a throwaway MongoDB container.
  - **Proves:** the drafts model and the guards behave as ADR-003 and ADR-012 need.
  - **Demo:** two tabs saving, and one is refused.
- **B09 `u3-repository-catalog`**
  - **DoD:** FR2.1 to FR2.5; a GitHub error yields `unconfirmed` (PB-04); the credential is read-only (FR2.2); a fake GitHub is used in CI.
  - **Proves:** visibility fails closed.
  - **Demo:** Discover with a simulated GitHub outage.

### U4 — media-library

- **B10 `u4-upload-authorizations`**
  - **DoD:** FR4.8 criteria; expired, oversized and non-owner requests are refused; an asset from another project is refused (PB-10).
  - **Proves:** uploads cannot be abused or cross projects.
  - **Demo:** an upload to preview storage with a single-use authorization.
- **B11 `u4-image-processor`**
  - **DoD:**
    - FR4.2 criteria, including corrupt HEIC, the pixel-limit refusal before decode, and EXIF/GPS removal;
    - the variant rule;
    - the processor's role is denied the database.
  - **Proves:** untrusted images are contained.
  - **Demo:** a GPS-tagged photo yields clean derivatives.
- **B12 `u4-file-processor`**
  - **DoD:** FR4.4 criteria: renamed HTML, zip bomb, plain ZIP named `.vsdx`, XXE; "Metadata could not be read" on failure.
  - **Proves:** maker files are contained.
  - **Demo:** a zip bomb is rejected within the limits.
  - **Integration:** the U11 consumer contract tests for this unit's endpoints pass against the real implementation in preview, and the Studio flow that uses them is demonstrated ("Studio integration ownership").

### U5 — description-assistant

- **B13 `u5-provider-port-fake`**
  - **DoD:** FR5.4, FR5.8 and FR5.9 with the fake provider; no provider call without spending approval (verified by a spy).
  - **Proves:** the AI gates hold before any money is spent.
  - **Demo:** the request is refused with "AI suggestions need approval".
- **B14 `u5-suggestion-flow`**
  - **DoD:** FR5.1, FR5.2, FR5.6 and FR5.7; a prompt-injection fixture cannot change the instructions; provenance is recorded.
  - **Proves:** suggestions never overwrite text or leak.
  - **Demo:** a suggestion inserted with its provenance shown.
  - **Note:** the real provider stays disabled until E6.
  - **Integration:** the U11 consumer contract tests for this unit's endpoints pass against the real implementation in preview, and the Studio flow that uses them is demonstrated ("Studio integration ownership").

### U6 — link-checker

- **B15 `u6-url-and-address-policy`**
  - **DoD:** the NFR17 address and parsing criteria, including `169.254.169.254`, `::ffff:10.0.0.5` and `fd00:ec2::254`, and decimal and octal literals.
  - **Proves:** the allow-list policy is correct on its own.
  - **Demo:** a table-driven test run.
- **B16 `u6-pinned-fetch`**
  - **DoD:** the rebinding, redirect, TLS, size and time criteria; the function identity has no other permissions and no VPC; the security review is recorded.
  - **Proves:** SSRF is not possible.
  - **Demo:** a redirect to `127.0.0.1` is not followed.

### U7 — site-renderer

- **B17 `u7-pages-and-tokens`**
  - **DoD:** FR9.1 to FR9.6; the approved token contrast holds (FR9.6, NFR8); no inline script; the snapshot fixtures come from the approved prototype's STARS and Baduk data, with Monopoly and Risk absent.
  - **Proves:** the approved design is reproduced from the snapshot alone.
  - **Demo:** a rendered home page and exhibit, compared with the prototype.
- **B18 `u7-islands-and-parity`**
  - **DoD:** FR9.7 carousel behaviour (keyboard, no auto-advance, announcements, reduced motion); the parity and purity tests; no serious or critical axe violations; within the JavaScript budget from NFR Design.
  - **Proves:** preview and the live site cannot drift, and the JavaScript stays small.
  - **Demo:** identical output from Node and the browser.

### U8 — site-publisher

- **B19 `u8-validate-and-fence`**
  - **DoD:** C3 tests K1 to K18 and F1; semantic rules S1 to S7; the fence only ever increases.
  - **Proves:** R-07 holds at the application boundary.
  - **Demo:** an `originals/` key gets `invalid`, and nothing is written.
- **B20 `u8-write-delete-restore`**
  - **DoD:** test P1; ordered writes and deletions; restore; invalidation; the IAM test denies `originals/`, `incoming/` and `results/`.
  - **Proves:** public storage equals the snapshot.
  - **Demo:** a fixture snapshot published to preview, then restored.

### U9 — publication

- **B21 `u9-status-and-tickets`**
  - **DoD:** FR3.2, FR7.2, FR7.3, FR10.6 and FR10.7 preparation; the inventory digest; the frozen candidate.
  - **Proves:** the owner sees exactly what would be published.
  - **Demo:** the Monopoly fixture is blocked by its rights review.
- **B22 `u9-atomic-acceptance`**
  - **DoD:** tests CS-01 to CS-04, CS-14, CS-15 and CS-18, as deterministic interleaving tests.
  - **Proves:** content that was not reviewed can never be accepted.
  - **Demo:** an edit in another tab, then a refused confirmation.
- **B23 `u9-sequence-runner`**
  - **DoD:** tests CS-05 to CS-08a, CS-11 and CS-13.
  - **Proves:** no stale run can overwrite newer public state.
  - **Demo:** a take-down racing a publish ends in the correct home page.
- **B24 `u9-recovery-takedown`**
  - **DoD:** tests CS-09, CS-10, CS-12, CS-16, CS-17, CS-19 and CS-20; FR8.1 to FR8.4.
  - **Proves:** failures and crashes always converge on the committed state.
  - **Demo:** an export crashed partway, then recovered.
- **B25 `u9-snapshot-and-preview`**
  - **DoD:** tests PB-01 to PB-12; semantic rules S8 to S10; the PB-02 export scan finds no private identifiers or withheld values.
  - **Proves:** the publication boundary holds from end to end.
  - **Demo:** the export scan report.
  - **Integration:** the U11 consumer contract tests for this unit's endpoints pass against the real implementation in preview, and the Studio flow that uses them is demonstrated ("Studio integration ownership").

### U10 — content-backup

- **B26 `u10-nightly-export-restore`**
  - **DoD:** NFR10; the restore is tested once against preview; the storage is private, versioned and encrypted.
  - **Proves:** at most 24 hours of edits can be lost.
  - **Demo:** a restore into an empty preview database.

### U11 — studio-web

- **B27 `u11-shell-signin-projects`**
  - **DoD:** FR1.3 and FR1.4 behaviour in the client; FR3.5; status words; the alert.
  - **Proves:** the Studio works against the real API.
  - **Demo:** sign-in to preview with the Auth0 development tenant.
- **B28 `u11-editor-uploads`** (built in M3 against the C1 contract; contract fakes in tests only)
  - **DoD verified at M3, against the real U3 in preview:**
    - the editor (FR4.1) and the leave guard (FR4.6);
    - draft save with conflict handling;
    - the image, alt-text, attachment and suggestion user interface, exercised by contract tests against C1 mock handlers;
    - no secrets in the bundle;
    - a list of the endpoints still pending (U4 uploads, U5 suggestions).
  - **DoD deferred to the providing units:**
    - FR4.8 uploads end to end, at B12 (U4, M4);
    - FR5.2 suggestions end to end, at B14 (U5, M4).
  - **Proves:** curation takes little effort (intent).
  - **Demo (M3):** an exhibit edited and saved in preview; upload and suggestion controls show "not available yet". **Demo (M4):** an exhibit edited with real uploaded images.
- **B29 `u11-preview-publish`** (built in M3 against the C1 contract for U9; contract fakes in tests only, none in product code)
  - **DoD verified at M3:**
    - preview rendering through U7 in the sandboxed frame from a C4 fixture (FR6.1);
    - the confirmation, inventory and `PREVIEW_BLOCKED` user interface, exercised by contract tests against C1 mock handlers;
    - the owner-only preview route (FR6.2);
    - a list of the endpoints still pending (U9).
  - **DoD deferred to B25 (U9, M5):**
    - the real preview payload with download addresses;
    - the full-inventory confirmations;
    - Publish, Update and take-down end to end in preview;
    - the repeat of B29's 🔒 review against the real U9.
  - **Proves:** the owner can publish confidently.
  - **Demo (M3):** a preview of a fixture exhibit in the Studio. **Demo (M5):** a publish to preview, end to end.

## Human Stops: Revision 1 Compared With Revision 6

These are estimates; the exact count comes from the engine's directives at Construction entry. Every Bolt (about 34: S0 to S3, B01 to B29 and B05a) is presented individually at its unit's checkpoint, and the answer covers the unit (D2-A). Design-stage questions inside each unit are answered from the approved records under Michael's standing instruction (P-03, P-05), unless one is genuinely his decision.

| Stop | Revision 1 | Revision 6 (D2-A, recommended) | Revision 6 (D2-B) |
|---|---|---|---|
| D1 re-approvals (Units Generation; possibly Contract Design and this plan) | 0 | 1 to 3, once | 1 to 3, once |
| Code Generation Plan Approval | 11 | 12 | 12 |
| Unit checkpoints, or milestone reviews | 11 | 12 | 6 |
| Verification command | 1 | 1 | 1 |
| Merge decisions | Per Bolt | 0 with standing authorization (E10, decided once); about 12 if decided per unit | Same |
| **Total (approximate)** | **23** | **26 to 28** | **20 to 22** |
| **First end-to-end working software** | After about 28 Bolts | **After 4 Bolts (M1)** | After 4 Bolts (M1) |
| **First Studio user interface** | Last unit | **4 Bolts in (slice), full Studio at M3** | Same |
| **First merge verified in preview** | Not defined (no preview path was planned) | **M2 (B05a + E2)** | M2 |

**What revision 6 gains.** The stop count does not fall under the recommended option. The gains are elsewhere:
- working software after four Bolts;
- the Studio early;
- a real preview path at M2;
- every stop carrying a demonstration and its decisions together.

**Other ways to reduce overhead, needing no policy change.** Fewer stops need D2-B or D2-C, and both trade away part of the approval or review discipline; they are Michael's to choose. These options cost nothing in discipline:

| Option | Removes | Needs |
|---|---|---|
| Standing merge authorization for Bolts approved at their unit checkpoint with clean evidence (CI, 🔒 review, 🧪 preview) | A separate merge decision after each checkpoint | The E10 decision, made once |
| Merge the pending records pull requests #8 to #12 as one decision | Five separate merges | Michael's decision |
| Approve E2 at M2 | Long-lived stacked branches | Michael's decision |

## Assumptions & Open Questions

- **Engine order.** The engine resolves the build order from the amended dependency graph. If it differs from the order stated here, the milestones follow the engine and this is reported at M1.
- **Reopening Units Generation.** Whether it also reopens the later Inception stages is confirmed when D1 is executed. The outcome is reported, and any extra re-approval is presented as an unchanged artifact.
- **Nothing else is authorized.** This plan authorizes no merge, deployment, preview creation or spending.
