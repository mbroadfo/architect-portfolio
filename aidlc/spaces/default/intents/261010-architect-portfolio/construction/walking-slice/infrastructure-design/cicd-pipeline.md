# CI/CD Pipeline — U0 walking-slice

**Inputs:**
- U0 NFR design: `../nfr-design/`, the security, reliability and logical-components files;
- NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- components and contract-summary;
- team-practices (Way of Working, Deployment, Code Style);
- `infrastructure-design-questions.md`.

U0 uses **no cloud infrastructure**. S1 to S3 run on a local Docker stack, and S0 merges the CI pipeline. Every cloud resource belongs to U2 and the owning units, and needs Michael's approval (E1, E2).

## Stages (S0 — `.github/workflows/ci.yml`)

Triggers: `pull_request` to `main`, and `push` to `main`. There is no `pull_request_target`.

**Permissions.** Top-level `permissions: contents: read`. Only the CodeQL job adds `security-events: write` and `actions: read`.

**Pinning.** Every action is pinned to a commit SHA. Runners are `ubuntu-24.04`, never `latest`. Tool versions are pinned:
- Python `3.12` (exact patch release recorded in `.python-version`);
- Node `22` (exact release in `.nvmrc`);
- `actionlint` and `gitleaks` as released binaries, verified by checksum, so no third-party action needs extra permissions.

**Checkout.** On pull requests, every job checks out the pull request **head** commit (`ref: ${{ github.event.pull_request.head.sha }}`) with `fetch-depth: 0`, rather than GitHub's synthetic merge commit.

1. **`changes`.** A SHA-pinned path filter decides which **path-gated** jobs must run:
   - `python`, `web`, `guard` and `audit` are path-gated;
   - `workflow-lint`, `review-check` and `gitleaks` **always run**;
   - any change under `.github/`, `scripts/`, or to a lockfile, `.python-version` or `.nvmrc` forces every path-gated job to run.
2. **Component jobs**, run in parallel and each conditional on `changes`:
   - **python:** `ruff check`, `ruff format --check`, `mypy`, `pytest --cov --cov-fail-under=80`.
   - **web:** `npm ci`, `prettier --check`, `eslint` (including `react/no-danger`), `tsc --noEmit`, `vitest run --coverage` with an 80% lines threshold, `vite build`.
   - **guard:** builds the deployable outputs, then runs `scripts/guard_fake_idp.py`. The outputs are the `backend` wheel (`python -m build`) and the `web` bundle (`vite build`); in S0 these are minimal placeholder packages, so real outputs exist. The guard **fails if it scanned zero files**. Its negative-fixture test must fail on the contaminated fixture and pass on the clean one.
   - **workflow-lint:** `actionlint` and `scripts/check_workflows.py` (permissions, pinning, no `pull_request_target`).
   - **review-check** (pull requests only): `scripts/check_security_review.py`.
     - It computes the patch identity of `git merge-base origin/${{ github.base_ref }} <head sha>`..`<head sha>`, excluding `docs/security-reviews/`, and compares it with a `verdict: READY` record.
     - It does not run on `push` to `main`, because every change reaches `main` through a pull request where it already ran.
   - **gitleaks:** the whole diff.
   - **audit:** `npm audit --audit-level=high`, and `pip-audit -r requirements.lock` against a reviewed ignore file.
3. **`gate`.** It declares `needs:` on every job and runs with `if: always()`. It fails if any needed job failed or was cancelled, or was skipped although `changes` required it. On `push` events, `review-check` is skipped by design (it runs on pull requests only), and `gate` accepts that one skip. This is the single required status check.

**CodeQL** runs in `.github/workflows/codeql.yml` on `pull_request` and `push` to `main`, with **no path filter**, so it always reports. It analyses `python` and `javascript-typescript`, both of which have source in S0 (the scripts and the placeholder web package). Its job alone adds `security-events: write` and `actions: read`.

**Required checks.** The check names to register are `gate` and the two CodeQL analysis checks. Michael registers the exact names, shown after the first run, as required on `main` (E13).

## Stage → Gate

| Stage | Gate |
|---|---|
| Pull request opened or updated | `gate` and CodeQL must pass, once registered as required (E13) |
| Merge | Michael's unit-checkpoint approval and merge authorization (D2-A, E10); squash merge |

## Deployment, Promotion, Rollback

- **Deployment.** None in S0 or the slice. Preview deployment arrives with U2's B05a, and production with an owner-approved `production` run (team practice).
- **Rollback.** CI changes are rolled back by reverting the S0 commit through a pull request.

## Secrets in CI

None. No secret is defined and no cloud credential is used. Fork pull requests get a read-only token.

## Assumptions & Open Questions

- No cloud resource is designed or created here. U2's Infrastructure Design covers preview and production.
