# Design System Mapping

## Sources and Scope

Uses wireframes and user-flow in `../../ideation/rough-mockups/`, approved corrections, requirements in `../requirements-analysis/requirements.md`, and team-practices in `../practices-discovery/team-practices.md`. User stories are skipped. A proposed first-party visual system for React/TypeScript; no dependency installed or selected.

## Proposed Tokens

| Token | Value | Use |
|---|---|---|
| canvas | `#0B1420` | Page background |
| surface | `#142234` | Cards, forms, dialogs |
| raised | `#1D3046` | Inputs, placeholders |
| text | `#F2F5F7` | Headings/body |
| muted | `#BBC8D6` | Descriptions/timestamps |
| accent | `#86E3CE` | Links, primary controls, focus |
| on-accent | `#0B1420` | Filled-button text |
| warning | `#F5CC8D` | PRIVATE/pending, with text |
| danger | `#FFB6BA` | Errors/destructive labels |
| border | `#667D95` | Form/control edges |
| spacing | 4, 8, 12, 16, 24, 32, 48, 64 px | Grouping without fixed content heights |
| radius | 6 px controls; 12 px cards | Restrained geometry |
| type | System UI sans; system monospace for metadata | No remote fonts |
| type scale | 14 metadata; 16 body; 20 subheading; 28 section; fluid 36–56 title | Relative units, wrapping |
| focus | 3 px accent ring, 3 px offset | Warm-white outer ring on navy surround for filled accent controls |
| motion | 120 ms color/opacity | No parallax/autoplay; reduced motion removes transitions |

Contrast calculations are in `verification.md`; token checks alone do not certify accessibility. Captions use opaque surfaces, never text over arbitrary images. Accent/warning/danger text sits on canvas/surface/raised, never on each other.

## Component Mapping

| Component | Semantic foundation | Screens / requirements |
|---|---|---|
| SiteHeader/Footer | header/footer/links | P1/P2; identity, All work, plain mailto once supplied; no Studio link |
| ExhibitCard | article, one link, heading/image | P1/S5; title accessible name, meaningful alt, no nested links |
| ExhibitContent | main, h1, ordered h2 | P2/S5; empty sections omitted, text escaped |
| ImageViewer | labelled dialog/buttons | P2; Escape, focus containment/return |
| StudioHeader | header/nav | S2–S5; Projects/Discover/Sign out |
| ProjectList | table or labelled list | S2; four worded statuses, take-down |
| RepositoryList | list/labels/buttons | S3; visibility/linking/search |
| FormField/AssetRow | label/input/textarea/fieldset/progress | S4; errors, lead radio, alt text |
| SuggestionPanel | aside/native buttons | S4; provider/sources/permissions/limits |
| OperationStatus | status region/activity list | S2/S4; pending distinct from saved status |
| ConfirmationDialog | dialog/headings/inventory/buttons | S6/S7; safe cancel, no implicit submit |
| ErrorSummary | alert/field anchors | S4/S6; focus summary after failed submission |

## Responsive Rules

| Width | Public | Studio |
|---|---|---|
| 320–767 px | One column, image before text, wrapping links | One column; project cards; viewport dialogs |
| 768–1023 px | Two orderly columns, third full-width | Wrapping table; AI below editor |
| 1024–1439 px | 7/5 then full-width composition | Main editor plus 320 px AI aside when it fits |
| 1440+ px | Max 1280 px; prose 68ch | Max 1440 px workspace, readable fields |

Check 320, 375, 767, 768, 900, 1023, 1024 and 1440 px and zoom. Touch controls use a project design minimum of 44×44 px with 8 px spacing; this is not claimed as a universal WCAG 2.1 AA criterion.

## Assumptions & Open Questions

No committed application library exists. Later implementation chooses components that meet these semantic contracts. No paid fonts, services or external imagery required. These token and breakpoint values remain proposals at this gate.
