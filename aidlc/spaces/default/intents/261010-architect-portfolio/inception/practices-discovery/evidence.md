# Practices Discovery Evidence — Architect's Portfolio

This is the evidence after the lead's revision turn. It covers:

- the lead's draft;
- the owner's interview (`practices-discovery-questions.md`, Q1-Q4);
- the integrated practices;
- the owner's four-item revision at the affirmation gate (2026-10-10, recorded as Request Changes).

## Run context

- **Project type**: Greenfield. The repository holds only docs and AI-DLC records: no application code, no CI configuration, no lint or test configuration.
- **Participants**: `aidlc-pipeline-deploy-agent` (lead) only. Collaborators are off for this plan (`collaborators: off`), so no support agent contributions exist, and quality, developer and devsecops reviews did not run.
- **Baseline**: The five matching sections of `aidlc/spaces/default/memory/org.md` were treated as suggested defaults, not established facts. `team.md` has no affirmed practice sections. Its single Mandated rule (record approved decisions in version control and reuse them) is respected and not duplicated.
- **Owner guidance**: Settle routine decisions from the charter, the recorded decisions and sensible defaults, and send the owner only genuinely open questions (P-03). The revision adds: keep the Testing Posture and Code Style standards; keep autonomous development within approved boundaries; do not reopen settled product questions.
- **Commit at discovery**: `5bcac65` on `main`.
- **Interview**: Michael Broadfoot answered Q1-Q4 on 2026-10-10 and chose the recommended option (A) for each.
- **Gate revision**: At the affirmation gate the owner asked for four changes, quoted in full below. This turn applies them. Testing Posture and Code Style are unchanged, apart from a records-pull-request wording in the Commits bullet.

## What was inspected

| Source | What it gave |
| --- | --- |
| `docs/CHARTER.md` | Stack (React/TypeScript/Vite, Python Lambda, MongoDB Atlas, Auth0, S3 + CloudFront, Cloudflare DNS, Terraform, GitHub Actions with OIDC); public repository; autonomy policy (approval for architecture, security, paid services, destructive operations and production deploys; never deploy publicly or change live DNS without authorization; never commit secrets or unlicensed material); multi-agent portability; one owner of workflow state at a time; the spa-on-aws finding |
| `ideation/approval-handoff/decision-log.md` | D-04 (no analytics), D-12 (every deploy and DNS step needs owner approval), D-15, D-19, D-21, D-22 (publication and privacy invariants), P-01 (plan, Guard Policy off), P-03 (routine decisions answered from the record), P-04 (approved artifacts committed and pushed) |
| `ideation/approval-handoff/initiative-brief.md` | Risk register: private-material exposure, cost ceiling, spa-on-aws keys, live DNS changes |
| `aidlc-state.md` | Scope `classic`, plan `portfolio-inception-slice`, Test Strategy Standard, Depth Standard, Construction Execution serial, Construction Iteration unit-major |
| `.claude/scopes/aidlc-portfolio-inception-slice.md` | `skeleton: off` |
| `git log` (6 commits, `main` only, no other branches) | Records committed straight to `main` so far; imperative, stage-named commit subjects |
| `.gitattributes` | `* text=auto eol=lf`: LF line endings already enforced |
| `spa-on-aws` (`README.md`, `workflows/*.yml`, `terraform/main.tf`, `frontend/package.json`) | Reuse candidates and conflicts (see Deployment below) |
| `.claude/knowledge/aidlc-shared/audit-format.md` | The audit trail is "operational evidence, not a tamper-proof human-authorship boundary" (`HUMAN_TURN` section). Used to describe AI-DLC gate approvals honestly |
| `practices-discovery-questions.md` | Q1-Q4, each answered A |

## Per-area reasoning

### Way of Working

- **Inferred**: Trunk-based development with squash-merge (the `org.md` default) fits one owner with rotating AI harnesses.
- **Q1**: Each Bolt goes through a pull request with passing CI, and the agent squash-merges after the owner's AI-DLC approval.
- **Revision item 1**: Every change, including records, now goes through a pull request. Routine records are batched into one records pull request per approved gate, or per phase. No agent pushes directly to `main`, and only one agent or harness writes at a time. This replaces the earlier "records go straight to `main`" practice and P-04's direct push.
- **Revision items 3 and 4**: These add the approval and credential boundaries and the independent security review. Both are covered below.

### Walking Skeleton

- **Inferred**: The approved plan's scope file declares `skeleton: off`, so there is no checkpoint ceremony. The thinnest integrated path still comes first (Q4).
- **Revision item 2**: The path is now proven in AWS in `preview`, once the owner approves creating it.

### Testing Posture

- **Unchanged by the revision.** Tests are written after each layer is implemented, with an 80% line-coverage floor, invariant tests, no live paid services, and acceptance-criterion IDs cited (Q4).
- The preview end-to-end runs are described under Deployment, which the revision asked for.

### Deployment

