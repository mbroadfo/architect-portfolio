# Interaction Specification

## Sources and Boundaries

Inputs: wireframes and user-flow in `../../ideation/rough-mockups/`, approved fixes beside them, requirements in `../requirements-analysis/requirements.md` (Amendment A1 to A1.2: CR-01 to CR-05), and team-practices in `../practices-discovery/team-practices.md`. User stories are skipped. Screen IDs match `mockups.md` (R5). These are implementation contracts proposed for design approval, not implemented capabilities. The working prototype in `prototype/` demonstrates them with simulated data, and `prototype/tests/verify.cjs` checks the demonstrable parts (`verification.md`).

## Journey Contracts

| Journey | Trigger and steps | Success | Failure and recovery |
|---|---|---|---|
| Curate | S1 owner+MFA → S2 → S3 → create/link → S4 edit/save → optional AI review → S5 → S6 | Approved saved revision exported; page/card/assets consistent | GitHub/AI errors do not change edits; conflict preserves local copy; publish failure retains last successful public version |
| Update | Open published project → edit/save → Changes since last publish → preview → full Update confirmation | New revision public | Saving alone never updates public content |
| Withdraw | S2 or S4 Take down → S7 named confirmation | Page/card/assets/cache gone within five minutes; Studio content retained | Copies outside this site cannot be revoked; failed removal shown explicitly |
| Republish | Open Taken down → edit/save (still Taken down) → preview → full Publish confirmation | Published only after checks and successful operation | No shortcut based on prior publication |
| Create | S2 New project → title (category optional) → Draft → S4; repository optional, linkable later from S3 | Draft with no repository; nothing public | Empty title: inline error, focus kept; no AI suggestions until a repository is linked (FR5.1) |
| Feature | S4 Feature in the carousel → Save → Publish/Update; S8 reorder → Update featured order | Carousel shows published featured exhibits in the confirmed order | More than 5 featured: blocked with reason; reorder stays private until confirmed (FR9.7) |
| Explore | P1 featured carousel → categories → gallery → P2 case study; or P1b catalog/category → P2 | Static public content, no account, curated discovery | Unknown/unpublished exhibit or empty category: "isn't on display" with link to all work (HTTP 404 in production) |

Public exploration follows the R5 model: featured carousel → categories → gallery → case study (FR9.1, FR9.2, FR9.7, FR9.8). Category (what a project is) and access (how a visitor can reach it, shown as derived badges, FR4.10) are distinct axes, and lifecycle state (Draft/Published/Changes since last publish/Taken down) is collapsed with neither. Featured status and primary category are exhibit fields published with that exhibit's Publish or Update; saving a change to them on a published exhibit sets Changes since last publish. Featured order is site-level and has its own confirmation (S8).

### Project state and operation state

Use exactly Draft, Published, Changes since last publish, Taken down. Follow FR3.2: create → Draft; Publish from Draft/Taken down → Published; save Published → Changes since last publish; Update → Published; take down Published/Changes → Taken down; save Taken down stays Taken down. Saving Draft stays Draft. Saving Changes stays Changes.

Queued, Publishing, Updating and Taking down are operation indicators, not extra project statuses. Display the last successfully completed public state alongside pending operations. Operations for one exhibit run in confirmation order (FR7.8). Take down can be confirmed after a queued Publish, including from a currently Draft project with a confirmed publish pending; this queues removal after creation without pretending the project is already Published. Once both complete the project is Taken down. The action is otherwise unavailable for Draft/Taken down with no pending publication. This pending-operation exception implements FR7.8 without allowing an independent invalid FR3.2 transition.

A public operation failure leaves the last successful public version intact. Failed publication does not flip a status to Published. A later confirmed operation must not expose a mixture of versions; implementation must resolve failed dependencies and show them, with no silent reordering. Retries are explicit, idempotent and tied to the original action/revision; an operation superseded by a later successful action cannot be retried into reversing it. Offer fresh review instead.

## Editor and SaveStatus

| Field | Value |
|---|---|
| Component | ExhibitEditor / SaveStatus |
| Description | Preserve private work while separating save from publication |
| Category | input / feedback |

### States

| State | Trigger | Behavior |
|---|---|---|
| clean | Load saved revision | Saved at time, revision shown |
| dirty | Edit any field or insert suggestion | Unsaved changes; public copy unchanged |
| saving | Explicit Save | Snapshot buffer, retain further typing, disable duplicate Save only |
| saved | Server accepts revision | Saved timestamp; subsequent typing remains dirty |
| error | Network/server failure | Could not save. Your edits are still here. Retry |
| conflict | Stale revision | Nothing overwritten; retain local buffer, show latest saved copy side by side; owner manually resolves and saves against latest version |
| expired | Owner authorization expires | Hide private editor; authenticate same issuer/subject+MFA; restore protected unsaved buffer only for that owner |

