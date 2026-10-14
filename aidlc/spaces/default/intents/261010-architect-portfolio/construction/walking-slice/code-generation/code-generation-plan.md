# Code Generation Plan — U0 walking-slice

## Summary

- Builds: the repository layout and the S0 CI baseline, which merge to `main`, plus the local walking slice S1 to S3: create, save, preview and publish a static page, on a demonstration branch.
- Touches: `backend/`, `web/`, `local/`, `scripts/`, `.github/`, `tests/guard/`, `docs/security-reviews/`, `Makefile`, root configuration.
- Tests: about 40 pytest and about 12 Vitest unit tests, integration tests against a MongoDB replica set, the guard's negative-fixture tests, and the `make slice-check` end-to-end run; 80% line-coverage floor.

## Inputs and Traceability Keys

**Design inputs:**
- `../functional-design/`:
  - `functional-spec.md` (AC0.1 to AC0.11, workflows W1 to W6, repository layout);
  - `rules.md` (BR1.1 to BR5.2);
  - `entities.md`.
- `../nfr-requirements/` (including `tech-stack-decisions.md`).
- `../nfr-design/` (security and reliability design).
- `../infrastructure-design/` (`cicd-pipeline.md`, `infrastructure-specification.md`).
- Contract-summary: C2 PublicSiteSnapshot 1.0, C9 and C11.
- `bolt-plan.md` Phase A.

U0 has no user stories. Each step cites the acceptance criteria (AC0.x) and rules (BRx.y) it implements.

## Where Code Goes and How It Lands

**Location.** Application code is written at the workspace root, never in the AI-DLC record.

**Branches.** The conductor, not the developer, assembles each Bolt's branch and pull request, following `bolt-plan.md` "How Bolts Land":
- **S0** lands on `main` through its own pull request, once Michael approves U0's checkpoint and merges are authorized (E10).
- **S1 to S3** are committed only to `slice/walking-slice`. They are opened as draft pull requests labelled "demonstration, do not merge", and are never merged or deployed.

The developer keeps S0 files and S1 to S3 files in separate directories, so each Bolt's branch can be cut cleanly:
- S1 to S3 live under `slice/`, `local/` and the slice parts of `backend/` and `web/`;
- the `source-manifest.json` marks each path's Bolt.

## Steps

### Step 1 — Environment prerequisites check (all Bolts)

- [x] Verify the tools: `git`, Python 3.12 or later, Node 22, npm, Docker, and Docker Compose v2.
- [x] Record the versions found in `code-summary.md`.
- [x] If Docker or Compose is unavailable, still build S0 (it needs no Docker), then halt S1 to S3 and report. Nothing is installed without Michael.

### Bolt S0 — `u0-repo-and-ci-baseline` (merges to `main`)

**Step 2 — Project structure and production configuration skeleton.**
- [x] Repository layout:
  - `backend/` (a Python package `portfolio_api` with a placeholder module and `pyproject.toml`);
  - `web/` (npm workspace root, plus `web/site/`, a placeholder Vite and TypeScript package);
  - `contracts/` and `infra/` (README placeholders);
  - `local/` (README only in S0);
  - `scripts/`;
  - `.github/`;
  - `docs/security-reviews/` (README with the record format).
- [x] Root configuration: `.editorconfig`, `.python-version` (3.12.x), `.nvmrc` (22), `.gitignore` additions, `requirements.lock` (hashed, generated with `pip-compile`), `package-lock.json`.
- [x] Tooling configuration: `ruff.toml` (lint and format), `mypy.ini` (strict for scripts), `.prettierrc`, `eslint.config.js` (typescript-eslint, react-hooks, jsx-a11y, eslint-plugin-react with `react/no-danger` as an error).
- Implements: BR5.1 (layout); functional-spec "Repository layout".

**Step 3 — Bootstrap the test runners and record the unit-scoped commands.**
- [x] pytest with pytest-cov (`backend/pyproject.toml` and `tests/scripts/` configuration).
- [x] Vitest, with coverage threshold `lines: 80`, in `web/site`.
- [x] Record the exact unit-scoped commands in `unit-test-instructions.md`.
- Implements: NFR13.4.

