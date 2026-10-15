# Observability Design — U0 walking-slice

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
| NFR11.1 | A request-id middleware reads `X-Request-Id`, or generates one, and echoes it. Logs are JSON lines with `request_id`, `method`, `route`, `status` and `duration_ms`. A redaction filter removes `Authorization` and token-like values. A unit test checks the format and the redaction |
| NFR13.2 | The aggregate job's summary (`$GITHUB_STEP_SUMMARY`) lists each component step as run, skipped or failed |

## Assumptions & Open Questions

- The production designs for these concerns belong to the owning units' NFR Design.
