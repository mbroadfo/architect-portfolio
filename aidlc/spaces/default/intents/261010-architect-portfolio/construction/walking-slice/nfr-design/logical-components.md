# Logical Components — U0 walking-slice

**Inputs:**
- U0 NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- contract-summary (C2, C9, C11);
- components;
- team-practices;
- `nfr-design-questions.md`.

U0 is the delivery-only walking slice. S0 merges to `main`; S1 to S3 run only on the local stack.

## Local Stack Components

| Component | Runs where | Failure domain | Notes |
|---|---|---|---|
| Studio page (React, Vite) | Host browser and dev server | Owner's browser | Holds no secrets; the token is in memory |
| API (FastAPI, plus a Node runtime for the renderer subprocess) | Docker container | Local stack | Refuses to start with the fake issuer unless in explicit local mode |
| Slice renderer (TypeScript CLI) | Inside the API container, as a subprocess | One Publish | Pure: snapshot in, files out |
| Fake issuer | Docker container, local only | Local stack | Key in memory; never in an artifact (build guard) |
| MongoDB, single-node replica set | Docker container | Local stack | Transactions for Publish |
| nginx static server | Docker container | Local stack | Serves `public` (a symbolic link) with the C9 headers |

**Merged to `main` by S0:**
- the repository layout;
- `.github/workflows/ci.yml` and `codeql.yml`;
- `.github/security-sensitive-paths.txt`;
- Dependabot configuration;
- `scripts/` (the guard, the workflow lint, the review check, the output scan);
- the guard fixtures and their tests.

**Blast radius.** Every runtime component above is local and disposable. The only shared, persistent surface is the CI configuration on `main`, which is why NFR13.6 applies to it.

## Assumptions & Open Questions

- The production designs for these concerns belong to the owning units' NFR Design.
