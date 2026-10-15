# Scalability Design — U0 walking-slice

**Inputs:**
- U0 NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- contract-summary (C2, C9, C11);
- components;
- team-practices;
- `nfr-design-questions.md`.

U0 is the delivery-only walking slice. S0 merges to `main`; S1 to S3 run only on the local stack.

## Design

No scalability design applies: the slice is single-user and local (NFR7 N/A in the requirements). The owning units design scaling.

## Assumptions & Open Questions

- The production designs for these concerns belong to the owning units' NFR Design.
