## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-product-lead-agent
**Scope:** Requirements Amendment A1 (CR-01 to CR-05)

### Findings

| ID | Severity | Location | Finding | Required action |
|---|---|---|---|---|
| A1-P01 | Major | FR9.7, FR9.8, FR7.1, FR3.2, FR7.4 | Featuring an exhibit, reordering the carousel, or changing a category changes public content (home page, category page). Nothing says this goes through Publish/Update, whether it moves a Published exhibit to "Changes since last publish", or that the home and category pages are re-exported within the FR7.4 5-minute bound. As written, the public site could change without an explicit Publish, which FR7.1 forbids. | State that featured status, order and primary category are published only via Publish/Update (FR7.2 already lists them), give the FR3.2 transition, and extend the FR7.4 export and 5-minute criterion to the home and category pages. |
| A1-P02 | Major | FR8.1-FR8.3, FR6.1 | Take-down (FR8.2) and preview (FR6.1) were not extended for the carousel and categories. There is no criterion for taking down a featured exhibit (removed from the carousel, slot and order handling, a republish restores it or not) or for taking down the last exhibit in a category. FR6.1 previews only the card. | Add Given/When/Then criteria: a taken-down exhibit leaves the carousel, category page and counts within the FR7.4 bound, and the empty-carousel and empty-category rules of FR9.1 apply. Extend FR6.1 to the carousel and category placement, or state that this is out of scope. |
| A1-P03 | Major | FR4.9 vs FR4.4 | FR4.9 says attachments are "never rendered ... in the browser" but also that a drawing is "shown visually only through an owner-uploaded image or PDF". FR4.4 serves every download as an attachment, so a PDF is never rendered inline. The two cannot both be tested. | Reword: a PDF is offered only as a download, and visual display uses an owner-uploaded image (plus alt text). Or specify exactly how an inline PDF is shown and secured, and amend FR4.4. |
| A1-P04 | Major | FR4.10, FR10.5, FR4.3 | Repository visibility is "read from GitHub" at Publish, and a failed check is "a warning, not a block". No rule says what happens when visibility or licence cannot be read (API error, rate limit, repository renamed). A private repository could be badged or linked as public. This is a publication-boundary gap (NFR2, D-15). | Add: unknown visibility is treated as private (fail closed), no repository link or name is shown, and Publish says so. Add a Given/When/Then for a failed visibility read. |
| A1-P05 | Minor | FR4.10 | The badge derivation is undefined. "In browser", "Source available" and "Open source · licence" need a stated mapping. Which licences count as open source (OSI-approved SPDX id?) is open, as are GitHub's "other" and NOASSERTION. Access requirement and phone suitability have no public display rule. "Invitation" access sits oddly with the out-of-scope "invitation-only access". | Add a short derivation table, name the open-source test (for example OSI-approved SPDX identifier), define the other/NOASSERTION case, say how access and phone suitability are shown, and note that the access field describes the linked app, not this site. |
| A1-P06 | Minor | NFR16 / NFR17 | The NFR17 block was inserted above NFR16's rate-limit Given/When/Then, so that criterion now sits under NFR17 and NFR16 has none. | Move the 429 criterion back under NFR16. |
| A1-P07 | Minor | FR10.5, NFR17 | The "sign-in page detected" heuristic is undefined, so it has no pass/fail. NFR17 introduces a third outcome, "Refused: non-public address", outside the FR10.5 labels. The 5-second timeout is unclear (per request or total). Multi-record DNS answers and IPv4-mapped IPv6 are not covered. | Define the detection rule, for example HTTP 401/403 or a login-form marker. Add "Refused" to the label set. State that the timeout is per hop with an overall cap. Require every resolved address to pass validation. |
| A1-P08 | Minor | FR4.2, FR4.4 | The failed-HEIC-conversion outcome is not stated (reject with reason?). VSDX is a ZIP container, and nothing says how content validation separates it from a generic ZIP. | Add a criterion for a corrupt or unconvertible HEIC (rejected, with the reason). State the VSDX signature and structure check and its fixed content type. |
| A1-P09 | Minor | FR10.6, FR10.7 | "Artwork resembling third-party trade dress" is subjective, and "flags the review as outstanding" does not say where the review state is recorded. FR10.7 has no Given/When/Then, and does not say how an unauthorized Risk URL is kept out of Publish. | Define an owner-set "trademark/artwork review complete" flag per exhibit, with Publish confirmation behaviour. Add a criterion that Risk's live URL is excluded from public export until the owner authorizes it. |
| A1-P10 | Minor | FR9.6 | The pass/fail is tied to "prototype R5", a work in progress (the Refined Mockups changes request was recorded just before this amendment) and not a fixed reference. Only contrast is measurable. | Cite a fixed version or path of the approved prototype, or list the design tokens. Keep the 4.5:1 check as the measurable part. |
| A1-P11 | Minor | FR9.8 | The owner "manages" the category list, but there is no create/rename/delete requirement. Deleting a category that holds exhibits, a duplicate name and a category URL slug are not covered. Whether an exhibit may have no category is only implied by "at most one". | Add a short Studio category-management requirement with the delete-in-use rule, or limit v1 to the four fixed categories. |
| A1-P12 | Minor | Intent Analysis, FR10.2, Assumptions, Out of Scope, FR9.1 | Stale or untraced text remains. FR10.2's example uses `/work/ai-arcade`, and the assumptions still say "seed repositories" and "seed exhibits". D-23 says "Monopoly Arena", but the requirements say "Monopoly". Out of Scope newly adds "a journal", "visitor accounts" and "search", with no CR. FR9.1 drops "varied tiles" without naming the decision. | Update the stale references, align the name with D-23, cite a CR or D-id for each Out of Scope addition, and note the tile change. |

