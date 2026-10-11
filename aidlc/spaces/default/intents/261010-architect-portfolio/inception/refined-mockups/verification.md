# Refined Mockups — Verification (R5)

## Scope

Results of `prototype/tests/verify.cjs`, run 2026-10-11T15:06:04.564Z. The suite uses Chromium (Playwright 1.64) and axe-core 4.10.2 against the prototype, served from a local HTTP server on 127.0.0.1. **182 of 182 checks passed.**

- Raw evidence for every check is in `prototype/tests/results.json`; evidence is snapshotted when each check runs.
- The 61 screenshots are in `screenshots/r5-revision/`. All are genuine renders from the suite, and all are distinct: 61 files, 61 unique hashes.

Verified against:

- requirements — `../requirements-analysis/requirements.md`, Amendment A1 to A1.2;
- wireframes and user-flow — `../../ideation/rough-mockups/`;
- team-practices — `../practices-discovery/team-practices.md`.

This is design evidence for the prototype. It does not certify the built application; see Not Verified Here.

## Results by Area

| Area | Checks | Passed |
|---|---|---|
| Responsive and runtime — no horizontal overflow, no console errors (public pages at 390, 768, 1024 and 1440 px; Studio views at 390 and 1440 px) | 76 | 76 |
| Accessibility — axe-core 4.10.2: no serious or critical violations, and no console errors during the axe run | 24 | 24 |
| Privacy — no request to any origin other than the local test server (FR9.5, NFR15) | 24 | 24 |
| Keyboard and focus | 3 | 3 |
| Carousel and motion | 4 | 4 |
| Dialogs | 1 | 1 |
| Public-site rules (design-review view) | 5 | 5 |
| Approved-publication export — payload, schema, assets, every route incl. direct routes to Monopoly and Risk, derived featured/categories/counts | 15 | 15 |
| Footer and email (FR9.4) | 16 | 16 |
| Studio workflows | 12 | 12 |
| Contrast (text and non-text) | 2 | 2 |

## Behavioural Checks

