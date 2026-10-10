# Initiative Brief — Architect's Portfolio

One-page summary of the approved Ideation work, for the go/no-go decision to enter Inception. Sources: `intent-statement`, `stakeholder-map`, `scope-document`, `intent-backlog`, `wireframes` (with `rough-mockups/proposed-default-fixes.md`). Not produced in this plan, so not consumed: `competitive-analysis`, `feasibility-assessment`, `constraint-register`, `team-assessment`.

## Intent and Problem

Michael Broadfoot needs one credible, image-rich home for a body of work currently scattered across GitHub, Google Drive, SketchUp and the workshop: a public, exhibition-style portfolio at michael.broadfoot.consulting, curated through a private Studio that makes publishing low-effort, with AI assistance. It supports a consulting presence and shares projects with engineers and makers. [intent-statement]

**Audiences in the first release:** prospective clients and employers, fellow engineers and architects, makers. Invited people come in a later version. [intent-statement] [stakeholder-map]

**Success measures:** the three seed exhibits published; owner time from repository to published exhibit measured, with the target set after first use. No visitor analytics. [scope-document]

## Market Validation

Not applicable: a personal portfolio has no market to size, and market research is not part of the approved plan. The charter names john.bacus.org and devanmetz.com as inspiration for interaction ideas only. [approval-handoff-questions Q5]

## Feasibility and Risk Highlights

No separate feasibility stage ran; the approach follows known patterns, and these risks are carried into the Inception stages that resolve them.

| Risk | Likelihood | Impact | Mitigation and owner |
|------|------------|--------|----------------------|
| Private material (private repositories, AI text drawn from private sources) becomes public by accident | Medium | High | Explicit publish approval covers every public item, including media, files, links and AI-generated text; nothing is exposed automatically. Requirements Analysis records it; architecture and security design enforce it. [proposed-default-fixes] |
| Monthly running costs (database, sign-in, AI usage) exceed what the owner accepts | Medium | Medium | Budget ceiling set in Requirements Analysis before any paid service; no recurring expense without approval (charter §7). |
| The AI provider for the description workflow is undecided | High | Medium | Decided in Requirements Analysis, behind a provider-independent interface (charter §5). |
| The reference deployment setup (spa-on-aws) uses long-lived administrator keys, which conflict with the charter's keyless CI/CD requirement | Known | High | Replace rather than reuse that part; Infrastructure Design owns it (charter initiation findings). |
| Live site, DNS and redirect changes affect the real domains | Low | High | Every deployment and DNS change waits for the owner's explicit approval. [scope-document] |
| Exhibit imagery is not ready or not owned (copyright in a public repository) | Medium | Medium | Use the owner's own screenshots, renders and photos; the image source is settled in Requirements Analysis. |

## Scope Boundary

**In the first release** (17 backlog items, 16 Must Have): [scope-document] [intent-backlog]

- **Studio, owner only:** sign in; discover a GitHub repository; create or link a project; edit the narrative, image gallery, links and build-it-yourself files; an AI description suggestion with its sources shown; preview; explicit publish; take down.
- **Public site:** the Exhibition-wall gallery of image cards, and an exhibit page per published project.
- **Launch:** the three seed exhibits (AI Arcade, STARS, Mom's Recipe Box), live at michael.broadfoot.consulting with the mike.broadfoot.consulting permanent redirect, after owner approval.

**Roadmap, not this release:** visitor appearance customization; richer gallery (featured work, grouping, filtering, tags); invitation-only access; Google Drive and SketchUp connectors; any visitor analytics. [scope-document]

**Carried into Requirements Analysis as approved owner decisions:** Take down / Unpublish is Must Have; publish approval covers all public content and private material is never exposed automatically. [proposed-default-fixes]

## Concept Visuals

Approved direction: Concept A, "Exhibition wall". Large, varied image tiles in a responsive, orderly grid, collapsing to a single column on phones, in the charter's dark-navy "Engineering Studio" style. The exhibit page leads with the lead image and summary, then the narrative, gallery, links and build files. Six Studio screens are sketched with their empty, error and accessibility states. [wireframes] [proposed-default-fixes]

## Team Plan

Michael Broadfoot is product owner and sole decision-maker. AI engineering agents do the work: Claude Code first, with Codex or Copilot taking over from the committed records when needed. Progress lives in the GitHub repository. An independent AI architecture reviewer advises from the repository. [stakeholder-map] [approval-handoff-questions Q6]

## Go/No-Go Recommendation

**Go — proceed to Inception.** The problem, audiences, boundary and visual direction are approved, and the first release is small enough to finish. Two conditions apply before any spending: Requirements Analysis must set the monthly budget ceiling and choose the AI provider, and no paid service is introduced until the owner approves it.

## Assumptions & Open Questions

Carried to the stage that owns each one:

- Monthly budget ceiling: Requirements Analysis. [assumption]
- AI provider for the description workflow: Requirements Analysis. [assumption]
- Static export on publish vs live reads for the public site: Requirements Analysis and Domain Design. [assumption]
- Exhibit image source (upload, GitHub, or both): Requirements Analysis. [assumption]
- Build order: Delivery Planning. [assumption]
- The charter's invitation-link question is moot for the first release, because non-public access is out of scope; it returns with the roadmap item. [assumption]
