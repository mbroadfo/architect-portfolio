# Requirements — Architect's Portfolio, First Release

Sources: the initial request and `docs/CHARTER.md`; the approved Ideation artifacts — `intent-statement`, `scope-document` (with `intent-backlog`), `rough-mockups/wireframes.md` and `proposed-default-fixes.md`, and the decision log (D-01 to D-22); the affirmed `team-practices` (now `aidlc/spaces/default/memory/team.md`) and project rules (`project.md`); and this stage's answers (`requirements-analysis-questions.md`, Q1 to Q6). Every requirement names its source. IDs are permanent traceability keys.

## Intent Analysis

Michael Broadfoot wants one credible, image-rich home for a scattered body of work, aimed at prospective clients and employers, engineers and makers, and wants curating it to take little effort (intent-statement; D-01, D-02). The first release proves the whole loop on real work: the owner signs in to a private Studio, turns a GitHub repository into an exhibit with an AI-drafted description they review, previews it, publishes it explicitly, and can take it down; visitors see it in an image-led gallery at michael.broadfoot.consulting (scope-document; D-09, D-14, D-21). The three seed exhibits — AI Arcade, STARS and Mom's Recipe Box — are published this way (charter §8).

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

- **FR1.1** The Studio shall require sign-in through the identity provider and admit only the single configured owner identity.
  - Given a visitor who is not signed in, When they open any Studio page, Then they see the sign-in screen and no Studio content.
  - Given someone signed in with any identity other than the owner's, When they open the Studio, Then they see "This workspace is private." and nothing about projects.
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
- **FR2.2** GitHub access shall be read-only and limited to what discovery and AI evidence need (repository metadata, README and documentation files).
- **FR2.3** A repository already linked to a project shall open that project rather than create a duplicate.
- **FR2.4** When GitHub is unreachable or rate-limited, the Studio shall say so, offer a retry, and leave existing projects untouched.
  - Given GitHub returns an error or times out, When the owner opens Discover, Then the message "Can't reach GitHub right now" appears with a retry, and the Projects list still works.
- **FR2.5** Discovering or linking a repository shall never change its visibility on GitHub or publish anything.

### FR3 — Projects

Source: charter §3, §8; IB-4; wireframes S2; D-21.

- **FR3.1** The owner shall be able to create a project from a repository, or link a repository to an existing project; a project may link several repositories.
- **FR3.2** Each project shall have exactly one status, shown in words: Draft, Published, Changes since last publish, or Taken down.
- **FR3.3** Saved changes shall persist across sessions and devices.
- **FR3.4** If the same project is saved from two tabs or devices, the later save shall be refused with a clear conflict message rather than silently overwrite.
  - Given a project open in two tabs, When the first tab saves and then the second tab saves older content, Then the second save is refused with a message and nothing is lost.
- **FR3.5** The Projects list shall show an empty state with a "Discover a GitHub repository" action when no projects exist.

### FR4 — Exhibit content

Source: charter §3, §8; IB-5 to IB-8; scope Q2 and Q4 (this stage); D-15, D-17, D-19.

- **FR4.1** An exhibit shall have a title, a one-paragraph summary, and six narrative sections: inspiration, design challenges, architectural decisions, implementation, outcomes, lessons learned. Empty sections are omitted on the public page.
- **FR4.2** The owner shall upload exhibit images in the Studio (Q4): JPEG, PNG or WebP, up to 10 MB each, with alt text per image. One image is designated the lead image.
  - Given an upload of an unsupported type or a file over 10 MB, When it is submitted, Then it is rejected with the reason and the rest of the exhibit is unaffected.
- **FR4.3** The owner shall add links out to repositories, a live application and a demo. A link to a private repository is never shown publicly (D-15).
  - Given an exhibit linked to a private repository, When it is published, Then the public page has no "View code" link for that repository.
