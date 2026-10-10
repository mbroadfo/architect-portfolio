# Practices Discovery — Questions

Greenfield interview over the five practice areas. The release engineer's draft (`team-practices.md`, `evidence.md`) recommends a practice for each area from the charter and the framework defaults. Following the owner's instruction to batch only genuinely open choices, three areas get a direct question and the remaining recommendations are confirmed together in Q4.

## Q1. Way of Working — how should code changes reach `main`?

A. A pull request per delivery increment; CI must pass; once you approve the increment in AI-DLC, the agent squash-merges it, so you never click Merge (recommended)
B. Same pull requests, but you click Merge on each one in GitHub yourself
C. No pull requests; the agent squash-merges locally after CI passes on the pushed branch, then pushes `main`
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Deployment — which AWS environments?

A. One `production` environment, no staging; before launch it is reachable only at its CloudFront address, with no custom domain (recommended)
B. Add a staging environment that deploys automatically on merge (free-tier resources, no custom DNS); production still gated. May add a small recurring cost and needs standing authorization for automatic deploys to a publicly reachable address
C. Nothing in AWS until launch is ready; local and CI only until then
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. Deployment — how do you authorize a deploy?

A. Approve the run in GitHub's deployment review (you are the required reviewer on the `production` environment); GitHub records who approved and when (recommended)
B. Tell the agent in the AI-DLC session and it starts the deploy (no GitHub approval step)
C. Both: the agent asks in-session, then you approve the GitHub run
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. Accept the draft's recommendations for the remaining areas?

- **Build a thin end-to-end slice first?** A walking skeleton is a minimal version that runs the whole way through, built first to prove the pieces connect before the real features go in. Recommendation: no separate skeleton checkpoint (the approved plan has it off), but Delivery Planning orders the thinnest end-to-end path first (public page served, API health check, CI passing with keyless AWS access, clean infrastructure plan).
- **Testing:** tests written after each layer, before the increment goes for approval; 80% line coverage on the frontend and the API, enforced in CI; dedicated tests for the privacy and publish rules (D-15, D-21, D-22); no live paid services in tests.
- **Code style:** Prettier, ESLint and strict TypeScript for the frontend; Ruff and mypy for Python; terraform fmt and tflint; CI must pass before merge (format, lint, types, tests with coverage, build, secret scan, dependency audit, CodeQL).

A. Accept all three recommendations
B. Accept, with changes (please specify)
C. Not yet defined
X. Other (please specify)

[Answer]: A
