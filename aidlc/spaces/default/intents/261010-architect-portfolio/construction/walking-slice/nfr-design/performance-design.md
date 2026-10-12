# Performance Design — U0 walking-slice

**Inputs:**
- U0 NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- contract-summary (C2, C9, C11);
- components;
- team-practices;
- `nfr-design-questions.md`.

U0 is the delivery-only walking slice. S0 merges to `main`; S1 to S3 run only on the local stack.

## Design

| ID | Design |
|---|---|
| NFR6.1 | One FastAPI process, one MongoDB connection pool, and indexed lookups on `_id` and `slug`. These are well under 1 s locally |
| NFR6.2 | One Node renderer subprocess per Publish, rendering the fixture project's few pages. Writing the release and swapping a symbolic link stay well under 10 s. `make slice-check` measures and asserts both |
| NFR13.3 | CI is split into **component jobs**, run in parallel: python, web, guard and workflow-lint, review check, gitleaks, and audit. A SHA-pinned path filter skips a component job when its paths are unchanged. One **`gate`** job declares `needs:` on all of them and runs with `if: always()`. It passes only when every needed job either succeeded or was skipped because its paths were unchanged; a failed or cancelled job, or one that should have run, fails the gate. `gate` is the single required check. CodeQL runs in its own workflow and is also required. Caching uses `setup-python` and `setup-node`, pinned |
| NFR13.4 | Coverage: `pytest --cov --cov-fail-under=80` in the python job, and Vitest `coverage.thresholds.lines: 80` in the web job |
| NFR13.5 | Audit job: `npm audit --audit-level=high`, and `pip-audit -r requirements.lock`, which fails on any finding (it has no severity filter, so this is stricter). Accepted exceptions live in a reviewed ignore file, each with a reason and an expiry date |

## Assumptions & Open Questions

- The production designs for these concerns belong to the owning units' NFR Design.
