# Refined Mockups — Engineering Studio

## Review Surface and Sources

Open `design-board.html` locally for desktop and phone compositions and critical state specimens. It has no scripts, external resources, live data or network calls. It is a static design artifact, not an application or proof of implemented security.

Inputs: `../../ideation/rough-mockups/wireframes.md` (wireframes), `../../ideation/rough-mockups/user-flow.md` (user-flow), approved `proposed-default-fixes.md` beside them, `../requirements-analysis/requirements.md` (requirements), and `../practices-discovery/team-practices.md` (team-practices). User stories are skipped. Requirement IDs provide traceability.

All six approved corrections are incorporated: private code links hidden; phone grid stacked; tags removed; plain email contact; lead image and alt text required; take-down in list/editor and gallery card in preview. Requirements add Taken down status, upload validation, exact publication content, owner authentication and AI permissions.

## Visual Proposal

Work appears immediately below a compact identity header. A generous asymmetric grid, navy surfaces, warm-white type and restrained mint controls frame imagery. No marketing hero, categories, appearance controls, visitor account or public Studio link. Proposed tokens are in `design-system-mapping.md`.

At 1440 px, public content is capped at 1280 px with 48 px gutters. At tablet width use 24 px gutters; on phones use 20 px, reducing to 16 px at 360 px. Body text starts at 16 px with 1.6 line height. Layout must work at 320 CSS px and 400% zoom.

Image placeholders explicitly request real screenshots, CAD renders or workshop photos; they do not pretend to depict real projects. Sample descriptions require separate content approval before publication.

## Screen Specifications

| Screen | Desktop composition | Phone/tablet adaptation | Traceability |
|---|---|---|---|
| P1 Gallery | Identity and descriptor; 12-column wall: first card 7 columns, second 5, third full-width image/text split. One link per card; no masonry reordering. | Below 768 px all cards stack in DOM order, image before text. Tablet uses 6/6 plus full-width third. | FR9.1, FR9.4–FR9.6; D-14, D-16 |
| P2 Exhibit | All work; lead image; title/summary and existing public links; six narrative sections at 68ch; optional image gallery and downloads. | Same order, wrapping links and prose; image enlargement in accessible dialog. | FR4.1, FR4.3–FR4.5, FR9.2–FR9.3 |
| S1 Sign-in | Studio, privacy explanation, Sign in. Auth0 handles sign-in and MFA. No project content preloaded. | Fluid width; provider errors wrap. | FR1.1–FR1.4 |
| S2 Projects | Heading, Discover; table with project, repo count, exact worded status, updated time, Open and conditional Take down. Owner-only activity section with time/exhibit/action/outcome. | Below 768 px labelled project cards retain all fields and actions. | FR3.1–FR3.5, FR7.7, FR8.1 |
| S3 Discover | Search, count, repository rows with PRIVATE/public, updated time, linked project. Use reveals inline Create project/Link to existing choice; linked rows offer Open only. | Stacked rows; full-width search; labels always visible. | FR2.1–FR2.5, FR3.1 |
| S4 Editor | Projects breadcrumb, title/status, Save, Preview, Review publication. Main form: title/summary, six narrative fields, uploads/alt/lead selector, links/files and repositories. AI aside. Separate Take down control. | Below 1024 px AI follows form; Jump to AI suggestion link. Actions wrap without covering fields. Editing remains possible on phones. | FR3–FR5, FR8.1 |
| S5 Preview | Persistent Preview — not public banner; gallery card above full P2; Back to editor and Review publication. Same public renderer as export, admin controls outside it. | Card and page reflect viewport; banner never obscures focus. | FR6.1–FR6.2; D-20 |
| S6 Publish/update | Large dialog: saved revision, target URL, complete public content inventory, text, images/alt, files/type/size, links, AI-origin labels and private-source attribution. Cancel then explicit confirmation. | Full viewport dialog, one scroll region; wrapping inventory; actions never obscure content. | FR7.1–FR7.8; D-22 |
| S7 Take down | Names exhibit; page/card/assets removed, Studio retained, downloaded/third-party copies cannot be withdrawn. Cancel first. | Single-column dialog. | FR8.1–FR8.4 |

