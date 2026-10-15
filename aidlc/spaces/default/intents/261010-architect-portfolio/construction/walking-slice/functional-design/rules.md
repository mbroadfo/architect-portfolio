# Business Rules — U0 walking-slice

**Inputs:** unit-of-work (U0); requirements; components; contract-summary (C2, C9); `entities.md`; `functional-design-questions.md`.

## Rules

```yaml
rules:
  - id: BR1.1
    statement: Every slice API request must come from the configured owner, proven by a verified token.
    category: authorization
    applies_to: all slice API routes except the slice health route (which returns only a fixed status)
    trigger: any request
    logic: >
      Accept a request only if every check passes, in this order:
      the bearer token is present;
      its signature verifies against the configured issuer's published signing keys;
      the signing algorithm is on the allow-list (RS256 or ES256; never none or HS*);
      the issuer equals OwnerIdentity.issuer;
      the audience equals the configured API audience;
      it is not expired and not used before its start time (60 seconds of clock skew allowed);
      the subject equals OwnerIdentity.subject.
      Email and display-name claims are never used.
    violation: 401 for a missing, unverifiable, expired, wrong-issuer, wrong-audience or wrong-algorithm token; 403 for a valid token with another subject; in every case no handler runs and nothing is read or changed
    source: FR1.1, FR1.2, NFR1
  - id: BR1.3
    statement: The fake issuer is refused at runtime outside local mode.
    category: policy
    applies_to: API startup
    trigger: process start
    logic: IF the configured issuer is the local fake issuer, or any loopback or localhost address, AND the environment is not explicitly local THEN refuse to start
    violation: the process exits with a configuration error; no route is served
    source: team practice (production code gets no way around authentication); NFR1
  - id: BR1.2
    statement: The fake identity provider exists only in the local development stack.
    category: policy
    applies_to: every non-local artifact, meaning every output of a deployable build target (the API package, the public site bundle, the Studio bundle, and any container image); the local stack directory local/ is the only exclusion
    trigger: every CI run (the S0 guard)
    logic: >
      The fake identity provider lives only under local/fake-idp/ and carries the marker AIDLC_LOCAL_ONLY_FAKE_IDP.
      Its signing key is generated in memory at start-up and never written to disk or committed, because the repository is public.
      The guard scans every non-local artifact for the marker, the fake provider's package name, the local fake issuer URL, and private-key material.
      IF any is found THEN fail.
    violation: CI fails; nothing is produced
    source: team practice; NFR1; NFR3 (no secrets in the repository)
  - id: BR2.1
    statement: A save must be based on the current revision.
    category: constraint
    applies_to: SliceProject
    trigger: save
    logic: IF the request's base revision differs from the stored revision THEN refuse; ELSE store the change and increment the revision by 1
    violation: 409 STALE_REVISION; nothing changed
    source: FR3.3, FR3.4
  - id: BR2.2
    statement: A project needs a valid title and summary, and a unique slug.
    category: validation
    applies_to: SliceProject
    trigger: create, save
    logic: >
      IF the title is empty or longer than 120 characters, or the summary is longer than 1200 characters, THEN refuse.
      The slug is proposed from the title at creation and stays editable until the first publish, after which it is fixed.
      Uniqueness is enforced by a unique index; a duplicate is refused.
    violation: 422 VALIDATION_FAILED, or 409 SLUG_TAKEN
    source: FR3.1, FR4.1, C2 Slug and Exhibit
  - id: BR3.1
    statement: Nothing becomes public without an explicit Publish confirmation of the reviewed revision.
    category: policy
    applies_to: Publish
    trigger: Publish
    logic: >
      IF the confirmation does not name the project's current revision THEN refuse.
      ELSE, as one atomic step (a conditional write on the project at that revision, inside one database transaction), freeze the SlicePublishedVersion and record it as current.
    violation: 409 STALE_REVISION; nothing written
    source: FR7.1, ADR-012 (thin form)
  - id: BR3.2
    statement: The published output contains only the approved allow-list.
    category: validation
    applies_to: SlicePublishedVersion.snapshot
    trigger: Publish
    logic: IF the snapshot is not valid against C2 PublicSiteSnapshot 1.0 THEN refuse and write nothing
    violation: publish fails; the output folder is unchanged
    source: FR4.10, NFR2, ADR-002, C2
  - id: BR3.3
    statement: The output folder contains only what the renderer produced from the snapshot.
    category: constraint
    applies_to: the local public folder
    trigger: Publish
    logic: >
      Render into a new temporary folder, then swap it with the public folder in one rename.
      On any failure, delete the temporary folder; the public folder stays the last successful output.
      The output holds only the rendered pages, the fixture image derivatives and the static assets.
    violation: Publish fails, and the public folder keeps the last published output
    source: FR7.4, C9
  - id: BR3.4
    statement: Status is derived, never stored.
    category: calculation
    applies_to: SliceProject.status
    trigger: every read
    logic: IF there is no published version THEN Draft; IF the published sourceRevision equals the revision THEN Published; ELSE Changes since last publish
    violation: n/a
    source: FR3.2, ADR-003
  - id: BR4.1
    statement: Preview uses the same renderer as Publish, is marked, and is never written to the output folder.
    category: policy
    applies_to: Preview
    trigger: Preview
    logic: render the candidate with the same renderer in preview mode, inside a sandboxed frame marked "Preview — not public"; write nothing
    violation: n/a
    source: FR6.1, FR6.2, ADR-008, C11
  - id: BR5.1
    statement: One aggregate required check gates every pull request (S0).
    category: policy
    applies_to: pull requests to main
    trigger: every pull request
    logic: >
      The aggregate job always runs. It runs each component's checks when that component's paths changed:
      format, lint, type, tests with coverage, gitleaks, dependency audit, CodeQL, the BR1.2 guard and the BR5.2 review check.
      It fails if any check that ran failed. A check that was skipped because its paths did not change counts as passed.
    violation: the pull request cannot merge once Michael registers the check as required (E13)
    source: team practice (Way of Working, one gate check; Code Style, checks before merge)
  - id: BR5.2
    statement: Security-sensitive changes need an independent review recorded for their exact content (S0; provisional).
    category: policy
    applies_to: pull requests that touch the provisional security-sensitive paths listed in .github/security-sensitive-paths.txt
    trigger: every pull request
    logic: >
      IF a touched path matches the list THEN require a review record under docs/security-reviews/ whose recorded patch identity equals the pull request's current patch identity.
      A rebase that keeps the same patch identity keeps the review valid; any content change needs a new review.
      The path list and the record location are provisional until the CI Pipeline stage confirms them.
    violation: the check fails, naming the paths that need a review
    source: team practice (independent security review); bolt-plan "How Bolts Land" item 3
  - id: BR4.2
    statement: All owner text is escaped.
    category: validation
    applies_to: rendered pages and the Studio page
    trigger: render
    logic: render text as plain text, never as markup or script
    violation: n/a; escaping is unconditional
    source: FR4.5, NFR15
```

