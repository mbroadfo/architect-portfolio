# Security review: U0 repository layout and CI baseline (S0)

patch-id: 4df5067c7b7435887182500b47737f41e45fb8e5
verdict: READY

- **Pull request:** #13 "u0-repo-and-ci-baseline: repository layout, CI gate and verification entry point".
  Head 02b2f961c14c0e79053761cd284860d33f5c3459, base `origin/main` ba29ace. I recomputed the
  patch identity with `scripts/check_security_review.py --base origin/main --head HEAD`, and it
  matches the identity above.
- **Reviewer:** aidlc-devsecops-agent, a separate Claude session (Claude Opus 5.5) that did not
  author the change. Reviewed 2026-10-12. I changed no code.
- **Verdict basis:** no Critical or High finding is open. Three Medium and four Low findings are
  open and are listed below. They do not block under the record rules, but they should be
  closed or accepted in the CI Pipeline stage.

## Scope

I reviewed all 59 files of the diff against the U0 threat model:
- `nfr-requirements/security-requirements.md` and `nfr-design/security-design.md`;
- `functional-design/rules.md` (BR1.2, BR5.1, BR5.2);
- `functional-design/functional-spec.md` (AC0.2, AC0.9, AC0.10, AC0.11);
- `infrastructure-design/cicd-pipeline.md`.

I read these in full:
- `.github/workflows/ci.yml`, `.github/workflows/codeql.yml`, `.github/dependabot.yml`,
  `.github/security-sensitive-paths.txt`;
- `scripts/gate_results.py`, `scripts/check_workflows.py`, `scripts/check_security_review.py`,
  `scripts/guard_fake_idp.py`, `scripts/scan_output.py`, `scripts/compose_isolation.py`;
- the runner, service and report parts of `scripts/verify.py`, and `scripts/verify-checks.toml`;
- `.pip-audit-ignore`, `.gitignore` and `docs/security-reviews/README.md`.

I read the tests under `tests/scripts/` selectively and ran them.

**Bootstrap note.** This pull request introduces the review check. Its own `review-check`
therefore runs the pull request's copy of the checker and its own path list (the job prints a
notice saying so). This record, and Michael's review, are the only controls on that first use.

## Findings

### S0-1. Medium, open: the patch identity ignores whitespace, so a semantic edit made after review can keep it

- **Location:** `scripts/check_security_review.py`, `compute_patch_id` (`git patch-id --stable`).
  The README states that "any content change needs a new review".
- **Problem:** `git patch-id` drops all whitespace before hashing. In Python and YAML,
  indentation carries meaning, so an edit made after review can change behaviour without
  changing the identity. Examples:
  - indenting a verification call into a dead `if` branch;
  - moving a `raise` or `return` across a block;
  - moving a workflow key to another job;
  - removing a space inside a string literal.

  The old review record then still matches.
- **Evidence:** a probe repository with the security-sensitive path `backend/portfolio_api/auth.py`.
  I made two edits after review:
  - indenting `return tok` under a `raise`, which makes it unreachable;
  - changing `"not owner"` to `"notowner"`.

  The identity stayed `c510c86e655b…` throughout. With `git patch-id --verbatim` the three
  revisions give three different identities (`54a09026…`, `fb7298cd…`, `28627b99…`).
- **Fix:** use `git patch-id --verbatim` (Git 2.40 or later; local Git is 2.47), and add a
  regression test for an indentation-only change. Once the checker on `main` changes, every
  existing identity changes, so open reviews must be re-recorded.

### S0-2. Medium, open (accepted residual, documented): a pull request can rewrite the workflow that decides `gate`

- **Location:** `.github/workflows/ci.yml` (the `review-check` step and the `gate` job),
  `scripts/gate_results.py`, `scripts/check_workflows.py`.
- **Problem:** on `pull_request`, GitHub runs the pull request's own copy of `ci.yml`. The
  checker and the path list come from the base, but the step that fetches and runs them does
  not. A pull request can therefore:
  - edit that step;
  - drop a job from `needs`;
  - edit `gate_results.py`.

  Any of these makes `gate` pass. `check_workflows.py` and `EXPECTED_JOBS` come from the same
  pull request, so they do not prevent it.
- **What does hold:** honest malformed input fails closed, which I verified (see R2 below). The
  residual risk is recorded in `docs/security-reviews/README.md`.
- **What this rests on:** the `main` ruleset and Michael's review of every change under
  `.github/` and `scripts/`. While agents use Michael's credentials, that review is procedural.
- **Recommendation for the CI Pipeline stage:** Michael's review should explicitly check every
  change to `.github/workflows/` and `scripts/gate_results.py`. Re-assess this once agents have
  their own GitHub identity (the target control in `team.md`).

### S0-3. Medium, open: the review check rests on unreviewed trust anchors

- **Location:** `.github/security-sensitive-paths.txt` (provisional).
- **Problem:** several files that a security control depends on are not on the list, so
  changing them needs no review record:
  - `.pip-audit-ignore`: one line with a future expiry silences a high or critical finding in
    the required dependency audit;
  - `backend/pyproject.toml`: decides what goes into the wheel, so it is what keeps the fake
    issuer out of the deployable output;
  - `requirements*.in` and `*.lock`, and `web/**/package*.json`: supply chain.

  These slice-branch paths have the same gap, but only matter if they reach `main`:
  - `local/compose.env`: the guard's issuer URL;
  - `local/fixtures/derivatives.sha256.json`: the trusted digests for the scan;
  - `local/slice_check.py`, `local/compose.verify.yaml`, `local/*.Dockerfile`;
  - `backend/tests/**`: the approval and privacy invariant tests.
