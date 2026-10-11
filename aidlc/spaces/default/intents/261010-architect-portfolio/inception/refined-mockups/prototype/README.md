# Refined Mockups — Working Prototype (R5)

Status: **design proposal for the owner's Refined Mockups gate.** Not approved, and nothing here is published. It implements the requirements as amended by A1 to A1.2 (CR-01 to CR-05). The design narrative is in `../mockups.md`; the results are in `../verification.md`.

## Open it

Open these files directly in a browser; no server or build step is needed:

| Page | File |
|---|---|
| Home | `index.html` |
| All projects | `catalog.html` |
| A category | `catalog.html?category=games`, `catalog.html?category=astronomy` |
| Project case studies | `project.html?p=stars`, `project.html?p=baduk`, `project.html?p=monopoly-arena` |
| Not on display | `project.html?p=risk`, `catalog.html?category=woodworking` |
| Studio (owner only, simulated) | `studio.html` — start at sign-in, or open `#projects`, `#discover`, `#edit/stars`, `#featured`, `#activity` directly |

Add `?notes` to any page, or press **Show scope notes**, to outline requirement annotations.

## What is real and what is draft

- **Live captures** (`assets/live/`): screenshots of the deployed public STARS and Baduk apps, captured with Playwright on 2026-10-10 and labelled "Live capture".
- **Draft concept art** (`assets/draft/`): crops of the owner's concept board (`reference/concept-board.png`), labelled "Draft". Monopoly keeps placeholder art until its rights review (FR10.6).
- **Risk:** no image, no copy and no links. Its repository is private, and its live URL is withheld from this public repository (FR10.7).
- **Copy:** drafted from public READMEs and live pages, labelled "Draft case study", and not owner-approved.
- **Studio:** all data is simulated in memory. Nothing is saved, sent, checked or published.
- **Fonts** (`fonts/`): self-hosted, under the SIL Open Font License 1.1 (licences included), so the pages make no third-party requests.

## Files

- **Pages:** `index.html`, `catalog.html`, `project.html`, `studio.html`.
- **Styles:**
  - `styles.css` — tokens and the public site;
  - `studio.css` — the Studio;
  - `fonts/fonts.css`.
- **Scripts:**
  - `data.js` — content and badge derivation;
  - `shell.js` — public sidebar, cards and footer;
  - `app.js` — home carousel;
  - `site.js` — catalog and project pages;
  - `studio.js` — Studio views and dialogs;
  - `icons.js` — icon sprite.
- **Tests:** `tests/verify.cjs` (verification suite) and `tests/results.json` (latest run).

## Re-run the verification

You need Node 22, Playwright 1.64 with Chromium, and axe-core 4.10.2. Then, from this folder:

```bash
PW=<path to node_modules/playwright> AXE=<path to axe-core/axe.min.js> node tests/verify.cjs
```

The suite regenerates every screenshot in `../screenshots/r5-revision/` and writes `tests/results.json`. Each check reports PASS or FAIL with evidence.

## History

- **R4:** the first prototype built from the concept board; its screenshots are `../screenshots/proto-*.png`.
- **R5 first cut:** the four candidates on the home page; screenshots `../screenshots/proto-r5-*.png`.
- **R5 revision (this one):** catalog, category and project pages; Studio; self-hosted fonts; skip links; verification suite; screenshots `../screenshots/r5-revision/`.
- **Older material:** `../design-board.html` and the earlier screenshots (`01–04`, `gallery-*`, `editor-*`) are kept as history only.
