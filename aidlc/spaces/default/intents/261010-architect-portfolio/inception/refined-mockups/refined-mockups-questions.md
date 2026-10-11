# Refined Mockups — Design Inputs

## Sources

Every topic below is answered by approved records or by explicit owner direction. They are carried forward, not attributed as new owner answers, and no unresolved owner choice blocks the design proposal. Summary confirmation is off for this workflow (P-03), so no questionnaire was issued.

**Inputs:**

- wireframes — `../../ideation/rough-mockups/wireframes.md`;
- user-flow — `../../ideation/rough-mockups/user-flow.md`;
- `../../ideation/rough-mockups/proposed-default-fixes.md`;
- requirements — `../requirements-analysis/requirements.md`, Amendment A1 to A1.2;
- team-practices — `../practices-discovery/team-practices.md`;
- the owner's direction of 2026-10-10: the concept board, the R4 and R5 feedback, and the "Autonomous Continuation" instruction authorizing CR-01 to CR-05.

User Stories is skipped in the approved plan; no stories artifact is invented.

## Resolved Topics

| Topic | Established answer | Evidence |
|---|---|---|
| Screens and navigation | Public: home (featured carousel, categories, gallery), catalog and category pages, project case study, not-on-display. Studio: sign-in, Projects, new project, Discover, editor, preview, publish/update and take-down confirmations, featured order, activity | Rough Mockups Q1–Q3; FR1–FR10; CR-05 |
| Visual direction | Crafted studio: warm charcoal, brass, editorial serif type, sophisticated imagery, restrained interaction. Baseline is prototype R5 and the owner's concept board | CR-04, D-26, FR9.6; owner direction 2026-10-10 |
| Launch content | STARS, Monopoly (working title "Monopoly Arena"), Baduk, Risk. Each needs individual approval; any approved subset may launch | CR-01, D-23, FR10.1 |
| Organisation | One primary category per project, from four fixed categories; empty categories hidden; featured order confirmed separately | CR-05, D-27, FR9.1, FR9.7, FR9.8 |
| Projects without GitHub | Title-only creation; repositories optional; AI suggestions only with a repository | CR-02, D-24, FR3.1, FR5.1 |
| Access indicators | Badges derived from access metadata; "Source available" vs "Open source"; fail closed on unconfirmed visibility | CR-03, D-25, FR4.10 |
| Responsive structure | Phones single column; tablet two columns; desktop sidebar with a wide hero. Studio desktop-first, usable on phones | D-16 as amended by D-26; FR9.1 |
| Accessibility | WCAG 2.1 AA: keyboard, visible focus, skip link, alt text, 4.5:1 contrast, reduced motion, no autoplay | Rough Mockups Q6; NFR8; FR9.7 |
| Save, AI and publication | Explicit Save; preview of card, carousel and category; full inventory at Publish; private code links omitted; reachability is not approval | FR3–FR7, FR10.5; D-15, D-20, D-22 |
| Exclusions | No tags, journal, search, analytics, visitor accounts, appearance controls or new connectors in v1 | D-04, D-08, D-17, D-27 |

## Assumptions & Open Questions

- Visual tokens, spacing and breakpoints are designer proposals that become the FR9.6 reference when the gate is approved.
- Imagery is either a labelled live capture of a public app or labelled concept art. Copy is drafted from public READMEs. Neither is approved for publication.
- **Owner inputs before launch:** imagery, approved copy, biography, contact email.
- **Owner decisions** (D-28): the trademark and artwork review for Monopoly and Risk; licensing for STARS and Monopoly; authorizing Risk's live URL; per-candidate publication.
- **Later stages:** the AI provider and framework, GitHub credential mechanism, secure edit recovery, rate limits, image pixel limit and link-check isolation.
- The stale spa-on-aws charter statement is tracked by issue #2.
