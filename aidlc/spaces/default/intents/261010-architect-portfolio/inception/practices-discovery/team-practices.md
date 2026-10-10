# Team Practices — Architect's Portfolio

Michael Broadfoot affirmed these practices in the Practices Discovery interview (`practices-discovery-questions.md`, Q1-Q4, answer A for each) and then revised them at the affirmation gate with four changes (owner revision, 2026-10-10):

1. protect `main`;
2. verify changes outside production first;
3. separate human authority from agent authority;
4. require an independent security review.

On affirmation, the five sections below replace the matching sections of `aidlc/spaces/default/memory/team.md` word for word. Evidence and reasoning: `evidence.md`.

## Way of Working

We use trunk-based development on `main`. It suits one owner working with AI agents that hand over between Claude Code, Codex and Copilot.

- **One short-lived branch per Bolt.** Application and infrastructure changes are made on a branch cut from `main`. The branch holds one Bolt and normally merges within 1-2 days. We keep no long-lived `develop` or release branches. Releases are gated by tags and the deployment approval, never by a branch.
- **Every change reaches `main` through a pull request.** This covers application code, infrastructure, architectural and policy changes, and AI-DLC records and docs. No agent pushes directly to `main`.
- **A GitHub ruleset on `main` enforces this:**
  - a pull request is required;
  - the required status check must pass;
  - force-pushes and deletion are blocked;
  - the bypass list is empty.

  Rulesets are available for public repositories on GitHub Free. The ruleset covers the whole branch, because GitHub does not offer path-restricting push rules for a public repository on the Free plan. That is why records go through pull requests too.
- **One gate check that always runs.** CI skips the components a pull request does not touch, but a required check that never runs stays pending and blocks the merge. So the required status check is a single aggregate job. It runs on every pull request, runs or skips each component's checks according to the changed paths, and fails if any of them fails.
- **Code pull requests.** Each Bolt branch is pushed and opened as a pull request against `main`. Before Michael approves the Bolt at its AI-DLC gate, it needs:
  - every check passing;
  - preview verification, where Deployment requires it;
  - an independent security review, where required (see below).

  After that approval, the agent squash-merges the pull request (`gh pr merge --squash`). The result is one commit on `main`, named by the Bolt slug. Michael does not click Merge (Q1). Construction worktrees map to base `main`, target `main`, strategy `squash`. A Bolt lands through its pull request, never through a local squash-merge pushed directly.
- **Records pull requests, batched.** Routine AI-DLC records (stage artifacts, state and audit shards, `docs/`) are grouped into one records pull request per approved stage gate. When several gates close together, one pull request covers the phase. The active agent merges it once its checks pass and the gates it records have been approved. Architectural or policy content, such as an ADR, a security policy or `AGENTS.md` rules, is merged only after Michael has approved that content at its gate.
- **One writer at a time.** Exactly one agent or harness is active at any time. Only that agent creates branches, opens or merges pull requests, and writes the AI-DLC workflow state. Before another agent takes over, the active one commits and pushes its work, merges or hands over its open pull requests, and records the handoff in a records pull request. The next agent can then continue from the repository alone.
- **Who approves, and how that is enforced.** Agents may prepare commits, pull requests, tests and deployments. Today they work with Michael's own GitHub credentials (git and the `gh` CLI on Michael's machine). GitHub therefore cannot tell an agent's action from Michael's. A merge, review, deployment approval or ruleset change made with those credentials is not independent human approval, and we do not claim that GitHub enforces the difference. Only two things count as Michael's approval:
  - Michael's own answer at an AI-DLC gate. The audit trail records the reply, but as evidence, not as tamper-proof proof of authorship.
  - Michael personally clicking Approve on a GitHub deployment review.
- **Controls that hold technically today, whoever is acting:**
  - The ruleset blocks direct pushes, force-pushes and merges with failing checks. The exception: an admin, and that includes anyone using Michael's credentials, can edit or disable the ruleset.
  - AWS issues deploy credentials only to OIDC tokens from the matching GitHub environment.
  - The Cloudflare token is readable only by jobs in the `production` environment.