### Props / Inputs

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| project | object | yes | none | Saved content and version |
| buffer | object | yes | saved content | Editable local work |
| saveState | enum | yes | clean | State above |
| authorization | verified identity | yes | denied | Server authorizes every request |

### Responsive Behaviour

Desktop form and AI aside; tablet/phone one column. Visible Save/Preview/Review publication actions wrap; never cover fields. Preview/publication first requests explicit Save if dirty; cancelling keeps the buffer. Leaving dirty editor offers Stay / Discard unsaved changes, with Stay focused; no automatic publish or save implied by navigation.

### Accessibility

Visible labels, fieldset groups, inline errors linked with descriptions. Polite save-status announcements. Conflict explanation receives focus, not a destructive button. Return from reauthentication focuses restored editor heading and announces recovery.

### Usage Example

S4: change Summary → Unsaved changes → Save → Saved revision 12. Existing public revision 11 remains unchanged. Secure recovery storage and cross-device conflict implementation are design obligations for Domain/NFR Design; do not place private buffers in unprotected persistent browser storage or expose them after sign-out/non-owner login. Intentional sign-out warns about unsaved work and clears locally accessible private state; session-expiry recovery must still satisfy FR1.4.

## AssetUploadRow

| Field | Value |
|---|---|
| Component | AssetUploadRow |
| Description | Upload into private storage, then validate before attachment |
| Category | input / feedback |

### States

Idle → authorizing → uploading → checking → accepted, or rejected/expired/error. No image/file is attached or publishable until server content checks succeed. Individual retry/removal never discards other fields. Cancellation abandons an incomplete upload without attaching it.

### Props / Inputs

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| kind | image or build-file | yes | image | Applicable limits |
| file | local file | yes on upload | none | No extension-only trust |
| alt | string | for published image | empty | Visible field on each image |
| lead | boolean | one image per publishable exhibit | false | Native radio choice |
| result | validated asset identity | after checking | none | Version bound into publication |

### Responsive Behaviour

Rows stack below 768 px. Picker is a real button; optional drag/drop has the same keyboard alternative. Progress and type/size remain visible.

### Accessibility

Upload hints precede picker: JPEG, PNG, WebP or HEIC (converted to a web image), up to 10 MB per image; maker and design files PDF, SKP, FCStd, DXF, STL, ZIP or VSDX, up to 50 MB each. Label progress per filename; announce completion/rejection without repeated percentage announcements. Alt text field has a link from publication error summary.

### Usage Example

Upload image → Checking file → accepted thumbnail, alt text and Set as lead. Wrong signature/type/size gives a specific reason. Upload authorization is short-lived, single-use and bound to limits, issued only to owner; upload bytes go directly to private storage, never through API body. Export re-encodes image derivatives and strips all metadata; originals stay private. Downloads show filename/type/size and use attachment/nosniff/safe type headers. The allowed list is PDF, SKP, FCStd, DXF, STL, ZIP and VSDX (FR4.4, CR-02). ZIP-based checks read only the central directory and named entry within size/ratio limits with DTDs and external entities disabled; images are dimension-checked before decoding (FR4.2). Attachments are offered only as downloads if included at Publish (FR4.9).

## SuggestionPanel

| Field | Value |
|---|---|
| Component | SuggestionPanel |
| Description | Reviewable provider-independent AI text assistance |
| Category | input / display / feedback |

### States

Unconfigured; spending approval needed; provider not approved for private sources; monthly limit reached; rate-limited; ready; generating; suggestion available; error. Each blocked state explains its reason and sends no provider request. No button on this design silently grants spending or private-data permission. Provider/terms/spending approvals occur through explicit owner decisions in their owning stages.

### Props / Inputs

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| providerName | string | before request | unconfigured | Named before text is sent and retained with result |
| evidence | list | yes | empty | Repository/file names and visibility, Studio-only |
| permissions | booleans | yes | denied | Owner auth, spending and private-provider approval |
| usage | count and limit | for paid provider | disabled | Owner-set monthly limit, no guessed budget |
| suggestion | text plus provenance | on success | none | Never executable markup or commands |

### Responsive Behaviour

Desktop aside; below 1024 px the panel follows the editor in DOM order. A "Jump to AI suggestions" link appears before the form for keyboard users; it is visible in the flow (or as skip link), has explicit text "Jump to AI suggestions", and on activation moves focus to the first focusable control in the SuggestionPanel (the Suggest button or first input). After insert/edit/discard, focus returns to the originating field or next logical editor control. Sources and long paths wrap. No fixed height clipping.

### Accessibility

