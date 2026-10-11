# Requirements — Architect's Portfolio, First Release

Sources: the initial request and `docs/CHARTER.md`; the approved Ideation artifacts — `intent-statement`, `scope-document` (with `intent-backlog`), `rough-mockups/wireframes.md` and `proposed-default-fixes.md`, and the decision log (D-01 to D-22); the affirmed `team-practices` (now `aidlc/spaces/default/memory/team.md`) and project rules (`project.md`); and this stage's answers (`requirements-analysis-questions.md`, Q1 to Q6). Every requirement names its source. IDs are permanent traceability keys.

**Amendment A1 (2026-10-10).** This document includes change requests CR-01 to CR-05, applied after the owner authorized them in his instruction "Architect Portfolio — Autonomous Continuation" on 2026-10-10. They are recorded as D-23 to D-28 in the decision log. The independent architecture review relayed by the owner shaped their final text. The proposal, the review refinements and the evidence are in `inception/refined-mockups/requirements-change-proposal.md` and `launch-inventory.md`. The authorization covers these requirements and design work only. It does not cover deployment, publication of any particular project, or approval of any stage gate. Every change is listed in the Change Log at the end, and amended or new requirements cite their CR.

## Intent Analysis

Michael Broadfoot wants one credible, image-rich home for a scattered body of work, aimed at prospective clients and employers, engineers and makers, and wants curating it to take little effort (intent-statement; D-01, D-02). The first release proves the whole loop on real work: the owner signs in to a private Studio, turns a GitHub repository into an exhibit with an AI-drafted description they review, previews it, publishes it explicitly, and can take it down; visitors see it in an image-led gallery at michael.broadfoot.consulting (scope-document; D-09, D-14, D-21). The launch candidates — STARS, Monopoly, Baduk and Risk — are each eligible to be published this way, only after its own owner approval. None is required for launch (FR10.1; CR-01, which supersedes the charter §8 seed examples AI Arcade, STARS and Mom's Recipe Box).

Two properties matter more than any feature: nothing private ever becomes public without the owner's explicit approval of that exact content (charter §4, §5; D-22), and the public site stays free of tracking (charter §3; D-04).

**Decisions made in this stage** (Q1 to Q6):

- Running cost stays on free tiers until an application genuinely needs something paid. Small pay-per-use spending (AI calls, AWS requests beyond free allowances) happens only when the owner has explicitly approved it; no dollar limit is assumed or pre-approved, and budget alerts are notifications, not spending caps (Q1, Q5, owner clarification 2026-10-10).
- The AI is a curation assistant for the owner only, inside the private Studio. It uses an open, provider-independent framework with server-side provider adapters. Runtime provider credentials live in AWS SSM Parameter Store (chosen because it is free; Secrets Manager is not), readable only through least-privilege IAM and only via authenticated, authorized Studio endpoints, and never reach the browser. The first provider is chosen in design (Q2, Q6, owner clarification 2026-10-10).
- The public site is a static export written on publish; it never calls the API or the database (Q3).
- Exhibit images are uploaded in the Studio; selecting images from a GitHub repository is a future enhancement (Q4, owner clarification 2026-10-10).

## Functional Requirements

Acceptance criteria use Given/When/Then. "Owner" means Michael Broadfoot signed in to the Studio.

### FR1 — Studio access (owner only)

Source: charter §4, §8; intent-backlog IB-1; wireframes S1.

- **FR1.1** The Studio shall require sign-in through the identity provider and admit only the single configured owner identity. The server matches the owner on two configured values in the validated token: the Auth0 issuer and the immutable subject ID. Email address, display name and any user-editable claim never establish ownership. Public self-registration on the Auth0 tenant is disabled. (Review R-01; owner guidance.)
  - Given a visitor who is not signed in, When they open any Studio page, Then they see the sign-in screen and no Studio content.
  - Given someone signed in with any identity other than the owner's, When they open the Studio, Then they see "This workspace is private." and nothing about projects.
  - Given a token whose email equals the owner's but whose subject ID differs (a look-alike or newly created account), When it calls any Studio endpoint, Then the call is refused with 403.
  - Given a token with the owner's subject ID but issued by a different issuer, or an unverified, expired or malformed token, When it calls any Studio endpoint, Then the call is refused with 401 or 403.
  - Given the Auth0 tenant's sign-up page, When anyone tries to create an account, Then sign-up is not available.
- **FR1.2** Every Studio API operation shall verify, on the server, that the caller is the owner; client-side checks alone never grant access.
  - Given a request to any Studio API endpoint without a valid owner session, When it is received, Then it is refused with 401 or 403 and no data is returned or changed.
- **FR1.3** The owner's sign-in shall require multi-factor authentication.
  - Given the owner signs in, When credentials are accepted, Then a second factor is required before the Studio opens.
- **FR1.4** When the owner's session expires mid-edit, unsaved edits shall survive re-authentication.
  - Given unsaved changes in the exhibit editor, When the session expires and the owner signs in again, Then the editor reopens with the unsaved changes intact.

### FR2 — Repository discovery (GitHub)

Source: charter §4, §8; IB-3; wireframes S3; D-15.

- **FR2.1** The Studio shall list the owner's GitHub repositories, public and private, with name, visibility (shown as text), last-updated date and, where linked, the project it belongs to; the list is searchable by name.
  - Given the owner opens Discover, When the list loads, Then each repository shows its visibility as the word PRIVATE or public, not only as an icon.
  - Given a search with no match, When results return, Then the Studio says no repository matches and keeps the search text.
- **FR2.2** GitHub access shall use a read-only credential scoped to the owner's repositories and to what discovery and AI evidence need (repository metadata, README and documentation files): a fine-grained personal access token or a GitHub App installation, chosen in design. It is a runtime secret under NFR3. (Review R-03.)
  - Given the GitHub credential, When it is used to attempt any write to a repository, Then GitHub refuses it.
- **FR2.3** A repository already linked to a project shall open that project rather than create a duplicate.
- **FR2.4** When GitHub is unreachable or rate-limited, the Studio shall say so, offer a retry, and leave existing projects untouched.
  - Given GitHub returns an error or times out, When the owner opens Discover, Then the message "Can't reach GitHub right now" appears with a retry, and the Projects list still works.
- **FR2.5** Discovering or linking a repository shall never change its visibility on GitHub or publish anything.

### FR3 — Projects

Source: charter §3, §8; IB-4; wireframes S2; D-21.

- **FR3.1** The owner shall be able to create a project with only a title, and may link zero, one or several repositories to it at any time. A repository link is optional; work such as woodworking, CAD and design projects is supported as fully as software. (CR-02.)
  - Given no repository, When the owner creates a project titled "Hall table", Then a Draft project exists with no repository link.
  - Given a project with no repository, When the owner links a repository later, Then the link is added and the project's content is unchanged.
- **FR3.2** Each project shall have exactly one status, shown in words: Draft, Published, Changes since last publish, or Taken down. Allowed transitions (Review R-06):

  | From | Owner action | To |
  |------|--------------|----|
  | (new) | Create (title only, or from a repository) | Draft |
  | Draft | Publish | Published |
  | Published | Save an edit | Changes since last publish |
  | Changes since last publish | Update the public exhibit | Published |
  | Published, or Changes since last publish | Take down | Taken down |
  | Taken down | Save an edit | Taken down (edits stay private) |
  | Taken down | Publish | Published |

  Any other transition is refused. Every Publish and Update goes through the full confirmation and checks in FR7.
  - Given a project in Taken down, When the owner chooses Publish, Then the full Publish confirmation (FR7.2) and checks (FR7.3) run before anything becomes public.
- **FR3.3** Saved changes shall persist across sessions and devices.
- **FR3.4** If the same project is saved from two tabs or devices, the later save shall be refused with a clear conflict message rather than silently overwrite.
  - Given a project open in two tabs, When the first tab saves and then the second tab saves older content, Then the second save is refused with a message and nothing is lost.
- **FR3.5** The Projects list shall show an empty state with both a "New project" action and a "Discover a GitHub repository" action when no projects exist. (CR-02.)

### FR4 — Exhibit content

Source: charter §3, §8; IB-5 to IB-8; scope Q2 and Q4 (this stage); D-15, D-17, D-19.

- **FR4.1** An exhibit shall have a title, a one-paragraph summary, and six narrative sections: inspiration, design challenges, architectural decisions, implementation, outcomes, lessons learned. Empty sections are omitted on the public page.
- **FR4.2** The owner shall upload exhibit images in the Studio (Q4): JPEG, PNG, WebP or HEIC/HEIF, up to 10 MB each, with alt text per image. HEIC/HEIF photos are converted during upload processing to sanitized web images (JPEG or WebP); conversion keeps only the primary image, after applying its orientation, so thumbnails, depth maps, sequences and metadata items are dropped. Only the converted image is ever published, and the original stays in private storage (CR-02). One image is designated the lead image. Uploads are validated by their actual content (file signature), not by extension or declared type. Image decoding checks the declared dimensions against a pixel limit (set in NFR Design) before any full decode, runs with memory and time limits, and rejects the file on any failure; upload processing is a security-sensitive path (team practice). Published images are derivatives re-encoded on export with all metadata removed — EXIF, GPS location, device, timestamps, embedded thumbnails and comments; originals stay in private storage. (Review R-02; owner guidance; review-04 A1-S07, review-03 A1-P08.)
  - Given an upload of an unsupported type or a file over 10 MB, When it is submitted, Then it is rejected with the reason and the rest of the exhibit is unaffected.
  - Given a file named `photo.jpg` whose content is not a JPEG, PNG, WebP or HEIC/HEIF image, When it is uploaded, Then it is rejected.
  - Given a corrupt or unconvertible HEIC file, When it is uploaded, Then it is rejected with the reason "This photo could not be converted" and nothing is stored for it.
  - Given an image whose declared dimensions exceed the pixel limit, When it is uploaded, Then it is rejected without being fully decoded.
  - Given an uploaded HEIC photo, When the exhibit is published, Then the public copy is a JPEG or WebP with no metadata, and no HEIC file is in public storage.
  - Given an uploaded photo containing GPS and device EXIF tags, When the exhibit is published, Then the public copy of that image contains no EXIF, GPS or device metadata.
- **FR4.3** The owner shall add links out to repositories, a live application and a demo. A link to a private repository is never shown publicly (D-15).
  - Given an exhibit linked to a private repository, When it is published, Then the public page has no "View code" link for that repository.
- **FR4.4** The owner shall attach maker and design files of the allowed types — PDF, SKP, FCStd, DXF, STL, ZIP and VSDX (CR-02) — up to 50 MB each. Other formats (for example DWG, STEP, 3MF) are deferred until a project needs them; public links state the file type and size. Each file is validated by its actual content against an allowed list of file types: VSDX is accepted only when it is a ZIP whose `[Content_Types].xml` declares a Visio drawing part, and FCStd only when it is a ZIP containing `Document.xml`. Content checks on ZIP-based files read only the central directory and at most the named entry, enforce limits on uncompressed size and compression ratio, never extract to disk, and parse XML with DTDs and external entities disabled. Public downloads are always served as attachments, with a fixed safe content type for their file type (`application/octet-stream` unless NFR Design fixes a more specific one), `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff` and `Content-Security-Policy: sandbox; default-src 'none'`, so a browser never renders or runs them in the site's context. (Review R-02; owner guidance; review-04 A1-S08, A1-S10; review-03 A1-P08.)
  - Given a file whose content does not match an allowed type (for example an HTML or executable file renamed `.pdf`, or a plain ZIP renamed `.vsdx`), When it is uploaded, Then it is rejected.
  - Given a zip bomb renamed `.vsdx`, When it is uploaded, Then it is rejected within the size and ratio limits without being extracted.
  - Given a VSDX whose XML declares an external entity, When it is checked, Then the entity is not resolved and no outbound or file read occurs.
  - Given a published download, When it is requested, Then the response carries `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, the sandbox Content-Security-Policy and the fixed content type for its file type.
- **FR4.8** Image and file uploads shall go directly from the Studio to private storage through short-lived, single-use upload authorizations (for example pre-signed URLs) issued only to the owner. The size limit and allowed type are bound into each authorization, and the server re-checks content before the file can be attached to an exhibit. Uploads never pass through the API's request body. (Review R-04.)
  - Given an upload authorization, When it is used after it expires, for a larger file than authorized, or by anyone without an owner session to request it, Then the upload is refused.
- **FR4.5** Text the owner or the AI writes shall be rendered as plain formatted text; markup and scripts in it are escaped, never executed, on any page.
- **FR4.6** Leaving the editor with unsaved changes shall ask first.
- **FR4.7** The first release has no topic tags (D-17).
- **FR4.9** Maker and design attachments shall be stored privately, offered publicly only if the owner includes them at Publish, and never rendered or executed in the browser. PDFs, like every attachment, are offered only as downloads (FR4.4); a drawing is shown inline only as an owner-uploaded image with alt text. (CR-02; review-03 A1-P03, review-04 A1-S10.)
  - Given an SKP file attached but not included at Publish, When the exhibit is published, Then the file is not in public storage and the page has no link to it.
  - Given a published PDF, When a visitor opens its link, Then it is downloaded, not displayed in the page.
- **FR4.10** Each exhibit shall record access metadata separately from its narrative: an optional live URL; the linked app's access requirement (open, sign-in, invitation — this describes the linked app, not this site); phone suitability (suitable, desktop only, unknown); and, for each linked repository, its visibility and licence as read from GitHub. Public badges are derived only from these fields, never typed freehand (CR-03):

  | Field value | Public badge |
  |---|---|
  | Live URL included at Publish, access open | "In browser" |
  | Live URL included at Publish, access sign-in | "Sign-in required" |
  | Live URL included at Publish, access invitation | "By invitation" |
  | Phone suitability desktop only | "Best on desktop" (suitable and unknown show no badge) |
  | Repository confirmed public, licence an OSI-approved SPDX identifier | "Open source · ⟨SPDX id⟩" |
  | Repository confirmed public, no licence, "other" or NOASSERTION | "Source available" |
  | Repository private, or visibility not confirmed | "Source private" |

  **Fail closed.** A repository whose visibility cannot be confirmed from GitHub at Publish or Update (error, rate limit, rename) is treated as private: no name, link or licence is shown, and the confirmation says so. **Export allow-list.** The public export contains only the derived badge labels, the owner-included live URL, and the name, URL and licence of each repository confirmed public at Publish. Nothing else from access metadata or link checks — reachability results, final addresses, sign-in detection, check times, private repository names, URLs or IDs — is exported. (Review-03 A1-P04, A1-P05; review-04 A1-S11, A1-S12.)
  - Given a public repository with no licence, When the exhibit is published, Then its badge reads "Source available".
  - Given a private repository, When the exhibit is published, Then the badge reads "Source private" and no repository link or name appears (FR4.3, D-15).
  - Given GitHub returns an error when visibility is read at Publish, When the confirmation renders, Then the repository is treated as private, its name and link are omitted, and the confirmation states that visibility could not be confirmed.
  - Given a published exhibit, When the public export is scanned (HTML, attributes, JSON, alt text, file names), Then it contains no access-metadata field outside the allow-list.

### FR5 — AI description suggestion

Source: charter §5, §8; IB-9; Q2, Q5, Q6; D-22; wireframes S4.

- **FR5.1** The owner shall request a description suggestion for a project; the suggestion is drawn from the linked repositories' README and documentation files. A project with no linked repository offers no suggestion, and the owner writes its text; this workflow is otherwise unchanged (CR-02).
  - Given a project with no linked repository, When the owner opens the editor, Then no suggestion action is offered and the editor says suggestions need a linked repository.
- **FR5.2** Each suggestion shall list the source files it was drawn from, and shall never overwrite existing text: the owner chooses Insert, Edit or Discard.
  - Given a suggestion is shown, When the owner does nothing, Then no exhibit field changes.
- **FR5.3** The AI capability shall be reachable only through owner-authenticated Studio functions; it is never exposed to visitors or the public site (Q2).
  - Given a request to the suggestion endpoint without an owner session, When it is received, Then it is refused and no provider call is made.
- **FR5.4** The AI integration shall use a provider-independent interface (charter §5) with server-side provider adapters, implemented with an open framework, so providers can be swapped by configuration. The first provider is chosen in design (Q6).
- **FR5.5** Provider API credentials used at runtime shall be stored as SecureString parameters in AWS SSM Parameter Store (standard tier, no charge), read only by the Studio API's execution role through a least-privilege IAM policy scoped to those parameters, and used only inside authenticated, authorized Studio endpoints. They never reach the browser, the repository, logs or the public site. (GitHub Actions secrets are not available to Lambda at runtime, so they are not the runtime store.) Source: Q2; owner clarification 2026-10-10; project rule NEVER commit secrets.
  - Given any browser response from the Studio or the public site, When it is inspected, Then it contains no provider credential.
  - Given a Lambda function or role other than the Studio API's, When it requests the provider parameters, Then IAM denies the read.
- **FR5.6** Repository content passed to the AI shall be treated as untrusted data: it is delimited, cannot change the system instructions, and the AI has no tools or actions — it only returns text.
- **FR5.7** A failed, timed-out (60 seconds) or malformed AI response shall leave all text unchanged and show "No suggestion this time" with a retry.
- **FR5.8** Calls to a paid AI provider shall stay disabled until the owner has explicitly approved that pay-per-use spending. The owner sets a monthly suggestion limit when approving; past that limit, new suggestions are refused with a clear message until the next month or until the owner raises it (NFR4).
  - Given the owner has not approved AI spending, When a suggestion is requested, Then no provider call is made and the Studio explains that AI suggestions need approval.
- **FR5.9** Private repository content shall be sent to an external AI provider only after the owner has approved that provider for private content, based on its documented data-use terms: no training on submitted content, and stated retention. The Studio names the provider that will receive repository text before each suggestion request, and records which provider was used with the suggestion. (Review R-05; owner guidance.)
  - Given a configured provider that has not been approved for private content, When a suggestion is requested for a project linked to a private repository, Then no repository content is sent and the Studio explains why.
  - Given an approved provider, When the owner opens the suggestion panel, Then the panel names the provider before the request is sent.

### FR6 — Preview

Source: charter §8; IB-10; wireframes S5; D-20.

- **FR6.1** The owner shall preview an exhibit exactly as visitors will see it — its page, its gallery card, its slide in the featured carousel when it is featured, and its place on its category page — marked "Preview — not public" at all times. (CR-05; review-03 A1-P02.)
- **FR6.2** A preview shall never be reachable by visitors.
  - Given a preview, When a person who is not the owner requests its address, Then they receive no exhibit content.

### FR7 — Publication

Source: charter §4, §5, §8; IB-2, IB-11; D-19, D-22; Q3.

- **FR7.1** Nothing shall become public except through the owner's explicit Publish confirmation.
- **FR7.2** The Publish confirmation shall list everything that will become public — text sections, AI-originated text, images, downloadable files and links — and name any linked private repository whose content informed the text (D-22). It also shows (CR-03, CR-05):
  - for each live link and repository link that will become public, the latest check result and its time (FR10.5), with any redirect to a different registrable domain flagged;
  - the featured status and primary category that will be published (FR9.7, FR9.8);
  - for each attachment, its embedded document metadata and, for ZIP-based files, its list of entries, flagging names that look like secrets (`.env`, `.git/`, `id_rsa`, `*.pem`) and stating that the file is published unchanged (review-04 A1-S09);
  - any outstanding rights review (FR10.6) or unauthorized live URL (FR10.7).

  Attachment metadata extraction and entry listing run under the same size, ratio and parser limits as FR4.4; if extraction fails, the confirmation says "Metadata could not be read" rather than showing none (review-04 A1-S17).
- **FR7.3** Publish shall be blocked, with the reason shown, when the title is empty, there is no lead image, any image lacks alt text (D-19), or a required rights review is outstanding (FR10.6; review-03 A1-P15).
- **FR7.4** Publishing shall export the exhibit as static public content — its page, its gallery card and its assets — and re-export every page that shows it: the home page (gallery and featured carousel) and its category page (Q3; CR-05). Re-exported pages are built only from the last published state of every exhibit; unpublished changes to other exhibits never appear (review-04 A1-S18). The public site never reads the Studio's database or API.
  - Given the owner confirms Publish, When export completes, Then the exhibit page, its card, its carousel slide when featured and its category page entry are publicly visible within 5 minutes and the project status is Published.
  - Given exhibit B has saved but unpublished changes, When exhibit A is published and the home page is re-exported, Then the home page shows B as last published.
- **FR7.5** Edits to a published exhibit shall stay private until the owner confirms "Update the public exhibit"; meanwhile the status is "Changes since last publish".
- **FR7.6** Publishing shall be safe to repeat: a double click or retry produces one consistent public exhibit.
- **FR7.7** Each publish, update and take-down shall be recorded in an owner-visible activity log with time, exhibit and action.
- **FR7.8** Publication operations (publish, update and take-down) for the same exhibit shall run one at a time, in the order the owner confirmed them. The public state always matches the last successfully completed owner action, never a mix of two. An edit saved while a publication operation runs is not included in it, and leaves the status at "Changes since last publish". (Review R-06; owner guidance.)
  - Given the owner confirms Publish and then Take down in quick succession, When both complete, Then the exhibit is not public, and no page, card or asset from the publish remains in public storage.
  - Given a publication operation fails partway, When the owner looks at the exhibit, Then the public state equals the last successful action and the Studio shows the failure with a retry.

### FR8 — Take down (Must Have, D-21)

Source: D-20, D-21; IB-16; wireframes S2, S4, P2.

- **FR8.1** The owner shall take down a published exhibit from the Projects list or the editor, after a confirmation naming the exhibit.
- **FR8.2** Take-down shall remove the exhibit's page, gallery card and public assets from public storage and from the content-delivery cache, and remove it from the featured carousel, its category page and the category counts. A category left with no published exhibit is removed and its address returns 404 (FR9.3). The affected pages are re-exported and invalidated in the cache. The exhibit's featured slot is released and is not restored automatically if it is published again. (CR-05; review-03 A1-P02, review-04 A1-S15.)
  - Given the owner confirms Take down, When it completes, Then within 5 minutes the exhibit no longer appears in the gallery, its address shows "This exhibit isn't on display" with a 404 status, and its images and files return 404.
  - Given a featured exhibit is taken down, When the take-down completes, Then within 5 minutes it is absent from the carousel, the remaining featured exhibits keep their order, and an empty carousel is not shown.
  - Given the only published exhibit in a category is taken down, When the take-down completes, Then within 5 minutes the category is absent from the home page and its address returns 404.
- **FR8.3** A taken-down exhibit shall keep its Studio content and can be published again later.
- **FR8.4** Take-down removes content only from this site and its content-delivery cache. It cannot revoke copies already downloaded by visitors, or held in third-party caches, search-engine caches or archives. The take-down confirmation says so. (Owner guidance on R-06.)
  - Given the owner opens the take-down confirmation, When it is shown, Then it states that copies already downloaded or cached elsewhere cannot be withdrawn.

### FR9 — Public site

Source: charter §1, §2, §3; scope-document; wireframes P1, P2; D-04, D-09, D-14, D-16 to D-18.

- **FR9.1** The home page shall show, in order: a featured carousel when any exhibit is featured (FR9.7), the categories (FR9.8), and the gallery of published exhibits — image-led cards for published exhibits only, in an orderly grid of equal cards from tablet width up and a single column on phones (D-14, D-16; the equal-card grid of the CR-04 identity, D-26, replaces D-16's varied tiles; CR-05; review-03 A1-P12). Featured items and category counts include published exhibits only, and a category with no published exhibit is not shown.
  - Given no exhibit is published, When a visitor opens the site, Then the header and "New work is being installed." appear, with no broken grid.
  - Given a card's image fails to load, When the gallery renders, Then the card keeps its title and summary and still opens the exhibit.
- **FR9.2** Each exhibit page shall show the lead image, title, summary and the links that exist, then the narrative sections, the image gallery (with an enlarged view) and the build-it-yourself downloads; absent blocks are omitted.
- **FR9.3** An unknown or taken-down exhibit address shall show "This exhibit isn't on display" with a link to all work and a 404 status.
- **FR9.4** The footer shall carry a GitHub link, a plain email contact link that collects nothing, and the copyright line (D-18).
- **FR9.5** The public site shall set no tracking or analytics cookies, load no third-party analytics or advertising scripts, and require no visitor account (charter §3; D-04). It requests nothing from any third-party origin: fonts, styles, scripts and images are all self-hosted (review-04 A1-S16).
  - Given a visitor loads the home page, an exhibit page and a category page, When the requests are recorded, Then every request goes to the site's own origin.
- **FR9.6** The visual design shall follow the owner-approved crafted studio identity — warm charcoal with brass accents, editorial serif display type with a clean sans for interface text, sophisticated imagery, restrained interaction — using the design tokens recorded in `inception/refined-mockups/design-system-mapping.md` as approved at the Refined Mockups gate (until that gate is approved, the R5 token table there is the working reference; review-03 A1-P14), without copying any inspiration site's appearance or branding. Every text and background token pair meets 4.5:1 contrast (NFR8). (CR-04; replaces the charter's "Engineering Studio" dark-navy direction; review-03 A1-P10.)
  - Given the approved token table, When each text token is measured against each background it is used on, Then every pair is at least 4.5:1.
- **FR9.7** The owner shall mark up to 5 exhibits as featured, drafts included in the count, and set their order (review-03 A1-P15). Only published exhibits appear in the carousel: featuring a draft takes effect when it is published. Featured status is an exhibit field published with that exhibit's Publish or Update; saving a change to it on a published exhibit sets "Changes since last publish" (FR3.2). Reordering the carousel, which affects several exhibits, reaches the public site only through an explicit "Update featured order" confirmation that lists the new order; it is recorded in the activity log (FR7.7) and safe to repeat (FR7.6). The carousel never advances on its own; it is operable by keyboard, has visible previous and next controls and a position indicator, announces the change of slide politely to screen readers, and respects reduced motion (NFR8, WCAG 2.2.2). (CR-05; review-03 A1-P01, review-04 A1-S14.)
  - Given no published exhibit is featured, When the home page renders, Then no carousel or empty frame appears.
  - Given the carousel has focus, When the visitor presses the right arrow key, Then the next featured exhibit is shown and announced, and nothing advances without input.
  - Given the owner reorders the featured exhibits and saves, When no "Update featured order" confirmation has been given, Then the public carousel order is unchanged.
- **FR9.8** In v1 each project shall have at most one primary category, chosen from four fixed categories: Games & AI Arenas, Astronomy & Exploration, Woodworking, Software & Tools, each with a fixed address (`/category/games`, `/category/astronomy`, `/category/woodworking`, `/category/software`). A project may have no category; it then appears only in the gallery. Each category has a page listing its published exhibits; a category with no published exhibit is not shown, and its address returns 404 with "This category isn't on display" and a link to all work (review-03 A1-P15). A category is not a tag (FR4.7 unchanged). The primary category is an exhibit field published with that exhibit's Publish or Update; saving a change to it on a published exhibit sets "Changes since last publish". Classification is modelled as a project-to-category relationship with one entry marked primary, not as a single field on the project, so a later release can allow several classifications without migrating data; v1's Studio and public site use only the primary category. Creating, renaming or deleting categories is on the Future Roadmap. (CR-05; architecture review refinement; review-03 A1-P01, A1-P11.)
  - Given a category with two published exhibits and one draft, When its page renders, Then it lists the two published exhibits only.
  - Given a published exhibit whose category the owner changes and saves, When no Update has been confirmed, Then the public site still shows it in its previous category.

### FR10 — Launch content and launch

Source: charter §2, §8; IB-14, IB-15; D-12; CR-01, CR-03 (D-23, D-25).

- **FR10.1** The launch candidates — STARS, Monopoly (working title "Monopoly Arena"), Baduk and Risk — are each eligible for individual publication through the Studio workflow, not hand-authored. None of them is mandatory for launch, and launch may proceed with any owner-approved subset. A candidate is published only after the owner has approved its content, its rights (names, artwork, imagery), its live URL, and its publication; a candidate without those approvals stays in Draft and does not delay launch. (CR-01; supersedes the three seed exhibits AI Arcade, STARS and Mom's Recipe Box.)
  - Given STARS and Baduk are approved and Monopoly and Risk are not, When the owner approves launch (FR10.4), Then the site launches with STARS and Baduk published and Monopoly and Risk in Draft.
- **FR10.2** The site shall be served over HTTPS at michael.broadfoot.consulting, and mike.broadfoot.consulting shall answer with a permanent (301) redirect that keeps the path and query string.
  - Given a request to `https://mike.broadfoot.consulting/work/stars?x=1`, When it is served, Then the response is 301 to `https://michael.broadfoot.consulting/work/stars?x=1`.
- **FR10.3** The production site shall be indexable by search engines; the preview environment shall send `noindex` and not be openly browsable (team practices, Deployment).
- **FR10.4** Going live and every DNS change shall happen only after the owner's explicit approval (project rule; D-12).
- **FR10.5** When the owner opens Publish or Update for an exhibit with a live URL, the Studio shall check the link and record the result with its time. The result is one of three labels: "Reachable", "Not reachable" or "Refused (non-public address)" — never "Verified", "Safe" or "Approved". The record also holds the final address after redirects, with userinfo, query and fragment removed, and whether a sign-in page was detected: HTTP 401 or 403, or a password input field in the capped response body, inspected statically. Repository visibility and licence are read from GitHub at the same time (FR4.10). A failed check is a warning, not a block: the owner decides whether to publish, change the link or remove it. The published live URL is exactly the owner-entered URL shown in the confirmation, never the address after redirects. There is no scheduled monitoring, and nothing changes on the public site without an owner Publish or Update. A passing check shows only that the URL was reachable at that moment; it is never evidence that the linked app is secure, appropriate or authorized for publication. (CR-03; architecture review refinement; review-03 A1-P07; review-04 A1-S05, A1-S12.)
  - Given a live URL that answers 404, When the owner opens Publish, Then the confirmation shows "Not reachable" and the owner chooses whether to continue.
  - Given a URL that answers 200, When the confirmation renders, Then it reads "Reachable at ⟨time⟩" and states that reachability is not a security or publication check.
  - Given a URL that answers 401, When the check runs, Then the result is "Reachable" with "sign-in page detected".
- **FR10.6** Exhibit titles and artwork for Monopoly (current working title "Monopoly Arena") and Risk are provisional until the owner records "Rights review complete" for that exhibit in the Studio, after a trademark and artwork review. Until that flag is set, the exhibit cannot be published: the Publish confirmation shows the outstanding review and Publish is unavailable. (CR-01; review-03 A1-P09.)
  - Given Monopoly without "Rights review complete", When the owner opens Publish, Then the outstanding review is shown and Publish cannot be confirmed.
- **FR10.7** A live URL becomes public only when the owner includes it at that Publish; for a project linked to a private repository it is excluded by default. Risk's live URL is excluded from every public export until the owner records "Live URL authorized" after a privacy and security review of the live app. Risk's source repository is private and is never linked or exposed (FR4.3, D-15), and nothing is drawn from it for public text or imagery without the owner's approval (D-22, FR5.9). Withheld repository names and live URLs never appear in this public source repository, its history or its pull requests; tests, fixtures and seed data use placeholders, and a CI check compares committed content against hashes of the withheld values held as a CI secret, so the check never discloses them. (CR-01; review-03 A1-P09; review-04 A1-S13.)
  - Given Risk without "Live URL authorized", When it is published, Then no public page, card, attribute or file contains its live URL.
  - Given a commit that contains a withheld value, When CI runs, Then the check fails without printing the value.

## Non-Functional Requirements

- **NFR1 — Authentication and authorization.** Owner-only Studio with MFA (FR1); server-side authorization on every Studio operation; the public site has no write path and no access to the Studio's database or API. Verified by the invariant tests in team practices (Studio endpoints reject callers who are not signed in). Source: charter §6; team practices.
- **NFR2 — Publication boundary.** Public storage contains only exported, owner-approved content. No Studio data, draft, private repository content or AI suggestion reaches public storage except text the owner approved at Publish. Original uploads, Studio data and the nightly export (NFR10) live in private storage that the public distribution can never serve. Verified by invariant tests: nothing public without explicit publish; take-down removes, including from the carousel and category pages; private material never exposed, checked by scanning the whole public export (HTML, attributes, JSON, alt text and file names) for private repository identifiers and withheld URLs; requests for original uploads or export objects through the public site return 403 or 404. Source: charter §4, §5; D-15, D-21, D-22; project rules; Review R-07; review-04 A1-S11, A1-S15.
- **NFR3 — Secrets.** Runtime secrets (the read-only GitHub credential, AI provider credentials, identity-provider client secrets, database credentials) live in AWS SSM Parameter Store as SecureString parameters, readable only by the roles that need them through least-privilege IAM. Deploy-time secrets that cannot use OIDC (such as the Cloudflare token) live in GitHub Actions environment secrets. Secrets never appear in code, configuration, browser bundles, logs or CI output. Secrets Manager is not used, because Parameter Store's standard tier is free. Source: project rule NEVER commit secrets; Q2; owner clarification 2026-10-10.
- **NFR4 — Cost.** Free tiers by default. Pay-per-use spending (AI calls, AWS usage beyond free allowances) happens only after the owner explicitly approves it; no dollar limit is assumed. AWS budget alerts notify the owner of actual and forecast spend and are not treated as hard caps. The real control on AI spend is the in-app gate and owner-set monthly limit (FR5.8). Any paid tier, new service or recurring expense needs the owner's approval. Source: Q1, Q5; owner clarification 2026-10-10; project rule NEVER introduce a recurring expense without approval.
- **NFR5 — Public performance.** On a mid-range phone over a 4G connection, the gallery and an exhibit page reach Largest Contentful Paint in 2.5 seconds or less, measured with Lighthouse mobile in CI against the built site. Images are served in responsive sizes; hashed assets are cached immutably. Source: charter §3 (strong imagery); scope success measures.
- **NFR6 — Studio responsiveness.** Studio API operations other than AI suggestions and file uploads answer within 1 second at the 95th percentile; an AI suggestion completes or times out within 60 seconds (FR5.7). Source: intent (low-effort curation).
- **NFR7 — Availability.** The public site is served entirely from the content-delivery network and storage, with no runtime dependency on the API, database or identity provider (Q3). The Studio has no uptime target beyond the providers' own; there is no on-call. Source: Q3; stakeholder map (single owner).
- **NFR8 — Accessibility.** Public site and Studio meet WCAG 2.1 AA: keyboard operable, visible focus, alt text on every published image, text contrast at least 4.5:1 on the dark theme, reduced motion respected. Automated axe checks report no serious or critical violations. Source: rough-mockups Q6; team practices.
- **NFR9 — Visitor privacy.** No visitor accounts, cookies for tracking, analytics, profiling or server-side collection of appearance preferences; content-delivery access logging stays off for the public site. Source: charter §3; D-04; project rule.
- **NFR10 — Data durability.** Studio content (projects, exhibit text, metadata) is exported nightly to versioned storage, so at most 24 hours of edits can be lost; uploaded images and files are kept in versioned storage. That storage is private, blocks all public access, is encrypted at rest, and is never an origin of the public distribution (Review R-07). Restore is documented and tested once before launch. The free database tier has no automated backups, which is why this export exists. Source: corner sweep (store unavailable, data loss); NFR4.
- **NFR11 — Observability.** The API exposes a health endpoint used by post-deploy smoke checks; Studio API errors are logged with a request id and no secrets or personal data, kept 30 days; the activity log (FR7.7) is kept for the life of the project. No visitor-level logging. Source: team practices (smoke checks); NFR9.
- **NFR12 — Browser support.** The latest two versions of Chrome, Edge, Firefox and Safari (desktop and mobile). Source: corner sweep (supported platforms).
- **NFR13 — Quality gates.** The affirmed testing and code-style practices apply: 80% line coverage for the frontend and the API, the listed CI gates, invariant tests, and preview verification before production. Source: team practices.
- **NFR14 — Portability.** Decisions, requirements, ADRs and agent instructions live in the repository (`docs/PROJECT_BRIEF.md`, `docs/decisions/`, `AGENTS.md`), so another AI assistant can continue from the records alone. Source: charter §7; project rules.

- **NFR15 — Security response headers.** Every response from the public site and the Studio carries a baseline of security headers (Review R-08):
  - a Content-Security-Policy with `default-src 'self'`, which allows scripts, styles, fonts and images only from the site itself (no inline or third-party scripts on the public site), and sets `frame-ancestors 'none'` (review-04 A1-S16);
  - `Strict-Transport-Security` with a max-age of at least one year;
  - `X-Content-Type-Options: nosniff`;
  - `Referrer-Policy: strict-origin-when-cross-origin`, or stricter.

  The Studio's policy also allows only the identity provider and the API origins it needs. Public downloads add the sandbox policy of FR4.4. Verified by an automated check in the post-deploy smoke tests and in preview.
- **NFR16 — Rate limits.** The AI suggestion, upload-authorization and link-check endpoints, and Studio sign-in, enforce request-rate limits; requests beyond a limit receive 429 and cause no provider call, upload authorization or outbound request. The AI limit applies in addition to the monthly suggestion limit (FR5.8). A link check covers at most one live URL per exhibit. The specific rates are set in NFR Design. (Review R-08; CR-03; review-04 A1-S06.)
  - Given requests to the AI suggestion endpoint above its configured rate, When they arrive, Then the excess requests receive 429 and no provider call is made.
  - Given link checks above the configured rate, When they arrive, Then the excess requests receive 429 and no outbound request is made.
- **NFR17 — SSRF protection for link checks.** The link check (FR10.5) runs only server-side, inside owner-authenticated Studio endpoints. It shall (CR-03; architecture review refinement; review-04 A1-S01 to A1-S05):
  - **Addresses:** connect only to addresses that are globally routable unicast under the IANA IPv4 and IPv6 special-purpose address registries — an allow-list, not a deny-list. IPv4-mapped and IPv4-embedding IPv6 forms are normalized to the IPv4 address before checking. If a hostname resolves to several addresses and any is refused, the URL is refused.
  - **Parsing:** parse the URL with one canonical parser; allow only `https` on port 443; reject URLs containing userinfo or a non-canonical IP literal (decimal, octal or hex IPv4).
  - **Pinning and TLS:** connect to the validated address, so a DNS change between check and request (rebinding) cannot bypass it. TLS uses the original hostname for SNI and certificate validation, which is never disabled; an invalid certificate gives "Not reachable".
  - **Redirects:** resolve, validate and pin every redirect target again, and follow at most 3.
  - **Limits:** GET or HEAD only, with `Accept-Encoding: identity`; 5 seconds per hop and 15 seconds for the whole check, DNS included; read at most 256 KB, counted after any decoding.
  - **No rendering:** request only the URL and its validated redirects; never render the page, run scripts or load subresources (no headless browser).
  - **Headers:** send no credentials, cookies or identifying headers.
  - **Isolation:** run where a bypass reaches no private network, AWS-internal endpoint, secret or database — no VPC attachment, or egress limited to public addresses — under an execution identity with no other permissions. NFR Design states how.
  - **Logging:** log the host, resolved address, decision and reason, never the response body (NFR11).

  The response is never shown to visitors and never stored beyond the recorded result. The validator is security-sensitive: its implementation requires the independent AI security review and invariant tests before merge (project rule).
  - Given a live URL that resolves to `169.254.169.254`, `10.0.0.5`, `::ffff:10.0.0.5` or `fd00:ec2::254`, When the check runs, Then no request is sent and the result is "Refused (non-public address)".
  - Given a public URL that redirects to `http://127.0.0.1/`, When the check runs, Then the redirect is not followed and the result is "Not reachable".
  - Given a hostname whose first DNS answer is public and whose second is private, When the check runs, Then no connection is made to the private address.
  - Given a host with an invalid certificate, a response over 256 KB, or a response slower than 5 seconds, When the check runs, Then the result is "Not reachable" within 15 seconds.

## Constraints

| Constraint | Source |
|------------|--------|
| React, TypeScript and Vite frontend; Python API on AWS Lambda; MongoDB Atlas; Auth0 for owner sign-in; S3 and CloudFront; Cloudflare DNS; Terraform; GitHub Actions with GitHub OIDC | charter §6 |
| A modular monolith with clean contracts; public and administrative security boundaries kept separate | charter §6 |
| GitHub is the only content connector in the first release; projects may exist without any repository, with files uploaded by hand | D-08; CR-02 (D-24) |
| Free tiers by default; pay-per-use spending only after explicit owner approval, with no pre-approved dollar limit; no new infrastructure, paid service or recurring expense without approval | Q1, Q5; owner clarification 2026-10-10; charter §6, §7 |
| Runtime secrets in AWS SSM Parameter Store (standard tier), not Secrets Manager | owner clarification 2026-10-10 |
| Two environments, `preview` and `production`; production deploys and DNS changes only through an owner-approved `production` run | team practices; project rules |
| Every change reaches `main` through a pull request with passing checks | project rules |
| Independent AI security review for authentication, authorization, private-material and publication changes | project rules |
| Public repository: no secrets and no copyrighted material without rights | charter §7 |

## Assumptions

- The owner holds or can create, at no cost: a GitHub account owning the launch-candidate repositories, an Auth0 free tenant (plus a development tenant for preview), a MongoDB Atlas account for free-tier clusters, and the Cloudflare zone for broadfoot.consulting. [assumption — confirmed in Infrastructure Design]
- The free tiers chosen cover a single owner and modest public traffic. [assumption — confirmed by Infrastructure Design's cost estimate]
- The owner holds the rights to every image and file uploaded for the launch candidates (rights for Monopoly and Risk names and artwork are confirmed by FR10.6's review). [assumption — the owner's responsibility at Publish]
- An AI description suggestion costs roughly a cent or less per call. [assumption — checked when the provider is chosen, before the owner approves AI spending]
- The contact email address is supplied by the owner before launch. [assumption]

## Out of Scope

Per the approved scope and its Future Roadmap: visitor appearance customization; richer gallery features (free-form filtering, topic tags, search — D-27); a journal (D-27); invitation-only and other non-public access; visitor accounts (D-27); Google Drive and Trimble/SketchUp connectors; visitor analytics of any kind; a second AI workflow; AI exposed to visitors (Q2). Featured work and category browsing were moved into the first release by CR-05. The launch content is the four candidates of FR10.1 (CR-01), plus any project the owner creates without a repository (CR-02); none is mandatory.

Added to the future roadmap at this stage: selecting exhibit images from a linked GitHub repository (Q4, owner clarification 2026-10-10).

Added to the future roadmap by Amendment A1:

- several categories per project (the model already allows it; FR9.8);
- other CAD and model formats (for example DWG, STEP, 3MF) when a project needs them;
- a larger attachment limit;
- AI suggestions drawn from uploaded documents;
- scheduled link monitoring;
- creating, renaming or deleting categories (CR-02, CR-03, CR-05).

## Open Questions

| Question | Owner | Resolved in |
|----------|-------|-------------|
| Which provider the AI framework calls first (Q6), and which open framework is used | Architect | Domain Design and NFR Design |
| Approval to create the `preview` environment, and whether that approval also authorizes agents to deploy pull-request builds to it | Michael | Infrastructure Design |
| Approval of AI pay-per-use spending and the monthly suggestion limit, once the provider and its cost per call are known | Michael | NFR Design, before AI is enabled |
| A distinct GitHub identity for agents | Michael | CI Pipeline and Infrastructure Design |
| Correcting the stale spa-on-aws claim in the charter and the initiative brief | Michael | GitHub issue #2 |

## Assumptions & Open Questions

The Assumptions and Open Questions sections above are the complete list; neither blocks Inception.

Owner decisions outstanding after Amendment A1. None blocks Inception, and none is approved by A1:

- the trademark and artwork review for Monopoly and Risk (FR10.6);
- the licensing decision for STARS and Monopoly, which stay unlicensed until it is made;
- authorizing Risk's live URL after its privacy and security review (FR10.7);
- publication approval of each candidate (FR10.1).

## Change Log

| Version | Date | Change | Authority |
|---------|------|--------|-----------|
| 1.0 | 2026-10-10 | Requirements Analysis approved | Owner approval at the Requirements Analysis gate, 2026-10-10T19:02:36Z |
| A1 | 2026-10-10 | CR-01: launch candidates STARS, Monopoly, Baduk, Risk; any approved subset may launch (Intent Analysis, FR10.1, FR10.6, FR10.7, Out of Scope). CR-02: projects without a repository; HEIC conversion; VSDX added; 50 MB limit kept (FR3.1, FR3.2, FR3.5, FR4.2, FR4.4, FR4.9, FR5.1, Constraints). CR-03: access metadata, reachability check at publication, SSRF protection (FR4.10, FR7.2, FR10.5, NFR16, NFR17). CR-04: crafted studio identity (FR9.6). CR-05: featured carousel and categories in v1 (FR9.1, FR9.7, FR9.8, FR7.2, Out of Scope). | Owner instruction "Architect Portfolio — Autonomous Continuation", 2026-10-10, authorizing CR-01 to CR-05 (D-23 to D-28). Refinements from the independent architecture review relayed by the owner. |
| A1.1 | 2026-10-10 | Resolves the independent reviews of A1 (`reviews/review-03-amendment-a1-product.md`, `reviews/review-04-amendment-a1-security.md`): publication path for featured order and categories and the FR3.2 transition (FR7.4, FR9.7, FR9.8); take-down and preview of the carousel and categories (FR6.1, FR8.2); PDFs offered as downloads only (FR4.9); fail-closed repository visibility, badge table and public-export allow-list (FR4.10); attachment metadata and ZIP entries shown at Publish (FR7.2); image pixel and decode limits, HEIC failure, ZIP and XML limits, sandboxed downloads (FR4.2, FR4.4); SSRF allow-list, pinned TLS, no rendering, isolation, logging and three result labels (FR10.5, NFR17); NFR16 criteria restored and link-check rate limit; no third-party origins and `default-src 'self'` (FR9.5, NFR15); fixed token reference (FR9.6); four fixed categories (FR9.8); rights-review and live-URL flags, withheld values kept out of this repository (FR10.6, FR10.7); stale seed references (FR10.2, Assumptions, Out of Scope). | Within the CR-01 to CR-05 authorization: precision and security controls only; no owner decision reopened. |
| A1.2 | 2026-10-10 | Minor findings from the re-reviews (both READY): FR9.1 grid source in D-26 (A1-P13); FR9.6 working token reference (A1-P14); featured count, FR7.3 rights-review block, category 404 text (A1-P15); metadata extraction limits and failure text (A1-S17); re-export from published state only (A1-S18). | Same authorization; resolved by the author, not re-reviewed (minor). |
