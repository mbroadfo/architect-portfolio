# Security re-review: U0 repository layout and CI baseline (S0)

patch-id: 63cd8b0422ff2d172f56de9eebe9615e47fc3d2f
verdict: READY

- **Pull request:** #13 "u0-repo-and-ci-baseline: repository layout, CI gate and verification entry point".
  - Head 61e7b563c436546e52ca772ab5420d688f25263e, base `origin/main` ba29ace.
  - The identity above is now `git patch-id --verbatim`. I recomputed it locally with
    `scripts/check_security_review.py --base origin/main --head HEAD`, and the CI
    `review-check` log for 61e7b56 printed the same value.
  - This record replaces `2026-10-12-u0-repo-and-ci-baseline.md`. That record bound the old
    `--stable` identity and is kept only as history.
- **Reviewer:** aidlc-devsecops-agent, a separate Claude session (Claude Opus 5.5) that did not
  author the change or its fixes. Re-reviewed 2026-10-14. I changed no code.
- **Verdict basis:** no Critical or High finding is open.
  - Fixed and verified by probe: S0-1, S0-3, S0-4 and S0-5.
  - Open and tracked: S0-2 and S0-6 (Medium and Low), and S0-7 (owner action).
  - New: two Low findings, N-1 and N-2.

## Scope

I reviewed the fix commit 61e7b56 (diff from 02b2f96) in full:
- `scripts/check_security_review.py`, `scripts/check_workflows.py`, `scripts/compose_isolation.py`;
- `.github/security-sensitive-paths.txt`, `docs/security-reviews/README.md`;
- the tests added in `tests/scripts/`.

I checked for regressions against the unchanged S0 files. `ci.yml`, `codeql.yml`,
`gate_results.py`, `scan_output.py`, `guard_fake_idp.py`, `verify.py` and `verify-checks.toml`
are byte-identical to 02b2f96.

**Bootstrap note, unchanged:** this pull request introduces the review check, so its own
`review-check` uses the pull request's copy of the checker and of the path list.

## Findings: status

### S0-1. Medium: fixed

`compute_patch_id` now uses `git patch-id --verbatim`. I reran my earlier probe repository:
- reviewed version: `54a09026…`;
- `return tok` re-indented: `fb7298cd…`;
- space removed inside a string: `28627b99…`.

Before the fix, all three had one identity. Whitespace tests were added. The identity is
computed from commits, not the working tree, so it does not depend on the platform: the local
Windows value and the CI Linux value agree.

### S0-2. Medium: open, tracked (accepted residual)

A pull request can still rewrite `ci.yml`, `gate_results.py` and `check_workflows.py`, which
decide `gate`. This rests on the `main` ruleset and on Michael's review of `.github/` and
`scripts/`, as `docs/security-reviews/README.md` records. N-1 below is a related lint gap.

### S0-3. Medium: fixed (small residual in N-2)

The list now covers every anchor I named. Verified with the checker's own matcher:
- `.pip-audit-ignore`, `backend/pyproject.toml`;
- the root, back-end and fake-issuer `requirements*.in` and `*.lock`;
- every `package-lock.json`;
- `local/compose.env`, `local/compose.verify.yaml`, `local/fixtures/derivatives.sha256.json`,
  `local/slice_check.py`;
- `local/*.Dockerfile`, their dockerignore files and `local/fake-idp/Dockerfile`;
- `backend/tests/**`.

The paths that exist only on the slice branch take effect if they ever reach `main`.

### S0-4. Low: fixed

Compose arguments are normalised before checking.
- **Refused now:** `down --volumes=true`, `down -tv`, `--profile x rm -fsv`, `down --rmi=all`,
  `down --remove-orphans=true`, and also `-v=true`, `--volumes false`, `--rmi local`,
  `volume rm x` and `system prune`.
