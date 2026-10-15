# Security Requirements — U0 walking-slice

**Inputs:**
- functional-spec, rules and entities: `../functional-design/`;
- requirements (NFR1 to NFR17);
- contract-summary (C2, C9, C11);
- team-practices (Testing Posture, Code Style, Deployment);
- `bolt-plan.md` Phase A;
- `nfr-requirements-questions.md`.

U0 is the delivery-only walking slice. S0 merges; S1 to S3 run only on a local stack and are never deployed. Every requirement row carries its inception NFR ID with a sub-number.

## Requirements

| ID | Requirement | Verification |
|---|---|---|
| NFR1.1 | Owner-only API: signature verified against the issuer's keys; RS256 or ES256 only; issuer, audience, expiry and subject checked; never by email (BR1.1) | AC0.1, with forged-signature, unsigned, wrong-audience and other-subject fixtures |
| NFR1.2 | The fake issuer is refused at runtime outside explicit local mode (BR1.3). Explicit local mode means the environment variable `APP_ENV=local` **and** the API bound only to a loopback address; anything else is non-local | AC0.1a |
| NFR1.4 | Fail closed when keys cannot be obtained: if the issuer's signing keys cannot be fetched or parsed, or a token's key id is unknown after one refresh, the request is refused with 401 and nothing is read or changed. Keys are cached at most 10 minutes | A unit test with an unreachable key endpoint and an unknown key id |
| NFR1.3 | The fake identity provider never ships. It lives only under `local/fake-idp/` with the marker `AIDLC_LOCAL_ONLY_FAKE_IDP`; its key exists only in memory; the S0 guard scans every non-local artifact (BR1.2) | AC0.2 with a negative fixture |
| NFR2.1 | Published output contains only the C2 allow-list (BR3.2) | AC0.9 allow-list scan of every output file |
| NFR2.2 | Nothing is published without an explicit confirmation of the reviewed revision, done atomically (BR3.1) | AC0.6, AC0.7 |
| NFR3.1 | No secrets in the repository: no committed keys or tokens; gitleaks runs in S0 | gitleaks on every pull request; NFR1.3 |
| NFR4.1 | The slice spends nothing: no cloud resources, no paid APIs | Local stack only (Docker MongoDB, local static server) |
| NFR13.1 | The S0 CI gates: aggregate check, CodeQL, dependency audit, and the content-bound review check (BR5.1, BR5.2) | AC0.10, AC0.11 |
| NFR13.4 | Coverage floor: at least 80% line coverage for the merged Python and TypeScript code. A drop below fails the aggregate check | The coverage step in the aggregate check |
| NFR13.5 | Dependency audit: `npm audit` and `pip-audit` fail the check on any **high** or **critical** finding | The audit step in the aggregate check |
| NFR13.6 | CI security. Every workflow:<br>• declares least-privilege `permissions:`, by default `contents: read`; only CodeQL adds `security-events: write`;<br>• pins every third-party action to a full commit SHA;<br>• runs pull requests from forks with no secrets and no write token, and never uses `pull_request_target`;<br>• carries no cloud credentials in S0;<br>• is itself a security-sensitive path under BR5.2 | A workflow lint in the aggregate check that fails on missing `permissions:`, unpinned actions or `pull_request_target`; and the BR5.2 review |
| NFR15.1 | Escaping and no inline scripts in rendered pages; the local static server sends the C9 CSP header | AC0.6; a header check in `make slice-check` |
| NFR15.2 | The Studio page keeps the token in memory only and sends it as a bearer header | A unit test that nothing is written to local or session storage |

**Threats considered.** These are the threats this unit addresses: a compromised workflow or third-party action (NFR13.6), forged or replayed tokens, an unreachable key endpoint, a fake issuer leaking into a deployment, private-field leakage into the output, cross-site scripting through owner text, committed secrets, and the slice being deployed by mistake. Every threat this unit can mitigate maps to a requirement above.

## Assumptions & Open Questions

- The production NFR targets are set on the owning units (U3, U7, U8, U9, U11). The slice demonstrates the path; it does not measure it.
