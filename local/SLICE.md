# Running the walking slice locally (U0, S1 to S3)

The walking slice demonstrates the whole path on one machine: **create, save, preview and
publish** a project, and see it served as a static page. It runs only on a local Docker
Compose stack. It is never deployed, uses no cloud service and no paid service, and lives
only on the `slice/walking-slice` demonstration branch.

## What is real and what is a local-only fake

| Part | Where | Real or fake |
| --- | --- | --- |
| Studio API: owner check, create, save, preview, Publish, reconciliation | `backend/portfolio_api/` | Real implementation code |
| Shared renderer (React static markup, C2 validation, C11 output) | `web/slice-renderer/` | Real implementation code |
| Studio page | `web/slice-studio/` | Real implementation code |
| MongoDB single-node replica set, nginx static server | `local/compose.yaml` | Real software, local containers |
| **Identity provider** | `local/fake-idp/` | **LOCAL-ONLY FAKE**, marked `AIDLC_LOCAL_ONLY_FAKE_IDP`; signing key generated in memory at start-up |
| In-memory repositories, fixed renderer, pointer-file link | `backend/tests/unit/slice/fakes.py` | **LOCAL-ONLY FAKES**, used by unit tests only |
| Fixture image | `local/fixtures/` | Placeholder test data drawn from code; metadata-free |

The API accepts the fake issuer only because `local/compose.env` sets `APP_ENV=local`; with any
other environment it refuses to start (BR1.3). The CI guard fails if the fake provider leaks
into any build output (BR1.2).

## Prerequisites

- Docker with Compose v2
- Node 22 and npm
- Python 3.12 or later (only for the check script and the scan)
- `make` (optional: each target is one command, shown below)

One-time, project-local setup (npm packages and the Playwright browser go into
`web/node_modules`; nothing is installed system-wide):

```sh
make slice-setup
# or, without make:
npm --prefix web ci
npm --prefix web/slice-renderer ci
npm --prefix web/slice-studio ci
cd web && PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install chromium
```

## Verify the slice

The project-wide verifier runs every registered check, including the slice's, and reports
which ran, failed or were skipped:

```sh
python scripts/verify.py --strict                  # everything (make verify)
python scripts/verify.py --unit walking-slice      # the slice only (make slice-verify)
python scripts/verify.py --list                    # what is registered and runnable here
```

The slice's checks are:

- the back-end unit tests (80% coverage floor);
- the fake issuer tests;
- the renderer and Studio package checks;
- the C2/C11 contract tests;
- the MongoDB integration tests;
- the end-to-end check below;
- the dependency audits (optional, because they need the network).

## The two stacks

| Stack | Compose project | Host ports | Database | Who starts and stops it |
| --- | --- | --- | --- | --- |
| Your demo stack | `portfolio-slice` (`local/compose.yaml`) | 8000, 8080, 9000, 27017 | `mongo-data` volume (kept) | You. `make slice-down` is the only command that removes its volumes, and only when you run it |
| Verification stack | `portfolio-verify-<checkout id>` (`local/compose.yaml` + `local/compose.verify.yaml`), one per checkout or worktree | Free loopback ports chosen for each run (API, site, issuer, MongoDB, Studio dev server) | tmpfs: empty in every new container | `scripts/verify.py` and `local/slice_check.py`. They stop it with a plain `down`, which removes that project's containers and network only |

The checkout id is the first 10 hex digits of the SHA-256 of the checkout path, so two
worktrees never share containers, networks, volumes or ports. A lock file
(`.verify-work/verify.lock`) stops two runs in the same checkout from overlapping; the second
one exits at once and says so. Both scripts refuse `portfolio-slice` and any project name that
does not start with `portfolio-verify-`, and they never pass `-v`, `--volumes`, `--rmi`,
`--remove-orphans` or a prune.

The verification never starts, stops or changes your demo stack, and never removes a volume.
Its `site` volume (`portfolio-verify-<checkout id>_site`) keeps earlier releases between runs.
The API reconciles them against the empty database at start-up, and a new Publish serves only
the new release.

The back-end integration tests run in a Linux container on that stack's network
(`local/it.Dockerfile`, Compose service `slice-it`, profile `tests`), so the site-store and
restart-reconciliation tests use real symbolic links on every host.

## Run the end-to-end check (W6)

```sh
make slice-check
# or, without make:
python local/slice_check.py              # add --keep-running to inspect the stack afterwards
```

The check runs in the verification stack:

1. asserts that the Compose configuration publishes ports on `127.0.0.1` only;
2. starts the stack with `up -d --build --force-recreate`. When `scripts/verify.py` runs it, the verifier has already started the stack (`SLICE_STACK_MANAGED=1`);
3. asserts that the database is empty (REL-0.2);
4. runs the Playwright journey:
   - sign in, create, save;
   - preview, sandboxed and marked "Preview — not public";
   - Publish of the reviewed revision, and the static page with the title escaped;
   - "Changes since last publish" and the 409 reload message;
   - the C9 headers on a 200 and a 404;
   - the timings: API calls under 1 s, Publish under 10 s;
5. exports the published release and its snapshot, and runs the public-output allow-list scan
   (`scripts/scan_output.py`). Every published image must equal an authorized fixture
   derivative byte for byte: the scan compares it with `local/fixtures/derivatives.sha256.json`.

It exits non-zero on any failure. It stops the verification stack at the end unless you pass
`--keep-running`, in which case it prints the `down` command to use later. It prints the ports
it chose at the start; with the stack up:

| Address | What |
| --- | --- |
| `http://localhost:<SLICE_SITE_PORT>/` | The public static site served by nginx |
| `http://localhost:<SLICE_API_PORT>/health` | The API health route (the only unauthenticated route) |
| `http://localhost:<SLICE_IDP_PORT>/.well-known/jwks.json` | The fake issuer's public keys |

## Run your own demo stack

```sh
docker compose -f local/compose.yaml up -d --build
npm --prefix web/slice-studio run dev    # then visit http://localhost:5173
```

The Studio expects the API on port 8000. If another local service already holds one of the
host ports, move the slice's port with `SLICE_API_PORT`, `SLICE_SITE_PORT`, `SLICE_IDP_PORT`
or `SLICE_MONGO_PORT`, and point the Studio at it with `VITE_API_BASE`. Remove the stack and
its volumes, deliberately, with `make slice-down` (`docker compose -f local/compose.yaml down -v`).

## Run single suites by hand

From the repository root, with the Python tooling installed in `.venv`
(`pip install --require-hashes -r requirements.lock -r backend/requirements-slice.lock`):

```sh
python -m pytest backend/tests/unit/slice --cov=portfolio_api.slice --cov=portfolio_api.auth --cov=portfolio_api.settings --cov-fail-under=80
python -m pytest local/fake-idp/tests
npm --prefix web/slice-renderer run test
npm --prefix web/slice-studio run test
```

The integration tests need a MongoDB replica set. `scripts/verify.py --unit walking-slice`
starts the verification stack for them and runs them in the `slice-it` Linux container.

On Windows without Developer Mode, one site-store unit test that needs real symbolic links is
skipped; it runs on Linux and in CI. `verify.py --strict` reads each test report and allows
that one skip only on Windows (`allowed_skips` in `scripts/verify-checks.toml`); any other
skipped test fails a strict run.