- **Still accepted (no regression):** every argument list the registry and `slice_check.py`
  actually use: `up -d --build --force-recreate`, plain `down`, `--profile tests run --rm
  --no-deps --build -T slice-it`, `exec -T …`, `config --format json` and `cp …`.

### S0-5. Low: fixed (residual gap in N-1)

Permissions are now allow-listed for each workflow and job. Probes:
- `write-all` and `read-all` are refused at the top level and at job level.
- Job `contents: write` is refused.
- `security-events: write` on a `ci.yml` job is refused.
- CodeQL `contents: write` is refused.
- The path-gated `if:` must match exactly, so `... || always()` is refused. So is a
  `${{ }}`-wrapped form, which is stricter than needed but safe.
- Both real workflows pass.

### S0-6. Low: open, tracked

The public-output scan still does not check tag or attribute names, attributes with empty
values, or non-string JSON values. The fake-issuer guard's archive depth and its exact-match
issuer URL are also unchanged.

### S0-7. Low, informational: open (owner action E13)

CodeQL blocks a merge only once Michael registers its checks as required. The `gate` job
does not depend on it.

## New findings

### N-1. Low, open: the workflow lint does not pin the gate's own `if: always()` and does not forbid `continue-on-error`

- **Location:** `scripts/check_workflows.py`.
- **Probes that pass the lint:**
  - `gate` with `if: success()`, or with no `if:`. GitHub then skips `gate` when a component
    fails, and a skipped required check does not block a merge.
  - `continue-on-error: true` on the `python` job or on one of its steps. A failing step then
    reports success.
- **Context:** this is the honest-mistake side of S0-2.
- **Fix:** require `jobs.gate.if == 'always()'`, and refuse `continue-on-error` in `ci.yml`.

### N-2. Low, open: a few files that weaken checks without touching their code are still unlisted

- **Location:** `.github/security-sensitive-paths.txt`.
- **Files not covered:**
  - `web/**/package.json` (the `test` and `build` scripts that CI runs);
  - `web/*/vitest.config.ts` (coverage thresholds);
  - `web/slice-studio/vite.config.ts` (the alias that points the Studio's preview at the
    shared renderer);
  - `tests/scripts/`, `local/tests/`, `local/mongo-init.js`, `Makefile` and `local/slice.mk`.
- **Context:** none of these is a trust anchor in the S0-3 sense.
- **Fix:** consider them when the CI Pipeline stage confirms the list.

## Codex R1 to R5 and the CodeQL fix: still hold

- **R1, fixed and tightened.** The isolation rules are unchanged except that S0-4 made the
  argument filter stricter.
- **R2, fixed.** `gate_results.py` is unchanged. Codex's reproduction still exits 1. On GitHub,
  `gate` fails on 61e7b56 only because `review-check` has no record for the new identity.
- **R3, fixed.** `scan_output.py` is unchanged. The real-fixture reproduction is still reported
  as "bytes differ from the authorized derivative".
- **R4, fixed.** On #13, `slice-e2e` is correctly skipped because there is no slice code.
- **R5:** no S0 code; see the #14 record.
- **CodeQL `js/polynomial-redos`:** slice code only; see the #14 record. On #13, both CodeQL
  analyses and the CodeQL results check pass.

## Automated verification I relied on

**Run locally by me** (C:\Users\Mike\Documents\Code\ap-s0, Python 3.13.5 from the main tree's venv):
- `pytest tests/scripts --cov=scripts --cov-fail-under=80`: 293 passed, coverage 96.81%.
- `python scripts/check_workflows.py`: OK, 2 workflow files.

**Seen by me on GitHub** (run 38626154229, head 61e7b56):
- passed: `changes`, `python`, `web`, `guard`, `audit`, `workflow-lint`, `gitleaks`, both
  CodeQL analyses and the CodeQL results check;
- skipped as designed: `slice-e2e`;
- failed: `review-check` (no record for 63cd8b04…), and therefore `gate`.

I did not see any run made after this record was added.

**Not run by me:** actionlint, gitleaks, and CodeQL locally.
