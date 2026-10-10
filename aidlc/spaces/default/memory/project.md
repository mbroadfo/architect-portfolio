# Project-Level Rules

> Project-specific specialisation and corrections. Loaded after `org.md` and
> `team.md` as strict-additive guidance; contradictions with broader policy
> are rejected. Populated by practices-discovery and the self-learning loop.
>
> Use sparingly: most teams don't need a project layer. Reach for it
> only when this specific project needs stable, durable guidance beyond the
> team practice (for example, package-specific release checks or an additional
> regression suite for a legacy component).

## Way of Working

<!-- Project-specific specialisation. Example: -->
<!-- This monorepo requires package-scoped branch names and a package owner -->
<!-- review in addition to the team's normal merge policy. -->

## Walking Skeleton

<!-- Project-specific specialisation. Example: -->
<!-- The walking skeleton must exercise the legacy service adapter as well -->
<!-- as the new service boundary. -->

## Testing Posture

<!-- Project-specific specialisation. -->

## Guard Policy

<!-- Project-specific. Mode: strict, relaxed, or off. Strict here holds for every intent, whatever one person asks in chat; relaxed or off here applies to every intent whose policy came from its scope, unless the person sets another; changing this line changes it. A section under the retired Change Control heading, written by an earlier release, is still read. -->

## Deployment

<!-- Project-specific specialisation. -->

## Code Style

<!-- Project-specific specialisation. -->

## Tech Stack

<!-- Technology choices locked for this project. -->

## Decided

<!-- Decisions made in earlier stages that should not be re-asked. -->
<!-- Format: DECIDED: [decision] (Stage [slug], [date]) -->

## Scope Overrides

<!-- Custom scope rules for this project. -->

## Forbidden

<!-- Populated by practices-discovery affirmation gate. -->
<!-- Format: NEVER [behavior] (affirmed [date]) -->
<!-- Example: NEVER throw exceptions across service layer boundaries (affirmed 2026-05-17) -->

- NEVER deploy publicly or change live DNS without Michael Broadfoot's explicit authorization. [charter §7 Autonomy policy; D-12] (affirmed 2026-10-10)

- NEVER deploy to the production AWS environment or change Cloudflare DNS except through a run of the GitHub Actions `production` environment that Michael personally approved as its required reviewer. [Practices Discovery interview Q2 and Q3, answer A; charter §7; D-12; owner revision at Practices Discovery gate, 2026-10-10, item 3] (affirmed 2026-10-10)

- NEVER push directly to `main`, and never merge a pull request before its required checks pass and the owner has approved the AI-DLC gate it belongs to. [Practices Discovery interview Q1, answer A; owner revision at Practices Discovery gate, 2026-10-10, item 1] (affirmed 2026-10-10)

- NEVER treat a merge, review or deployment approval made with the owner's GitHub credentials as independent human approval. Never claim GitHub deployment approval is independently enforced until agents have their own identity or an equivalent control exists. [owner revision at Practices Discovery gate, 2026-10-10, item 3] (affirmed 2026-10-10)

- NEVER let an agent approve a GitHub deployment review, use a ruleset or admin bypass, or change rulesets, environment protection rules or AWS deploy-role trust policies. [owner revision at Practices Discovery gate, 2026-10-10, item 3; charter §7 security policy changes] (affirmed 2026-10-10)

- NEVER commit secrets, credentials, tokens or keys to the repository, because the repository is public. [charter §7] (affirmed 2026-10-10)

- NEVER commit copyrighted material the project does not have the rights to use. [charter §7] (affirmed 2026-10-10)

- NEVER make private material public automatically, including private repositories, private documents and AI-generated text drawn from private sources. Publishing requires Michael's explicit approval of all public content. [charter §4, §5; D-22] (affirmed 2026-10-10)

- NEVER introduce new infrastructure, a new paid service or a recurring expense without Michael's approval. [charter §6, §7] (affirmed 2026-10-10)

- NEVER add behavioral tracking, advertising analytics, visitor profiling or server-side collection of visitors' appearance preferences to the public site. [charter §3; D-04] (affirmed 2026-10-10)

## Mandated

<!-- Populated by practices-discovery affirmation gate. -->
<!-- Format: ALWAYS [behavior] (affirmed [date]) -->
<!-- Example: ALWAYS use Result<T,E> for fallible operations in service layer (affirmed 2026-05-17) -->

- ALWAYS get Michael Broadfoot's explicit approval before significant architectural changes, security policy changes and destructive operations. [charter §7 Autonomy policy] (affirmed 2026-10-10)

- ALWAYS authenticate GitHub Actions to AWS through GitHub OIDC with short-lived, least-privilege role credentials, never with long-lived IAM user access keys. [charter §6 Preferred technology; owner second revision at Practices Discovery gate, 2026-10-10, item 2: keep the OIDC patterns spa-on-aws v2 already uses] (affirmed 2026-10-10)

- ALWAYS keep `docs/PROJECT_BRIEF.md`, `docs/decisions/` (Architecture Decision Records) and `AGENTS.md` up to date alongside the AI-DLC state, so Codex or Copilot can take over from the committed records alone. [charter Role; charter §7] (affirmed 2026-10-10)

- ALWAYS keep exactly one active owner of the shared AI-DLC workflow state, and change that ownership only through a recorded handoff. Independent coding agents may work concurrently on separate branches and worktrees when their changes are isolated and merged through pull requests. [charter §7; owner second revision at Practices Discovery gate, 2026-10-10, item 1] (affirmed 2026-10-10)

- ALWAYS bring every change into `main` through a pull request whose required checks pass, including AI-DLC records and docs, batching routine records into one records pull request per approved gate where practical. [owner revision at Practices Discovery gate, 2026-10-10, item 1] (affirmed 2026-10-10)

- ALWAYS verify changes affecting authentication, APIs, publication, take-down or infrastructure in a non-production environment, with their smoke and end-to-end checks passing, before deploying them to production. [owner revision at Practices Discovery gate, 2026-10-10, item 2] (affirmed 2026-10-10)

- ALWAYS get an independent security review, from an AI reviewer that did not write the change, for any change to authentication, authorization, private-material handling or publication boundaries. Record it on the pull request, with the automated verification passing, before the owner approves the change. [owner revision at Practices Discovery gate, 2026-10-10, item 4] (affirmed 2026-10-10)

## Corrections

<!-- Project-specific corrections from human feedback. -->
<!-- Format: NEVER/ALWAYS [behavior] (learned [date]) -->