**Step 4 — Business logic (scripts): implement.**
- [x] `scripts/guard_fake_idp.py` (BR1.2):
  - it scans the build outputs `backend/dist/*` and `web/*/dist/**`;
  - it looks for the marker `AIDLC_LOCAL_ONLY_FAKE_IDP`, the package name `fake_idp`, the fake issuer URL read at scan time from `local/compose.env` (skipped if the file is absent), and PEM or JWK private-key patterns;
  - it fails when **zero** files were scanned;
  - it never scans `scripts/` or `local/`.
- [x] `scripts/check_workflows.py` (NFR13.6): fails on a workflow without a top-level `permissions:`, on an action not pinned to a 40-character SHA, or on any `pull_request_target`.
- [x] `scripts/check_security_review.py` (BR5.2):
  - reads `.github/security-sensitive-paths.txt`;
  - computes the patch identity of `merge-base(origin/<base>, <head>)..<head>`, excluding `docs/security-reviews/`;
  - requires a record in `docs/security-reviews/` with that `patch-id:` and `verdict: READY`.
- [x] `scripts/scan_output.py` (BR3.2, BR3.3): given a release folder and its C2 snapshot, it fails on any text that does not come from C2 fields, the fixture or the static assets. Used by S2 and S3.
- [x] `.github/security-sensitive-paths.txt` (provisional list: `.github/`, `scripts/`, the list file itself, `backend/**/auth*`, `backend/**/publish*`, `local/fake-idp/`, `infra/`).

**Step 5 — Business logic (scripts): write and run their tests.**
- [x] `tests/scripts/test_guard_fake_idp.py` (AC0.2):
  - the contaminated fixture `tests/guard/fixtures/contaminated/` (synthetic marker text, no real key) fails;
  - the clean fixture passes;
  - zero files scanned fails;
  - `scripts/` and `local/` are not scanned.
- [x] `tests/scripts/test_check_workflows.py` (NFR13.6): unpinned, missing `permissions:` and `pull_request_target` cases fail; a compliant workflow passes.
- [x] `tests/scripts/test_check_security_review.py` (AC0.11):
  - no record fails;
  - a mismatched patch identity fails;
  - `verdict: NOT-READY` fails;
  - a matching READY record passes;
  - a content-identical rebase still passes;
  - adding the record does not change the identity.

  Each case runs against a temporary git repository.
- [x] `tests/scripts/test_scan_output.py` (AC0.9): an extra field, a private string, a repository host and a clean release.
- [x] Run them; coverage of at least 80% for `scripts/`.

**Step 6 — Environment and build configuration (CI).**
- [x] `.github/workflows/ci.yml` (NFR13.1 to NFR13.6, BR5.1, AC0.10):
  - **base:** `ubuntu-24.04`; top-level `permissions: contents: read`; every action pinned to a SHA; checkout of the pull request head with `fetch-depth: 0`;
  - **`changes`:** path filter;
  - **path-gated jobs:** python, web, guard (builds the wheel and the web bundle, then the guard), audit (`npm audit --audit-level=high` and `pip-audit -r requirements.lock` with `.pip-audit-ignore`);
  - **always-run jobs:** workflow-lint (`actionlint` binary verified by checksum, plus `check_workflows.py`), review-check (pull requests only), gitleaks (binary verified by checksum);
  - **forcing rule:** edits under `.github/` or `scripts/`, to lockfiles, `.python-version` or `.nvmrc` force every job to run;
  - **`gate`:** `needs:` on everything, `if: always()`, failing on any failed, cancelled, or wrongly skipped job; the review-check skip on `push` is allowed.
- [x] `.github/workflows/codeql.yml`: `pull_request` and `push` to `main`, no path filter; `python` and `javascript-typescript`; `security-events: write` and `actions: read` on that job only.
- [x] `.github/dependabot.yml`: GitHub Actions, npm and pip updates.
- [x] The workflow lint passes on these workflows.

**Step 7 — Documentation.**
- [x] `README.md` sections: repository layout, prerequisites, how CI works, and how to record a security review.
- [x] Note for Michael (E13): register `gate` and the CodeQL checks as required on `main`.

