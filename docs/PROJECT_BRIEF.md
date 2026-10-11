# Architect Portfolio — Project Brief

## Purpose and Authority

Michael Broadfoot's public, image-rich studio of architecture, engineering and making, with a private owner-only Studio for low-effort curation. `CHARTER.md` is the initiating brief; approved decisions and requirements elaborate it, and where they differ the later record wins (for example, the charter's dark-navy aesthetic and seed examples are superseded by D-23 and D-26). This summary introduces no new requirements.

Authoritative release requirements: `../aidlc/spaces/default/intents/261010-architect-portfolio/inception/requirements-analysis/requirements.md` (approved 2026-10-10; Amendment A1 applies CR-01 to CR-05). Decisions D-01–D-28 and process decisions P-01–P-05 are in `.../ideation/approval-handoff/decision-log.md`; affirmed team practices are in `aidlc/spaces/default/memory/`. User Stories is deliberately skipped in the approved plan.

## First Release

- **Public site.** A crafted studio identity: warm charcoal, brass accents, editorial typography, restrained interaction (D-26). The home page has:
  - a manual featured carousel;
  - category browsing, with one primary category per project in v1, modelled to allow several later (D-27);
  - the gallery of published exhibits;
  - project detail and case-study pages.
- **Launch candidates:** STARS, Monopoly Arena, Baduk and Risk. Each is published on its own owner approval; any approved subset may launch (D-23).
- **Projects** can start from just a title. GitHub repositories are optional associations, so woodworking, CAD, design and software work are equally supported (D-24).
  - Image uploads accept HEIC, converted to sanitized web images.
  - Attachments: PDF, SKP, FCStd, DXF, STL, ZIP and VSDX, up to 50 MB.
- **Access facts** shown as badges: live URL, access requirement, phone suitability, repository visibility and licence. A link check at Publish means "Reachable", never "Verified"; it is SSRF-protected and runs only when the owner publishes (D-25).
- **Studio:** owner Auth0 sign-in with MFA, bound to the validated issuer and immutable subject, with every operation authorized server-side.
  - GitHub discovery and title-only project creation.
  - Narrative, media and file editing.
  - One reviewable AI description workflow, for projects with a repository.
  - Private preview, explicit publish and update, and take-down.
- **Public static export only.** No public database or API read path, visitor accounts, tracking, analytics, journal, search, tags or appearance settings.
- **Stack:** React/TypeScript/Vite, Python Lambda API, MongoDB Atlas, S3/CloudFront, Cloudflare, Terraform, and GitHub Actions with OIDC. Runtime secrets use standard-tier SSM SecureString.

## Publication and Cost Boundaries

All public text, images, files and links require explicit owner approval of their exact version, including AI text derived from private sources. Private repository links and evidence, private URLs and original uploads remain private.

Until Michael decides separately:

- Monopoly and Risk names and artwork are provisional.
- STARS and Monopoly stay unlicensed.
- Risk's private repository and live URL appear in no public artifact.

Paid AI requests remain disabled until spending and the monthly limit are explicitly approved. Sending private content also requires approval of that provider's data-use terms. No spend limit or infrastructure permission is assumed.

Every change reaches `main` through a PR with checks and the applicable owner approval. Security-sensitive changes need an independent AI security review and the automated verification defined by team practices. Deployment and DNS approval is separate. No agent approves a deployment or impersonates independent human review.

## Current Work and Handoff

**Stage:** Requirements Analysis is approved (Amendment A1 applied). Refined Mockups is in revision after the owner's Request Changes. Its baseline is the R5 prototype under `inception/refined-mockups/prototype/`, and it returns to Michael's approval gate after a fresh independent review.

**Ownership:** Claude Code is lead engineering agent and sole workflow owner by owner instruction (P-05; `ownership-handoff.md`). Codex and Grok are inactive as workflow writers.

**Restrictions in force:** no PR merge, deployment, unapproved cost, publication of project content, or approval of a stage gate on the owner's behalf.

## Open Decisions and Durable Architecture Records

Owner decisions still open:

- the trademark and artwork review for Monopoly and Risk;
- licensing for STARS and Monopoly;
- authorizing Risk's live URL after its privacy and security review;
- per-candidate publication approval.

Later design stages settle the AI provider and framework, the credential mechanism, secure recovery and detailed infrastructure contracts. The contact address remains an owner content input.

Issue #2 tracks an outdated spa-on-aws statement in the charter; approved practices reflect the v2 OIDC baseline. No ADR is fabricated before Domain Design. Architectural decisions belong in `docs/decisions/` when that stage produces and approves them.
