# Architect's Portfolio — AI-DLC Project Initiation Charter

Owner: Michael Broadfoot (product owner and chief architect).
This charter is the authoritative input to AI-DLC Inception. Requirements,
ADRs and backlog derived from it live under `docs/` and `aidlc/`.

## Role

The active coding agent is the lead engineering agent. Use the AWS Labs AI-DLC
methodology. Operate autonomously within approved requirements; preserve human
approval for consequential decisions. OpenAI Codex and GitHub Copilot must be
able to take over using committed project records alone.

## 1. Product vision

A personal architect's portfolio presenting what Michael designs, how he thinks,
what he builds, and what he chooses to share. Background: nearly four decades
of enterprise software engineering and architecture, cloud infrastructure,
identity management, AI, simulation, retro computing, woodworking, CAD, CNC and
fabrication.

Not a conventional corporate résumé. Visitors encounter the creations
immediately, like entering an exhibition of inventions, and can explore the
underlying engineering and design thinking when interested.

Inspiration (do not copy appearance or branding): https://john.bacus.org,
https://devanmetz.com

## 2. Identity and URLs

- Public identity: Michael Broadfoot
- Descriptor: Systems Architect · Engineer · Maker
- Canonical site: https://michael.broadfoot.consulting
- Permanent redirect: https://mike.broadfoot.consulting → canonical, HTTP 301,
  preserving paths and query strings
- Repository: mbroadfo/architect-portfolio
- "Digital Freehold" is a separate philosophical idea, not the portfolio brand.

## 3. Public portfolio

Image-rich gallery covering: software and cloud applications; AI agents and
experiments; games and simulations; scientific and technical explorations;
SketchUp and FreeCAD designs; woodworking, CNC and fabrication.

- A project may have multiple GitHub repositories, design files, documents,
  media assets and live applications.
- Each project explains inspiration, design challenges, architectural
  decisions, implementation, outcomes and lessons learned.
- Access modes (may overlap): public, invitation-only, clone-and-run,
  view-only, build-it-yourself.
- No visitor accounts or registration.
- No behavioral tracking, advertising analytics, visitor profiling, or
  server-side collection of appearance preferences.

UX: default aesthetic "Engineering Studio" — sophisticated dark-navy technical
design, precise typography, strong imagery, restrained effects. Visitors may
change appearance, accent colors and layout preferences client-side only.
Prefer real project images, screenshots, CAD renders and demos over generic
illustration.

## 4. Private administration studio

Visual workspace for: capturing ideas and organizing projects; managing
descriptions and classifications; associating repositories, designs, documents
and media; discovering changes from external sources; AI-assisted descriptions
and recommendations; editing and previewing exhibits; controlling access and
publication; reviewing outstanding curation tasks.

First connector: GitHub. Later: Google Drive, Trimble/SketchUp (subject to API
availability and permissions). Discovering private material must never make it
public automatically.

## 5. AI requirements

AI assists with discovery, classification, summarization, architectural
analysis, connecting related work and exhibit preparation.

- Provider-independent model interface.
- Start with one useful AI-assisted workflow; no premature agent framework.
- Suggestions are reviewable, editable and backed by source evidence.
- Publication requires explicit human approval.

## 6. Preferred technology

Evaluate and preferentially reuse https://github.com/mbroadfo/spa-on-aws.

React, TypeScript, Vite · Python API on AWS Lambda · MongoDB Atlas · Auth0 for
admin authentication · S3 + CloudFront · Cloudflare DNS · Terraform · GitHub
Actions with GitHub OIDC for CI/CD.

Favor a modular monolith with clean contracts. Keep public and administrative
security boundaries separated. No new infrastructure or recurring expense
without approval.

## 7. Development team and portability

Claude Code is the initial harness; rotate to Codex or Copilot when needed.
AI-DLC provides specialized roles (requirements, architecture, UX,
implementation, verification, security). Never rely on one provider's
conversation history: approved decisions, requirements, contracts and progress
live in version control. One active owner of shared workflow state at a time
during handoffs.

Durable human-readable records, maintained alongside AI-DLC state:

- `docs/PROJECT_BRIEF.md` — what we're building and why
- `docs/decisions/` — Architecture Decision Records
- `AGENTS.md` — rules for any AI coding assistant

### Autonomy policy

Proceed autonomously with approved implementation tasks, local tests,
debugging, refactoring and documentation. Request approval for significant
architectural changes, security policy changes, new paid services, destructive
operations and production deployment. Never deploy publicly or change live DNS
without authorization. Never commit secrets or copyrighted material we lack
rights to; the repository is public.

## 8. First vertical slice

The administrator can: authenticate to the Studio; discover an existing GitHub
repository; create or associate a project; edit its public presentation;
generate and review an AI description suggestion; preview the exhibit; save
persistent changes; explicitly authorize publication.

Seed examples: AI Arcade, STARS, Mom's Recipe Box. Do not attempt the whole
product in the first sprint.

## 9. Inception deliverables

Product requirements · UX design proposals · architectural overview · domain
and API contracts · ADRs · security/privacy assessment · vertical-slice
backlog · test strategy · human approval checkpoints · portable agent
instructions and handoff procedures.

Identify conflicts or gaps rather than silently inventing requirements. Present
requirements, UX direction and architecture for approval before major
implementation.

## Initiation findings (2026-10-10)

- Repository created public; AI-DLC 2.11.0 configured for Claude Code.
- spa-on-aws deploys with long-lived IAM user keys (Terraform user has
  AdministratorAccess). This conflicts with the GitHub OIDC requirement and
  must be replaced, not reused as-is. Its S3/CloudFront/ACM/Cloudflare
  Terraform and path-filtered workflows look reusable. It has no Auth0 or
  MongoDB integration.

## Open questions for the product owner

1. Invitation-only access vs. "no visitor accounts" — is a signed, expiring
   link acceptable?
2. Monthly budget ceiling (Atlas, Auth0, AI usage).
3. AI provider for the in-product AI workflow (separate from which agent
   develops the code).
4. Public read path: static export on publish (proposed) vs. live API reads.