### Bolt S1 — `u0-slice-projects-and-owner-check` (demonstration branch only)

**Step 8 — Data model and database behaviour: implement.**
- [x] `backend/portfolio_api/slice/models.py`: SliceProject and SlicePublishedVersion (Pydantic), including `currentVersionId`.
- [x] MongoDB collections with a unique index on `slug` (BR2.2).
- [x] Replica-set connection settings.

**Step 9 — Data model: write and run its tests.**
- [x] Validation: title of 1 to 120 characters, summary of at most 1200, slug format (AC0.4).
- [x] Integration: duplicate slug refused by the unique index.

**Step 10 — Repository and data access: implement.**
- [x] `ProjectRepository`: create, get, a save that compare-and-sets the revision (BR2.1), and list.
- [x] `PublicationRepository`: the conditional Publish transaction and the conditional compensation (BR3.1; `reliability-design` REL-0.1).

**Step 11 — Repository: write and run its tests (integration, MongoDB replica set).**
- [x] A stale save gets `STALE_REVISION` (AC0.3).
- [x] The Publish transaction compare-and-sets `revision` and the previous `currentVersionId` (AC0.6, AC0.7).
- [x] Compensation restores the previous state (AC0.9).
- [x] Concurrent Publishes of the same revision: exactly one wins.

**Step 12 — Business logic (auth and settings): implement.**
- [x] `backend/portfolio_api/auth.py`: `require_owner` (BR1.1):
  - JWKS client with a 10-minute cache, refreshing on an unknown key id at most once per 60 seconds;
  - algorithms RS256 and ES256 only;
  - `iss`, `aud`, `exp`, `iat` and `sub` checked with 60 seconds of leeway;
  - fails closed (NFR1.4).
- [x] `settings.py`: the local-class issuer rules, refused unless `APP_ENV=local` (BR1.3; NFR1.2).

**Step 13 — Business logic (auth): write and run its tests.**
- [x] Forged signature, unsigned token, `alg=none` or HS256, wrong issuer, wrong audience, expired, other subject (403), owner (200); unreachable JWKS gets 401; repeated unknown key ids cause a single fetch (AC0.1).
- [x] Settings: a local-class issuer outside `APP_ENV=local` refuses start-up (AC0.1a).

**Step 14 — Local fake issuer: implement and test.**
- [x] `local/fake-idp/` (FastAPI): marker `AIDLC_LOCAL_ONLY_FAKE_IDP`; ES256 key in memory; `/.well-known/jwks.json`; `/token?sub=` for the owner and test subjects; `iss` fixed at `http://fake-idp.invalid`.
- [x] Tests: the key is never written to disk; tokens verify against the JWKS.

### Bolt S2 — `u0-slice-render-and-publish` (demonstration branch only)

**Step 15 — Renderer: implement.**
- [x] `web/slice-renderer/`, a TypeScript CLI following the C11 shape (BR4.1, BR4.2):
  - snapshot JSON on stdin, `RenderOutput` JSON on stdout;
  - `render(snapshot, {mode, resolveAsset})` with `renderToStaticMarkup`;
  - preview mode adds the "Preview — not public" marking;
  - C2 validation with Ajv; no inline scripts.

**Step 16 — Renderer: write and run its tests.**
- [x] Escaping of hostile title and summary text (AC0.6).
- [x] An invalid snapshot throws `RenderInputError`.
- [x] The preview marking appears only in preview mode (AC0.5).
- [x] Deterministic output.
- [x] Coverage of at least 80%.

**Step 17 — API and endpoints: implement.**
- [x] FastAPI app with `docs_url`, `redoc_url` and `openapi_url` set to `None`.
- [x] `GET /health` with a fixed body.
- [x] Router-level `require_owner` on:
  - `POST /slice/projects`;
  - `PATCH /slice/projects/{id}` with `If-Match`;
  - `GET /slice/projects/{id}/preview`, returning the candidate snapshot;
  - `POST /slice/projects/{id}/publish` with the reviewed revision.