## Rules Summary

| Rule | Summary | Source |
|---|---|---|
| BR1.1 | Owner-only API: verified signature, algorithm allow-list, issuer, audience, expiry, subject | FR1.1, FR1.2 |
| BR1.3 | Fake issuer refused at runtime outside local mode | Team practice |
| BR1.2 | The fake identity provider never ships: marker scan of every non-local artifact; key only in memory | Team practice, NFR3 |
| BR2.1 | Saves use optimistic revisions | FR3.3, FR3.4 |
| BR2.2 | Title required; slug unique | FR3.1, FR4.1 |
| BR3.1 | Publish only on explicit confirmation of the reviewed revision | FR7.1, ADR-012 |
| BR3.2 | Output valid against the C2 allow-list | FR4.10, NFR2 |
| BR3.3 | The output folder equals the last snapshot | FR7.4 |
| BR3.4 | Status is derived | FR3.2, ADR-003 |
| BR4.1 | Preview uses the shared renderer, marked, not written | FR6.1, FR6.2 |
| BR4.2 | All text is escaped | FR4.5 |
| BR5.1 | One aggregate required check (S0) | Team practice |
| BR5.2 | Content-bound security review check (S0; provisional) | Team practice |

## Assumptions & Open Questions

- These are thin forms of the owning units' rules, with sources cited. The owning units' Functional Design gives the complete versions; for example, ADR-012's full ticket model belongs to U9.
