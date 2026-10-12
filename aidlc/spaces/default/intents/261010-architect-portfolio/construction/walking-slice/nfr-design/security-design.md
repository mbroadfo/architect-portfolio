# Security Design — U0 walking-slice

**Inputs:**
- U0 NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- contract-summary (C2, C9, C11);
- components;
- team-practices;
- `nfr-design-questions.md`.

U0 is the delivery-only walking slice. S0 merges to `main`; S1 to S3 run only on the local stack.

## Owner Authentication (NFR1.1, NFR1.4)

- **One check for every route.** A single FastAPI dependency, `require_owner`, is attached at router level to every slice route. Only `GET /health` is registered outside that router, and it returns only `{"status":"ok"}`. FastAPI's `/docs`, `/redoc` and `/openapi.json` are disabled (`docs_url=None`, `redoc_url=None`, `openapi_url=None`), so health is the only unauthenticated route. A test enumerates every route the app serves and asserts that only `/health` lacks `require_owner`. The OpenAPI document is generated to a file in CI instead.
- **What the check does:**
  - reads `Authorization: Bearer <jwt>`;
  - verifies the signature with keys fetched from `<issuer>/.well-known/jwks.json`, through a JWKS client that caches keys for at most 10 minutes and refreshes on an unknown key id at most once every 60 seconds (a test sends repeated unknown key ids and asserts a single fetch);
  - accepts only `algorithms=["RS256","ES256"]`;
  - requires `exp`, `iat`, `iss`, `aud` and `sub`, with 60 seconds of leeway;
  - compares `iss` and `sub` with the configured owner.
- **Results:**
  - **401:** any failure, including a key endpoint that is unreachable or a key id that is unknown after one refresh (fail closed);
  - **403:** a valid token with another subject;
  - in every case no handler runs.
- **Never used:** email and name claims.

## Fake Issuer Isolation (NFR1.2, NFR1.3)

- **Where it lives.** The fake issuer is a small FastAPI app in `local/fake-idp/`. Its source carries the marker `AIDLC_LOCAL_ONLY_FAKE_IDP`.
- **Its key.** At start-up it generates an ES256 key pair in memory, which is never written to disk. It serves `/.well-known/jwks.json`, and a token endpoint for the owner subject plus test subjects.
- **Runtime guard (BR1.3).** The fake issuer's issuer value is `http://fake-idp.invalid`; `.invalid` is a top-level domain reserved so that it can never resolve publicly. Inside the Compose network it is reached through a network alias of that name.
  - **Local-class issuers.** The settings validator treats an issuer as local-class when it:
    - uses `http` rather than `https`;
    - has a host under `.invalid`, `.local` or `localhost`;
    - has a single-label host, such as a Compose service name;
    - has a loopback or private address.
  - **Refusal.** A local-class issuer is refused at start-up unless `APP_ENV=local` is set.
  - **Host exposure.** The API binds `0.0.0.0` inside its container. The container is exposed to the host only as `127.0.0.1:8000:8000`, and `make slice-check` asserts that the Compose file publishes nothing on a non-loopback host address.
  - **No fake URL in code.** The validator contains only these generic rules, never the fake issuer's URL. The URL lives only in `local/compose.env`, so the build guard and the runtime guard do not conflict.
- **Build guard (BR1.2).**
  - `scripts/guard_fake_idp.py` scans every non-local build output: `backend/dist/*`, `web/*/dist/**`, and any image or bundle archive.
  - It looks for the marker, the package name `fake_idp`, the fake issuer URL, and PEM or JWK private-key patterns. The guard does not hard-code the issuer URL: it reads it at scan time from `local/compose.env`. It scans only build outputs, never `scripts/` or `local/`, so the guard cannot match itself.
  - It runs in the aggregate check. Its negative fixture, `tests/guard/fixtures/contaminated/` (a synthetic artifact containing the marker and no real key), must fail; a clean fixture must pass.

## Output Safety (NFR2.1, NFR2.2, NFR15.1)

- **Allow-list.** The snapshot is validated against C2 before rendering. The allow-list scan (`scripts/scan_output.py`) walks every file in the release and fails on any string that is not derived from the snapshot's C2 fields, the fixture, or the static assets.
- **Escaping.** Rendering uses React escaping. ESLint `react/no-danger` forbids `dangerouslySetInnerHTML`. Pages contain no inline scripts.
- **Headers.** nginx sends `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff` and `Referrer-Policy: strict-origin-when-cross-origin`, matching C9. `make slice-check` asserts them. HSTS does not apply to the local `http` server; C9 sets it in production.
- **CORS.** The API allows only the Studio dev origin `http://localhost:5173`, with no credentialed cookies, because authentication is by bearer header only.
- **Preview frame.** Preview renders into `<iframe sandbox srcdoc=…>` with no `allow-scripts`.

## Studio Token Handling (NFR15.2)

The Studio page gets a token from the local fake issuer's token endpoint, the local stand-in for Auth0's sign-in. It holds the token in a React state hook, sends it as a bearer header, and never writes it to local or session storage. A unit test checks both storages after sign-in. ESLint includes `eslint-plugin-react`, so that `react/no-danger` applies.

## CI Security (NFR13.6, NFR3.1)

- **Least privilege.** Workflows declare top-level `permissions: contents: read`. Only the CodeQL job adds `security-events: write`.
- **Pinned actions.** Every third-party action is pinned to a full commit SHA, with a trailing version comment. Dependabot proposes updates.
- **Forks.** There is no `pull_request_target` trigger. Fork pull requests run with a read-only token and no secrets, and S0 defines no secrets at all.
- **Workflow lint.** `scripts/check_workflows.py`, plus `actionlint`, fails on missing `permissions:`, unpinned actions or `pull_request_target`.
- **Secrets.** gitleaks scans every pull request.

## Content-Bound Review Check (BR5.2; provisional)

- **The check.** `scripts/check_security_review.py` works in three steps:
  1. It reads `.github/security-sensitive-paths.txt`.
  2. If the pull request touches a listed path, it computes the pull request's patch identity over the diff from `git merge-base origin/main HEAD` to `HEAD`, **excluding `docs/security-reviews/`**. Adding the review record therefore does not change the identity it must match.
  3. It requires a record in `docs/security-reviews/` with that `patch-id:` and `verdict: READY`. A `NOT-READY` or any other verdict fails the check.
- **Initial list.** The path list starts with `.github/`, `scripts/`, `.github/security-sensitive-paths.txt`, `backend/**/auth*`, `backend/**/publish*`, `local/fake-idp/` and `infra/`. The list, the scripts and the workflows are themselves on it, so they protect themselves.
- **Provisional.** The path list and the record format are provisional until the CI Pipeline stage confirms them.

## Assumptions & Open Questions

- The production designs for these concerns belong to the owning units' NFR Design.