- **FR4.4** The owner shall attach build-it-yourself files (for example PDF, SKP, FCStd, DXF, STL, ZIP), up to 50 MB each; public links state the file type and size.
- **FR4.5** Text the owner or the AI writes shall be rendered as plain formatted text; markup and scripts in it are escaped, never executed, on any page.
- **FR4.6** Leaving the editor with unsaved changes shall ask first.
- **FR4.7** The first release has no topic tags (D-17).

### FR5 — AI description suggestion

Source: charter §5, §8; IB-9; Q2, Q5, Q6; D-22; wireframes S4.

- **FR5.1** The owner shall request a description suggestion for a project; the suggestion is drawn from the linked repositories' README and documentation files.
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

### FR6 — Preview

Source: charter §8; IB-10; wireframes S5; D-20.

- **FR6.1** The owner shall preview an exhibit exactly as visitors will see it, including its gallery card, marked "Preview — not public" at all times.
- **FR6.2** A preview shall never be reachable by visitors.
  - Given a preview, When a person who is not the owner requests its address, Then they receive no exhibit content.

### FR7 — Publication

Source: charter §4, §5, §8; IB-2, IB-11; D-19, D-22; Q3.

- **FR7.1** Nothing shall become public except through the owner's explicit Publish confirmation.
- **FR7.2** The Publish confirmation shall list everything that will become public — text sections, AI-originated text, images, downloadable files and links — and name any linked private repository whose content informed the text (D-22).
- **FR7.3** Publish shall be blocked, with the reason shown, when the title is empty, there is no lead image, or any image lacks alt text (D-19).
- **FR7.4** Publishing shall export the exhibit as static public content — its page, its gallery card and its assets — and update the gallery (Q3). The public site never reads the Studio's database or API.
  - Given the owner confirms Publish, When export completes, Then the exhibit page and its card are publicly visible within 5 minutes and the project status is Published.
- **FR7.5** Edits to a published exhibit shall stay private until the owner confirms "Update the public exhibit"; meanwhile the status is "Changes since last publish".
- **FR7.6** Publishing shall be safe to repeat: a double click or retry produces one consistent public exhibit.
- **FR7.7** Each publish, update and take-down shall be recorded in an owner-visible activity log with time, exhibit and action.

### FR8 — Take down (Must Have, D-21)

Source: D-20, D-21; IB-16; wireframes S2, S4, P2.

- **FR8.1** The owner shall take down a published exhibit from the Projects list or the editor, after a confirmation naming the exhibit.
- **FR8.2** Take-down shall remove the exhibit's page, gallery card and public assets from public storage and from the content-delivery cache.
  - Given the owner confirms Take down, When it completes, Then within 5 minutes the exhibit no longer appears in the gallery, its address shows "This exhibit isn't on display" with a 404 status, and its images and files return 404.
- **FR8.3** A taken-down exhibit shall keep its Studio content and can be published again later.

### FR9 — Public site

Source: charter §1, §2, §3; scope-document; wireframes P1, P2; D-04, D-09, D-14, D-16 to D-18.

- **FR9.1** The home page shall be the Exhibition-wall gallery: image-led cards for published exhibits only, varied tiles in an orderly grid from tablet width up, a single column on phones (D-14, D-16).
  - Given no exhibit is published, When a visitor opens the site, Then the header and "New work is being installed." appear, with no broken grid.
  - Given a card's image fails to load, When the gallery renders, Then the card keeps its title and summary and still opens the exhibit.
- **FR9.2** Each exhibit page shall show the lead image, title, summary and the links that exist, then the narrative sections, the image gallery (with an enlarged view) and the build-it-yourself downloads; absent blocks are omitted.
- **FR9.3** An unknown or taken-down exhibit address shall show "This exhibit isn't on display" with a link to all work and a 404 status.
- **FR9.4** The footer shall carry a GitHub link, a plain email contact link that collects nothing, and the copyright line (D-18).
- **FR9.5** The public site shall set no tracking or analytics cookies, load no third-party analytics or advertising scripts, and require no visitor account (charter §3; D-04).
- **FR9.6** The visual design shall follow the charter's "Engineering Studio" direction — dark navy, precise typography, strong imagery, restrained effects — without copying the inspiration sites' appearance or branding (charter §1, §3).

