# Infrastructure Design Questions — U0 walking-slice

**Inputs:**
- U0 NFR design: `../nfr-design/`, the security, reliability and logical-components files;
- NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- components and contract-summary;
- team-practices (Way of Working, Deployment, Code Style);
- `infrastructure-design-questions.md`.

U0 uses **no cloud infrastructure**. S1 to S3 run on a local Docker stack, and S0 merges the CI pipeline. Every cloud resource belongs to U2 and the owning units, and needs Michael's approval (E1, E2).

Every answer comes from the approved records, under Michael's instruction to "continue autonomously … do not merge, deploy or incur spending without the separate authorization already required".

## Questions

### Q1. Where does the slice run?

A. Local Docker Compose only; no cloud resources, preview or production.
X. Other (please specify)

[Answer]: A — bolt-plan Phase A, NFR4.1, and Michael's instruction to keep the slice isolated from production.

### Q2. What CI does S0 provide?

A. GitHub Actions on GitHub-hosted runners, free for public repositories. Component jobs run behind an always-run `gate` job, and CodeQL runs separately. There are no deployment jobs, no cloud credentials and no secrets.
X. Other (please specify)

[Answer]: A — NFR13.1 to NFR13.6. Deployment jobs belong to U2's B05a and to the CI Pipeline stage.

### Q3. How are secrets handled?

A. There are none in S0 or the slice. The fake issuer's key is held in memory, and the only local configuration is `local/compose.env`, which contains no secrets and only placeholders.
X. Other (please specify)

[Answer]: A — NFR3.1 and NFR1.3.

## Assumptions & Open Questions

None for the owner. Registering `gate` and CodeQL as required checks on the `main` ruleset is Michael's action (E13).