### Summary
The amendment is mostly traceable to CR-01 to CR-05 and D-23 to D-28, and it keeps the MFA, cost and no-tracking boundaries intact. The publication path for featured and category changes (A1-P01), the take-down and preview cases (A1-P02), the PDF contradiction (A1-P03) and the missing fail-closed rule for repository visibility (A1-P04) would cause rework or a boundary gap, so it is NOT-READY. The remaining findings are wording and precision fixes.

### Re-review (A1.1, commit 2087934)

**Verdict:** READY

| ID | Status | Note |
|---|---|---|
| A1-P01 | Resolved (reviewer) | FR9.7 and FR9.8 now publish featured status and category only through Publish/Update (FR3.2 "Changes since last publish"). Reordering needs an explicit "Update featured order" confirmation. FR7.4 re-exports the home and category pages within 5 minutes. Each has a Given/When/Then. |
| A1-P02 | Resolved (reviewer) | FR8.2 removes the exhibit from the carousel, category page and counts, with criteria for a featured exhibit and for the last exhibit in a category. FR6.1 now previews the slide and category placement. |
| A1-P03 | Resolved (reviewer) | FR4.9 now says PDFs are download-only and drawings are shown inline only as images with alt text. A download criterion was added. |
| A1-P04 | Resolved (reviewer) | FR4.10 has a fail-closed rule, with an export allow-list and an export scan criterion. NFR2 matches. |
| A1-P05 | Resolved (reviewer) | A badge table covers OSI/SPDX, other/NOASSERTION, access and phone suitability. The access field is stated to describe the linked app. |
| A1-P06 | Resolved (reviewer) | NFR16 has its 429 criteria again, plus one for the link check. |
| A1-P07 | Resolved (reviewer) | Sign-in detection is defined (401/403 or a password field). "Refused" is a third label. Timeouts are 5s per hop and 15s overall. The allow-list handles multiple DNS answers and mapped IPv6. |
| A1-P08 | Resolved (reviewer) | There is a corrupt-HEIC criterion. VSDX and FCStd have ZIP structure checks. Pixel limits, zip-bomb and XXE criteria were added. |
| A1-P09 | Resolved (reviewer) | There are owner-set "Rights review complete" and "Live URL authorized" flags, and Publish is unavailable without the first. Criteria were added. |
| A1-P10 | Resolved (reviewer) | FR9.6 cites `design-system-mapping.md`, which exists, plus a measurable token-pair contrast criterion. It depends on that file as approved at the Refined Mockups gate, which is still pending; see A1-P14. |
| A1-P11 | Resolved (reviewer) | Four fixed categories with fixed addresses. No category is allowed. Category management is on the roadmap. |
| A1-P12 | Resolved (reviewer) | FR10.2 and the assumptions are updated, and "Monopoly Arena" is stated as the working title. Out of Scope additions cite D-27. The tile change is flagged, but see A1-P13. |

**New findings**

| ID | Severity | Location | Finding | Required action |
|---|---|---|---|---|
| A1-P13 | Minor | FR9.1 | The text says the "equal-card grid of the CR-04 identity, D-26" replaces D-16's varied tiles. D-26 and the refined-mockups documents do not record an equal-card grid, so the change has no recorded source. | Cite where the owner decided it, or restore D-16's wording until the owner confirms. |
| A1-P14 | Minor | FR9.6 | The token source is "as approved at the Refined Mockups gate", but that gate has not been approved (a Request Changes was recorded). The requirement therefore points to content that may still change. | Say that the file's version at approval governs, and re-check this requirement if the gate changes the tokens. |
| A1-P15 | Minor | FR9.7, FR7.3, FR9.8 | Two small gaps. First, it is unclear whether a featured draft counts against the 5 limit. Second, FR7.3 does not list the new Publish blocks (FR10.6), and the category 404 text is not stated, because FR9.3's wording is exhibit-specific. | State that drafts count toward the 5. Add the FR10.6 block to FR7.3. State a category 404 message. |

### Re-review summary
All twelve earlier findings are resolved in the text. The three new findings are Minor wording and traceability items, so none blocks READY.