### FR10 — Seed content and launch

Source: charter §2, §8; IB-14, IB-15; D-12.

- **FR10.1** The three seed exhibits — AI Arcade, STARS and Mom's Recipe Box — shall be published through the Studio workflow, not hand-authored.
- **FR10.2** The site shall be served over HTTPS at michael.broadfoot.consulting, and mike.broadfoot.consulting shall answer with a permanent (301) redirect that keeps the path and query string.
  - Given a request to `https://mike.broadfoot.consulting/work/ai-arcade?x=1`, When it is served, Then the response is 301 to `https://michael.broadfoot.consulting/work/ai-arcade?x=1`.
- **FR10.3** The production site shall be indexable by search engines; the preview environment shall send `noindex` and not be openly browsable (team practices, Deployment).
- **FR10.4** Going live and every DNS change shall happen only after the owner's explicit approval (project rule; D-12).

## Non-Functional Requirements

- **NFR1 — Authentication and authorization.** Owner-only Studio with MFA (FR1); server-side authorization on every Studio operation; the public site has no write path and no access to the Studio's database or API. Verified by the invariant tests in team practices (Studio endpoints reject callers who are not signed in). Source: charter §6; team practices.
- **NFR2 — Publication boundary.** Public storage contains only exported, owner-approved content. No Studio data, draft, private repository content or AI suggestion reaches public storage except text the owner approved at Publish. Verified by invariant tests (nothing public without explicit publish; take-down removes; private material never exposed). Source: charter §4, §5; D-15, D-21, D-22; project rules.
- **NFR3 — Secrets.** Runtime secrets (AI provider credentials, identity-provider client secrets, database credentials) live in AWS SSM Parameter Store as SecureString parameters, readable only by the roles that need them through least-privilege IAM. Deploy-time secrets that cannot use OIDC (such as the Cloudflare token) live in GitHub Actions environment secrets. Secrets never appear in code, configuration, browser bundles, logs or CI output. Secrets Manager is not used, because Parameter Store's standard tier is free. Source: project rule NEVER commit secrets; Q2; owner clarification 2026-10-10.
- **NFR4 — Cost.** Free tiers by default. Pay-per-use spending (AI calls, AWS usage beyond free allowances) happens only after the owner explicitly approves it; no dollar limit is assumed. AWS budget alerts notify the owner of actual and forecast spend and are not treated as hard caps. The real control on AI spend is the in-app gate and owner-set monthly limit (FR5.8). Any paid tier, new service or recurring expense needs the owner's approval. Source: Q1, Q5; owner clarification 2026-10-10; project rule NEVER introduce a recurring expense without approval.
- **NFR5 — Public performance.** On a mid-range phone over a 4G connection, the gallery and an exhibit page reach Largest Contentful Paint in 2.5 seconds or less, measured with Lighthouse mobile in CI against the built site. Images are served in responsive sizes; hashed assets are cached immutably. Source: charter §3 (strong imagery); scope success measures.
- **NFR6 — Studio responsiveness.** Studio API operations other than AI suggestions and file uploads answer within 1 second at the 95th percentile; an AI suggestion completes or times out within 60 seconds (FR5.7). Source: intent (low-effort curation).
- **NFR7 — Availability.** The public site is served entirely from the content-delivery network and storage, with no runtime dependency on the API, database or identity provider (Q3). The Studio has no uptime target beyond the providers' own; there is no on-call. Source: Q3; stakeholder map (single owner).
- **NFR8 — Accessibility.** Public site and Studio meet WCAG 2.1 AA: keyboard operable, visible focus, alt text on every published image, text contrast at least 4.5:1 on the dark theme, reduced motion respected. Automated axe checks report no serious or critical violations. Source: rough-mockups Q6; team practices.
- **NFR9 — Visitor privacy.** No visitor accounts, cookies for tracking, analytics, profiling or server-side collection of appearance preferences; content-delivery access logging stays off for the public site. Source: charter §3; D-04; project rule.
- **NFR10 — Data durability.** Studio content (projects, exhibit text, metadata) is exported nightly to versioned storage, so at most 24 hours of edits can be lost; uploaded images and files are kept in versioned storage. Restore is documented and tested once before launch. The free database tier has no automated backups, which is why this export exists. Source: corner sweep (store unavailable, data loss); NFR4.
- **NFR11 — Observability.** The API exposes a health endpoint used by post-deploy smoke checks; Studio API errors are logged with a request id and no secrets or personal data, kept 30 days; the activity log (FR7.7) is kept for the life of the project. No visitor-level logging. Source: team practices (smoke checks); NFR9.
- **NFR12 — Browser support.** The latest two versions of Chrome, Edge, Firefox and Safari (desktop and mobile). Source: corner sweep (supported platforms).
- **NFR13 — Quality gates.** The affirmed testing and code-style practices apply: 80% line coverage for the frontend and the API, the listed CI gates, invariant tests, and preview verification before production. Source: team practices.
- **NFR14 — Portability.** Decisions, requirements, ADRs and agent instructions live in the repository (`docs/PROJECT_BRIEF.md`, `docs/decisions/`, `AGENTS.md`), so another AI assistant can continue from the records alone. Source: charter §7; project rules.