- **Conflict found in the draft**: The `org.md` default deploys automatically on merge to staging. That conflicts with charter §7 and D-12. The narrowing to continuous delivery stands.
- **Q2 and revision item 2**: Q2 chose a single production environment with no staging. The revision keeps the cost concern ("a permanent paid staging environment is not mandatory") but requires testing outside production before any public deploy. The simplest cost-effective answer is a serverless `preview` environment that costs almost nothing while idle.
- **Q3 and revision item 3**: Q3 kept the owner as required reviewer on `production`. The revision requires saying plainly that this approval is procedural while agents hold the owner's credentials.
- **spa-on-aws review** (unchanged):
  - **Reusable**: S3 + CloudFront with Origin Access Control; ACM certificate in us-east-1; Terraform S3 backend with `use_lockfile`; `plan -out` then `apply tfplan`; cache headers; workflows filtered by path; `cancel-in-progress: false` for infrastructure.
  - **Replaced**:
    - long-lived `TERRAFORM_AWS_*` and `DEPLOY_AWS_*` keys, including an IAM user with AdministratorAccess;
    - deploying on every push without approval;
    - the automatic Cloudflare `dns` job;
    - the `vars` job, which writes GitHub variables with a personal access token;
    - the missing lint and test steps;
    - `npm install` used instead of `npm ci`.

### Code Style

- **Unchanged by the revision**, apart from the Commits bullet, which now names records pull requests instead of direct records commits.

## Interview decisions

| ID | Area | Owner's answer | Status after the revision |
| --- | --- | --- | --- |
| Q1 | Way of Working | A: a pull request per Bolt; CI must pass; the agent squash-merges after the owner's AI-DLC approval, and the owner never clicks Merge | Stands. Revision item 1 extends pull requests to all changes. Revision item 3 makes clear that the agent's merge is not the approval: the AI-DLC gate answer is |
| Q2 | Deployment | A: one `production` environment, no staging | Changed by revision item 2. A low-cost non-production `preview` environment is added. There is still no permanent paid staging environment |
| Q3 | Deployment | A: the owner approves the run in GitHub's deployment review as required reviewer on `production` | Stands. Revision item 3 adds that the approval is procedural until agents have their own identity |
| Q4 | Walking Skeleton, Testing Posture, Code Style | A: accept all three | Stands |

## Owner revision at the affirmation gate (2026-10-10)

The owner's words, verbatim:

> 1. **Protect main.** Application code, infrastructure, and consequential architectural or policy changes must use PRs with passing checks. Batch routine AI-DLC documentation/checkpoint commits where practical. Do not let multiple agents write directly to main without coordination.
> 2. **Establish a pre-production verification strategy.** A permanent paid staging environment is not mandatory, but we must test authentication, APIs, publication, take-down, and infrastructure changes in a non-production environment before deploying them publicly. Recommend the simplest cost-effective approach.
> 3. **Separate human and agent authority.** Agents may prepare commits, PRs, tests, and deployments, but their use of my GitHub credentials must not constitute independent human approval. Document how approval and credential boundaries will actually be enforced. Until distinct identities or an equivalent control exist, do not claim GitHub deployment approval is independently enforced.
> 4. **Require independent security review** for authentication, authorization, private-material handling, and publication boundaries. This can be another AI reviewer with automated verification rather than a permanent additional agent.

| Item | What changed | Where |
| --- | --- | --- |
| 1 Protect `main` | A ruleset on `main`: pull request required, required status check, no force-push or deletion, empty bypass list. All changes, records included, go through pull requests. Records are batched per approved gate or phase. One aggregate gate check always runs. One writer at a time, with a recorded handoff. No direct pushes | team-practices Way of Working; Mandated rules 4 and 5; Forbidden rule 3 |
| 2 Pre-production verification | A `preview` environment from the same Terraform: serverless, Atlas M0, an Auth0 development tenant, test data, no domain, gated address, ideally a separate AWS account. Changes to authentication, APIs, publication, take-down or infrastructure must pass smoke and end-to-end checks there before merge and production. Creating preview needs the owner's approval | team-practices Deployment and Walking Skeleton; Mandated rule 6 |
| 3 Human vs agent authority | States that actions taken with the owner's credentials are not approval. Lists which approvals count, which controls are technical, which are procedural, and the target agent identity | team-practices Way of Working and Deployment; Forbidden rules 2, 4 and 5 |
| 4 Independent security review | Pull requests touching authentication, authorization, private-material handling or publication boundaries need a review by an AI session or model that did not write the change, recorded on the pull request, plus passing automated verification. A CI check requires the review record | team-practices Way of Working; Mandated rule 7 |

### Technical versus procedural controls today

