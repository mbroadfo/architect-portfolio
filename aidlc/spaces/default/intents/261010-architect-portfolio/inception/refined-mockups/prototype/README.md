# Refined Mockups — Homepage Prototype

Status: **R5, draft for owner review.** Not approved. Requirements are unchanged. The proposed changes are in `../requirements-change-proposal.md` (CR-01 to CR-05, recorded as proposed owner decisions awaiting final sign-off), and the verified deployment facts are in `../launch-inventory.md`.

Open `index.html` in a browser. Add `?notes` to the address, or press **Show scope notes**, to outline everything outside the approved first release. Each project card then shows its verified deployment and access facts.

## R5 (current)

- **Projects:** the owner's launch candidates replace the invented ones: STARS, Monopoly Arena, Baduk and Risk (CR-01).
- **Featured carousel:** shows the three public candidates. Risk is not featured until Michael approves its public image, text and live link.
- **Explore by Type:** uses one axis, what a project *is*:
  - Games & AI Arenas: 3 projects;
  - Astronomy & Exploration: 1 project;
  - Woodworking: "Coming from the shop", which needs CR-02;
  - Software & Tools: nothing published yet.

  Access is shown as badges instead: "In browser", "Source available", "Open source · MIT", "Source private".
- **Badges** match the inventory. STARS and Monopoly are public repositories with no licence, so they show "Source available". Only Baduk shows "Open source". Risk shows "Source private" and has no source link (D-15). Its live link is marked pending approval.
- **Imagery:**
  - *Live captures* of the deployed STARS and Baduk apps, taken with Playwright on 2026-10-10.
  - *Draft concept art* cropped from the owner's concept board, for Monopoly and the type tiles. The Monopoly board itself is not captured because its artwork resembles third-party trade dress (see the inventory).
  - Risk: a placeholder until Michael approves an image.
- **Copy** for the three public apps is drafted from their public READMEs and live pages. Risk has no copy because its source is private (D-22). None of the copy is owner-approved.
- **Screenshots:** `../screenshots/proto-r5-*.png` — desktop 1440, mobile 390, tablet 1024, open menu, second slide, scope notes. No horizontal overflow and no console errors.

## R4 (history)

The first prototype showed the concept board's sample projects. Its screenshots are `../screenshots/proto-*.png`, the files without the `r5` prefix. The concept-board crops that only R4 used are not committed.

The earlier `01-desktop-home.png`, `02-desktop-catalog.png` and `04-desktop-detail.png` are byte-identical: one image saved under three names. They are kept as design history.

## Proposed for v1, still awaiting sign-off (outlined in scope notes)

- **Palette:** the warm charcoal and brass direction replaces "dark navy" in FR9.6 (CR-04).
- **Featured carousel and categories:** proposed for v1 (CR-05). On the live site, categories with no published exhibit are hidden; the prototype shows empty ones only to illustrate the layout. Topic tags stay out (FR4.7).
- **Journal and Search:** deferred (owner decision).

## Production notes

Fonts come from Google Fonts for this prototype only, and production self-hosts them (FR9.5, NFR9, NFR15). The prototype loads no inline scripts, which keeps it compatible with the CSP in NFR15.
