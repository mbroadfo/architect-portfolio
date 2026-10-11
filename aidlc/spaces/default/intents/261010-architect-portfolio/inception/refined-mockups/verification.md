# Refined Mockups — Verification (R5)

## Scope

Results of `prototype/tests/verify.cjs`, run 2026-10-11T02:13:09.028Z with Chromium (Playwright 1.64) and axe-core 4.10.2 against the files in `prototype/`. **107 of 107 checks passed.** Raw evidence for every check is in `prototype/tests/results.json`; the screenshots are in `screenshots/r5-revision/`.

Inputs verified against: requirements (`../requirements-analysis/requirements.md`, Amendment A1 to A1.2), wireframes and user-flow (`../../ideation/rough-mockups/`), and team-practices (`../practices-discovery/team-practices.md`). This verifies the prototype as design evidence. It does not certify the built application (see Not Verified Here).

## Results by Area

| Area | Checks | Passed |
|---|---|---|
| Responsive and runtime — No horizontal overflow and no console errors. Public pages at 390, 768, 1024 and 1440 px; Studio views at 390 and 1440 px. | 48 | 48 |
| Accessibility (axe-core 4.10.2) — No serious or critical violations. | 17 | 17 |
| Privacy: third-party requests — No request to any origin other than the page's own files (FR9.5, NFR15). | 17 | 17 |
| Keyboard and focus | 3 | 3 |
| Carousel and motion | 4 | 4 |
| Dialogs | 1 | 1 |
| Public-site rules | 5 | 5 |
| Studio workflows | 11 | 11 |
| Contrast | 1 | 1 |

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
| D-lightbox | Gallery opens an enlarged view by keyboard, arrows step, Escape closes and focus returns (FR9.2) | PASS |
| S-title-only | A project can be created with only a title; it starts as Draft with no repository, and the AI panel says suggestions need a repository (FR3.1, FR5.1) | PASS |
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

## Contrast Calculations

Lowest text/background pair: 5.55:1 (`--muted` on `--panel-2`). The full table is in `design-system-mapping.md`.

## Issues Found and Fixed During Verification

- **New-project dialog.** The browser's native validation blocked the empty-title submit before the accessible inline error appeared. Fixed with `novalidate` and an app-level error linked by `aria-describedby`, focus kept on the field (S-title-only).
- **Project page on phones.** A mobile rule for the home hero hid the project page's "View source" button. Rule scoped to the home hero; regression check added (F-mobile-actions).
- **Missing icons.** `i-eye` and `i-cloud` were missing from the sprite, so the Preview button and Access row had no icon. Added.
- **Bypass blocks.** Pages lacked a skip link (WCAG 2.4.1). Added to every page; the Studio version moves focus without changing its hash route (K-skip, K-skip-target).
- **Third-party fonts.** Google Fonts were requested. They are now self-hosted, OFL-licensed (P-*), resolving security review finding A1-S16.

## Visual Inspection

Screenshots inspected by the lead agent: home (desktop full and phone first screen), catalog, the STARS and Baduk case studies (desktop and phone), the Studio project list (desktop and phone), the Monopoly editor and the Baduk update confirmation. All are distinct, genuine renders produced by the suite, with no duplicated files.

## Not Verified Here

- Screen-reader passes (NVDA, VoiceOver), 200% and 400% zoom, and text-spacing overrides.
- Browsers other than Chromium (NFR12).
- HTTP status codes, response headers and CSP (NFR15); the prototype is opened from disk.
- Real upload validation, HEIC conversion, link checks and SSRF controls (NFR17), and the publication and take-down pipeline. These are simulated in the prototype and verified in implementation, with independent security review.
- Hosted Auth0 sign-in and MFA.