| ID | Check | Result |
|---|---|---|
| K-skip | First Tab lands on 'Skip to content' (WCAG 2.4.1) | PASS |
| K-skip-target | Activating the skip link moves focus to main content | PASS |
| K-focus-visible | Keyboard focus shows a visible outline | PASS |
| C-no-autoplay | Carousel does not advance on its own after 6 s (FR9.7, WCAG 2.2.2) | PASS |
| C-keyboard | Carousel next control and ArrowRight advance it; slide copy is announced politely | PASS |
| C-links | Featured slide links to its project page | PASS |
| M-reduced-motion | Reduced motion removes the carousel transition | PASS |
| F-empty-category | A category with no published exhibit is not on display (FR9.8) | PASS |
| F-counts | Category counts include published exhibits only (FR9.1) | PASS |
| F-risk-nolink | Unapproved Risk card has no link and no live URL | PASS |
| F-home-categories | Home shows only populated categories (FR9.1) | PASS |
| F-mobile-actions | Project page on a phone shows both Open the app and View source | PASS |
| X-payload | Export payload (26 files) contains no identifier of an unapproved candidate — Monopoly or Risk names, slugs, live hosts or assets | PASS |
| X-schema | Snapshot holds only approved projects with allow-listed fields: no publication state, access internals or private repositories (FR4.10) | PASS |
| X-assets | Export ships exactly the assets its approved projects reference, and no draft or unapproved art | PASS |
| X-route-index | export/index.html: no unapproved data in the rendered page or the loaded data, and every request stays inside export/ | PASS |
| X-route-catalog | export/catalog.html: no unapproved data in the rendered page or the loaded data, and every request stays inside export/ | PASS |
| X-route-catalog-category-games | export/catalog.html?category=games: no unapproved data in the rendered page or the loaded data, and every request stays inside export/ | PASS |
| X-route-catalog-category-astronomy | export/catalog.html?category=astronomy: no unapproved data in the rendered page or the loaded data, and every request stays inside export/ | PASS |
| X-route-project-p-stars | export/project.html?p=stars: no unapproved data in the rendered page or the loaded data, and every request stays inside export/ | PASS |
| X-route-project-p-baduk | export/project.html?p=baduk: no unapproved data in the rendered page or the loaded data, and every request stays inside export/ | PASS |
| X-route-project-p-monopoly-arena | export/project.html?p=monopoly-arena: no unapproved data in the rendered page or the loaded data, and every request stays inside export/ | PASS |
| X-direct-project-p-monopoly-arena | export/project.html?p=monopoly-arena: a direct route to an unapproved candidate shows "isn't on display" (FR9.3) | PASS |
| X-route-project-p-risk | export/project.html?p=risk: no unapproved data in the rendered page or the loaded data, and every request stays inside export/ | PASS |
| X-direct-project-p-risk | export/project.html?p=risk: a direct route to an unapproved candidate shows "isn't on display" (FR9.3) | PASS |
| X-derived-home | Export home: carousel, category tiles, counts and gallery come only from approved projects (STARS, Baduk) | PASS |
| X-derived-catalog | Export catalog and category page list and count only approved projects | PASS |
| E-footer-index-html | index.html: footer present once with the GitHub link and copyright (FR9.4) | PASS |
| E-email-index-html | index.html: no fake Email link — a real mailto: link, or the owner-content dependency shown as text | PASS |
| E-footer-catalog-html | catalog.html: footer present once with the GitHub link and copyright (FR9.4) | PASS |
| E-email-catalog-html | catalog.html: no fake Email link — a real mailto: link, or the owner-content dependency shown as text | PASS |
| E-footer-project-html-p-stars | project.html?p=stars: footer present once with the GitHub link and copyright (FR9.4) | PASS |
| E-email-project-html-p-stars | project.html?p=stars: no fake Email link — a real mailto: link, or the owner-content dependency shown as text | PASS |
| E-footer-project-html-p-risk | project.html?p=risk: footer present once with the GitHub link and copyright (FR9.4) | PASS |
| E-email-project-html-p-risk | project.html?p=risk: no fake Email link — a real mailto: link, or the owner-content dependency shown as text | PASS |
| E-footer-export-index-html | export/index.html: footer present once with the GitHub link and copyright (FR9.4) | PASS |
| E-email-export-index-html | export/index.html: no fake Email link — a real mailto: link, or the owner-content dependency shown as text | PASS |
| E-footer-export-catalog-html | export/catalog.html: footer present once with the GitHub link and copyright (FR9.4) | PASS |
| E-email-export-catalog-html | export/catalog.html: no fake Email link — a real mailto: link, or the owner-content dependency shown as text | PASS |
| E-footer-export-project-html-p-stars | export/project.html?p=stars: footer present once with the GitHub link and copyright (FR9.4) | PASS |
| E-email-export-project-html-p-stars | export/project.html?p=stars: no fake Email link — a real mailto: link, or the owner-content dependency shown as text | PASS |
| E-footer-export-project-html-p-monopoly-arena | export/project.html?p=monopoly-arena: footer present once with the GitHub link and copyright (FR9.4) | PASS |
| E-email-export-project-html-p-monopoly-arena | export/project.html?p=monopoly-arena: no fake Email link — a real mailto: link, or the owner-content dependency shown as text | PASS |
| D-lightbox | Gallery opens an enlarged view by keyboard, arrows step, Escape closes and focus returns (FR9.2) | PASS |
| S-title-only | A project can be created with only a title; it starts as Draft with no repository, and the AI panel says suggestions need a repository (FR3.1, FR5.1) | PASS |
| S-placeholder | A title-only project's card says it needs a lead image, and never claims a private source it doesn't have | PASS |
| S-publish-blocked | Publish is blocked with linked reasons when there's no lead image; initial focus is Cancel (FR7.3) | PASS |
| S-file-inventory | Publish confirmation lists attachment metadata and ZIP entries, published unchanged (FR7.2) | PASS |
| S-escape | Escape cancels the confirmation | PASS |
| S-leave-guard | Leaving with unsaved changes asks first, Stay focused (FR4.6) | PASS |
| S-rights-block | Monopoly cannot be published while the rights review is outstanding (FR10.6) | PASS |
| S-risk-url | Risk's live URL is excluded until authorized; the private repository is never named (FR10.7) | PASS |
| S-reachable | Ready update shows 'Reachable', never 'Verified', 'Safe' or 'Approved' (FR10.5) | PASS |
| S-published | Confirming moves Changes since last publish to Published (FR3.2) | PASS |
| S-takedown | Take-down names the exhibit, covers the carousel and category, warns about outside copies, and releases the featured slot (FR8.2, FR8.4) | PASS |
| S-order | Reordering is private until 'Update featured order' lists the new public order; drafts are shown as not yet public (FR9.7) | PASS |
| T-contrast | Every text/background token pair is at least 4.5:1 (FR9.6, NFR8) | PASS |
| T-nontext | Control borders and the focus ring are at least 3:1 against every surface (WCAG 1.4.11) | PASS |

