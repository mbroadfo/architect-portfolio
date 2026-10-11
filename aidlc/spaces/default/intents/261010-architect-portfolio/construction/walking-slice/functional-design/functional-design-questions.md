# Functional Design Questions — U0 walking-slice

**Inputs:**
- unit-of-work (U0, Amendment D1);
- unit-of-work-story-map (U0 is delivery-only and owns no FR);
- requirements;
- components;
- contract-summary (C2, C9);
- the approved `bolt-plan.md`, revision 6, Phase A (S0 to S3).

Every answer below comes from those approved records. Michael's instruction at the Delivery Planning gate was to "proceed through any required one-time re-approvals and then begin the early walking slice … Continue autonomously. Only escalate important decisions or mandatory human approval gates." No question needs his judgement, so no question is put to him.

## Questions

### Q1. Which behaviour does the slice implement?

A. Only the thin path: create, save (with an optimistic revision), preview, and Publish on explicit confirmation to a local static folder. Plus S0's repository layout and CI baseline.
B. A broader subset of the Studio.
X. Other (please specify)

[Answer]: A — `bolt-plan.md` Phase A sets out S0 to S3. Everything else belongs to the owning units.

### Q2. How is the owner identified locally?

A. A local-only fake identity provider issues tokens. The slice checks issuer plus subject exactly as FR1.1 requires, and an S0 build-time guard forbids the fake in any non-local artifact.
B. No authentication locally.
X. Other (please specify)

[Answer]: A — the plan's S1 scope and DoD; FR1.1 and FR1.2; and team practice ("production code gets no way around authentication").

### Q3. What does Publish produce?

A. A frozen candidate validated against the approved C2 schema, rendered by a thin React static renderer, written to a local public folder that a local static server serves. No storage, CDN or remote write.
B. Write directly to cloud storage.
X. Other (please specify)

[Answer]: A — the plan's S2 scope, ADR-002, and C2. The slice is never deployed.

### Q4. Which data does the slice use?

A. Placeholder text and one bundled fixture image, with no real project content and no withheld values.
X. Other (please specify)

[Answer]: A — the plan's slice boundaries and FR10.7 (withheld values never in this repository).

### Q5. What happens to the slice code?

A. S0 merges. S1 to S3 stay on `slice/walking-slice` as a reference: they are never merged or deployed, are taken over by the owning units through their own Bolts, and the branch is archived once U9 lands.
X. Other (please specify)

[Answer]: A — the plan's Phase A ("Only S0 merges").

## Assumptions & Open Questions

None for the owner.
