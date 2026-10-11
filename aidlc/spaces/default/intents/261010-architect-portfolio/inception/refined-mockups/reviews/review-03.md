## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-00 | Major | aidlc/spaces/default/intents/261010-architect-portfolio/inception/refined-mockups/mockups.md > review findings table | The reviewer's findings table could not be read, so its rows are not listed here: the findings report could not be read. Write the whole review again with the required Prior findings and New findings tables | Address the reviewer's findings as written below this table. | Resolved (reviewer) |
| R-01 | Major | aidlc/spaces/default/intents/261010-architect-portfolio/inception/refined-mockups/verification.md > Results by Area, "Responsive and runtime" (48 of 48), and prototype/tests/results.json > R-*-1440 entries | The claim "No horizontal overflow and no console errors" is not supported by its own raw evidence. All 17 `R-*-1440` entries (every public page and the Studio views) record non-empty `errors` lists, for example "Access to XMLHttpRequest at 'file:///...' ... Failed to load resource: net::ERR_FAILED", yet are marked `pass: true`. `verify.cjs` computes pass as `ov <= 0 && !errors.length`, so those entries should have failed. The results file and the script logic disagree, so the 107/107 headline cannot be trusted as stated. The errors may be benign file:// loading noise, but the document does not say so. | Before the gate, re-run the suite and publish consistent results, or state in verification.md exactly which resource fails to load from disk at 1440 px and why it is harmless. Confirm that nothing the owner sees is missing when the pages are opened from disk, and correct the 107/107 and "no console errors" statements to match. | Resolved (reviewer) |
| R-02 | Minor | mockups.md > P1 Selected Work; prototype/data.js (risk entry); home-desktop-full.png | The home gallery shows a Risk card titled "Risk" with a "Source private" badge and a "Live link pending approval" badge. The card has no link and no image, and the repository name and live URL appear nowhere. It is labelled "for review only" in the prose, but the screenshot is of a public page. If the owner approves this layout literally, a visitor would learn that a private-source project exists before it is approved (FR10.1, FR10.7). | Make explicit in mockups.md that the card exists only in the prototype's review mode, and that the production export omits it entirely until approved. Consider labelling the card in the prototype itself, for example "Review only, not on the live site". Add an acceptance check that an unapproved candidate leaves no card, badge or count in the production export. | Resolved (reviewer) |
| R-03 | Minor | mockups.md > Launch Content and Imagery; screenshots home-desktop-full.png (Monopoly and Games tiles) | The Monopoly and Games imagery is a photographic board-and-dice image labelled "Draft image · concept art". A reader may take it as the approved look. The design rests on an unresolved trademark and artwork review (FR10.6, D-28), and the Games category tile on the home page, which shows the same image, will have no approved image if Monopoly is withheld. | Record a fallback for the Games tile and the Monopoly card if the rights review fails. For example, use a neutral non-trademark image, or use the Baduk capture. State that the draft-image label is removed only on owner approval. | Resolved (reviewer) |
| R-04 | Minor | design-system-mapping.md > Contrast; accessibility-checklist.md > Non-text contrast | Text contrast is measured (lowest 5.55:1), but non-text contrast (control borders at `--line-2`, alpha 0.20) is only asserted as "well above 3:1" and not measured. Control borders at 20% alpha on charcoal are likely below the 3:1 that checklist row requires. | Measure the control-border and focus-ring contrast, or raise the border alpha or colour for form controls. Record the numbers in design-system-mapping.md. | Resolved (reviewer) |
| R-05 | Minor | verification.md > Visual Inspection | The statement "All are distinct, genuine renders produced by the suite" covers only a subset of the 57 screenshots. It lists inspected screens such as the Monopoly editor and the Baduk update confirmation, but not the blocked-publish, leave-guard, take-down and featured-order dialogs. | Either inspect the remaining state screenshots or narrow the sentence to the screens actually inspected. | Resolved (reviewer) |

> R-00 Reviewer note: This pass reviewed the artifacts afresh, and each concern is recorded as its own row.

> R-01 Reviewer note: I read prototype/tests/results.json: 182 of 182 checks pass, and none of the 76 responsive and runtime entries has a non-empty errors list. The tests now run over a local HTTP server, and verification.md explains the earlier file:// cause. The headline statements match the raw evidence.

> R-02 Reviewer note: mockups.md labels the Risk and Monopoly cards as design-review view only. I rebuilt export/ with tools/build-export.cjs (2 projects exported, 2 candidates excluded). Grepping export/ finds no Monopoly or Risk slug, title, asset or URL. Check X-payload (tests/verify.cjs) asserts this, and the direct-route checks assert that export/project.html?p=risk and ?p=monopoly-arena show "isn't on display".

> R-03 Reviewer note: mockups.md (Launch Content and Imagery) records the fallback: Monopoly stays in Draft, and the only concept art shown is the neutral dice image.

> R-04 Reviewer note: A `--control-border` token (#857b6d) was added, and the contrast calculations in verification.md now measure 4.08:1 or more. T-nontext in the suite checks control borders and the focus ring against every surface.

> R-05 Reviewer note: verification.md now names the 13 screenshots that were inspected, so it no longer implies the rest were.

### Summary

All four owner corrections hold up when I check them directly. I confirmed three things:

- **Approved-publication snapshot:** it contains only STARS and Baduk, and the home carousel, category tiles, counts, catalog and case studies in the export derive from it.
- **Monopoly and Risk:** neither appears in the exported payload or its assets, and direct routes to both resolve to "isn't on display". The Monopoly and Risk checks (X-payload, X-direct) assert this on the data, not only the DOM.
- **Email link:** the exported footer shows "Email address to come" as tracked owner-content text, not a fake link. It becomes a real mailto: only once Michael supplies the address, and the E-email checks guard this.

I found nothing new that would block engineering. The only caveat is that the simulated approvals for STARS and Baduk are labelled as demo-only, and Michael has approved nothing for publication.
