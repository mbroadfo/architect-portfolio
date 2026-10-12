# Performance Requirements — U0 walking-slice

**Inputs:**
- functional-spec, rules and entities: `../functional-design/`;
- requirements (NFR1 to NFR17);
- contract-summary (C2, C9, C11);
- team-practices (Testing Posture, Code Style, Deployment);
- `bolt-plan.md` Phase A;
- `nfr-requirements-questions.md`.

U0 is the delivery-only walking slice. S0 merges; S1 to S3 run only on a local stack and are never deployed. Every requirement row carries its inception NFR ID with a sub-number.

## Requirements

| ID | Requirement | Measure |
|---|---|---|
| NFR6.1 | Local slice API calls (create, save, preview data) answer quickly enough to demonstrate | Under 1 s each on a developer machine, checked in `make slice-check` |
| NFR6.2 | A local Publish of the fixture project completes | Under 10 s, including rendering and the folder swap, checked in `make slice-check`. This is a demonstration target, not NFR5's production LCP budget, which U7 and U8 own |
| NFR13.3 | CI stays within team practice's time budget | The S0 aggregate check completes in under 10 minutes |

## Assumptions & Open Questions

- The production NFR targets are set on the owning units (U3, U7, U8, U9, U11). The slice demonstrates the path; it does not measure it.
