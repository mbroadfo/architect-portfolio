## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 2

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/261010-architect-portfolio/construction/walking-slice/nfr-requirements/tech-stack-decisions.md > Database row | The Publish rules (BR3.1 and the W4 compensating transaction) need a multi-document database transaction, but the stack says only "MongoDB 7 in Docker locally" and a "throwaway container" in CI. A standalone mongod rejects transactions, so AC0.6, AC0.7 and AC0.9 cannot pass as specified. | State that the local and CI MongoDB runs as a single-node replica set (and that Atlas M0 supports transactions), and add that as a requirement under NFR10.1 or the stack decisions. | Resolved (reviewer) |
| R-02 | Major | aidlc/spaces/default/intents/261010-architect-portfolio/construction/walking-slice/nfr-requirements/security-requirements.md > NFR13.1 and the Threats considered paragraph | S0 merges to main the CI workflows, the gitleaks, CodeQL and audit steps, and the guard. Yet no requirement covers the security of the CI itself: least-privilege GITHUB_TOKEN permissions per job, no secrets exposed to fork or pull-request code, and pinned or trusted action versions. The threat list omits a compromised workflow or action. Team practice requires least-privilege permissions and the guard and review check are the controls for every later unit. | Add NFR requirements for workflow permissions, fork and pull-request trust, and action pinning, with a verification (for example a workflow-lint check in the aggregate job), and add CI compromise to the threats considered. | Resolved (reviewer) |
| R-03 | Major | aidlc/spaces/default/intents/261010-architect-portfolio/construction/walking-slice/nfr-requirements/ (all files) > NFR13 coverage | The 80% line-coverage floor named in Q4 and required by NFR13 and team practice appears in no requirement row or verification. The two files that carry an NFR13.1 row (security: gate list; performance: CI under 10 minutes) mention no floor. The dependency-audit failure threshold (high or critical) is also unstated. The merged S0 code therefore has no measurable coverage or audit target. | Add measurable rows: at least 80% line coverage for the S0 code (CI scripts and guard) enforced by the aggregate check, and the audit failing on high or critical findings. | Resolved (reviewer) |
| R-04 | Minor | aidlc/spaces/default/intents/261010-architect-portfolio/construction/walking-slice/nfr-requirements/security-requirements.md and performance-requirements.md > NFR13.1 | The ID NFR13.1 is used for two different requirements (the CI gate list, and the 10-minute CI time), so a citation of NFR13.1 is ambiguous. | Give the CI time budget its own sub-ID (for example NFR13.3). | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/261010-architect-portfolio/construction/walking-slice/nfr-requirements/traceability.json > NFR5 and NFR7 | NFR5 (public Largest Contentful Paint 2.5 s on mobile) is marked OK through a 10-second local publish time, which is a different measure. NFR7 is marked OK through a row that says "None". Neither coverage is an honest equivalent; both read as N/A with the owning unit named. | Mark NFR5 and NFR7 N/A with the owning units, or rename NFR5.1 as a slice functional target not claiming NFR5. | Resolved (reviewer) |
| R-06 | Minor | aidlc/spaces/default/intents/261010-architect-portfolio/construction/walking-slice/nfr-requirements/security-requirements.md > NFR1.1 and NFR1.2 | The requirements leave out what happens when the issuer's signing keys cannot be fetched (the request should fail closed with 401 and not fall back to unverified acceptance), and do not define "explicit local mode" (which setting enables it). AC0.1a cannot be written precisely without it. | Add a fail-closed requirement for key-fetch failure, and name the single explicit local-mode setting the test toggles. | Resolved (reviewer) |
| R-07 | Minor | aidlc/spaces/default/intents/261010-architect-portfolio/construction/walking-slice/nfr-requirements/traceability.json > NFR9 and NFR10 | NFR9 N/A relies on NFR2.1, which scans the allow-list but does not cover cookies or tracking; NFR10 is marked OK through failure consistency, while the nightly export and restore it names are not addressed or marked N/A for the slice. | State the NFR9 and NFR10 export parts as N/A with the owning unit, or add the missing checks (no cookies or tracking in the output scan). | Resolved (reviewer) |

> R-01 Reviewer note: tech-stack-decisions.md Database row and REL-0.1 now require a single-node replica set locally and in CI, and note Atlas M0 is a replica set.

> R-02 Reviewer note: NFR13.6 adds least-privilege permissions, SHA-pinned actions, fork trust, no pull_request_target and a workflow lint. Threats paragraph now names a compromised workflow or action.

> R-03 Reviewer note: NFR13.4 (80% coverage floor) and NFR13.5 (audit fails on high or critical) added with measurable verification.

> R-04 Reviewer note: The CI time budget is now NFR13.3 in performance-requirements.md; NFR13.1 is unique to security.

> R-05 Reviewer note: NFR5 and NFR7 are now N/A with owning units named.

> R-06 Reviewer note: NFR1.4 adds the fail-closed rule; NFR1.2 defines local mode as APP_ENV=local plus a loopback-only bind.

> R-07 Reviewer note: NFR9 and NFR10 are N/A with owning units (U7 and U2, U10); REL-0.x rows are stated as derived from BR3.1 and BR3.3.

### Notes

The traceability sensor passes with no gaps, orphans or invalid targets. Sub-IDs NFR13.1 to NFR13.6 each appear exactly once across the files. No new defects found.
