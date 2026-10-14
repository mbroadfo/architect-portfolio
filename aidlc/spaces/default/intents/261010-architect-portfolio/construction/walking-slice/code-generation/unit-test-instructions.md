# Unit Test Instructions — U0 walking-slice

The test strategy is Standard: 5 to 8 tests per component, plus integration tests at the key boundaries. The methodology is test-after: implement each layer, then write and run its tests. The coverage floor is 80% lines (NFR13.4).

## Framework Setup

- **Python:** pytest, pytest-cov, httpx (FastAPI test client) and PyJWT, pinned in `requirements.lock`. The configuration lives in `backend/pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage]`).
- **TypeScript:** Vitest with `@vitest/coverage-v8`, React Testing Library and jsdom. The configuration lives in each package's `vitest.config.ts`, with `coverage.thresholds.lines = 80`.
- **End to end:** Playwright, pinned in `web/package.json`; it is used only by `make slice-check`.

## Unit-Scoped Run Commands

Run each command from the repository root. All of them are scoped to U0's paths.

**S0 scripts:**

```
python -m pytest tests/scripts --cov=scripts --cov-fail-under=80
```

**S1 and S2 back end, unit tests** (fakes; no Docker):

```
python -m pytest backend/tests/unit/slice --cov=backend/portfolio_api/slice --cov=backend/portfolio_api/auth.py --cov=backend/portfolio_api/settings.py --cov-fail-under=80
```

**S1 and S2 back end, integration tests** (they need the MongoDB replica set from `local/compose.yaml`):

```
docker compose -f local/compose.yaml up -d mongo mongo-init
python -m pytest backend/tests/integration/slice
```

**Fake issuer:**

```
python -m pytest local/fake-idp/tests
```

**S2 renderer:**

```
npm --prefix web/slice-renderer exec -- vitest run --coverage
```

**S3 Studio page:**

```
npm --prefix web/slice-studio exec -- vitest run --coverage
```

**End-to-end slice check (W6):**

```
make slice-check
```

## Coverage Targets

At least 80% line coverage for:
- `scripts/`;
- the slice back end (`backend/portfolio_api/slice`, `auth.py`, `settings.py`);
- `web/slice-renderer`;
- `web/slice-studio`.

A target is never lowered to make a step pass.

## Mocking and Stubbing

- **Identity provider:** unit tests sign tokens with a test key pair generated in the test, and stub the JWKS client. Integration tests use the local fake issuer. Nothing calls Auth0, and no live paid service is used (team practice).
- **MongoDB:** unit tests use in-memory repository fakes that implement the repository interfaces. Integration tests use the real single-node replica set in Docker, so transactions are exercised.
- **Renderer:** the API's unit tests stub the renderer subprocess with a fixed `RenderOutput`. The renderer's own tests call `render()` directly.
- **Filesystem:** Publish tests use a temporary directory for `site/`, with failure injection at render, transaction and swap.

## Test Data

- **Fixture image:** one bundled image, already metadata-free, with its derivatives under the C8 variant rule, in `local/fixtures/`.
- **Text:** placeholder text only. No real project content and no withheld values (FR10.7).
- **Guard fixtures:** `tests/guard/fixtures/contaminated/` contains a synthetic artifact with the marker text and no real key; `tests/guard/fixtures/clean/` contains a clean artifact.
- **Review-check tests:** each test builds a temporary git repository.
