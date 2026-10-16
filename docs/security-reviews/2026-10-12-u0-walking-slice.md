# Security review: U0 walking slice (S0 plus S1 to S3), demonstration only

patch-id: 8fa4d6764f0291711d68078f7a0cbd1208595dcd
verdict: READY

- **Pull request:** #14 "[Demonstration, do not merge] U0 walking slice (S1–S3)".
  - Head 661448b5a78461c4a738cb0c15a18d3f16f8c399, base `origin/main` ba29ace.
  - The head commit fixes the CodeQL `js/polynomial-redos` alert raised at f11464f. That
    changed the identity from `2e977a65…` to the one above, which I recomputed with
    `scripts/check_security_review.py --base origin/main --head HEAD`.
  - This pull request is never merged or deployed.
- **Reviewer:** aidlc-devsecops-agent, a separate Claude session (Claude Opus 5.5) that did not
  author the change. Reviewed 2026-10-12. I changed no code.
- **Verdict basis:** no Critical or High finding is open. The CodeQL High finding is fixed.
  The S0 findings S0-1 to S0-7 also apply here, because S0 is part of this diff; see the #13
  record. The slice adds three Low findings, all local-only.

## Scope

I reviewed the S0 content (as in the #13 record) and the slice against the U0 threat model:
the NFR security design and requirements, BR1.1 to BR5.2, AC0.1 to AC0.11, the infrastructure
design and REL-0.1.

I read these in full:
- `backend/portfolio_api/auth.py`, `settings.py`;
- `slice/app.py`, `api.py`, `publish.py`, `site_store.py`, `renderer.py` and `snapshot.py`, and
  the publish transaction and compensation in `slice/mongo.py`;
- `local/fake-idp/fake_idp/app.py`, `local/compose.yaml`, `local/compose.verify.yaml`,
  `local/compose.env`, `local/nginx.conf`, `local/api.Dockerfile`;
- the export, scan and isolation parts of `local/slice_check.py`;
- `local/fixtures/derivatives.sha256.json`;
- the preview, token and API-client code in `web/slice-studio/src/`;
- the change in `web/slice-renderer/src/variants.ts`.

I checked the renderer for raw HTML: it renders with `renderToStaticMarkup`, has no
`dangerouslySetInnerHTML`, and lints with `react/no-danger`. I read the R5 integration tests.

## Checks that held

- **Owner check (BR1.1).**
  - `require_owner` is attached at router level to every `/slice` route.
  - `/docs`, `/redoc` and `/openapi.json` are disabled, so only `/health` is unauthenticated.
  - The algorithm allow-list is RS256 and ES256, and a token's algorithm must match its key.
  - The signature is verified, with exact `iss`, `aud`, required `exp`, `iat`, `iss`, `aud` and
    `sub`, and 60 seconds of leeway.
  - A token for another subject gets 403. Email and name claims are never used.
  - The key set fails closed: at most 10 minutes old, one refresh attempt per 60 seconds, no
    redirects followed.
  - Library versions: PyJWT 2.15.1, FastAPI 0.143.0.
- **Local issuer refusal (BR1.3).**
  - A local-class issuer is refused unless `APP_ENV=local`: `http`, `.invalid`, `.local`,
    `localhost`, single-label hosts, and private, loopback or reserved addresses in any numeric
    form.
  - `AUTH_JWKS_URL` must be public https outside local mode.
  - Production code holds no fake issuer URL.
- **Fake issuer isolation (BR1.2).**
  - The key is generated in memory, and the issuer serves only the public JWK.
  - The marker is present in its source and in the Studio bundle.
  - The wheel includes only `portfolio_api*`.
  - Every container runs as user 10001, and every image is pinned by digest.
- **Publication boundary (BR3.1 to BR3.4).**
  - The revision is checked first, then the snapshot is built from that revision. It is
    validated against a closed C2 model (`extra="forbid"`, `strict`), then rendered into
    `releases/<id>`.
  - One transaction makes a compare-and-set on revision and `currentVersionId` and inserts the
    version.
  - Only then is the relative `public` link swapped atomically.
  - Compensation is conditional and transactional. Reconciliation runs at start-up and before
    every Publish.
  - Renderer output paths are allow-listed (`PAGE_PATH`, `ASSET_REF`, `STATIC_ASSET_PATH`;
    downloads refused), so a page path cannot leave its release.
  - Preview renders into `<iframe sandbox="" srcdoc>` and writes nothing.
  - The Studio keeps its token in memory only.
- **Local exposure.**
  - Every host port is published on 127.0.0.1, and `slice_check.py` asserts it.
  - nginx sends the C9 headers with `always` and mounts the site read-only.

## Findings

### S0-1 to S0-7 (see the #13 record)

S0-1 to S0-7 are the findings in the #13 record:
- **Medium:** S0-1, S0-2 and S0-3 (S0-3 covers the slice trust anchors `local/compose.env`,
  `local/fixtures/derivatives.sha256.json` and `backend/tests/**`);
- **Low:** S0-4 to S0-7.

All are open.

### CQ-1. High (CodeQL `js/polynomial-redos`), fixed in 661448b

- **Location:** `web/slice-renderer/src/variants.ts:37`, `downloadName`.
- **Problem:** the anchored `-+$` and `^-+|-+$` regexes were flagged as polynomial.
- **Fix:** they are replaced by a linear `trimHyphens` loop. The only regex left,
  `/[^a-z0-9]+/g`, has no suffix that can fail, so it does not backtrack polynomially.
- **My verification:**
  - Using Node type stripping, the new function gave the same result as the old one on 2,010
    inputs (fixed and random, including Unicode, empty and all-hyphen labels), with no
    differences.
  - The hostile inputs from the new test each ran in about 0.1 ms.
  - It still agrees with `download_name` in `scripts/scan_output.py`.
  - The slice refuses downloads (`requiredDownloads` must be empty), so the code path is not
    reachable from slice data.
  - No other slice regex has an unanchored repeated suffix.
- **GitHub:** at 661448b the CodeQL results check passes, and the code-scanning API returned no
  open alerts. I could not run the renderer's Vitest suite, because this worktree has no
  `node_modules`.

### SL-1. Low, open: an unauthenticated request with malformed JSON gets 422, not 401

- **Location:** `backend/portfolio_api/slice/api.py`, `app.py` (FastAPI parses the body before
  the router dependency runs).
- **Evidence:** `POST /slice/projects` with no token and a body of `{not json` returns 422. Valid
  JSON with no token returns 401, as do a bad `revision` type and a bad `If-Match`.
- **Impact:** no handler runs and nothing is read or changed. The caller learns only that the
  route parses JSON. AC0.1 says 401 for every refused call.
- **Fix:** run the owner check before body parsing (middleware or a custom route class), or
  amend AC0.1.

### SL-2. Low, open: the runtime refusal checks `APP_ENV` but not loopback binding

- **Location:** `backend/portfolio_api/settings.py`.
- **Problem:** NFR1.2 defines explicit local mode as `APP_ENV=local` **and** loopback-only
  binding. The API checks only `APP_ENV`. Loopback exposure is enforced by
  `local/compose.yaml` and `slice_check.py`'s `assert_loopback_only`, not by the process, so the
  same image run with `APP_ENV=local` and a public port would trust the fake issuer.
- **Impact:** acceptable for a stack that is never deployed.
- **For later units:** the owning unit's production authentication must not let a single
  environment variable enable a local issuer, for example by also refusing when a
  production-only setting is present.

### SL-3. Low, open (local-only, accepted for the demonstration): the local services do not check the Host header

- **Location:** `local/fake-idp/fake_idp/app.py`, and the API.
- **Problem:** while the demonstration stack runs, a hostile web page could use DNS rebinding to
  mint owner tokens from `127.0.0.1:<idp port>` without authentication and drive the local API.
- **Impact:** limited to test data on the local stack; nothing is deployed.
- **Fix:** Starlette's `TrustedHostMiddleware` (localhost and the Compose names) would close it
  cheaply.

### Note for later units (not a finding)

`load_settings` and the fake issuer strip the trailing `/` from the issuer. Auth0 issues
`iss` with a trailing slash, so an exact comparison will refuse every real token until this is
handled. It fails closed.

## Codex review R1 to R5: confirmation

- **R1, Docker cleanup and isolation: fixed.**
  - There is no `down -v` in `local/slice_check.py` or in CI.
  - `slice_check.py` uses the shared isolation rules: the per-checkout project, refusal of
    `portfolio-slice`, free ports, the lock, and a plain `down`.
  - Its only deletion is its own gitignored `local/.slice-check/scan`.
  - MongoDB in the verification stack is on tmpfs.
  - `local/tests` passed (19 tests).
  - CI ran the real isolation check `verify-docker-isolation`, which passed (1 test). I did not
    start Docker.
- **R2, CI false passes: fixed.** Verified on the shared S0 code (see the #13 record).
  `verify.py --strict` also fails on test-level skips from the JUnit reports.
- **R3, unauthorized image bytes: fixed.** Codex's reproduction against the final code:
  - I copied the real `local/fixtures/ast_SliceFixtureImage0001/w480.jpg` to the allow-listed
    key `media/ast_SliceFixtureImage0001/w480.jpg` and appended
    `PRIVATE_DRAFT_NOTE=not-authorized-for-publication`.
  - With the committed manifest, `scan_file` reports "bytes differ from the authorized
    derivative (sha256 456fb83c0f45…, authorized a79bd7beac54…)".
  - Codex's own 4-argument call reports "no authorized derivative digest for this file".
  - The untouched fixture passes.
  - `main` without `--media-digests` exits 2.
  - `slice_check.py` passes the manifest and scans the release that `public` points at, against
    that version's snapshot read from the database.
- **R4, end-to-end journey in CI: fixed.**
  - CI ran `slice-e2e` on f11464f with
    `verify.py --strict --kind e2e --kind integration`.
  - Results: `slice-integration` passed (13 tests), `verify-docker-isolation` passed,
    `slice-e2e` passed, and `scan_output: OK - 9 file(s) scanned`.
  - Summary line: "verify: OK (3 passed, 0 failed, 0 skipped)".
- **R5, rollback after a partial write: fixed.**
  - `backend/tests/integration/slice/test_publish_faults.py` injects faults inside real MongoDB
    transactions:
    - the insert fails after the pointer update, and both are rolled back;
    - a failed commit leaves `public` unchanged;
    - compensation with a failed delete is rolled back and the error is surfaced;
    - a swap failure is compensated, and a restart agrees with the database;
    - a swap failure plus a compensation failure is repaired on restart.
  - A recording wrapper proves that the first write really ran.
  - These ran on Linux in CI at f11464f as part of the 13 `slice-integration` tests, with no
    skips under `--strict`. 661448b does not touch them.

## Automated verification I relied on

**Run locally by me** (C:\Users\Mike\Documents\Code\ap-slice, Python 3.13.5 from the main tree's venv):
- `pytest backend/tests/unit --cov=portfolio_api --cov-fail-under=80`: 191 passed, 1 skipped
  (the symbolic-link test; this Windows host cannot create symbolic links), coverage 92.20%;
- `local/fake-idp/tests`: 10 passed;
- `local/tests`: 19 passed;
- `tests/scripts`: 234 passed.

**Seen by me on GitHub.**
- `gh pr checks 14` at 661448b:
  - passed: `changes`, `python`, `web`, `guard`, `audit`, `workflow-lint`, `gitleaks`, both
    CodeQL analyses and the CodeQL results check;
  - still running: `slice-e2e`;
  - failed: `review-check` (no record at that commit).
- The completed run at f11464f (run 38309921432): `slice-e2e` and the back-end unit tests
  (192 passed on Linux) passed.

I did not see the final `slice-e2e` or `gate` results for 661448b, or any run after this record.

**Not run by me:** Docker, Playwright, actionlint, gitleaks, CodeQL locally, and the TypeScript
suites.
