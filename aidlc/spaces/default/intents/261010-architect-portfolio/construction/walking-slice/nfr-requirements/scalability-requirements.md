# Scalability Requirements — U0 walking-slice

**Inputs:**
- functional-spec, rules and entities: `../functional-design/`;
- requirements (NFR1 to NFR17);
- contract-summary (C2, C9, C11);
- team-practices (Testing Posture, Code Style, Deployment);
- `bolt-plan.md` Phase A;
- `nfr-requirements-questions.md`.

U0 is the delivery-only walking slice. S0 merges; S1 to S3 run only on a local stack and are never deployed. Every requirement row carries its inception NFR ID with a sub-number.

## Requirements

| ID | Requirement |
|---|---|
No scalability requirement applies to the slice. It is a single-user local demonstration. NFR7 is owned by U3, U7 and U8, which run on pay-per-use serverless services. The traceability marks it N/A.

## Assumptions & Open Questions

- The production NFR targets are set on the owning units (U3, U7, U8, U9, U11). The slice demonstrates the path; it does not measure it.
