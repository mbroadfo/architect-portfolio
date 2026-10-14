# Security re-review: U0 walking slice (S0 plus S1 to S3), demonstration only

patch-id: b4888bfd94c712441a072497cdb7751d36fdeb72
verdict: READY

- **Pull request:** #14 "[Demonstration, do not merge] U0 walking slice (S1–S3)".
  - Head d7eb0228e2ea1a7533c7688a8fa5abaff72a979e, base `origin/main` ba29ace.
  - The identity above is `git patch-id --verbatim`. I recomputed it locally, and the CI
    `review-check` log for d7eb022 printed the same value.
  - This record replaces `2026-10-12-u0-walking-slice.md`, which is kept only as history.
  - This pull request is never merged or deployed.
- **Reviewer:** aidlc-devsecops-agent, a separate Claude session (Claude Opus 5.5) that did not
  author the change or its fixes. Re-reviewed 2026-10-14. I changed no code.
- **Verdict basis:** no Critical or High finding is open.
  - Fixed and verified by probe: SL-1 and SL-3, plus the S0 fixes.
  - Fixed earlier and still holding: CQ-1.
  - Open and tracked: SL-2, and the S0 items S0-2, S0-6 and S0-7.
  - New: two Low findings from the S0 part, N-1 and N-2 (see the #13 re-review record).

## Scope

I reviewed the fix commit d7eb022 (diff from 661448b) in full:
- `backend/portfolio_api/settings.py`, `slice/api.py`, `slice/app.py`;
- `local/fake-idp/fake_idp/app.py`;
- the S0 fix files, and the new tests.

The S0 files in this branch are byte-identical to #13 at 61e7b56, apart from the review
records.

These files are unchanged since 661448b:
- `auth.py`, `publish.py`, `mongo.py`, `site_store.py`, `renderer.py`, `snapshot.py`;
- `web/slice-renderer/`, `local/slice_check.py`;
- `scan_output.py`, `gate_results.py` and the workflows.

## Findings: status

### SL-1. Low: fixed

- **Change:** routes no longer declare FastAPI body parameters. Each body is a dependency,
  `owner_body(Model)`, that itself depends on `require_owner`. The body is read and validated
  only after the owner check, and bodies over 64 KiB are refused.
- **Probes against the API test harness**, loaded from a scratch directory so nothing was
  added to the worktree:

  | Caller | Request | Result |
  |---|---|---|
  | No token | malformed JSON | 401 (was 422) |
  | No token | valid JSON | 401 |
  | No token | a 200 KB body | 401 |
  | No token | a publish with a bad `revision` type | 401 |
  | Bad bearer token | malformed JSON | 401 |
  | Token for another subject | malformed JSON | 403 |
  | Any refused caller | (all of the above) | no handler ran |

- **Owner paths, no regression:**
  - malformed JSON: 422 with the C1 `VALIDATION_FAILED` shape;
  - an oversized body or an unknown field: 422;
  - create: 201;
  - `PATCH` without `If-Match`: 428;
  - `PATCH` with `If-Match: "1"`: 200;
  - publish with a bad type: 422;
  - publish of revision 2: 200.
- **Note:** without a `Content-Length` header, the 64 KiB limit is checked only after the whole
  body has been read. That can only happen after the owner check, so it is informational.

### SL-2. Low: open, tracked

The local-issuer refusal still depends only on `APP_ENV=local`. Loopback exposure is enforced by
the Compose file and by `assert_loopback_only` in `slice_check.py`, not by the API process. This
is acceptable for a stack that is never deployed. The owning unit's production authentication
must not let one environment variable enable a local issuer.

### SL-3. Low: fixed

- **Change:** `TrustedHostMiddleware` is now the outermost middleware on the API and on the fake
  issuer.
- **API:**
  - `ALLOWED_HOSTS` is required outside `APP_ENV=local`; without it the API refuses to start.
  - Wildcards and ports are refused, and `create_app` also refuses an empty list or `*`.
  - In local mode the default is `localhost`, `127.0.0.1` and `api`.
  - Probes: `Host: attacker.example` gets 400 on `/health` and on `/slice/projects`;
    `Host: localhost:8000` gets 200.
- **Fake issuer:**
  - `/token` with `Host` set to `attacker.example`, `attacker.example:9000`,
    `localhost.attacker.example` or `127.0.0.1.nip.io` gets 400.
  - `localhost:9000`, `127.0.0.1:9000` and `fake-idp.invalid` get 200.
  - Its health check uses `127.0.0.1`, which is allowed.
- **No regression:** in CI on d7eb022, the full Compose and Playwright journey passed with these
  allow-lists.

### CQ-1. High (CodeQL `js/polynomial-redos`): fixed in 661448b, still holds

`variants.ts` is unchanged since 661448b. On d7eb022, both CodeQL analyses and the CodeQL
results check pass.

### S0 findings (see the #13 re-review record)

- **Fixed:** S0-1 (verbatim identity), S0-3 (path list), S0-4 (Compose argument
  normalisation), S0-5 (permission allow-list and exact `if:`).
- **Open and tracked:** S0-2 (Medium; a pull request can rewrite the workflow that decides
  `gate`), S0-6 (Low; scan and guard blind spots), S0-7 (owner action E13).
- **New:** N-1 (Low; the lint does not pin `gate`'s `if: always()` or forbid
  `continue-on-error`) and N-2 (Low; a few check-weakening files are still unlisted).

## Codex R1 to R5: still hold

- **R1, fixed and tightened by S0-4.**
  - `slice_check.py` is unchanged.
  - `local/tests` passed (31 tests).
  - In CI, `verify-docker-isolation` passed (1 test).
- **R2, fixed.** `gate_results.py` is unchanged. Codex's reproduction still exits 1.
- **R3, fixed.** `scan_output.py` and the digest manifest are unchanged. The real-fixture
  reproduction (appending `PRIVATE_DRAFT_NOTE=not-authorized-for-publication` to `w480.jpg` at
  its allow-listed key) is still reported: "bytes differ from the authorized derivative".
- **R4, fixed.** CI `slice-e2e` on d7eb022 (run 38626158725) passed with
  `verify: OK (3 passed, 0 failed, 0 skipped, 0 not applicable)`:
  - `slice-integration` passed (13 tests);
  - `verify-docker-isolation` passed;
  - `slice-e2e` passed;
  - `scan_output: OK - 9 file(s) scanned`.
- **R5, fixed.** The fault-injection tests are unchanged and ran among those 13 Linux
  integration tests with no skips under `--strict`.

## Automated verification I relied on

**Run locally by me** (C:\Users\Mike\Documents\Code\ap-slice, Python 3.13.5 from the main tree's venv):
- `pytest backend/tests/unit --cov=portfolio_api --cov-fail-under=80`: 242 passed, 1 skipped
  (the symbolic-link test; this Windows host cannot create symbolic links);
- `local/fake-idp/tests`: 20 passed;
- `local/tests`: 31 passed;
- `tests/scripts`: 293 passed;
- `check_workflows.py`: OK.

**Seen by me on GitHub** (run 38626158725, head d7eb022):
- passed: `changes`, `python`, `web`, `guard`, `audit`, `slice-e2e`, `workflow-lint`,
  `gitleaks`, both CodeQL analyses and the CodeQL results check;
- failed: `review-check` (no record for b4888bfd…), and therefore `gate`.

I did not see any run made after this record was added.

**Not run by me:** Docker, Playwright, the TypeScript suites, actionlint, gitleaks, and CodeQL
locally.
