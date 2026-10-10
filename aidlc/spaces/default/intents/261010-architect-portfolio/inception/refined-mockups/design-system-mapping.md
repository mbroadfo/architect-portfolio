# Design System Mapping

## Sources and Scope

Uses wireframes and user-flow in `../../ideation/rough-mockups/`, approved corrections, requirements in `../requirements-analysis/requirements.md`, and team-practices in `../practices-discovery/team-practices.md`. User stories are skipped. A proposed first-party visual system for React/TypeScript; no dependency installed or selected.

## Proposed Tokens (Revised Premium Craft Direction)

| Token | Value | Use |
|---|---|---|
| canvas | #0D1117 | Deep charcoal / blue-black page background |
| surface | #1A1F26 | Cards, forms, dialogs, secondary surfaces |
| raised | #252B33 | Inputs, elevated elements |
| text | #F5F0E6 | Headings/body (parchment/cream lean) |
| muted | #A8B0B8 | Descriptions, timestamps |
| accent | #C9A66B | Bronze/brass links, primary controls, focus |
| on-accent | #0D1117 | Text on filled accent |
| walnut | #5C4033 | Warm accent for craft elements |
| border | #4A5563 | Form/control edges |
| spacing | 4, 8, 12, 16, 24, 32, 48, 64, 96 px | Generous, intentional grouping |
| radius | 4 px controls; 8 px cards | Restrained, crafted geometry |
| type | System UI sans; system monospace for metadata | No remote fonts. Strong hierarchy |
| type scale | 13 metadata; 16 body; 18–20 subheading; 24–28 section; fluid 32–60 title | Editorial presence |
| focus | 2 px bronze ring, 2 px offset | Warm, visible on dark |
| motion | 150 ms color/opacity/ease | Cinematic but restrained; reduced motion disables |
| imagery | Large cinematic, real later | Moodboard placeholders only for now |

Contrast and accessibility calculations remain in verification.md. Tokens chosen for premium, warm, technical feel on dark base.

## Component Mapping (Updated for New Public Structure)

| Component | Semantic foundation | Screens / requirements |
|---|---|---|
| SiteHeader | header/nav/identity | P1 hero; name, positioning, navigation to categories/approach |
| Hero | section with lead imagery | P1; name, statement, montage |
| FeaturedWork | article, strong image, teaser | P1; flagship with access mode |
| CategorySection | section, curated groups | P1; Selected Works by category, showing access modes |
| ApproachSection | editorial prose | P1; how I think / craftsmanship |
| ProjectCard | curated entry, not generic | P1/P2; category + mode visible |
| ProjectDetail | main, h1, ordered sections | P2; lead, summary, category, access mode, narrative, gallery, links |
| ImageViewer | labelled dialog | P2; Escape, focus return |
| (Studio components S1–S7) | header, lists, forms, dialogs | Preserved as functional/restrained admin |

## Responsive Rules

| Width | Public | Studio |
|---|---|---|
| 320–767 px | Stacked hero → featured → categories (beautiful list or cards) → approach | One column; functional cards; viewport dialogs |
| 768–1023 px | Two-column where helpful; featured prominent | Wrapping; AI below |
| 1024–1439 px | Hero with presence; curated grid or masonry-feel for categories | Main + aside |
| 1440+ px | Max 1280–1440 px content; generous whitespace; cinematic imagery | Max 1440 px workspace |

Check 320, 375, 767, 768, 1024, 1440 px and 200%/400% zoom. Touch targets 44×44 px minimum with 8 px separation (project usability convention, not claimed universal WCAG).

## Assumptions & Open Questions

No committed application library. Later implementation chooses components that meet these semantic and visual contracts. No paid fonts. Imagery will be real project assets. Tokens are proposals at this gate. The new direction starts with browser apps but the category + mode separation supports expansion to woodworking, cloud, AI, downloads, etc.

Studio remains functional and restrained; public experience carries the crafted, premium identity.
