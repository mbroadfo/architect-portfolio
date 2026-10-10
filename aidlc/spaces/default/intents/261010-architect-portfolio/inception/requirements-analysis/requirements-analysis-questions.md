# Requirements Analysis — Questions

Already decided and not asked again (team rule: approved decisions are reused): the charter (`docs/CHARTER.md`); Ideation decisions D-01 to D-22 (`ideation/approval-handoff/decision-log.md`), including Take down as Must Have (D-21) and publish approval covering all public content (D-22); the approved scope and backlog; Concept A and the six fixes; and the affirmed practices (`aidlc/spaces/default/memory/team.md`, `project.md`). The charter's invitation-link question is moot for the first release, because non-public access is out of scope (D-08).

Only the charter's remaining open owner questions and one carried-over scope item are asked here.

## Q1. What is the monthly running-cost ceiling for the first release?

Charter open question 2. Expected usage (an estimate, confirmed in Infrastructure Design): AWS serverless hosting a few dollars or less; MongoDB Atlas free tier; Auth0 free plan; AI usage pay-per-call and small for one owner. The ceiling decides which paid tiers are ever acceptable without a new approval.

A. Up to US$10 per month across AWS, database, sign-in and AI
B. Up to US$25 per month
C. Up to US$50 per month
D. Free tiers only, except pay-per-use AWS and AI charges of a few dollars
E. Not yet defined
X. Other (please specify)

[Answer]: X — "free tiers only until we find an application needs something paid - like fargate.compute"

## Q2. Which AI provider should power the description-suggestion workflow?

Charter open question 3. The workflow sits behind a provider-independent interface (charter §5), so this is the first adapter, not a lock-in. Suggestions may be generated from private repository content, so where that content is sent matters.

A. Claude through Amazon Bedrock — runs inside the project's AWS account under the same keyless IAM roles; no separate API key; content is not used for model training (recommended)
B. Claude through the Anthropic API directly — needs an API key stored as a secret
C. OpenAI API — needs an API key stored as a secret
D. Not yet defined
X. Other (please specify)

[Answer]: X — "so this is an ai agent that helps me curate and publish new applications?  Not an ai that is exposed to the guests?  If  so, I would want an open framework where I would store the keys in github actions but these are restricted to functions only available to me (admin)" — Confirmed: the AI assists only the owner inside the private Studio; visitors never reach it.

## Q3. How should the public site read published content?

Charter open question 4. The charter proposed static export on publish.

A. Static export on publish — publishing writes the exhibit pages and images to the public site's storage; the public site never calls the API or the database, so the public and administrative boundaries are physically separate; take-down deletes the exported files (recommended)
B. Live API reads — the public site calls a read-only public API that reads published content from the database on each visit
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. Where do exhibit images come from in the first release?

Carried from Scope Definition, where it was left open. Charter §3 prefers real project images, screenshots, CAD renders and demos.

A. Uploaded in the Studio — works for workshop photos and CAD renders that live in no repository (recommended)
B. Pulled from the GitHub repository (for example, images referenced in the README)
C. Both — upload in the Studio, plus pick images found in a linked repository
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. "Free tiers only" versus pay-per-use AI calls — which applies?

Follow-up to Q1 and Q2. Key-based AI providers charge per call and have no lasting free tier; a description suggestion costs roughly a cent or less. Small AWS request charges can also appear beyond the free allowances.

A. Allow pay-per-use charges up to a small hard cap (for example US$5 a month), watched by a budget alert; anything beyond needs approval (recommended)
B. Strictly zero spend — the AI suggestion uses only a free option, even if quality or limits suffer
C. Not yet defined
X. Other (please specify)

[Answer]: A

Owner clarification (2026-10-10): free tiers, with small pay-per-use spending only when explicitly approved. The US$5 figure in option A was an example, not an approved limit; budget alerts are notifications, not hard caps. Runtime credentials go in AWS SSM Parameter Store (free), not Secrets Manager. Selecting images from GitHub is a future enhancement.

## Q6. Which provider should the open framework call first?

Follow-up to Q2. The framework stays provider-independent; this only picks the first key to configure. Keys live as GitHub Actions environment secrets and are usable only by owner-only Studio functions.

A. Anthropic (Claude) API key
B. OpenAI API key
C. Both, selectable per suggestion
D. Not yet defined — decide in design
X. Other (please specify)

[Answer]: D