## Screen State Matrix

| Screen | Empty | Loading / operation | Success | Error / partial |
|---|---|---|---|---|
| P1 | New work is being installed. | Reserved image space; static text, no API. | Published exhibits only. | Failed image retains title/summary/link; one exhibit fills composition. |
| P2 | Omit absent optional blocks. | Reserved image dimensions. | Approved export. | Unknown/taken down: This exhibit isn't on display, All work, actual HTTP 404. Failed image keeps description. |
| S1 | Sign in to continue. | Signing in. | Owner with MFA reaches Projects. | Non-owner: This workspace is private, no names/counts. Session expiry retains protected recovery for same owner. |
| S2 | No projects yet; Discover a GitHub repository. | Busy skeletons; no content for unverified session. | Four status words; activity. | Retry on load error. Verified owner retains existing rows during refresh failure. Operation state separate from project status. |
| S3 | No repositories / no match; query retained. | Loading/searching, polite count. | Use / Open linked project. | Can't reach GitHub right now. Your projects are unaffected. Rate-limit retry respects server time. |
| S4 | New draft, labelled fields. | Saving; upload then Checking file; AI generating up to 60 seconds. | Saved revision/time; accepted upload; suggestion ready. | Conflict/offline preserves buffer; inline upload/alt errors; expiry hides private content until owner returns. |
| S5 | Missing fields visible with links back to edit. | Preparing saved revision preview. | Card plus page, always marked private. | Retry or reauthenticate; never fall back to public draft URL. |
| S6 | Missing requirements listed; confirmation unavailable. | Queued then publishing/updating. | Completion time; publicly visible within five minutes. | Failure retains last successful public version; explicit revision-bound retry. |
| S7 | Hidden for Draft/Taken down. | Queued then taking down. | Taken down after page/card/assets/cache removal. | Failure retains last successful public state; explicit retry. |

## Content Approval and Revision Binding

The S6 specimen is a composition, not an approval shortcut. Production must expose the complete proposed content, not just counts or a generic checkbox. Expandable groups reveal exact text and each asset/link identity. Private repository names appear only in Studio. Public exports contain neither private source paths nor evidence metadata. Manually edited AI text retains its origin in the confirmation inventory.

Confirmation binds one saved revision and asset versions. A change before confirmation expires the inventory and requires fresh review. Edits saved after confirmation are excluded and leave Changes since last publish. Operations execute in confirmation order. Take down after a queued publish remains possible, with successful completion leaving nothing public. Full behavior is in `interaction-spec.md`.

## Requirements Coverage

| Group | Coverage / implementation obligation |
|---|---|
| FR1 | S1/recovery; issuer+subject verification and MFA are server/provider controls, not visual proof. |
| FR2 | S3 visibility/search/already-linked/GitHub failure. |
| FR3 | S2/S4 four statuses, explicit save and conflict preservation. |
| FR4 | S4 fields/upload checks; P2 public layout. |
| FR5 | Provider/evidence/permissions/limits, Insert/Edit/Discard; no autonomous publish. |
| FR6 | S5 private card+page. |
| FR7 | S6 exact inventory, revision binding, serial operations/activity. |
| FR8 | S2/S4 entry points, S7 and P2 404. |
| FR9 | P1/P2, no analytics/accounts/tags, plain contact. |
| FR10 | Seed titles only on sample board. Real content/domains/301/indexability/launch remain later owner and implementation gates. |
| NFR1–NFR4 | Owner boundary, no browser credentials, spending disabled pending permission. |
| NFR5–NFR7 | Responsive reserved images/static reads/pending states. Performance requires built-site measurement. |
| NFR8–NFR9 | Accessibility checklist; local resources, no preference collection. |
| NFR10–NFR14 | Safe saves, activity, portable records. Backups/runtime logs/browser tests/quality gates remain implementation work. |
| NFR15–NFR16 | Escaped content and rate-limit messages; CSP/headers/server limits require implementation verification. |

## Assumptions & Open Questions

This proposes screen details, not new product scope or security policy. Secure edit recovery, transaction implementation, provider choice and upload authorization remain architecture work. Content approval, spending approval, deployment approval and this design gate are separate decisions.