Native buttons and labelled suggestion textarea. "Jump to AI suggestions" link (visible text + aria-label) only below 1024 px; focus moves to panel on activation and returns after action. Polite Generating status; at 60 seconds show No suggestion this time. Your text is unchanged. Retry follows server retry time for 429 and is never automatic. Provider permission and usage explanations are visible text. Keyboard: Tab order includes the jump link when present; Escape not trapped in panel. Verification: axe + manual keyboard at 1024 px breakpoint.

### Usage Example

Show Provider: configured provider and the exact README/docs source list before Suggest description. Linked private repository blocks request unless that provider is approved for private content under documented no-training/stated-retention terms. Insert appends to the selected target field without replacing existing text; Edit changes the proposed text in the panel first, then Insert; Discard changes nothing. Insertion marks editor dirty and retains AI/private-source provenance even after edits. Repository instructions are untrusted data; AI has no tools/actions. Suggestion output is escaped everywhere.

## PublicationConfirmation

| Field | Value |
|---|---|
| Component | PublicationConfirmation |
| Description | Owner approves exact public snapshot, not all future edits |
| Category | input / display |

### States

Preparing inventory; ready; blocked; stale; confirming; queued; running; complete; failed. Required fields: nonempty title, validated lead image, alt text for every image, and a completed rights review where one is required (FR7.3, FR10.6). Other unresolved upload checks also block. The reasons are linked to editor fields; no disabled button without explanation.

### Props / Inputs

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| action | publish/update/take-down | yes | none | Exact label and result |
| revision | immutable saved identity | yes | none | Includes asset versions and complete inventory |
| inventory | full text/assets/links/provenance | publish/update | none | Inspectable content, not counts alone |
| linkChecks | label + time per live link | when a live URL is included | none | "Reachable", "Not reachable" or "Refused (non-public address)"; never Verified/Safe/Approved; URL published exactly as entered (FR10.5) |
| attachmentMeta | metadata + ZIP entries per file | when files are included | none | Secret-like names flagged; "published unchanged" stated; "Metadata could not be read" on failure (FR7.2) |
| placement | category, featured position | yes | none | What the home and category pages will show (FR7.2, FR9.7, FR9.8) |
| publicState | last successful action | yes | none | Shown alongside pending operation |
| blockers | list | yes | empty | Server repeats all checks |

### Responsive Behaviour

Large dialog on desktop, viewport dialog on phone. One scroll region for inventory only; Cancel and Confirm actions are fixed at the bottom (or sticky below the scroll region) and remain fully accessible and in viewport at all times, even with long inventory (multiple narrative sections + 3+ images + files + warnings). Section headings wrap; no nested dialog; expandable groups do not obscure or push actions off-screen.

### Accessibility

Labelled modal, inert background, focus contained; initial focus Cancel; Escape cancels before confirmation and returns to trigger. No backdrop confirmation. Once submitted, Close only dismisses progress and explicitly says the operation continues; Escape must not claim cancellation. Failed validation focuses summary; success politely announced and activity updated.

### Usage Example

Review publication opens saved revision 12. Owner inspects title/summary/narratives, every image/alt, each file and link, AI-origin fields, and private source names. PRIVATE warning: only reviewed exhibit content becomes public; repository stays private and its View code link is omitted. A revision change before confirmation invalidates this review. Confirm sends the approved snapshot identity; edits made afterward are excluded. Double click reuses operation identity. Preview and public export must agree on approved content. Neither public JSON nor HTML may contain private evidence metadata or hidden private links.

For Take down, name the exhibit and state: removes its page, gallery card, images and files from this site and its delivery cache; keeps Studio content; cannot withdraw downloaded copies or third-party caches/archives. No auto-confirm or optimistic claim of removal.

## FeaturedCarousel

| Field | Value |
|---|---|
| Component | FeaturedCarousel |
| Description | Manual showcase of up to 5 published, featured exhibits on the home page (FR9.7) |
| Category | display / navigation |

### States

| State | Trigger | Behavior |
|---|---|---|
| hidden | No published featured exhibit | No carousel or empty frame rendered |
| showing n of m | Load, or previous/next/dot/arrow key | Image, eyebrow, title, highlights, summary, View Project, Open the App (only when a live URL is published); position `0n / 0m` |
| reduced motion | `prefers-reduced-motion: reduce` | Slide change without crossfade |

### Props / Inputs

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| slides | published featured exhibits in confirmed order | yes | [] | Lead image + alt, title, highlights, summary, project link, optional live URL |
| index | number | yes | 0 | Current slide |

### Responsive Behaviour

Desktop: image fills the right of the band behind a gradient into the copy column; arrows and count bottom right. At 720 px and below: image on top (4:3), copy below, dots (28 px targets) instead of arrows, secondary action hidden.

### Accessibility

`aria-roledescription="carousel"` region with a label; copy region `aria-live="polite"`; previous/next are named buttons; dots carry `aria-current`. Never advances on its own (WCAG 2.2.2). Arrow keys act only when focus is within the carousel and not on a link.

