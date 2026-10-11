# Ideation Decision Log — Architect's Portfolio

Every decision made during Ideation, so later stages and other AI assistants reuse them instead of re-asking (team rule, `aidlc/spaces/default/memory/team.md` ## Mandated). All dates are 2026-10-10; the decider is Michael Broadfoot unless noted.

## Decisions

| ID | Decision | Made at | Source |
|----|----------|---------|--------|
| D-01 | The portfolio solves four problems: scattered work, a credible showcase for consulting, sharing with makers and engineers, and low-effort curation | Intent Capture | intent-statement (Q1) |
| D-02 | First-release audiences: clients and employers, engineers, makers; invited people come in a later version | Intent Capture | intent-statement (Q2, Q9, Q10) |
| D-03 | Success: the three seed exhibits published; repository-to-publish time measured, target set after first use | Intent Capture, refined at Scope Definition | intent-statement (Q3, Q11); scope-document |
| D-04 | No visitor analytics of any kind in the first release (aggregate request counting deferred) | Scope Definition approval | scope-document |
| D-05 | Triggers: consulting presence, body of work ready, AI-DLC showcase, personal milestone | Intent Capture | intent-statement (Q4) |
| D-06 | Michael is the sole stakeholder and decides scope, priority and publication; AI agents propose | Intent Capture | stakeholder-map (Q5, Q6) |
| D-07 | Progress lives in the GitHub repository; no formal reporting cadence | Intent Capture | stakeholder-map (Q7) |
| D-08 | Out of the first release: Drive and SketchUp connectors, non-public access, appearance customization | Intent Capture | intent-statement (Q8) |
| D-09 | Public side: an exhibit page per published project and an image-led gallery as the entry point (three seed cards suffice) | Scope Definition, refined at approval | scope-document (Q1) |
| D-10 | Exhibits carry the narrative sections, an image gallery, links out, and build-it-yourself material | Scope Definition | scope-document (Q2) |
| D-11 | No deadline; scheduled by readiness | Scope Definition (agent, on owner's instruction) | scope-document (Q5) |
| D-12 | Done means live at michael.broadfoot.consulting with the mike. permanent redirect; every deploy and DNS step needs owner approval | Scope Definition (agent, on owner's instruction, from charter §2) | scope-document (Q6) |
| D-13 | Roadmap, not this release: appearance customization, richer gallery and filtering, invitation-only access, external connectors | Scope Definition approval | scope-document (Future Roadmap) |
| D-14 | Gallery concept A, "Exhibition wall": compelling imagery, responsive and orderly layout | Rough Mockups | proposed-default-fixes |
| D-15 | Hide "View code" for private repositories | Rough Mockups approval | proposed-default-fixes (R-01) |
| D-16 | Single column on phones; varied tiles from tablet width up, in an orderly grid | Rough Mockups approval | proposed-default-fixes (R-02) |
| D-17 | No topic tags in the first release | Rough Mockups approval | proposed-default-fixes (R-03) |
| D-18 | Footer contact as a plain email link that collects no visitor data | Rough Mockups approval | proposed-default-fixes (R-04) |
| D-19 | A lead image with alt text is required to publish | Rough Mockups approval | proposed-default-fixes (R-05) |
| D-20 | Take down is available on the Projects list and in the editor; preview shows the gallery card | Rough Mockups approval | proposed-default-fixes (R-06) |
| D-21 | Take down / Unpublish is Must Have for the first release | Rough Mockups approval | proposed-default-fixes |
| D-22 | Publish approval covers all public content (text, media, files, links, AI-generated text, including text from private sources); private material is never exposed automatically | Rough Mockups approval | proposed-default-fixes |

## Decisions After Ideation (Requirements Amendment A1)

Authority for D-23 to D-28: Michael Broadfoot's instruction "Architect Portfolio — Autonomous Continuation", 2026-10-10, which authorized change requests CR-01 to CR-05 and set the interim positions in D-28. The text was refined by the independent architecture review the owner relayed. These decisions authorize requirements and design work only. They do not authorize deployment, publication of any particular project, or approval of any stage gate.

The proposal, review history and evidence are in `inception/refined-mockups/requirements-change-proposal.md` and `launch-inventory.md`. The amended requirements are in `inception/requirements-analysis/requirements.md` (Amendment A1).

| ID | Decision | Made at | Source |
|----|----------|---------|--------|
| D-23 | **Launch candidates (CR-01).** STARS, Monopoly Arena, Baduk and Risk replace the seed exhibits AI Arcade, STARS and Mom's Recipe Box. Each is eligible for publication on its own, none is mandatory, and launch may proceed with any approved subset. Each candidate's content, imagery, rights, public URL and publication need individual owner approval. Supersedes the "three seed exhibits" in D-03 and D-09; the rest of those decisions stands. | Refined Mockups (owner instruction) | FR10.1, FR10.6, FR10.7 |
| D-24 | **Optional GitHub (CR-02).** A project can start with only a title; repositories are optional associations. Woodworking, CAD, design documents and software are supported equally. Attachments: PDF, SKP, FCStd, DXF, STL, ZIP, VSDX, up to 50 MB. HEIC photos are converted to sanitized web images. Other formats are deferred. The GitHub-based AI suggestion workflow is unchanged. D-08 (GitHub is the only connector) stands. | Refined Mockups (owner instruction) | FR3.1, FR3.5, FR4.2, FR4.4, FR4.9, FR5.1 |
| D-25 | **Deployment metadata (CR-03).** Each exhibit records availability, access requirement, repository visibility, licence and phone suitability. A link check at publication means "Reachable", never Verified, Safe or Approved. SSRF protections are mandatory, and their implementation gets an independent security review. No automated public-content changes and no scheduled link monitoring. | Refined Mockups (owner instruction) | FR4.10, FR7.2, FR10.5, NFR17 |
| D-26 | **Visual identity (CR-04).** The crafted studio aesthetic replaces the charter's dark-navy "Engineering Studio" direction: warm charcoal, brass accents, editorial typography, sophisticated imagery, restrained interaction. Includes the R5 equal-card exhibit grid, which replaces D-16's varied tiles (FR9.1). | Refined Mockups (owner instruction) | FR9.6 |
| D-27 | **Featured projects and categories (CR-05).** The first release has featured work, a manual carousel and category browsing. One primary category per project in v1, modelled as a project-to-category relationship so multiple classifications need no migration later. No journal, search, analytics, topic tags or visitor accounts in v1. Narrows D-13 ("richer gallery"): featured work and grouping move into v1, while filtering, tags and search stay on the roadmap. | Refined Mockups (owner instruction) | FR9.1, FR9.7, FR9.8 |
| D-28 | **Interim positions until decided separately.** Monopoly and Risk keep provisional names and safe placeholder imagery pending a trademark and artwork review. STARS and Monopoly keep their current unlicensed status, and no open-source licence is invented. Risk's private source and live URL stay out of every public artifact until explicitly authorized after a privacy and security review. | Refined Mockups (owner instruction) | FR10.6, FR10.7; launch-inventory.md |

## Process Decisions

| ID | Decision | Source |
|----|----------|--------|
| P-01 | Workflow plan: tailored "portfolio-inception-slice" on the classic base (21 stages), Guard Policy off, full reviews | approved at workflow start |
| P-02 | Approved decisions are recorded in version control and reused; stage observations do not become permanent rules | team.md ## Mandated |
| P-03 | Learnings and summary-confirmation questionnaires are off for this workflow; routine questions are answered from the charter and record, and only genuinely open questions are batched to the owner | owner instruction at Scope Definition |
| P-04 | Approved stage artifacts are committed and pushed for the independent architecture reviewer | owner instruction at Scope Definition approval |
| P-05 | Claude Code is lead engineering agent and sole AI-DLC workflow owner. It proceeds autonomously on routine design, documentation, engineering, testing and workflow matters, and escalates only material decisions: new costs, production or DNS changes, making private information public, final publication approval, material authentication, authorization or privacy changes, destructive actions, significant legal, trademark, licensing or security risk, unrecoverable audit issues, and mandatory human gates. | owner instruction "Architect Portfolio — Autonomous Continuation", 2026-10-10 |

## Assumptions & Open Questions

None. Open items with owning stages are listed in initiative-brief.md.