- [x] Request-id and JSON logging middleware with redaction (NFR11.1).
- [x] CORS for `http://localhost:5173` only.
- [x] Publish service (W4, REL-0.1):
  1. serialize with a lock;
  2. reconcile;
  3. take T;
  4. build the C2 snapshot from the SliceProject mapping;
  5. call the renderer CLI;
  6. write `releases/<versionId>/`;
  7. run the transaction;
  8. swap the relative `public` symbolic link;
  9. compensate on failure.

**Step 18 — API: write and run its tests.**
- [x] Route enumeration: only `/health` is unauthenticated, and no handler runs on a rejected call, proven with a spy (AC0.1).
- [x] Create, save, preview and publish happy paths (AC0.5, AC0.6).
- [x] Stale Publish gets 409 (AC0.7).
- [x] The status derivation table (AC0.8).
- [x] Failure injection at the render, transaction and swap steps, each leaving a consistent state (AC0.9).
- [x] Reconciliation after a simulated crash.
- [x] The log redaction test.
- [x] Coverage of at least 80%.

**Step 19 — Local stack configuration.**
- [x] `local/compose.yaml`:
  - `mongo` (`--replSet rs0`, a health check that pings and checks primary);
  - an idempotent `mongo-init` with explicit member `mongo:27017`;
  - `fake-idp` (alias `fake-idp.invalid`, `127.0.0.1:9000`);
  - `api` (`127.0.0.1:8000`, `depends_on` conditions, `site` read-write);
  - `nginx` (`127.0.0.1:8080`, `site` read-only).
- [x] Images pinned by digest.
- [x] `local/compose.env` (placeholders, `APP_ENV=local`).
- [x] `local/nginx.conf`: server-level `add_header … always`, no location overrides.
- [x] Initial `releases/empty/` placeholder, with `public` linked to it.

### Bolt S3 — `u0-slice-studio-page` (demonstration branch only)

**Step 20 — Frontend behaviour: implement.**
- [x] `web/slice-studio/` (React, Vite):
  - sign-in through `http://localhost:9000/token`, with the token kept in React state only;
  - project list and New project;
  - editor with Save and conflict handling;
  - preview in `<iframe sandbox srcdoc>`;
  - Publish confirmation naming the revision;
  - errors for 401/403, 409 and 422;
  - `data-testid` attributes.

**Step 21 — Frontend behaviour: write and run its tests (Vitest and React Testing Library).**
- [x] The token is never written to local or session storage (NFR15.2).
- [x] The 409 message (AC0.3).
- [x] The preview frame is sandboxed without `allow-scripts` (AC0.5).
- [x] Publish sends the reviewed revision (AC0.6).
- [x] Coverage of at least 80%.

**Step 22 — End-to-end slice check.**
- [x] `Makefile` target `slice-check`, with Playwright against the local stack (W6):
  - start from an empty database;
  - create, save, preview, publish;
  - assert the static page, the C9 headers on a 200 and a 404, and the timings (NFR6.1, NFR6.2);
  - assert that the Compose file publishes nothing on a non-loopback host address;
  - run `scan_output.py` (AC0.9).

### All Bolts

**Step 23 — Documentation and traceability.**
- [x] `local/README.md`: how to run the slice.
- [x] `code-summary.md`.
- [x] `traceability.json` (AC0.1 to AC0.11 mapped to steps and tests).
- [x] `source-manifest.json`, listing every created path with its Bolt.


## Testing Contract