## Contrast Calculations

- **Text:** the lowest text/background pair is 5.55:1 (`--muted` on `--panel-2`).
- **Non-text:** the lowest boundary or focus-ring pair is 4.08:1 (`--control-border` on `--panel-2`).

Full tables are in `design-system-mapping.md`.

## Issues Found and Fixed — Owner Request Changes (2026-10-11)

- **Publication boundary.** The former `?export` mode still treated Monopoly Arena as publishable, although its rights review is outstanding, and still loaded Risk's draft metadata into the page. It was replaced by a generated export, `export/`, built from an explicit approved-publication snapshot. The X-* checks prove that unapproved data is absent from the payload, the snapshot, the assets, every rendered route and the in-memory data — not merely hidden.
- **Email link.** The footer pointed to a fake `#contact`. Until Michael supplies the public address, it is now shown as an owner content input ("Email address to come"), checked by E-email-*.
- **Missing footer (found by the new checks).** Project and "isn't on display" pages replaced `<main>`, which removed the footer added by the page shell. The footer is now re-appended on those pages, checked by E-footer-*.
- **Duplicate captures.** The Monopoly and Risk direct routes render the same generic page by design. Both routes are still tested, but only one is captured, so every screenshot file is distinct.

## Issues Found and Fixed During Verification and the Previous Review

- **Misleading test evidence** (stage review, Major). On 1440 px runs, `results.json` showed console errors under passing checks. Two causes:
  - axe-core preloads stylesheets with XMLHttpRequest, which `file://` pages block;
  - the suite stored a live reference to the error list, so errors logged later (during the axe run) appeared in earlier, correctly passing evidence.

  Fixed by serving the prototype over a local HTTP server, snapshotting evidence at check time, and failing an axe check if the axe run itself logs errors. Re-run: no console errors anywhere.
- **Non-text contrast** (stage review, Minor). The input borders, a 20% alpha line, were below 3:1. Added `--control-border` (#857b6d) for inputs, search, chips and buttons; now measured at 4.08:1 or more (T-nontext).
- **Unapproved candidate on the home page** (stage review, Minor). First addressed with a `?export` view; that was superseded on 2026-10-11 by the generated approved-publication export (see above), because the `?export` view still loaded unapproved data.
- **Concept art tied to the rights review** (stage review, Minor). The Games & AI Arenas tile now uses the genuine Baduk live capture. Only the Monopoly card keeps neutral concept art (dice), which carries no third-party trade dress.
- **Misleading placeholder.** A title-only project's card said "Source is private". It now says "No lead image yet" when there is no private repository (S-placeholder).
- **Capture artifact.** Full-page captures taken after scrolling placed the sticky Studio bar mid-page. Captures now start from the top.
- **New-project dialog.** Native validation hid the accessible inline error. Fixed with `novalidate` and an app-level error (S-title-only).
- **Project page on phones.** A home-hero rule hid "View source". Rule scoped; regression check added (F-mobile-actions).
- **Smaller fixes:** missing `i-eye` and `i-cloud` icons added; skip links added (WCAG 2.4.1); Google Fonts replaced with self-hosted, OFL-licensed fonts.

## Visual Inspection

The lead agent inspected 13 screenshots by eye: `export-route-monopoly-mobile`, `export-category-games-desktop`, `home-desktop-full`, `home-mobile-first-screen`, `catalog-mobile`, `project-baduk-desktop`, `project-stars-mobile`, `studio-projects-desktop`, `studio-projects-mobile`, `studio-editor-title-only`, `studio-publish-ready-baduk`, `studio-takedown-dialog`, `studio-discover-desktop`. Some were inspected at an earlier render of the same view during this revision; the final run re-rendered all of them.

The remaining 48 screenshots are covered by the automated checks above (layout overflow, errors, axe and behaviour), not by individual visual review.

## Not Verified Here

- Screen-reader passes (NVDA, VoiceOver), 200% and 400% zoom, and text-spacing overrides.
- Browsers other than Chromium (NFR12).
- HTTP status codes, response headers and CSP (NFR15). The test server sets no security headers.
- Real upload validation, HEIC conversion, link checks and SSRF controls (NFR17), and the publication and take-down pipeline. These are simulated in the prototype and verified in implementation, with independent security review.
- Hosted Auth0 sign-in and MFA.