## Constraints

| Constraint | Source |
|------------|--------|
| React, TypeScript and Vite frontend; Python API on AWS Lambda; MongoDB Atlas; Auth0 for owner sign-in; S3 and CloudFront; Cloudflare DNS; Terraform; GitHub Actions with GitHub OIDC | charter §6 |
| A modular monolith with clean contracts; public and administrative security boundaries kept separate | charter §6 |
| GitHub is the only content connector in the first release | D-08 |
| Free tiers by default; pay-per-use spending only after explicit owner approval, with no pre-approved dollar limit; no new infrastructure, paid service or recurring expense without approval | Q1, Q5; owner clarification 2026-10-10; charter §6, §7 |
| Runtime secrets in AWS SSM Parameter Store (standard tier), not Secrets Manager | owner clarification 2026-10-10 |
| Two environments, `preview` and `production`; production deploys and DNS changes only through an owner-approved `production` run | team practices; project rules |
| Every change reaches `main` through a pull request with passing checks | project rules |
| Independent AI security review for authentication, authorization, private-material and publication changes | project rules |
| Public repository: no secrets and no copyrighted material without rights | charter §7 |

## Assumptions

- The owner holds or can create, at no cost: a GitHub account owning the seed repositories, an Auth0 free tenant (plus a development tenant for preview), a MongoDB Atlas account for free-tier clusters, and the Cloudflare zone for broadfoot.consulting. [assumption — confirmed in Infrastructure Design]
- The free tiers chosen cover a single owner and modest public traffic. [assumption — confirmed by Infrastructure Design's cost estimate]
- The owner holds the rights to every image and file uploaded for the seed exhibits. [assumption — the owner's responsibility at Publish]
- An AI description suggestion costs roughly a cent or less per call. [assumption — checked when the provider is chosen, before the owner approves AI spending]
- The contact email address is supplied by the owner before launch. [assumption]

## Out of Scope

Per the approved scope and its Future Roadmap: visitor appearance customization; richer gallery features (featured work, grouping, filtering, tags); invitation-only and other non-public access; Google Drive and Trimble/SketchUp connectors; visitor analytics of any kind; projects beyond the three seed exhibits; a second AI workflow; AI exposed to visitors (Q2).

Added to the future roadmap at this stage: selecting exhibit images from a linked GitHub repository (Q4, owner clarification 2026-10-10).

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