- **Controls that are procedural today.** Agents never:
  - approve a deployment review;
  - use a bypass;
  - edit rulesets, environment protection rules or AWS trust policies;
  - start a production run without Michael's recorded AI-DLC approval;
  - use Michael's AWS administrator credentials.
- **Target control (owner action, scheduled for the CI Pipeline and Infrastructure Design stages).** Agents get their own GitHub identity: preferably a GitHub App, otherwise a machine user. That identity:
  - has write access only;
  - has no admin rights;
  - is not a reviewer on `production`;
  - is on no bypass list.

  Agent sessions use only that identity, and Michael's own credentials are kept out of them. Then `production` turns on "Prevent self-review" (it would block Michael's own approvals today, because runs are started under Michael's identity), and Michael's approvals become technically distinct from agent actions. Requiring one approving review on pull requests also becomes possible at that point. It would add one Approve click per pull request and change the Q1 answer, so it will be offered then, not assumed.
- **Independent security review for sensitive changes.** Some pull requests change authentication, authorization, the handling of private material, or publication boundaries (publish, take-down, and what the public site can read). Before Michael approves such a pull request, it needs both of these:
  - **An independent AI security review.** The reviewer is a session or model that did not write the change, such as a separate review session in another harness. It reviews the diff against the threat model. Its findings and verdict are committed with the pull request, at a records path the CI Pipeline stage defines, and blocking findings are fixed first.
  - **Automated verification:** CodeQL, secret scanning, the dependency audit, the approval and privacy invariant tests, and the preview end-to-end checks all pass.

  A CI check fails when a pull request changes the designated security-sensitive paths without a recorded review for its latest commit. Those paths are named once the architecture sets the module layout. The check proves that a review exists. The reviewer's independence is a procedural control.

## Walking Skeleton

We use whatever walking-skeleton setting the active scope declares and keep no fixed team rule of our own. (A walking skeleton is a minimal version that runs end to end, built first to prove the pieces connect.) This project's approved plan (`portfolio-inception-slice`, based on `classic`) declares `skeleton: off`. That means no skeleton checkpoint ceremony. The Construction choice between continuing automatically and reviewing each checkpoint is offered when Construction starts.

Delivery Planning still orders the work so the thinnest integrated path comes first, in line with the first vertical slice in charter §8. The first Units prove the pieces connect:

- the public page builds and is served;
- the API answers a health check;
- CI passes using OIDC credentials;
- the Terraform plan is clean.

Feature depth is added after that. This path is proven locally and in CI first. It is proven in AWS in `preview` once Michael approves creating that environment. Production waits for an approved production run.

## Testing Posture

- **Methodology**: test-after
- **Ordering**: Implement each testable layer of a Bolt, then write and run that layer's tests before the Bolt is offered for approval.
- **Methodology evidence**: This is the `org.md` default for a team with no affirmed posture, and the owner affirmed it in the Practices Discovery interview (Q4). The repository is greenfield, with no tests or team habit that points elsewhere. Rigor comes from the coverage floor, the invariant tests and the CI gates below, not from the order in which tests are written.
- **Test strategy**: The workflow's Standard test strategy sets how many tests are written and of which types. The floors below add to it and never replace it.
- **Coverage floor**: At least 80% line coverage for the frontend and for the Python API, measured in CI. A change that drops coverage below the floor does not merge. Floors and quality targets are never lowered to make a step pass.
- **Frontend tests**: Vitest with React Testing Library for components and logic. Automated accessibility checks (axe) run on the public pages, including a check that every published image has alt text (D-19).
- **API tests**: pytest with coverage. Unit tests replace integration boundaries with fakes. Integration tests run in CI against a throwaway MongoDB container and never against the live Atlas cluster.
- **End-to-end tests**: A small Playwright suite covers the critical journeys: the public gallery and an exhibit page, plus the Studio journey from discovering a repository through preview, publish and take-down. NFR design decides how Studio sign-in is exercised in CI. Production code gets no way around authentication.
- **Infrastructure checks**: `terraform fmt -check`, `terraform validate`, tflint, and a `terraform plan` run on every pull request that touches infrastructure.
- **Approval and privacy invariants**: The Bolt that introduces each of these behaviours also adds a test for it:
  - Studio endpoints reject callers who are not signed in.
  - Nothing reaches the public site without an explicit publish.
  - Take-down removes content from the public site.
  - Private repository material is never exposed, including the hidden "View code" link (D-15, D-21, D-22).
