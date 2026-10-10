# Rough Mockups — Owner Decision and Proposed Default Fixes

Status: **approved by the owner with Rough Mockups (2026-10-10), including Concept A and all six fixes below.** Nothing here changes the reviewed wireframes (`wireframes.md`, `user-flow.md`); these items are carried into Refined Mockups.

## Owner decision (2026-10-10)

**Gallery concept: Concept A — "Exhibition wall".** Owner's direction: use compelling project imagery with a responsive, orderly layout. Refined Mockups develops Concept A to that direction; Concept B is not pursued.

## Proposed default fixes for the review findings

The product-lead review (advisory, verdict READY) raised six findings. Proposed resolutions:

| Finding | Severity | Proposed default |
|---------|----------|------------------|
| R-01: "View code" link to a private repository would be dead for visitors | Major | Hide "View code" on the public page whenever the linked repository is private. S6 states this instead of warning about a dead link. |
| R-02: Only desktop layouts drawn; Concept A's varied tiles are the hardest to fit on a phone | Major | Concept A collapses to a single column on phones, keeping each exhibit's lead image dominant; tile variation applies only from tablet width up, within a fixed, orderly grid (matches "responsive, orderly layout"). |
| R-03: Topic tags shown on cards and pages, but tagging is not in the approved scope | Minor | Drop tags from the first release; they belong with the roadmap's richer gallery features (grouping, filtering). |
| R-04: Footer contact link is not an approved capability | Minor | Keep it as a plain email link that collects no visitor data, since consulting enquiries are part of the intent. |
| R-05: No state for an exhibit without a lead image | Minor | A lead image (with alt text) is required to publish; Publish stays disabled with the reason shown until one is set. |
| R-06: "Take down" location undrawn; S5 preview does not show the gallery card | Minor | "Take down" is available as a row action on S2 Projects and as a control in the S4 editor, each with its own confirmation; S5 Preview shows the gallery card above the exhibit page. |

## Requirements carried into Requirements Analysis (owner, at approval, 2026-10-10)

These are approved owner decisions; Requirements Analysis records them as requirements and does not re-ask them.

1. **Take down / Unpublish is Must Have for the first release.** This promotes intent-backlog IB-16 from Should to Must.
2. **Explicit publication approval covers all public content.** The owner's publish approval must cover everything that becomes public: narrative text, media, downloadable files, links, and AI-generated descriptions, including any drawn from private sources. Private source material is never exposed automatically.
