# Interaction Specification

## Sources and Boundaries

Inputs: wireframes and user-flow in `../../ideation/rough-mockups/`, approved fixes beside them, requirements in `../requirements-analysis/requirements.md`, team-practices in `../practices-discovery/team-practices.md`. User stories are skipped. Screen IDs match `mockups.md`. These are implementation contracts proposed for design approval, not implemented capabilities.

## Journey Contracts

| Journey | Trigger and steps | Success | Failure and recovery |
|---|---|---|---|
| Curate | S1 owner+MFA → S2 → S3 → create/link → S4 edit/save → optional AI review → S5 → S6 | Approved saved revision exported; page/card/assets consistent | GitHub/AI errors do not change edits; conflict preserves local copy; publish failure retains last successful public version |
| Update | Open published project → edit/save → Changes since last publish → preview → full Update confirmation | New revision public | Saving alone never updates public content |
| Withdraw | S2 or S4 Take down → S7 named confirmation | Page/card/assets/cache gone within five minutes; Studio content retained | Copies outside this site cannot be revoked; failed removal shown explicitly |
| Republish | Open Taken down → edit/save (still Taken down) → preview → full Publish confirmation | Published only after checks and successful operation | No shortcut based on prior publication |
| Explore | P1 card → P2 summary/narrative/gallery/downloads → All work | Public static content, no account | Missing exhibit is HTTP 404 with useful navigation |

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

Upload hints precede picker: JPEG/PNG/WebP, up to 10 MB per image; approved build-file types, up to 50 MB each. Label progress per filename; announce completion/rejection without repeated percentage announcements. Alt text field has a link from publication error summary.

### Usage Example

Upload image → Checking file → accepted thumbnail, alt text and Set as lead. Wrong signature/type/size gives a specific reason. Upload authorization is short-lived, single-use and bound to limits, issued only to owner; upload bytes go directly to private storage, never through API body. Export re-encodes image derivatives and strips all metadata; originals stay private. Downloads show filename/type/size and use attachment/nosniff/safe type headers. The final allowed build-file list is confirmed in contract/security design (FR4.4); examples are PDF, SKP, FCStd, DXF, STL, ZIP, not arbitrary executable archives.

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

Desktop aside; below 1024 px follow editor in DOM with jump link. Sources and long paths wrap. No fixed height clipping.

### Accessibility

Native buttons and labelled suggestion textarea. Polite Generating status; at 60 seconds show No suggestion this time. Your text is unchanged. Retry follows server retry time for 429 and is never automatic. Provider permission and usage explanations are visible text.

### Usage Example

Show Provider: configured provider and the exact README/docs source list before Suggest description. Linked private repository blocks request unless that provider is approved for private content under documented no-training/stated-retention terms. Insert appends to the selected target field without replacing existing text; Edit changes the proposed text in the panel first, then Insert; Discard changes nothing. Insertion marks editor dirty and retains AI/private-source provenance even after edits. Repository instructions are untrusted data; AI has no tools/actions. Suggestion output is escaped everywhere.

## PublicationConfirmation

| Field | Value |
|---|---|
| Component | PublicationConfirmation |
| Description | Owner approves exact public snapshot, not all future edits |
| Category | input / display |

### States

Preparing inventory; ready; blocked; stale; confirming; queued; running; complete; failed. Required fields: nonempty title, validated lead image, alt text for every image. Other unresolved upload checks also block. The reasons are linked to editor fields; no disabled button without explanation.

### Props / Inputs

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| action | publish/update/take-down | yes | none | Exact label and result |
| revision | immutable saved identity | yes | none | Includes asset versions and complete inventory |
| inventory | full text/assets/links/provenance | publish/update | none | Inspectable content, not counts alone |
| publicState | last successful action | yes | none | Shown alongside pending operation |
| blockers | list | yes | empty | Server repeats all checks |

### Responsive Behaviour

Large dialog on desktop, viewport dialog on phone. One scroll area; section headings and actions wrap. No nested dialog. All inventory groups can expand without hiding confirm controls behind overlays.

### Accessibility

Labelled modal, inert background, focus contained; initial focus Cancel; Escape cancels before confirmation and returns to trigger. No backdrop confirmation. Once submitted, Close only dismisses progress and explicitly says the operation continues; Escape must not claim cancellation. Failed validation focuses summary; success politely announced and activity updated.

### Usage Example

Review publication opens saved revision 12. Owner inspects title/summary/narratives, every image/alt, each file and link, AI-origin fields, and private source names. PRIVATE warning: only reviewed exhibit content becomes public; repository stays private and its View code link is omitted. A revision change before confirmation invalidates this review. Confirm sends the approved snapshot identity; edits made afterward are excluded. Double click reuses operation identity. Preview and public export must agree on approved content. Neither public JSON nor HTML may contain private evidence metadata or hidden private links.

For Take down, name the exhibit and state: removes its page, gallery card, images and files from this site and its delivery cache; keeps Studio content; cannot withdraw downloaded copies or third-party caches/archives. No auto-confirm or optimistic claim of removal.

## Public Components

ExhibitCard inputs: approved title, summary, image derivative/alt, public URL. States: reserved image, loaded, image failed; link always usable. One accessible link per card; visible title provides name; hover is optional and keyboard focus equivalent. Phone stacks all content. Example: focus AI Arcade card → Enter → P2.

ImageViewer inputs: public derivative, alt, invoking thumbnail. States: closed/loading/open/failed. Labelled dialog with Close, Escape and focus return, no autoplay; phone fits image and controls without clipping. Downloads name type/size. Missing exhibit uses real HTTP 404, not a successful response with error copy. Public page never fetches Studio API/database or loads analytics.

## Assumptions & Open Questions

Secure recovery storage, snapshot atomicity, queue failure resolution and exact rate limits are later implementation decisions; the invariants above are mandatory acceptance obligations. No UI mockup proves them. Independent security review remains required for implementation of authentication, private data and publication boundaries.