- **No live paid services in tests**: GitHub, Auth0 and the AI provider are replaced by fakes behind their interfaces in unit and CI tests. Tests never spend money or call production systems.
- **Traceability**: Test names or docstrings cite the IDs of the acceptance criteria they verify.
- **Runnable**: Every suite runs from a clean checkout with only the documented prerequisites, locally and in CI.

## Deployment

- **Continuous delivery, not continuous deployment.** Every merge to `main` builds versioned artifacts and keeps them: the static site bundle and the Lambda package, each tagged with its commit SHA. Nothing reaches production until Michael explicitly approves that deploy. This narrows the `org.md` "deploy on merge to staging" default to fit the charter's authorization rule.
- **Two environments: `preview` and `production`.** `preview` is a non-production copy built from the same Terraform modules, with its own state and inputs:
  - pay-per-use serverless services only (S3, CloudFront, Lambda, API Gateway HTTP API);
  - a free MongoDB Atlas M0 cluster in its own Atlas project;
  - a separate Auth0 development tenant on the free plan;
  - test data only;
  - the fake AI provider, unless a test explicitly needs the real one;
  - no custom domain and `noindex`;
  - a CloudFront Function gate, so the address is not openly browsable.

  Preview should live in a separate AWS account under AWS Organizations, which costs nothing extra, so preview credentials cannot reach production resources. The fallback is the same account, with preview roles limited to preview-named resources. Preview stays standing because it costs almost nothing when idle, and Terraform can destroy and rebuild it on demand.
- **Preview cost and approval.** Our estimate is under $1 a month while idle, mostly cents for S3 storage and request charges above the free allowances. Infrastructure Design's cost estimate confirms the figure. Creating preview is new infrastructure, so it needs Michael's approval before it exists (charter §6).
- **Who may deploy to preview (owner decision).** We recommend that Michael's approval to create preview also give standing authorization for agents to deploy pull-request builds there. Preview holds test data only and has no custom domain. Until Michael gives that authorization, each preview deploy needs Michael's authorization like any other deploy.
- **Verify in preview before production.** Some pull requests change authentication, APIs, publication, take-down or infrastructure. Each of these is deployed to preview from its pull request: Terraform plan and apply against the preview state, then the site and Lambda deploy. It must pass its smoke checks and the end-to-end suite there, with the results recorded on the pull request, before it merges. Production receives only artifacts whose changes passed preview. Preview runs one at a time (a GitHub concurrency group), which fits the one-writer rule.
- **Production.** The `production` environment lists Michael as its required reviewer. Every production deploy job runs only in that environment: Terraform apply, publishing the site and updating the Lambda function. Terraform applies exactly the plan reviewed in that run (`plan -out=tfplan`, then `apply tfplan`). Before launch, production is reachable only at its CloudFront default address, with no custom domain. Michael personally clicks the approval.
- **What that approval does and does not prove.** As Way of Working explains, the approval is a procedural control until agents have their own identity. An agent holding Michael's credentials could technically approve the run through GitHub's API. Agents never do, and we do not describe that approval as independently enforced.
- **DNS is its own step.** Cloudflare record changes go through a separate, separately approved run of the `production` environment: the custom domain, ACM certificate validation, and the 301 redirect from `mike.broadfoot.consulting` to `michael.broadfoot.consulting`. An infrastructure push never creates or changes DNS records as a side effect. Preview has no DNS records.
- **Credentials.** GitHub Actions reaches AWS through GitHub OIDC, with three roles:
  - a read-only role for pull-request plans;
  - a preview deploy role, trusted only for tokens from the `preview` environment;
  - a production deploy role, trusted only for `repo:mbroadfo/architect-portfolio:environment:production`.

  AWS checks those trust conditions on every token. We create no IAM users and no long-lived AWS access keys. The Cloudflare API token cannot use OIDC, so it is a least-privilege token for this one zone, stored as a secret on the `production` environment. Michael runs the one-time bootstrap (Terraform state bucket, OIDC provider, roles, preview account) with Michael's own credentials. Agents never use those credentials.
