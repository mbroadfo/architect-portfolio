# Refined Mockups — Michael Broadfoot’s Studio

## Review Surface and Sources

Open `design-board.html` locally for desktop and phone compositions and critical state specimens. It has no scripts, external resources, live data or network calls. It is a static design artifact, not an application or proof of implemented security. All imagery is conceptual moodboard only; real project photography, screenshots, CAD renders and workshop photos will replace placeholders later.

Inputs: `../../ideation/rough-mockups/wireframes.md` (wireframes), `../../ideation/rough-mockups/user-flow.md` (user-flow), approved `proposed-default-fixes.md` beside them, `../requirements-analysis/requirements.md` (requirements), and `../practices-discovery/team-practices.md` (team-practices). User stories are skipped. Requirement IDs provide traceability.

All six approved corrections are incorporated: private code links hidden; phone grid stacked; tags removed; plain email contact; lead image and alt text required; take-down in list/editor and gallery card in preview. Requirements add Taken down status, upload validation, exact publication content, owner authentication and AI permissions.

## Visual Proposal

The public experience is framed as “Michael Broadfoot’s Studio — Selected Works”. It feels like a professional systems architect’s and maker’s curated studio: crafted, warm, cinematic, editorial, premium, technical and intentional.

Base: deep charcoal / blue-black (#0D1117, #11151C).  
Accents: warm walnut/bronze/brass (#8B5E3C, #C9A66B, #A67C52).  
Secondary surfaces: parchment/cream where useful (#F5F0E6).  
Imagery is large and cinematic. Typography has strong hierarchy. Less dashboard cards, more studio presence and selected works.

No fake wood overkill. Suggest materiality and premium craft.

Proposed tokens are in `design-system-mapping.md`.

Image placeholders explicitly request real screenshots, workshop photos, CAD / SketchUp / FreeCAD images, diagrams and code visuals; they do not pretend to depict finished projects. Sample descriptions require separate content approval before publication.

## Public Portfolio Structure

### 1. Hero / Identity Section (P1 Home)
- Name: MICHAEL BROADFOOT
- Positioning: Systems Architect · Engineer · Maker
- Concise statement: I architect software, systems and crafted artifacts that are precise, honest and worth keeping.
- Visually compelling lead image or montage (concept: workshop + code + architecture drawing)
- Subtle invitation to explore selected works.

### 2. Featured Work
One prominent flagship (e.g. a browser-ready app from the first-release focus).
- Large cinematic image
- Short narrative teaser
- Clear access mode (e.g. “Try in browser”)
- Link to full case study

### 3. Selected Works / Categories
Organized, beautiful discovery area.
- Grouped by project category (Browser Apps first for v1; later Woodworking / Physical Making, Architecture / Cloud, AI / Experiments, etc.)
- Within categories, cards or entries also surface access / interaction mode (Try, View source, Download & build, Read case study, Invitation only, etc.)
- Not a flat cluttered wall or interchangeable grid. Curated presence. Category-driven browsing with clear mode indicators.
- Supports growth: new categories and modes slot in without redesign.

### 4. How I Think / Approach
Editorial section on architectural thinking, constraints, prototypes, system design mindset, craftsmanship.
- Short pieces or excerpts that feel like studio notes.

### 5. Project Detail / Case Study Page (P2)
For each project:
- Lead image (cinematic)
- Summary
- Category (e.g. Browser Apps)
- Access / interaction mode (e.g. Try in browser • View source)
- Narrative / case study (inspiration, design challenges, architectural decisions, implementation, outcomes, lessons)
- Gallery (real images later)
- Build files / repo / external links as appropriate, with proper private-repo handling
- Lifecycle state indicators only where relevant to the visitor (published / taken down handled gracefully)

## Screen Specifications (Revised Public)

| Screen | Desktop composition | Phone/tablet adaptation | Traceability |
|---|---|---|---|
| P1 Home (Studio) | Hero with name + positioning + lead montage; Featured flagship below; Selected Works by category (curated groups, not dense grid); How I Think section; Footer with plain contact. | Stacked: hero, featured, categories (cards or list), approach notes. | FR9, new direction |
| P2 Project Detail | Lead image; title + category + access mode; summary; narrative sections; gallery; build/repo links; back to studio. | Same order, wrapping; image enlargement in accessible dialog. | FR4, FR9 |
| (Studio screens S1–S7 remain largely as previously approved — functional and restrained) | ... | ... | Preserve approved workflows |

## Screen State Matrix (Updated for new public)

| Screen | Empty | Loading / operation | Success | Error / partial |
|---|---|---|---|---|
| P1 | Quiet “New work is being installed.” with presence | Reserved image space | Featured + curated categories visible | Failed image keeps context and link |
| P2 | Omit absent blocks gracefully | Reserved image | Full approved case study | Unknown/taken down: graceful “not on display” with navigation; real HTTP 404 |

(Studio states preserved from prior approved version.)

## Requirements Coverage

(Updated to reflect new public structure while preserving all prior FR/NFR coverage for Studio, publication boundary, auth, etc.)

| Group | Coverage / implementation obligation |
|---|---|
| FR1–FR8 | Studio workflows unchanged (sign-in, discovery, edit, preview, explicit publish, take-down). |
| FR9 | Public now restructured as Studio / Selected Works with hero, featured, category browsing, approach section, detail pages. No analytics/accounts/tags, plain contact. |
| FR10 | Seed titles on concept board only. |
| NFRs | Accessibility, privacy, performance, security boundaries, cost gates preserved. New visual tokens must still meet contrast and touch targets. |

## Assumptions & Open Questions

This proposes a new public-facing identity and structure. The private Studio, publishing controls, security boundaries and all approved requirements remain valid and are not reopened.

Imagery is concept only. Real project assets will be supplied later.

Content approval, spending approval, deployment approval and this design gate are separate decisions.

Secure recovery, provider choice, infrastructure remain architecture work.

## Design Notes for Expansion

The category + access-mode + lifecycle separation allows graceful growth:
- Browser Apps start as primary v1 class.
- Woodworking, cloud architecture, AI experiments, downloadable tools, invitation-only items add new categories or modes without breaking the system.
- Curated “Selected Works” prevents the “zoo of unrelated creations” feel.

The design starts focused and extends. 
