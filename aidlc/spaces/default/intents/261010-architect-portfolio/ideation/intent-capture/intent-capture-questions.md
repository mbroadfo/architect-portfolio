# Intent Capture & Framing — Questions

## Sources

- [desc] Initial description: "Build Michael Broadfoot's architect portfolio as specified in docs/CHARTER.md (the authoritative project brief): a public image-rich exhibition-style portfolio at michael.broadfoot.consulting plus a private, Auth0-protected administration Studio with GitHub discovery and one AI-assisted description workflow, on React/TypeScript/Vite, Python Lambda API, MongoDB Atlas, S3+CloudFront, Cloudflare DNS, Terraform, GitHub Actions with OIDC. Inception first; first vertical slice per charter section 8. The charter's open questions must be resolved with the product owner."
- [scope] Workflow-selected scope: `classic`.

The charter (`docs/CHARTER.md`) already answers most of what this stage would normally ask (vision, identity and URLs, public portfolio contents, Studio capabilities, AI rules, technology preferences, autonomy policy, the first vertical slice). These questions cover only what it leaves open about **why** the portfolio exists, **for whom**, **how success is judged**, and **who else has a say**. The charter's four technical open questions (invitation-only links, budget ceiling, AI provider, static vs. live public reads) are taken up later, in Requirements Analysis.

## Q1. What problem is the portfolio primarily solving for you? (select all that apply)

This sets the problem statement every later requirement traces back to.

A. My work is scattered across GitHub, Google Drive, SketchUp and the workshop, with no single place that presents it as a coherent body of work
B. A résumé or LinkedIn profile cannot convey how I think and what I build; I want a credible showcase that supports consulting or advisory work
C. I want a place to share selected projects (including build-it-yourself designs) with peers and the maker community
D. Keeping project write-ups current is tedious; I want tooling (including AI assistance) that makes curating and publishing low-effort
E. Not yet defined
X. Other (please specify)

[Answer]: A, B, C, D

## Q2. Who are the main visitors you want the public portfolio to serve? (select all that apply)

The audience drives tone, navigation depth, and which project details are emphasized (business outcomes vs. engineering detail vs. build instructions).

A. Prospective consulting clients, hiring managers, or organizations evaluating me for advisory work
B. Fellow engineers and architects interested in the technical and architectural thinking
C. Makers, woodworkers and CNC/CAD hobbyists who may want to build or adapt my designs
D. Family, friends and specific invited people (for example, people connected to Mom's Recipe Box)
E. Not yet defined
X. Other (please specify)

[Answer]: A, D

## Q3. How should we judge whether the portfolio is succeeding? (select all that apply)

Success needs a measurable signal, but the charter forbids behavioral tracking, advertising analytics and visitor profiling. These options stay inside that rule.

A. Owner-side delivery milestones only (for example: the three seed exhibits published, and a new exhibit can go from GitHub repository to published in under a set time)
B. Curation-efficiency measures recorded inside the private Studio only (time from discovery to publication, share of AI suggestions accepted or edited) — no visitor data at all
C. Privacy-respecting aggregate counts only (for example, total requests per exhibit from CDN logs, with no cookies, no per-visitor identifiers, and no IP addresses retained)
D. Inbound outcomes you count yourself (for example, consulting inquiries or messages received through a contact link)
E. Not yet defined
X. Other (please specify)

[Answer]: A, C

## Q4. What triggered this initiative now? (select all that apply)

Knowing the driver helps decide what has to be in the first version and what can wait.

A. Establishing a consulting presence under the broadfoot.consulting domain
B. The body of work (AI Arcade, STARS, Mom's Recipe Box and others) has reached the point where it deserves a proper home
C. The portfolio is itself a showcase of AI-assisted, agent-driven development using AI-DLC
D. A personal milestone or career transition
E. Not yet defined
X. Other (please specify)

[Answer]: A, B, C, D

## Q5. Besides you, who has a stake in this project? (select all that apply)

The charter names you as product owner and chief architect. This checks whether anyone else's interests or consent must be represented.

A. No one else — I am the only stakeholder
B. An independent AI architecture reviewer (for example, ChatGPT reviewing the GitHub repository) whose input is advisory
C. People featured in, or co-owning, projects I exhibit (family members, collaborators on repositories) whose consent matters before their material is published
D. Invited viewers of invitation-only exhibits
E. Not identified
X. Other (please specify)

[Answer]: A

## Q6. Who decides scope, priority and publication?

This determines whose approval each gate needs.

A. Only me; AI agents propose, I decide
B. Me, after weighing advisory input from the independent reviewer
C. Me, except that people featured in an exhibit must approve content about them before it is published
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q7. How do you want to follow progress? (select all that apply)

The charter requires that progress live in version control so any AI assistant (or reviewer) can pick it up.

A. No formal cadence — the GitHub repository (commits, pull requests, AI-DLC records) is the status, and I look when I want
B. A short written status summary committed to the repository at each phase boundary
C. GitHub issues and pull-request descriptions as the main status channel, so an outside reviewer can follow along
D. Not applicable
X. Other (please specify)

[Answer]: A

## Q8. What should the first version deliberately leave out? (select all that apply)

The charter's section 8 defines the first vertical slice (Studio sign-in, discovering a GitHub repository, creating or linking a project, editing its presentation, an AI description suggestion, preview, saving, and explicit publication). This asks which neighbouring features stay out of it.

A. Google Drive and Trimble/SketchUp connectors (GitHub is the only source)
B. Invitation-only and other non-public access modes (published exhibits are public only)
C. Visitor appearance customization (theme, accent colours, layout preferences)
D. A fully navigable public gallery — the first public site shows only the published seed exhibits with minimal navigation
E. Nothing beyond what the charter already limits
X. Other (please specify)

[Answer]: A, B, C

## Q9. Your problem statement includes sharing projects with peers and the maker community, but your audience answer names only clients/employers and invited people. Should makers and fellow engineers be part of the intended audience?

The answer decides whether exhibits must carry build-oriented and deep technical detail, or can lead with outcomes and business value.

A. Yes — makers and fellow engineers are part of the audience too; I just ranked clients and invited people first
B. Secondary audience — they are welcome, but the site is designed for clients/employers and invited people
C. No — I'll share with makers some other way; this portfolio is for clients/employers and invited people
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q10. Invited people are part of your audience, but invitation-only access is out of the first version. How are invited people served in the first version?

A. Through the same public exhibits as everyone else; invitation-only content comes in a later version
B. They aren't served in the first version at all; they are a later-version audience
C. I'll send them direct links to public exhibits; no special access needed yet
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q11. For the delivery-milestone success measure, how quickly should a new exhibit go from "discovered GitHub repository" to "published", once the Studio exists?

A measurable target lets us check the curation workflow actually meets its purpose of low-effort publishing.

A. Within 15 minutes of my own time
B. Within 30 minutes of my own time
C. Within 1 hour of my own time
D. Not yet defined — set it after the first slice is in use
X. Other (please specify)

[Answer]: D
