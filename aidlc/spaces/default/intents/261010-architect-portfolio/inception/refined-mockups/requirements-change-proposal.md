# Requirements Change Proposal — CR-01 to CR-05

Status: **PROPOSED OWNER DECISIONS — awaiting Michael Broadfoot's final sign-off.**

The approved `inception/requirements-analysis/requirements.md` is **unchanged**. Nothing here is implemented, and nothing has been deployed.

**History:**

- Raised 2026-10-10 during Refined Mockups, after the owner reviewed homepage prototype R4.
- Revised the same day to record the owner's proposed decisions on each change.
- Evidence: `launch-inventory.md` and `prototype/` (this folder).

**When Michael signs off**, the lead agent will:

1. amend `requirements.md` with exactly the text below, plus a change-log entry naming CR-01 to CR-05;
2. run the adversarial requirements review again on the changed sections;
3. record the decisions as D-23 onward in the decision log;
4. update `docs/PROJECT_BRIEF.md`;
5. adjust the affected Studio mockups: creating a project without a repository, access metadata, category and featured controls.

Any part Michael rejects or changes at sign-off stays as approved today.

## Proposed owner decisions at a glance

| CR | Proposed decision | Deferred or excluded |
|---|---|---|
| CR-01 | Launch candidates are STARS, Monopoly, Baduk and Risk. Each needs its own approval of content, rights, URL and publication. No single project blocks launch. | Monopoly and Risk titles are provisional, pending trademark and artwork review. |
| CR-02 | A project needs no GitHub repository. Title-only drafts are allowed. Images and maker/design attachments are supported: PDF, SKP, FCStd, DXF, STL, ZIP, VSDX. HEIC photos are converted to sanitized web images. 50 MB limit kept. The GitHub-based AI workflow is unchanged. | Other CAD formats (DWG, STEP, 3MF and others) unless needed. A raised size limit. |
| CR-03 | Explicit metadata: live URL, access requirement, phone suitability, repository visibility, licence. Links are validated at publication, with the result recorded. The owner keeps control of published changes. URL validation is protected against SSRF. | Scheduled link monitoring. Automatic removal of public badges. |
| CR-04 | Warm charcoal and brass visual direction replaces "dark navy" (FR9.6). | — |
| CR-05 | Featured carousel and category grouping come into v1. The published-exhibits gallery and the accessibility requirements are kept. | Journal, Search, free-form filtering, topic tags (FR4.7 unchanged). |
| — | STARS and Monopoly stay unlicensed until a separate licensing decision. | Licensing. |
| — | Risk's live URL is not published without owner authorization and a privacy/security review. Its private repository is never exposed. | — |

---

## CR-01 — Launch candidates: STARS, Monopoly, Baduk, Risk

