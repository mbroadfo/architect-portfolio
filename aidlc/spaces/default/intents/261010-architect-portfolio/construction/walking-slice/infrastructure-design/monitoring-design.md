# Monitoring Design — U0 walking-slice

**Inputs:**
- U0 NFR design: `../nfr-design/`, the security, reliability and logical-components files;
- NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- components and contract-summary;
- team-practices (Way of Working, Deployment, Code Style);
- `infrastructure-design-questions.md`.

U0 uses **no cloud infrastructure**. S1 to S3 run on a local Docker stack, and S0 merges the CI pipeline. Every cloud resource belongs to U2 and the owning units, and needs Michael's approval (E1, E2).

## Metrics & KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| `slice-check` duration per step | `make slice-check` output | Each API call under 1 s; Publish under 10 s | NFR6.1, NFR6.2 |
| CI `gate` duration | GitHub Actions | Under 10 minutes | NFR13.3 |
| Coverage | pytest-cov and Vitest | At least 80% lines | NFR13.4 |

## Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| CI gate failure | `gate` or CodeQL fails on a pull request | Blocking | The pull request author (the agent) and the pull request page |
| Dependabot security update | A high or critical advisory | High | A Dependabot pull request, triaged by the records owner |

## SLIs / SLOs

None. The slice is a local demonstration with no service level. CI's SLI is gate duration, with the 10-minute target above.

## Logs & Tracing

`docker compose logs` shows the JSON request logs (request id, route, status, duration, with tokens redacted; NFR11.1). There is no tracing and no dashboard locally. The production observability belongs to U2 and U3.

## Assumptions & Open Questions

- No cloud resource is designed or created here. U2's Infrastructure Design covers preview and production.
