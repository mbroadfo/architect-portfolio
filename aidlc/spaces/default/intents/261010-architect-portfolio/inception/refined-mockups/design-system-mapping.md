# Design System Mapping — Crafted Studio (R5)

## Sources and Scope

**Inputs:**

- wireframes and user-flow — `../../ideation/rough-mockups/`;
- requirements — `../requirements-analysis/requirements.md`: FR9.6 (CR-04, D-26), FR9.1, FR9.5, FR9.7, FR9.8, NFR8, NFR15;
- team-practices — `../practices-discovery/team-practices.md`.

The project has no existing design system or component library (it is greenfield). This mapping proposes one. It is the token reference that FR9.6 cites, and it becomes binding when the Refined Mockups gate is approved; until then it is the working reference.

**Implementation:** `prototype/styles.css` (tokens and public components) and `prototype/studio.css` (Studio).

## Tokens

### Colour

All values are opaque except the borders and overlays.

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0e0d0b` | Page background |
| `--bg-2` | `#13110f` | Hero bands, table header |
| `--panel` | `#181613` | Cards, panels, fieldsets |
| `--panel-2` | `#1f1c18` | Image wells, raised panels |
| `--line` | `rgba(236,224,204,.10)` | Hairline borders |
| `--line-2` | `rgba(236,224,204,.20)` | Control borders |
| `--text` | `#ede5d8` | Primary text, titles |
| `--text-2` | `#cbc1b1` | Body and narrative text |
| `--muted` | `#9d9282` | Labels, hints, metadata |
| `--brass` | `#d6a363` | Accent, primary button, eyebrows |
| `--brass-hi` | `#e6b878` | Accent hover, focus ring, warnings |
| `--brass-ink` | `#1b140b` | Text on brass |
| `--note` | `#7fd3c3` | Prototype-only scope notes and live-capture chips (not shipped) |

### Contrast

Measured by the verification suite (`T-contrast`, `prototype/tests/results.json`) on WCAG relative luminance. Every text/background pair is at least 4.5:1.

| Text \ Background | `--bg` | `--bg-2` | `--panel` | `--panel-2` |
|---|---|---|---|---|
| `--text` | 15.54 | 15.07 | 14.45 | 13.58 |
| `--text-2` | 10.92 | 10.59 | 10.15 | 9.54 |
| `--muted` | 6.35 | 6.16 | 5.90 | 5.55 |
| `--brass` | 8.58 | 8.32 | 7.98 | 7.50 |
| `--brass-hi` | 10.63 | 10.31 | 9.88 | 9.29 |

`--brass-ink` on `--brass` is 8.06; on `--brass-hi` it is 9.98.

Non-text contrast (control borders, focus ring) is not measured automatically. The focus ring uses `--brass-hi`, which is well above 3:1 on every surface. The low-alpha `--line` hairlines are decorative, and no control relies on them alone.

### Typography

All four families are self-hosted (`prototype/fonts/`, SIL Open Font License 1.1), so the public site requests nothing from third-party origins (FR9.5, NFR15).

| Role | Family | Typical size |
|---|---|---|
| Display: titles, wordmark, card titles | Cormorant Garamond 500–600 | 44–70 px heroes, 26–30 px sections, 19–26 px cards |
| Reading: narrative, summaries | Source Serif 4 400, italic for the credo | 15–17 px, line-height 1.6–1.75 |
| Interface: navigation, labels, badges, forms | Inter 400–600 | 11–14 px; uppercase eyebrows tracked 0.14–0.2 em |
| Signature | Mrs Saint Delafield | 38 px; decorative only |

### Space, shape and motion

| Token | Value |
|---|---|
| `--gutter` | `clamp(16px, 3.2vw, 48px)`; 16 px minimum on phones |
| `--radius` | 4 px (controls and images 3 px, pills 99 px) |
| `--sidebar` | 264 px (desktop, 1101 px and up) |
| `--ease` | `cubic-bezier(.2,.7,.2,1)`, 200–700 ms |
| Reduced motion | `prefers-reduced-motion: reduce` sets every transition and animation to 0 s |

## Component Mapping

| Component | Screens | Built from | Key rules |
|---|---|---|---|
| Sidebar / MobileBar / Drawer | P1–P3 | wordmark, side-nav, credo | Lists only populated categories; drawer is focus-managed, Escape closes, scrim |
| SkipLink | All | `.skip` | First focusable element; moves focus to `main` |
| FeaturedCarousel | P1 | `.hero`, `.round-btn`, dots | Manual only, polite live region, keyboard arrows, per-slide View Project / Open the App |
| CategoryTile | P1 | `.type` | Image, icon, name, line, published count; hidden when empty |
| ExhibitCard | P1, P1b, S4, S5 | `.card` | Category eyebrow, title link, summary, derived badges; pending state without link or image |
| Badge | Cards, P2 | `.badge`, `.badge--live`, `.badge--pending` | Text only, derived from access metadata (FR4.10) |
| DraftChip | All imagery | `.draft-chip`, `--live` | Every non-final image is labelled "Draft" or "Live capture" (prototype aid) |
| CategoryChips | P1b | `.chip` | `aria-current="page"` on the active chip; counts are published only |
| ExhibitHero / InPageNav / StorySection / DetailsPanel | P2 | `.exhibit-*` | Sticky in-page navigation; empty narrative sections omitted |
| Gallery / Lightbox | P2 | `.gallery`, native `<dialog>` | Buttons with names, arrows step, Escape, focus return |
| NotOnDisplay | P3 | `.missing` | Message plus link to all work; production returns 404 |
| StudioBar | S2–S9 | `.studio-bar` | Current view marked; Sign out |
| ProjectTable | S2 | `.ptable` | Becomes labelled stacked cards below 860 px; status always in words |
| Field / Fieldset / Check | S2a, S4 | `.field`, `.fs`, `.check` | Visible labels, hints before inputs, inline errors linked |
| AssetRow | S4 | `.asset` | Thumbnail, alt text, lead radio; file state Checking → Accepted |
| Panel / SuggestionPanel | S4, S5 | `.panel` | Names the provider; blocked states explained; no hidden grants |
| StudioDialog / Inventory | S2a, S6–S8 | `.sdialog`, `.inventory`, `.inv` | One scroll region, sticky actions, initial focus Cancel, blockers linked to fields |
| PreviewBanner | S5 | `.preview-banner` | "Preview — not public", always visible |

## Responsive Rules

| Width | Public site | Studio |
|---|---|---|
| ≥ 1361 px | Sidebar, hero with side image, category tiles in a row, 2-column gallery, 3-column catalog | Table, editor with aside |
| 1101–1360 px | Same | Same |
| 721–1100 px | Top bar with drawer; catalog in 2 columns; project details below the story | Editor in one column; AI skip link shown; preview stacked |
| ≤ 860 px | — | Project table becomes stacked cards; repository rows wrap |
| ≤ 720 px | Stacked hero (image, then copy), dots instead of arrows, list-style category rows, 1-column gallery and catalog, full-width actions | Navigation wraps beneath the wordmark; form rows stack; dialogs fill the width |

The verification suite checked 390, 768, 1024 and 1440 px with no horizontal overflow on any public page; Studio views were checked at 390 and 1440 px.

## Assumptions & Open Questions

- The `--note` colour and draft chips are prototype review aids and are not part of the shipped identity.
- Exact image derivative sizes for responsive delivery (NFR5) are set in NFR Design.
- Non-text contrast is reviewed visually here; implementation adds an automated check if the component library allows it.
