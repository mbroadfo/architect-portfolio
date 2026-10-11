# External Dependency Map

**Inputs:**
- bolt-plan;
- requirements (Open Questions, Assumptions);
- team-practices (Way of Working, Deployment);
- contract-summary (open questions);
- decisions D-28 and P-05 to P-08.

A **Bolt** is one build pass over part of a unit of work, ending in working, tested code merged through one pull request. 🧪 marks a Bolt that must pass preview verification before it can merge. 🔒 marks a Bolt that needs an independent security review.

No other team or outside party is involved. Every item below is an approval or an account action by Michael, or a choice a later design stage makes. Nothing here is assumed approved.

## Dependencies

| ID | Dependency | Owner | Lead time (estimate) | Blocks | If it slips |
|---|---|---|---|---|---|
| E1 | One-time AWS bootstrap: Terraform state bucket, GitHub OIDC provider, read-only plan role, preview and production deploy roles. Preferably a separate preview account under AWS Organizations | Michael, with his own credentials. Agents never use them | About an hour, once Infrastructure Design has specified it | B04 and B05 (plan in CI), and every later 🧪 Bolt | Build B04 and B05 and validate them locally; CI planning waits |
| E2 | Approval to create `preview`. Estimated under $1 a month while idle; Infrastructure Design confirms the cost. Includes whether this approval also lets agents deploy pull-request builds to preview | Michael | One decision, at the Infrastructure Design gate | The merge of every 🧪 Bolt (team practice: verify in preview before merging) | Bolts are built and reviewed; merges queue until preview exists |
| E3 | Free Auth0 tenants: a development tenant for preview and a production tenant. Self-registration disabled; MFA on (FR1.1, FR1.3) | Michael | About an hour | B07 and B27 integration in preview. Unit tests use fakes | Fakes in CI; preview sign-in waits |
| E4 | Free MongoDB Atlas M0 clusters, one per environment, in separate projects | Michael | About 30 minutes | Preview integration for B08 onward. CI uses a throwaway container | CI unaffected; preview waits |
| E5 | The read-only GitHub credential: a fine-grained token or a GitHub App, chosen in NFR Design (FR2.2) | Michael creates it; NFR Design chooses | About 30 minutes after the choice | B09 against real GitHub in preview | Fake GitHub in CI; Discover against real repositories waits |
| E6 | AI provider and framework choice (NFR Design). Michael's approval of pay-per-use AI spending and the monthly limit (FR5.8). Approval of the provider for private content (FR5.9) | NFR Design proposes; Michael approves | One decision, once the cost per call is known | Enabling the real provider in B14 | Ships with the fake provider and AI disabled; nothing is spent |
| E7 | A separate GitHub identity for agents: a GitHub App or machine user (team practice, target control) | Michael, at CI Pipeline and Infrastructure Design | About an hour | Nothing in Construction. It enables "Prevent self-review" later | The control stays procedural, as documented |
| E8 | Cloudflare API token for the zone, and approval of each DNS change (FR10.2, FR10.4) | Michael | About 30 minutes, plus a separately approved production run | Launch only; no Construction Bolt | The site stays on its CDN default address before launch |
| E9 | Launch content and rights. The public email, biography, imagery and approved copy. For each candidate: content, rights, live-URL and publication approval (FR10.1). The Monopoly and Risk trademark and artwork review (FR10.6). STARS and Monopoly licensing. The Risk live-URL privacy and security review (FR10.7) | Michael | Michael's schedule | Publishing real exhibits. No Construction Bolt: fixtures use placeholders, and withheld values never enter the repository | Launch with any approved subset (FR10.1) |
| E10 | Authorization to merge Construction pull requests under team practice: the agent squash-merges after Michael approves the Bolt at its checkpoint. Records pull requests #8 to #12 also await Michael's merge decision | Michael | One decision, at Construction start | Every Bolt's merge | Bolt branches accumulate in a reviewed state; nothing reaches `main` |
| E11 | Independent security review sessions for 🔒 Bolts (team practice) | A separate AI session, started by the owner of the workflow state | Same day as the Bolt | The approval of each 🔒 Bolt | The Bolt waits for its review |
| E12 | Production deployment: each run personally approved by Michael in the `production` environment | Michael | Per run | Launch only | Nothing reaches production |

**Issue #2** (an outdated spa-on-aws statement in the charter) blocks nothing.

## Assumptions & Open Questions

- **Lead times are estimates.** Every item is Michael's decision or action, and none is assumed approved.
- **Merging first needs E2 and E10.** E2 and E10 are the two items that determine when the first Bolt can merge.
