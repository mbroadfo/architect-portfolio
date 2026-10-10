# Discovered Rules — Architect's Portfolio

These are hard constraints that the owner, Michael Broadfoot, stated directly, in any of these places:

- the charter (`docs/CHARTER.md`);
- the approved Ideation decisions (`ideation/approval-handoff/decision-log.md`);
- the owner's Practices Discovery interview answers (`practices-discovery-questions.md`);
- the owner's revision at the Practices Discovery gate on 2026-10-10.

On affirmation, every non-blank line under `## Mandated` and `## Forbidden` is appended to `aidlc/spaces/default/memory/project.md` with an affirmation date, so those two sections hold rule lines only. The source of each rule is cited at the end of its line. The existing `team.md` Mandated rule (approved decisions are recorded in version control and reused) is deliberately not repeated here.

## Mandated

- ALWAYS get Michael Broadfoot's explicit approval before significant architectural changes, security policy changes and destructive operations. [charter §7 Autonomy policy]
- ALWAYS authenticate GitHub Actions to AWS through GitHub OIDC with short-lived, least-privilege role credentials, never with long-lived IAM user access keys. [charter §6; charter Initiation findings: the spa-on-aws keys "must be replaced, not reused as-is"]
- ALWAYS keep `docs/PROJECT_BRIEF.md`, `docs/decisions/` (Architecture Decision Records) and `AGENTS.md` up to date alongside the AI-DLC state, so Codex or Copilot can take over from the committed records alone. [charter Role; charter §7]
- ALWAYS keep exactly one active agent or harness that writes to the repository and owns the shared AI-DLC workflow state, and complete a recorded handoff before another one starts. [charter §7; owner revision at Practices Discovery gate, 2026-10-10, item 1]
- ALWAYS bring every change into `main` through a pull request whose required checks pass, including AI-DLC records and docs, batching routine records into one records pull request per approved gate where practical. [owner revision at Practices Discovery gate, 2026-10-10, item 1]
- ALWAYS verify changes affecting authentication, APIs, publication, take-down or infrastructure in a non-production environment, with their smoke and end-to-end checks passing, before deploying them to production. [owner revision at Practices Discovery gate, 2026-10-10, item 2]
- ALWAYS get an independent security review, from an AI reviewer that did not write the change, for any change to authentication, authorization, private-material handling or publication boundaries. Record it on the pull request, with the automated verification passing, before the owner approves the change. [owner revision at Practices Discovery gate, 2026-10-10, item 4]

## Forbidden

- NEVER deploy publicly or change live DNS without Michael Broadfoot's explicit authorization. [charter §7 Autonomy policy; D-12]
- NEVER deploy to the production AWS environment or change Cloudflare DNS except through a run of the GitHub Actions `production` environment that Michael personally approved as its required reviewer. [Practices Discovery interview Q2 and Q3, answer A; charter §7; D-12; owner revision at Practices Discovery gate, 2026-10-10, item 3]
- NEVER push directly to `main`, and never merge a pull request before its required checks pass and the owner has approved the AI-DLC gate it belongs to. [Practices Discovery interview Q1, answer A; owner revision at Practices Discovery gate, 2026-10-10, item 1]
- NEVER treat a merge, review or deployment approval made with the owner's GitHub credentials as independent human approval. Never claim GitHub deployment approval is independently enforced until agents have their own identity or an equivalent control exists. [owner revision at Practices Discovery gate, 2026-10-10, item 3]
- NEVER let an agent approve a GitHub deployment review, use a ruleset or admin bypass, or change rulesets, environment protection rules or AWS deploy-role trust policies. [owner revision at Practices Discovery gate, 2026-10-10, item 3; charter §7 security policy changes]
- NEVER commit secrets, credentials, tokens or keys to the repository, because the repository is public. [charter §7]
- NEVER commit copyrighted material the project does not have the rights to use. [charter §7]
- NEVER make private material public automatically, including private repositories, private documents and AI-generated text drawn from private sources. Publishing requires Michael's explicit approval of all public content. [charter §4, §5; D-22]
- NEVER introduce new infrastructure, a new paid service or a recurring expense without Michael's approval. [charter §6, §7]
- NEVER add behavioral tracking, advertising analytics, visitor profiling or server-side collection of visitors' appearance preferences to the public site. [charter §3; D-04]

## Sources

- `docs/CHARTER.md` sections: Role, §3 Public portfolio, §4 Private administration studio, §5 AI requirements, §6 Preferred technology, §7 Development team and portability (Autonomy policy), and Initiation findings.
- `ideation/approval-handoff/decision-log.md`: D-04, D-12, D-22.
- `inception/practices-discovery/practices-discovery-questions.md`: Q1, Q2 and Q3, each answered A by the owner on 2026-10-10.
- Owner revision at the Practices Discovery affirmation gate, 2026-10-10, recorded as Request Changes:
  1. protect `main`;
  2. pre-production verification;
  3. separate human and agent authority;
  4. independent security review.
- Considered and left out because they are product requirements, not working rules, and Requirements Analysis owns them: no visitor accounts (charter §3), a provider-independent AI interface (charter §5), and AI suggestions backed by source evidence (charter §5).
- Kept as practices in `team-practices.md`, not as hard rules, so a later approved change can adjust them:
  - the specific `preview` design, including its cost estimate and the recommended standing authorization for preview deploys;
  - the target agent identity (a GitHub App or machine user);
  - the single aggregate CI gate check.
