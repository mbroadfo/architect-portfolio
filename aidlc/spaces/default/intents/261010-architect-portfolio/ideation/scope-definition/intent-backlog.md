# Intent Backlog — Architect's Portfolio, First Release

Proto-Units derived from the scope document (`scope-document.md`) and the approved intent statement (`ideation/intent-capture/intent-statement.md`). Units Generation and Delivery Planning refine these into buildable Units; nothing here prescribes technology.

## Prioritization Method

MoSCoW for the release boundary, because the first release is a fixed slice the charter already defines. Within Must Have, items are ordered dependency-first (see Sequencing).

## Backlog

| ID | Item | Who benefits | MoSCoW | Depends on | Source |
|----|------|--------------|--------|------------|--------|
| IB-1 | Owner-only Studio sign-in; everyone else is refused | Michael (curator) | Must | — | charter §8 |
| IB-2 | Publish boundary: nothing becomes public without an explicit owner action, and discovered private material stays private | Michael; visitors | Must | IB-1 | charter §4, §5, §8 |
| IB-3 | Discover an existing GitHub repository | Michael | Must | IB-1 | charter §8 |
| IB-4 | Create a project, or link a repository to an existing project | Michael | Must | IB-3 | charter §8 |
| IB-5 | Edit exhibit narrative sections (inspiration, design challenges, architectural decisions, implementation, outcomes, lessons learned) and save them | Michael; all visitors | Must | IB-4 | charter §3, §8 |
| IB-6 | Exhibit image gallery | Clients, engineers, makers | Must | IB-5 | Q2 |
| IB-7 | Links out to repositories, live application or demo | Engineers, clients | Must | IB-5 | Q2 |
| IB-8 | Build-it-yourself material (downloadable design files, cut lists, instructions) | Makers | Must | IB-5 | Q2 |
| IB-9 | AI description suggestion, reviewable and editable, showing its source evidence | Michael | Must | IB-4 | charter §5, §8 |
| IB-10 | Preview an exhibit exactly as visitors will see it | Michael | Must | IB-5 | charter §8 |
| IB-11 | Authorize publication of an exhibit | Michael; visitors | Must | IB-2, IB-10 | charter §8 |
| IB-12 | Public exhibit page for each published project | All first-release visitors | Must | IB-11 | Q1 |
| IB-13 | Public gallery of image-led exhibit cards as the entry point, so visitors meet the creations immediately; minimal for this release (three seed cards suffice) | All first-release visitors | Must | IB-12 | Q1; owner refinement at approval |
| IB-14 | Seed exhibits published: AI Arcade, STARS, Mom's Recipe Box | All first-release visitors | Must | IB-11, IB-13 | charter §8; intent-statement (Success Metrics) |
| IB-15 | Live at michael.broadfoot.consulting with the mike.broadfoot.consulting permanent redirect, after owner approval | All visitors | Must | IB-13 | Q6; charter §2 |
| IB-16 | Withdraw (un-publish) a published exhibit | Michael | Should | IB-11 | scope-document (assumption) |
| IB-18 | Record owner time from discovery to publication | Michael | Could | IB-11 | intent-statement (Success Metrics) |

## Won't Have (this time)

| Item | Source |
|------|--------|
| Google Drive and Trimble/SketchUp connectors | intent-statement (Q8) |
| Invitation-only and other non-public access modes | intent-statement (Q8, Q10) |
| Visitor appearance customization | intent-statement (Q8) |
| Richer gallery features (featured work, discipline grouping, filtering) | Q1; owner refinement at approval |
| Aggregate per-exhibit request counting and any other visitor analytics (formerly IB-17) | Owner refinement at approval (2026-10-10) |
| Projects beyond the three seed exhibits | charter §8 |
| A second AI-assisted workflow | charter §5 |

## Sequencing

Dependency-first along the charter's slice order, with the publish boundary in place before anything is public: [assumption, confirmed in Delivery Planning]

1. Studio access and the publish boundary (IB-1, IB-2)
2. Discover, create and link (IB-3, IB-4)
3. Exhibit content and AI suggestion (IB-5 to IB-9)
4. Preview and publication (IB-10, IB-11)
5. Public pages and the seed exhibits (IB-12 to IB-14)
6. Go-live and the Should/Could items (IB-15, IB-16, IB-18)

The Won't Have items above are kept in the scope document's Future Roadmap.

Must Have items are 15 of 17. That is above the usual 60% guideline, but deliberately so: the charter fixes the slice, and the Won't Have list carries the real deferrals.

## Assumptions & Open Questions

- The order above is a proposal, because the owner left build order open; Delivery Planning settles it. [assumption]
- IB-16 (withdraw) is Should Have pending confirmation in Requirements Analysis, as recorded in the scope document. [assumption]
- Where images come from (Studio upload, GitHub, or both) affects IB-6 and is settled in Requirements Analysis. [assumption]
