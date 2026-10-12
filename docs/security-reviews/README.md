# Security review records

A pull request that changes a path listed in `.github/security-sensitive-paths.txt` needs an
independent security review recorded here before Michael approves it (team practice, BR5.2).
The CI `review-check` job enforces that a matching record exists; the reviewer's
independence is a procedural control.

The path list and this record format are **provisional** until the CI Pipeline stage
confirms them.

## How to record a review

1. Push the pull request's final content.
2. Compute its patch identity: the stable `git patch-id` of the diff from the merge base to
   the head, excluding this folder. The check prints it when it fails:

   ```
   python scripts/check_security_review.py --base origin/main --head HEAD
   ```

3. An AI reviewer that did not write the change (a separate session or harness) reviews the
   diff against the threat model and writes one record file here, named
   `<YYYY-MM-DD>-<short-topic>.md`.
4. Commit the record on the same pull request. Adding the record does not change the patch
   identity, because this folder is excluded from it. A rebase that keeps the same content
   keeps the same identity; any content change needs a new review.

## What the check enforces, and what it does not

- **The check comes from the base branch.** The `review-check` job runs
  `scripts/check_security_review.py` as it is on the base branch, and the script reads
  `.github/security-sensitive-paths.txt` from the base too. A pull request therefore cannot
  narrow the list, or weaken the checker, that judges it.
- **Bootstrap exception.** The one exception is the pull request that introduces the check
  (the S0 pull request): the base has no checker or list yet, so the pull request's own copy
  is used, and the job log says so.
- **Every record must be READY.** Each record for the patch identity must say
  `verdict: READY`. One `NOT-READY` record for the same identity fails the check, even beside
  a `READY` one.
- **The gate itself is not covered by this check.** The pull request also supplies
  `.github/workflows/ci.yml` and `scripts/gate_results.py`, which decide the single required
  check. Changes to them are protected only by the `main` ruleset (a pull request with passing
  checks) and by Michael's review of that pull request. The same holds for any edit to the
  checker or the path list: it takes effect only once Michael has approved and merged it.
- **Independence is procedural.** Records are plain text and are not signed. The check proves
  that a record exists for the exact content. That the reviewer was independent is a
  procedural control.

## Record format

The check reads two lines, each at the start of a line and spelled exactly as shown:

```
patch-id: <the 40-character patch identity>
verdict: READY
```

`verdict: NOT-READY`, or any other value, fails the check. Blocking findings are fixed first,
which changes the patch identity and so needs a new record.

A record should also give, in free text:

- **Pull request:** its number and title.
- **Reviewer:** the harness or session and model that reviewed it, and confirmation that it
  did not write the change.
- **Scope:** the security-sensitive paths reviewed.
- **Findings:** each finding with its severity and how it was resolved.
- **Automated verification:** the CodeQL, secret scanning, dependency audit and invariant
  test results it relied on.

## Example

```
# Security review: CI baseline workflows

patch-id: 0123456789abcdef0123456789abcdef01234567
verdict: READY

- Pull request: #12 "u0-repo-and-ci-baseline"
- Reviewer: separate review session (another harness); did not author the change
- Scope: .github/workflows/ci.yml, .github/workflows/codeql.yml, scripts/
- Findings: none blocking
- Automated verification: gate and CodeQL green on the head commit
```