| Control | Kind today | Why |
| --- | --- | --- |
| No direct push, force-push or deletion on `main`; no merge with a failing required check | Technical (GitHub ruleset) | GitHub enforces rulesets for everyone, except that an admin can edit or disable the ruleset, and agents currently act as the admin. Not editing it is procedural (Forbidden rule 5) |
| Path-scoped push rules (for example, letting records bypass pull requests) | Not available | GitHub does not offer path-restricting push rules for a public repository on the Free plan, so the ruleset applies to every path |
| AWS deploy credentials only inside the matching GitHub environment | Technical (IAM OIDC trust condition on the `sub` claim) | AWS rejects tokens from other workflows or environments. It cannot tell who approved the environment run |
| Cloudflare token only in `production` jobs | Technical (environment secret) | Jobs outside the environment cannot read it |
| The owner's approval of a production deploy | Procedural | The owner is the required reviewer, but an agent holding the owner's credentials could approve through GitHub's API. Agents never do (Forbidden rules 4 and 5). "Prevent self-review" cannot be turned on yet, because runs start under the owner's identity and it would block the owner's own approval |
| The owner's approval of a Bolt or records pull request | Procedural | It is the owner's answer at the AI-DLC gate. The audit trail is evidence, not tamper-proof proof of authorship. The agent's merge with the owner's credentials is not the approval |
| Independence of the security reviewer | Procedural, with a technical presence check | A CI check requires a review record for the latest commit. That the reviewer did not write the change is a procedural guarantee |
| Agents never use the owner's AWS administrator credentials | Procedural | Those credentials exist on the owner's machine for bootstrap |
| Target: agents have their own GitHub identity (GitHub App or machine user: write only, no admin, not a reviewer, no bypass), and the owner's credentials are kept out of agent sessions | Becomes technical once in place | Only then can "Prevent self-review" and required pull-request reviews make the owner's approval technically distinct |

### Preview cost estimate (to be confirmed in Infrastructure Design)

| Item | Expected idle cost |
| --- | --- |
| CloudFront, including the gate function | About $0, within AWS's always-free allowances for low traffic |
| Lambda | About $0, within the always-free request and compute allowance |
| API Gateway HTTP API | Cents at most, at $1.00 per million requests once any first-year free tier ends |
| S3 (site assets; shares the Terraform state bucket) | Under $0.05 a month |
| CloudWatch Logs with short retention | About $0 at preview volumes |
| SSM Parameter Store, standard parameters | $0. Secrets Manager would add $0.40 per secret per month, which is why Infrastructure Design weighs it |
| Customer-managed KMS keys | Avoided ($1 a month each); AWS-managed keys are used |
| Separate AWS account under Organizations | $0 |
| MongoDB Atlas M0 in its own project | $0 on the free cluster tier |
| Auth0 development tenant | $0 on the free plan, to be confirmed when the tenant is created |
| AI provider | $0 by default (fake provider). Real calls only when a test needs them, within the budget ceiling set in Requirements Analysis |
| **Total** | **Estimated under $1 a month while idle.** This is an estimate, not a quote. Creating preview is new infrastructure and needs the owner's approval (charter §6) |

## Owner actions and decisions still open

1. **Apply the ruleset on `main`.** Changing protection rules is a security policy change, so the owner applies it or approves an agent-prepared change.
   - Recommended: now, with pull request required, force-push and deletion blocked, and no bypass.
   - The required status check is added once the aggregate gate workflow lands. Until then, records pull requests are checked by hand.
2. **Approve creating `preview`** as new infrastructure, at Infrastructure Design or Environment Provisioning, and decide the standing authorization. Recommended: that approval also lets agents deploy pull-request builds to preview without per-run approval. Without it, each preview deploy needs the owner's authorization.
3. **Choose where preview lives.** Recommended: a separate AWS account under Organizations. The fallback is the same account with preview-scoped roles.
4. **Give agents their own GitHub identity,** a GitHub App (preferred) or a machine user, and keep the owner's credentials out of agent sessions. Scheduled for the CI Pipeline and Infrastructure Design stages. Until it exists, deployment approval is described as procedural.
5. **Later, optionally:** once agents have their own identity, decide whether to require one approving GitHub review per pull request. This changes the Q1 answer, because it adds an Approve click.

## Unresolved uncertainty

- **Running the agent identity on one workstation**: Agents run as the owner's operating-system user on the owner's machine, and that machine also holds the owner's GitHub and AWS credentials. Keeping those credentials out of agent sessions may need separate OS accounts, credential helpers scoped to the agent identity, or cloud-hosted agent sessions. Settled with the agent identity (owner action 4).
- **The aggregate gate check and records pull requests**: The CI Pipeline stage defines the always-running gate job, its path rules, and the light checks for records pull requests (for example, secret scanning).
- **Recording merges in AI-DLC**: The CI Pipeline stage confirms how AI-DLC's Bolt completion records a merge made on GitHub, so the audit trail still shows one merge per Bolt.
- **Security-sensitive paths and the review record location**: These are named once the architecture sets the module layout.
- **The preview address gate**: Basic authentication through a CloudFront Function versus another lightweight gate is decided in NFR Design. A paid WAF IP allowlist is avoided on cost grounds.
- **Studio sign-in in end-to-end tests**: How Studio sign-in is exercised in CI and in preview, without a way around authentication in production, is left to NFR Design.
- **Runtime secret store**: SSM Parameter Store or Secrets Manager is left to Infrastructure Design.
- **Cloudflare token**: There is no OIDC option for Cloudflare, so one long-lived, least-privilege token remains on the `production` environment. Its rotation is left to Infrastructure Design.
- **Not reviewed**: Without the quality, developer and devsecops reviews, these practices were not independently checked. The independent security review practice applies to code changes, not to this stage.