- **Fix:** add these paths when the CI Pipeline stage confirms the list. `.pip-audit-ignore` and
  `backend/pyproject.toml` matter now.

### S0-4. Low, open: the Compose filter for data-removing arguments matches exact tokens only

- **Location:** `scripts/compose_isolation.py`, `check_compose_args`.
- **Problem:** these all pass the filter:
  - `down --volumes=true`;
  - `down -tv` (combined short flags);
  - `down --rmi=all`;
  - `down --remove-orphans=true`;
  - `--profile x rm -fsv` (`rm` after a global option).

  `down -v` is refused. Nothing in `verify-checks.toml` or `local/slice_check.py` uses these
  forms today, so this is defence in depth only.
- **Fix:** split `--flag=value` forms, expand combined short flags, and find the subcommand
  after any global options.

### S0-5. Low, open: the workflow lint checks that `permissions:` exists, not what it grants

- **Location:** `scripts/check_workflows.py`.
- **Problem:**
  - A top-level `permissions: write-all` passes.
  - Job-level permission escalation is not checked.
  - The path-gated `if:` test is a substring match, so `... == 'true' || always()` also passes.

  The current workflows are correct: `contents: read` at the top level, and CodeQL adds only
  `security-events: write` and `actions: read`.
- **Fix:** enforce the allowed permission values for each workflow and job.

### S0-6. Low, open: the public-output scan does not check tag or attribute names, or attributes with empty values

- **Location:** `scripts/scan_output.py`, `_HtmlScanner._check_attribute`.
- **Problem:** text, attribute values, file names and the bytes of binary files are checked,
  but not:
  - element and attribute names;
  - attributes whose value is empty, such as `<p data-anything="">`;
  - non-string JSON values.

  A renderer bug that emitted data in one of those places would not be caught. Separately, the
  fake-issuer guard opens only one level of nested zip, never tar-in-tar, and matches the issuer
  URL only exactly.
- **Fix:** allow-list tag and attribute names from the renderer's template vocabulary.

### S0-7. Low, informational: CodeQL becomes blocking only once it is registered

The `gate` job does not depend on the CodeQL workflow. CodeQL blocks a merge only after Michael
registers its checks as required (E13), which needs to happen before or together with this
merge.

## Codex review R1 to R5: are they fixed in this pull request's S0 part?

The code is in S0 in both pull requests; #14 contains this same S0 commit.

- **R1, Docker cleanup and isolation: fixed.**
  - `ci.yml` contains no `docker compose ... down -v`.
  - `scripts/compose_isolation.py`:
    - derives the project `portfolio-verify-<sha256 of the checkout path>`;
    - refuses `portfolio-slice` and any name without that prefix;
    - picks free loopback ports for each run;
    - holds an OS file lock for each checkout;
    - refuses `-v`, `--volumes`, `--rmi`, `--remove-orphans`, `prune` and the `rm` subcommand
      (with the gaps in S0-4).
  - `verify.py` tears down with a plain `down`.
  - The tests ran and passed.
- **R2, CI false passes: fixed.**
  - `gate_results.py` keeps a job inventory and requires each path-gated output to be exactly
    `"true"` or `"false"`.
  - I ran Codex's reproduction against the final code: it now exits 1 (it exited 0 before).
  - Other probes also fail the gate:
    - an empty outputs object;
    - `review-check` skipped on a pull request or on an unknown event;
    - `gitleaks` skipped or missing;
    - `changes` skipped;
    - a required path-gated job skipped;
    - a path-gated job cancelled;
    - empty `NEEDS_JSON` (exit 2).
  - All `"false"` with skipped path-gated jobs passes, and `review-check` skipped on `push`
    passes, as designed.
  - `check_workflows.py` keeps `gate.needs` equal to the inventory, and every checkout sets
    `persist-credentials: false`.
  - On GitHub, the throwaway control pull requests #15 to #18 (malformed output, missing output,
    skipped required job, missing job) each show `gate` failed. I saw the failures; I did not
    read the reasons the gate printed.
- **R3, unauthorized image bytes: fixed.**
  - `scan_output.py` requires `--media-digests` (it exits 2 without it).
  - With no manifest, nothing is authorized.
  - Every `media/` and `files/` file must match the SHA-256 recorded for its exact key.
  - The reproduction against the real fixture is recorded in the #14 review.
- **R4, end-to-end journey in CI: fixed.**
  - A `slice-e2e` job is in `gate.needs`.
  - The `changes` step sets it to `"false"` only when `local/compose.yaml` is absent, as on
    `main` after S0, where it was correctly skipped on #13.
- **R5, rollback after a partial write: no S0 code.** The tests are in S1; see the #14 review.

## Automated verification I relied on

**Run locally by me** (C:\Users\Mike\Documents\Code\ap-s0, Python 3.13.5 from the main tree's venv):
- `pytest tests/scripts --cov=scripts --cov-fail-under=80`: 234 passed, coverage 96.76%.
- `python scripts/check_workflows.py`: OK, 2 workflow files.

**Seen by me on GitHub** (`gh pr checks 13`, head 02b2f96):
- passed: `changes`, `python`, `web`, `guard`, `audit`, `workflow-lint`, `gitleaks`, both
  CodeQL analyses and the CodeQL results check;
- skipped as designed: `slice-e2e`;
- failed: `review-check` (no record at that commit), and therefore `gate`.

I did not see any run made after this record was added.

**Not run by me:** actionlint and gitleaks (neither is installed here), and CodeQL locally.
