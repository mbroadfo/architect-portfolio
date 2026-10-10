# Architect Portfolio — Project Brief

## Purpose and Authority

Michael Broadfoot's public, image-rich exhibition of architecture, engineering and making, with a private owner-only Studio for low-effort curation. `CHARTER.md` is the initiating brief; approved decisions and requirements elaborate it. This summary introduces no new requirements.

Authoritative release requirements: `../aidlc/spaces/default/intents/261010-architect-portfolio/inception/requirements-analysis/requirements.md`. Ideation decisions D-01–D-22 and affirmed team practices live in the same intent. User Stories is deliberately skipped in the approved plan.

## First Release

- Public Exhibition wall gallery and exhibit pages for AI Arcade, STARS and Mom's Recipe Box, published through the Studio, not hand-authored.
- Owner Auth0 sign-in with MFA, bound to validated issuer and immutable subject; all Studio operations authorized server-side.
- GitHub discovery, create/link project, edit narrative and upload media/build files, one reviewable AI description workflow, private preview, explicit publish/update and take-down.
- Public static export only; no public database/API read path, visitor accounts, tracking, tags or appearance settings.
- React/TypeScript/Vite, Python Lambda API, MongoDB Atlas, S3/CloudFront, Cloudflare, Terraform and GitHub Actions with OIDC. Runtime secrets use standard-tier SSM SecureString.

## Publication and Cost Boundaries

All public text, images, files and links require explicit owner approval of their exact version, including AI text derived from private sources. Private repository links/evidence and original uploads remain private. Paid AI requests remain disabled until spending and the monthly limit are explicitly approved; sending private content also requires approval of that provider's data-use terms. No spend limit or infrastructure permission is assumed.

Every change reaches main through a PR with checks and applicable owner approval. Security-sensitive changes need independent AI security review and the automated verification defined by team practices. Deployment/DNS approval is separate. No agent approves a deployment or impersonates independent human review.

## Current Work and Handoff

Requirements Analysis is approved. Refined Mockups develops the approved Engineering Studio direction and Concept A into responsive layouts, interactions and accessibility checks. Its new artifacts are proposals until Michael approves the stage. See `../aidlc/spaces/default/intents/261010-architect-portfolio/ownership-handoff.md` for the owner-directed Claude-to-Codex transition.

Current task restrictions: no Observer changes, infrastructure deployment, costs, PR merge or PR approval. Codex owns the shared workflow records; reviewers have no authority to advance them.

## Open Decisions and Durable Architecture Records

Provider/framework, credential mechanism, secure recovery and detailed infrastructure contracts are settled by later design stages. Contact address and real seed imagery/copy remain owner content inputs. Issue #2 tracks an outdated spa-on-aws statement in the charter; approved practices reflect the v2 OIDC baseline. No ADR is fabricated before Domain Design; architectural decisions belong in `docs/decisions/` when that stage produces and approves them.
