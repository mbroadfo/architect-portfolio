# Reliability Requirements — U0 walking-slice

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
| REL-0.1 | A failed Publish (in rendering, the transaction or the swap) leaves the previous output and the previous current version consistent. This needs multi-document transactions, so MongoDB runs as a **single-node replica set** locally and in CI | AC0.9 failure cases, run against the replica set |
| REL-0.2 | The slice keeps no data worth backing up; its local database can be recreated from the fixture | `make slice-check` starts from an empty database |

NFR10 (nightly export and tested restore) is owned by U10. The slice's REL-0.x rows are unit-level reliability rules derived from BR3.1 and BR3.3, not from NFR10.

## Assumptions & Open Questions

- The production NFR targets are set on the owning units (U3, U7, U8, U9, U11). The slice demonstrates the path; it does not measure it.