**Origin:** owner scope change, 2026-10-10. It replaces the charter §8 "seed examples" (AI Arcade, STARS, Mom's Recipe Box) for launch. The charter itself is not edited.

| Where | Approved text | Proposed text |
|---|---|---|
| Intent Analysis, ¶1 last sentence | "The three seed exhibits — AI Arcade, STARS and Mom's Recipe Box — are published this way (charter §8)." | "The launch candidates — STARS, Monopoly, Baduk and Risk — are published this way, each only after its own owner approval (FR10.1; CR-01)." |
| **FR10.1** | "The three seed exhibits — AI Arcade, STARS and Mom's Recipe Box — shall be published through the Studio workflow, not hand-authored." | "The launch candidates — STARS, Monopoly, Baduk and Risk — shall be published through the Studio workflow, not hand-authored. Each candidate needs its own owner approval of its content, its rights (names, artwork, imagery), its live URL, and its publication. A candidate without those approvals stays in Draft. No single candidate blocks launch." |
| New **FR10.6** | — | "Exhibit titles for Monopoly and Risk are provisional until the owner completes a trademark and artwork review. Until then, no board artwork resembling third-party trade dress is published, and the Publish confirmation flags the review as outstanding." |
| New **FR10.7** | — | "Risk's live app URL shall not be published until the owner authorizes it after a privacy and security review of the live app. Risk's source repository is private and is never linked or exposed (FR4.3, D-15), and nothing is drawn from it for public text or imagery without the owner's approval (D-22, FR5.9)." |
| Out of Scope | "…projects beyond the three seed exhibits…" | "…projects beyond the four launch candidates, other than projects the owner creates without a repository (CR-02)…" |

Licensing (owner decision, recorded here and not a requirement): STARS and Monopoly stay unlicensed, with source visible and all rights reserved, until a separate licensing decision. Their badges say "Source available", never "Open source".

---

## CR-02 — A project does not need a GitHub repository

**Origin:** woodworking and design work may start from an SKP file, a Visio drawing, a photograph or an idea. **D-08 is unchanged**: GitHub stays the only *connector*, and files are uploaded by hand.

| Where | Approved text | Proposed text |
|---|---|---|
| **FR3.1** | "The owner shall be able to create a project from a repository, or link a repository to an existing project; a project may link several repositories." | "The owner shall be able to create a project with only a title, and may link zero, one or several repositories to it at any time. A repository link is optional." Given no repository, When the owner creates a project titled "Hall table", Then a Draft project exists with no repository link. |
| FR3.2 table, first row | "(new) · Create or link from a repository · Draft" | "(new) · Create (title only, or from a repository) · Draft" |
| **FR3.5** | Empty state offers "Discover a GitHub repository" | Empty state offers both "New project" and "Discover a GitHub repository". |
| **FR5.1** | Suggestion drawn from linked repositories' README and documentation | **Unchanged.** A project with no linked repository has no AI suggestion, and the owner writes its text. |
| **FR4.2** (images) | "JPEG, PNG or WebP" | "JPEG, PNG, WebP, or HEIC/HEIF photos. HEIC/HEIF are converted on upload processing to sanitized web images (JPEG or WebP) with all metadata removed, as already required. The original stays in private storage." |
| **FR4.4** (attachments) | "PDF, SKP, FCStd, DXF, STL, ZIP", up to 50 MB | "PDF, SKP, FCStd, DXF, STL, ZIP, VSDX", **up to 50 MB (unchanged)**. Everything else in FR4.4 stays: content-based validation, served as an attachment with a fixed safe type and `nosniff`, file type and size stated. |
| New **FR4.9** | — | "Maker and design attachments shall be stored privately, offered publicly only if the owner includes them at Publish, and never rendered or executed in the browser. A drawing is shown visually only through an owner-uploaded image or PDF." |
| Future Roadmap | — | Add: other CAD and model formats (for example DWG, STEP, 3MF), when a project needs them; a larger attachment limit; AI suggestions drawn from uploaded documents. |

Content checks per accepted format, confirmed against real sample files during design:

| Format | Check | Note |
|---|---|---|
| PDF | `%PDF-` header | |
| SKP | UTF-16 "SketchUp Model" file header | Models over 50 MB are refused, with a clear message. |
| FCStd | ZIP containing `Document.xml` | |
| DXF | Text `SECTION` structure | |
| STL | ASCII `solid` header, or binary layout size check | Binary STL has no signature, so the check is structural only. This is the weakest check, accepted because downloads are always served as attachments. |
| ZIP | ZIP signature | Not extracted on the server. |
| VSDX | ZIP (Open XML) whose `[Content_Types].xml` declares Visio parts | |
| HEIC/HEIF | ISO-BMFF `ftyp` box with a HEIC/HEIF brand | Image input only, never published as-is. |

---

## CR-03 — Access metadata, validated at publication

**Origin:** no project is called browser-ready, and no repository called public, without checking. This CR adds no access systems, no visitor sign-in, no invitation access, and no hosting changes.

| Where | Proposed text |
|---|---|
| New **FR4.10** — access metadata | "Each exhibit records, separately from its narrative: an optional live URL; its access requirement (open, sign-in, invitation); its phone suitability (suitable, desktop only, unknown); and, for each linked repository, its visibility and licence. Public badges ('In browser', 'Source available', 'Open source · ⟨licence⟩', 'Source private') are derived only from these fields." |
| New **FR10.5** — validation at publication | "When the owner opens Publish or Update for an exhibit with a live URL, the Studio validates the link and records the result with a date: whether it answers over HTTPS, its final address after redirects, and whether a sign-in page was detected. Repository visibility and licence are read from GitHub at the same time. The Publish confirmation (FR7.2) shows the results. A failed check is a warning, not a block: the owner decides whether to publish, change the link, or remove it. There is no scheduled monitoring, and nothing changes on the public site without an owner Publish or Update." Given a live URL that answers 404, When the owner opens Publish, Then the confirmation shows the failed check and the owner chooses whether to continue. |
| New **NFR17** — SSRF protection | "Studio URL validation runs only server-side, inside owner-authenticated endpoints, and is rate-limited (NFR16). It shall: allow only `https` on port 443; resolve the hostname and refuse loopback, private, link-local, carrier-grade NAT, multicast and unspecified addresses (IPv4 and IPv6), including the cloud metadata address `169.254.169.254`; connect to the validated address so the check cannot be bypassed by a DNS change (rebinding) between check and request; re-validate every redirect target and follow at most 3; send no credentials, cookies or identifying headers; use only GET or HEAD with a 5-second timeout; and read at most 256 KB of the response. The response is never shown to visitors and never stored beyond the recorded result." Given a live URL that resolves to `169.254.169.254` or `10.0.0.5`, When validation runs, Then no request is sent and the result is "refused: non-public address". |
| FR7.2 (Publish confirmation) | Add: each live link and repository link that will become public, with its latest validation result and date. |

---

## CR-04 — Visual direction: warm charcoal and brass

| Where | Approved text | Proposed text |
|---|---|---|
| **FR9.6** | "…follow the charter's 'Engineering Studio' direction — dark navy, precise typography, strong imagery, restrained effects — without copying the inspiration sites' appearance or branding." | "…follow the owner-approved crafted studio direction — warm charcoal with brass accents, editorial serif display type with a clean sans for interface text, strong imagery, restrained effects — as shown in Refined Mockups prototype R5, without copying any inspiration site's appearance or branding. Text contrast stays at least 4.5:1 (NFR8)." |

---

## CR-05 — Featured carousel and category grouping in v1

| Where | Approved text | Proposed text |
|---|---|---|
| Out of Scope | "richer gallery features (featured work, grouping, filtering, tags)" | "richer gallery features (free-form filtering, tags, search), Journal" — featured work and category grouping move into v1. |
| **FR9.1** | Home page is the Exhibition-wall gallery | "The home page shall show, in order: a featured carousel (when any exhibit is featured), the categories, and the Exhibition-wall gallery of published exhibits (D-14, D-16). Featured items and category counts include published exhibits only. A category with no published exhibit is not shown." Existing empty-state and image-failure criteria stay. |
| New **FR9.7** — featured carousel | "The owner marks up to 5 published exhibits as featured and sets their order. The carousel never advances on its own. It is operable by keyboard, has visible previous and next controls and a position indicator, announces the change of slide politely to screen readers, and respects reduced motion (NFR8, WCAG 2.2.2)." Given no exhibit is featured, When the home page renders, Then no carousel or empty frame appears. |
| New **FR9.8** — categories | "Each project has at most one category, chosen from a short list the owner manages (initially Games & AI Arenas, Astronomy & Exploration, Woodworking, Software & Tools). Each category has a page listing its published exhibits. A category is not a tag (FR4.7 unchanged)." |
| FR4.7 | "The first release has no topic tags (D-17)." | Unchanged. |

---

## Remaining open items (not decided here)

- The trademark and artwork review for Monopoly and Risk (FR10.6).
- The licensing decision for STARS and Monopoly.
- Authorizing Risk's live URL after its privacy and security review (FR10.7).
- Whether Monopoly's 25 px phone overflow and Risk's desktop-only layout get fixed in those apps before launch. That work belongs to those apps' own repositories, not this one.