### Usage Example

Home: STARS 01/03 → next → Baduk 02/03 announced → ArrowRight → Monopoly Arena 03/03; View Project goes to `project.html?p=monopoly-arena`.

## CategoryBrowser

| Field | Value |
|---|---|
| Component | CategoryTile / CategoryChips / CategoryPage |
| Description | Browse published exhibits by their one primary category (FR9.8) |
| Category | navigation |

### States

Populated (count of published exhibits); hidden when empty; active chip (`aria-current="page"`); not-on-display for empty/unknown category.

### Props / Inputs

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| categories | four fixed categories with fixed addresses | yes | — | Games & AI Arenas, Astronomy & Exploration, Woodworking, Software & Tools |
| counts | published exhibits per category | yes | 0 | Drafts and taken-down exhibits never counted |

### Responsive Behaviour

Home tiles: two wide tiles side by side (one per row on phones, as image-backed rows). Catalog: chips wrap; grid 3/2/1 columns.

### Accessibility

Chips are links in a labelled `nav`; counts are text. Category pages have their own h1. Not-on-display page keeps the site navigation and offers a link to all work.

### Usage Example

Home → Games & AI Arenas (2) → category page lists Baduk and Monopoly Arena; Woodworking has no published exhibit, so it is absent and its address shows "This category isn't on display".

## AccessMetadata and Badges

| Field | Value |
|---|---|
| Component | AccessFields (S4) / Badge (public) |
| Description | Record how a linked app and its source can be reached; derive public badges from it (FR4.10, FR10.5–FR10.7) |
| Category | input / display |

### States

Live URL: empty; entered; withheld (private-repository default, or Risk until "Live URL authorized"). Repository: confirmed public (licence read), private, or unconfirmed (treated as private). Rights review: not required; outstanding; complete.

### Props / Inputs

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| liveUrl | https URL | no | empty | Published exactly as entered |
| access | open / sign-in / invitation | yes | open | Describes the linked app, not this site |
| phone | suitable / desktop only / unknown | yes | unknown | "Best on desktop" badge only for desktop only |
| repos | visibility + licence from GitHub | no | [] | Fail closed when unconfirmed |
| rightsReview, liveUrlAuthorized | owner flags | when required | false | Gate Publish (FR10.6) and URL export (FR10.7) |

### Responsive Behaviour

Field pairs side by side on desktop, stacked on phones. Badges wrap.

### Accessibility

Derived badges are plain text, not colour-coded alone. Withheld URL field is disabled with an explanatory note linked by `aria-describedby`. PRIVATE is always spelled out.

### Usage Example

Monopoly: live URL open, desktop only, public repository without licence → "In browser · Best on desktop · Source available"; rights review outstanding blocks Publish. Risk: URL withheld, private repository → "Live link pending approval · Best on desktop · Source private"; nothing named or linked.

## FeaturedOrder

| Field | Value |
|---|---|
| Component | FeaturedOrder (S8) |
| Description | Reorder featured exhibits privately; publish the order through an explicit confirmation (FR9.7) |
| Category | input |

### States

Editing (private); confirming (dialog lists the public order and which featured drafts are not yet shown); updated (logged, FR7.7).

### Props / Inputs

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| featured | ordered list, at most 5, drafts included | yes | [] | Drafts appear once published |

### Responsive Behaviour

Ordered list with move-up/move-down buttons; full width on phones.

### Accessibility

Move buttons are named per item ("Move Baduk up") and focus stays on the moved control; change is announced politely; no drag-only interaction.

### Usage Example

Move STARS down → Baduk first (private) → Update featured order → dialog: "Baduk, STARS"; "Not shown until published: Monopoly Arena" → confirm → activity entry.

## Public Components

**StudioHeader / Sidebar** — wordmark, tagline, Home, All Projects, populated categories, About, credo and signature. No public link to the Studio.

**ExhibitCard** — category eyebrow, title link, summary, derived badges; lead image with alt; failed image keeps title and link. Pending candidates (prototype only) show no link and no image.

**ProjectDetail** — hero (lead image, back link, title, summary, highlights, Open the app, View source), in-page nav, story sections (empty omitted), details panel, gallery with enlarged view (native dialog), downloads (type and size in link text, attachment only). Private repositories never linked.

**NotOnDisplay** — unknown/unpublished/taken-down exhibit or empty category; production HTTP 404.

The public site never fetches the Studio API or database, loads no analytics and requests nothing from third-party origins; all content is a static export after explicit owner confirmation.

## Assumptions & Open Questions

Secure recovery storage, snapshot atomicity, queue failure resolution and exact rate limits are later implementation decisions; the invariants above are mandatory acceptance obligations. No UI mockup proves them. Independent security review remains required for implementation of authentication, private data and publication boundaries.
