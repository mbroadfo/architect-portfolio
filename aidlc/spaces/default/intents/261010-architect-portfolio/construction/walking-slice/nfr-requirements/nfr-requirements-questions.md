# NFR Requirements Questions — U0 walking-slice

**Inputs:**
- functional-spec, rules and entities: `../functional-design/`;
- requirements (NFR1 to NFR17);
- contract-summary (C2, C9, C11);
- team-practices (Testing Posture, Code Style, Deployment);
- `bolt-plan.md` Phase A;
- `nfr-requirements-questions.md`.

U0 is the delivery-only walking slice. S0 merges; S1 to S3 run only on a local stack and are never deployed. Every requirement row carries its inception NFR ID with a sub-number.

Every answer comes from approved records, under Michael's instruction to "continue autonomously" and "only escalate important decisions or mandatory human approval gates". None of these is such a decision.

## Questions

### Q1. Performance targets for a local-only slice?

A. Functional targets only: the local Publish of the fixture project finishes within 10 seconds, and API calls answer within 1 second on a developer machine. The production budgets (NFR5, NFR6) belong to U3, U7 and U8.
X. Other (please specify)

[Answer]: A — the slice is never deployed (bolt-plan Phase A). NFR5 and NFR6 are measured on the owning units in preview.

### Q2. Python web framework for the API host?

A. FastAPI, with an AWS Lambda adapter for deployment later. It generates OpenAPI, matching contract C1.
B. A plain Lambda handler with no framework.
X. Other (please specify)

[Answer]: A — charter §6 asks for a Python API on Lambda, and C1 is an OpenAPI contract. This is a routine engineering choice within the charter. U3 confirms it in its own NFR Design.

### Q3. Front-end toolchain?

A. React, TypeScript and Vite, with npm and a committed lockfile. Vitest and React Testing Library for tests, and Playwright for the slice check.
X. Other (please specify)

[Answer]: A — charter §6, team practice (Code Style, Testing Posture), and Michael's Units Generation clarification that React is used for static generation.

### Q4. How is the slice tested, and what does CI enforce?

A. Test-after for each layer. 80% line coverage for the merged S0 code (CI scripts and the guard). The slice code on its branch is tested by `make slice-check`. Every CI gate listed in team practice runs from S0 on.
X. Other (please specify)

[Answer]: A — team practice (Testing Posture, Code Style), and `rules.md` BR5.1 and BR5.2.

## Assumptions & Open Questions

None for the owner.
