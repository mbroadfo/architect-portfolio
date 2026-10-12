# Observability Requirements — U0 walking-slice

**Inputs:**
- functional-spec, rules and entities: `../functional-design/`;
- requirements (NFR1 to NFR17);
- contract-summary (C2, C9, C11);
- team-practices (Testing Posture, Code Style, Deployment);
- `bolt-plan.md` Phase A;
- `nfr-requirements-questions.md`.

U0 is the delivery-only walking slice. S0 merges; S1 to S3 run only on a local stack and are never deployed. Every requirement row carries its inception NFR ID with a sub-number.

## Requirements

| ID | Requirement | Verification |
|---|---|---|
| NFR11.1 | Every API request is logged with a request id, method, route, status and duration. Never tokens, keys or personal data | A unit test on the log format |
| NFR11.2 | A health route returns only `{"status":"ok"}` | AC0.1 (exempt route) |
| NFR13.2 | CI shows each sub-check's result under the aggregate check | AC0.10 |

## Assumptions & Open Questions

- The production NFR targets are set on the owning units (U3, U7, U8, U9, U11). The slice demonstrates the path; it does not measure it.
