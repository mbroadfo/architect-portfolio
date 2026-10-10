# Refined Mockups — Design Inputs

## Sources

These topics are answered by approved records, carried forward rather than attributed as new owner answers. No unresolved owner choice prevents a design proposal. Dimensions, tokens and component details remain proposed for this stage gate.

Inputs: `../../ideation/rough-mockups/wireframes.md` (wireframes), `../../ideation/rough-mockups/user-flow.md` (user-flow), `../../ideation/rough-mockups/proposed-default-fixes.md`, `../requirements-analysis/requirements.md` (requirements), and `../practices-discovery/team-practices.md` (team-practices). User Stories is skipped in the approved plan; no stories artifact is invented.

## Resolved Topics

| Topic | Established answer | Evidence |
|---|---|---|
| Screens and navigation | Gallery, exhibit, sign-in, Projects, Discover, editor, private preview, publication and take-down confirmations | Rough Mockups Q1–Q3; FR1–FR9 |
| Visual direction | Engineering Studio: dark navy, precise typography, real imagery; Exhibition wall Concept A | Rough Mockups Q4; D-14; FR9.6 |
| Responsive structure | Public gallery single column on phones, varied orderly tiles from tablet width; Studio desktop-first, usable on tablet | Rough Mockups Q5; D-16; FR9.1 |
| Accessibility | Public and Studio WCAG 2.1 AA, keyboard operation, visible focus, alt text, contrast, reduced motion | Rough Mockups Q6; NFR8 |
| Save and AI | Explicit Save; suggestions show sources and Insert/Edit/Discard; no automatic text overwrite | user-flow step 4; FR3.3–FR5.9 |
| Publication | Private preview includes card and page; all public content explicitly confirmed; private code links omitted | D-15, D-20, D-22; FR6–FR7 |
| Failure states | Empty, loading, errors, conflict, expired session, AI timeout/limit/approval block, publication failure | FR1.4, FR2.4, FR3.4, FR5.7–FR5.9, FR7.8 |
| Exclusions | No tags, appearance controls, tracking, visitor accounts or new connectors | D-04, D-08, D-13, D-17 |

## Assumptions & Open Questions

- Visual tokens, spacing, breakpoints and detailed interactions are designer proposals for review, not new approved requirements.
- The board uses labelled sample text and neutral image placeholders. Seed titles are approved; no private repository content is fetched.
- Actual imagery, final exhibit copy and contact email are owner inputs before launch, not authorization to publish sample material.
- AI provider/framework, GitHub credential mechanism, secure edit recovery, rate limits and infrastructure permission stay with the later design stages named in requirements.
- The stale spa-on-aws charter statement remains tracked by issue #2; it is not silently corrected here.