```json
{
  "version": 1,
  "methodology": "test-after",
  "source": "team",
  "ordering": "Implement each testable layer of a Bolt, then write and run that layer's tests before the Bolt is offered for approval.",
  "scope": "classic",
  "test_strategy": "standard",
  "project_type": "greenfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. The specific\nmethodology (TDD, BDD, ATDD, or classic test-after) is affirmed at\npractices-discovery and recorded in `team.md` under this heading with explicit\n`Methodology` and `Ordering` fields; Code Generation resolves those fields\nindependently from coverage, tooling, and scope notes.\n\nWhen no posture has been affirmed, our default per scope is:\n- **Methodology**: test-after\n- **Ordering**: implement each applicable testable layer, then write and run\n  that layer's tests.\n- `mvp`, `enterprise`, `feature`, `infra`, `classic` add an 80% line-coverage\n  floor and CI execution before merge.\n- `bugfix`, `security-patch` add a targeted regression for the specific\n  bug/vulnerability and require the existing suite to remain green.\n- `express` uses the Minimal strategy: requirement-driven unit tests (one per\n  requirement, with a happy-path floor per component); existing tests remain\n  green.\n- `poc`, `refactor`, `workshop` add no extra new-test floor and require the\n  existing suite to remain green.\n\nThe active `Test Strategy` still applies in every scope and determines test\nvolume/types. Scope floors are additive; they never reduce or replace the\nselected strategy.\n\nBuild and Test verifies defined coverage floors and affirmed quality targets;\nthey may not be weakened to make a step pass.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "- **Methodology**: test-after\n- **Ordering**: Implement each testable layer of a Bolt, then write and run that layer's tests before the Bolt is offered for approval.\n- **Methodology evidence**: This is the `org.md` default for a team with no affirmed posture, and the owner affirmed it in the Practices Discovery interview (Q4). The repository is greenfield, with no tests or team habit that points elsewhere. Rigor comes from the coverage floor, the invariant tests and the CI gates below, not from the order in which tests are written.\n- **Test strategy**: The workflow's Standard test strategy sets how many tests are written and of which types. The floors below add to it and never replace it.\n- **Coverage floor**: At least 80% line coverage for the frontend and for the Python API, measured in CI. A change that drops coverage below the floor does not merge. Floors and quality targets are never lowered to make a step pass.\n- **Frontend tests**: Vitest with React Testing Library for components and logic. Automated accessibility checks (axe) run on the public pages, including a check that every published image has alt text (D-19).\n- **API tests**: pytest with coverage. Unit tests replace integration boundaries with fakes. Integration tests run in CI against a throwaway MongoDB container and never against the live Atlas cluster.\n- **End-to-end tests**: A small Playwright suite covers the critical journeys: the public gallery and an exhibit page, plus the Studio journey from discovering a repository through preview, publish and take-down. NFR design decides how Studio sign-in is exercised in CI. Production code gets no way around authentication.\n- **Infrastructure checks**: `terraform fmt -check`, `terraform validate`, tflint, and a `terraform plan` run on every pull request that touches infrastructure.\n- **Approval and privacy invariants**: The Bolt that introduces each of these behaviours also adds a test for it:\n  - Studio endpoints reject callers who are not signed in.\n  - Nothing reaches the public site without an explicit publish.\n  - Take-down removes content from the public site.\n  - Private repository material is never exposed, including the hidden \"View code\" link (D-15, D-21, D-22).\n- **No live paid services in tests**: GitHub, Auth0 and the AI provider are replaced by fakes behind their interfaces in unit and CI tests. Tests never spend money or call production systems.\n- **Traceability**: Test names or docstrings cite the IDs of the acceptance criteria they verify.\n- **Runnable**: Every suite runs from a clean checkout with only the documented prerequisites, locally and in CI."
    }
  ],
  "obligations": {
    "strategy": "standard",
    "strategy_volume": [
      "Five to eight tests per component.",
      "Unit tests plus integration tests for key boundaries.",
      "Add E2E, performance, or security tests when requirements demand them."
    ],
    "scope_floor": [
      "Keep the existing test suite green.",
      "This scope adds no extra new-test floor beyond the selected test strategy."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "test-after",
    "runner_step": "Bootstrap the minimal test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Bootstrap the minimal test runner/configuration and record the exact unit-scoped command.",
      "Data model / database behavior - implement.",
      "Data model / database behavior - write and run its tests after implementation.",
      "Repository / data access - implement.",
      "Repository / data access - write and run its tests after implementation.",
      "Business logic - implement.",
      "Business logic - write and run its tests after implementation.",
      "API / endpoint - implement.",
      "API / endpoint - write and run its tests after implementation.",
      "Frontend behavior - implement.",
      "Frontend behavior - write and run its tests after implementation.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:edcbd2b77a4c82b8f032874653d51c02396dd35d7e4307c46621155c3af8fed7",
  "contract_sha256": "sha256:fab897cdab145a92fc76ef5260f98230be1626901c0b62b676e4a5378ffc0493"
}
```