- **What we reuse from `spa-on-aws`.** We keep these patterns:
  - S3 + CloudFront with Origin Access Control;
  - an ACM certificate in us-east-1;
  - the Terraform S3 backend with native state locking;
  - immutable caching for hashed assets and no-cache for `index.html`;
  - CI workflows that run only for changed directories;
  - `cancel-in-progress: false` for infrastructure runs.

  We replace its IAM users and access keys, its unconditional deploy on every push, its automatic DNS writes, and its personal-access-token writes to GitHub variables.
- **Smoke checks after every deploy, in preview and in production.**
  - The gallery returns 200 and shows its cards.
  - An exhibit page loads.
  - The API health endpoint reports OK.
  - Once DNS is cut over, `mike.broadfoot.consulting` answers with a 301 that keeps the path and query string.

  A failed smoke check marks the deploy as failed and starts a rollback.
- **Rollback.** We redeploy the previous SHA-tagged artifact through an approved `production` run: the site bundle is synced again and the Lambda alias points back to the previous version. Infrastructure is rolled back by reverting the commit and applying a newly approved plan. Every deploy procedure documents how to roll it back.
- **Data changes.** Database changes are made in two steps: first add the new fields or collections, then remove the old ones in a later release. A destructive data change never ships in the same deploy as the code that depends on it. Destructive operations need Michael's approval.

## Code Style

We rely on configuration files at the repository root. Agents read the linter configuration first and suggest style changes only where the linter has no rule.

- **TypeScript / React**: Prettier for formatting. ESLint with typescript-eslint, react-hooks and jsx-a11y. TypeScript `strict` mode, with `tsc --noEmit` run in CI.
- **Python**: Ruff for linting and formatting. mypy type checking on the API package. Type hints on all public functions.
- **Terraform**: `terraform fmt` and tflint.
- **Naming**: Each language's usual conventions: camelCase in TypeScript, PascalCase for React components, snake_case in Python and for Terraform resource names.
- **Text files**: UTF-8 with LF line endings (already enforced by `.gitattributes`), plus an `.editorconfig` at the repository root.
- **Dependencies**: Pinned through committed lockfiles: `package-lock.json` installed with `npm ci`, and locked Python requirements. Dependabot proposes updates as pull requests.
- **Checks before merge**: Each of these runs in CI on every pull request, and any failure blocks the merge:
  - format check;
  - lint;
  - type check;
  - tests with the coverage floor;
  - build;
  - secret scanning (gitleaks);
  - dependency vulnerability audit, failing on high or critical findings (`npm audit`, `pip-audit`);
  - CodeQL code scanning.

  CI should finish within 10 minutes.
- **Secrets and configuration**: Secrets never appear in code, committed configuration, logs or CI output. Runtime secrets come from AWS SSM Parameter Store or Secrets Manager; Infrastructure Design picks one. `.env` files are gitignored, and a committed `.env.example` lists variable names only.
- **Commits**: One squash commit per Bolt, titled with the Bolt slug and a one-line imperative summary. Each records pull request is titled after the stage or phase it records.
