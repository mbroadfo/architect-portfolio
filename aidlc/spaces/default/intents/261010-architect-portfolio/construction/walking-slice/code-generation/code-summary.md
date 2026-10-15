# Code Summary — U0 walking-slice

All 23 plan steps are built. S0 (`u0-repo-and-ci-baseline`) is ready to merge to `main`.
S1 to S3 (the local walking slice) are built and verified end to end on the local stack. They
are for the `slice/walking-slice` demonstration branch only, and nothing was deployed. No git
operation was performed; the conductor cuts the branches.

The results below are from the run after code review iteration 1 (`reviews/review-01.md`).
The required fixes are listed under "Code Review Iteration 1".

## Environment Found (Step 1)

| Tool | Version found | Notes |
| --- | --- | --- |
| git | 2.47.1.windows.2 | |
| Python | 3.13.5 (host) | No 3.12 on the host. 3.13 meets "3.12 or later"; the locks were compiled, and the back-end suite was also run, in `python:3.12-slim` containers (3.12.14 and 3.12.15). `.python-version` pins 3.12.14 for CI |
| Node | v22.17.0 | `.nvmrc` pins 22.17.0 |
| npm | 11.4.2 | |
| Docker | 28.5.1 (server linux/x86_64) | Available, daemon running |
| Docker Compose | v2.40.3-desktop.1 | Available |
| make | not installed | Not installed by me (owner constraint). `make slice-check` was run as its exact recipe, `python local/slice_check.py` |
| Host OS | Windows 11, Git Bash | No symbolic-link privilege (Developer Mode off); see Known Limitations |

Docker and Compose v2 were available, so S1 to S3 were built and tested fully, including the
integration tests and the slice check. Nothing was skipped for lack of Docker.

**Installs (all project-local):**
- `.venv/` (gitignored) holds `requirements.lock` and `backend/requirements-slice.lock`, installed with `--require-hashes`.
- npm packages are in `web/`, `web/slice-renderer/` and `web/slice-studio/`.
- Playwright Chromium was installed into `web/node_modules` with `PLAYWRIGHT_BROWSERS_PATH=0`.
- Pillow was installed into `.venv` only to generate the fixture image once, then uninstalled.

**Container images pulled:** `mongo:7`, `nginx:1.29-alpine`, `python:3.12-slim`, `node:22-slim`, `rhysd/actionlint:1.7.12` and `zricethezav/gitleaks:v8.30.1`.

No system software or global tool was installed, no cloud or paid service was used, and
nothing was deployed. Read-only network use was limited to:
- package registries (PyPI, npm, Docker Hub);
- `git ls-remote` to resolve action SHAs;
- the actionlint and gitleaks release checksum files.

## Commands Run and Real Results

### S0

| Command | Result |
| --- | --- |
| `python -m pytest tests/scripts --cov=scripts --cov-fail-under=80` (approved) | **150 passed**. Coverage **96.69%**: check_security_review 97%, check_workflows 95%, gate_results 98%, guard_fake_idp 97%, scan_output 97%, verify 97% |
| `ruff check .` / `ruff format --check .` | All checks passed; 75 files formatted |
| `mypy` (strict, `scripts` + `backend/portfolio_api`) | Success: no issues in 22 source files |
| `.venv\Scripts\python.exe scripts\verify.py --strict` (cmd.exe, repo root) | **Exit 0**: 26 passed, 0 failed, 2 skipped (actionlint and gitleaks, optional, not on PATH), 0 not applicable. See "Owner-requested verification entry point" |
| `npm --prefix web run format:check / lint / typecheck / test / build` | All pass. `web/site`: **5 passed**, 100% lines |
| `python -m build --wheel --no-isolation --outdir backend/dist backend` | Wheel built, no warnings (after removing a deprecated `license` table) |
| `python scripts/guard_fake_idp.py` with the built Studio present | **FAIL, as intended:** the marker is found in `web/slice-studio/dist/assets/index-*.js` (R-06) |
| `python scripts/guard_fake_idp.py backend/dist web/site/dist web/slice-renderer/dist` | OK: **25 files** scanned (wheel incl. slice API, site, renderer CLI). No traces |
| `python scripts/guard_fake_idp.py` (default targets, Studio build output removed afterwards) | OK: 25 files |
| `python scripts/check_workflows.py` | OK: 2 workflow files compliant |
| actionlint 1.7.12 (Windows binary checksum-verified; then `rhysd/actionlint:1.7.12` with shellcheck and pyflakes) | 0 errors |
| `pip-audit --disable-pip --require-hashes -r` each of the 3 locks | No known vulnerabilities |
| `npm audit --audit-level=high` (web, slice-renderer, slice-studio) | 0 vulnerabilities |
| gitleaks 8.30.1 `dir` over every created directory and root file | No leaks found |

### S1 to S3

| Command | Result |
| --- | --- |
| `python -m pytest backend/tests/unit/slice --cov=backend/portfolio_api/slice --cov=backend/portfolio_api/auth.py --cov=backend/portfolio_api/settings.py --cov-fail-under=80` (approved, Windows host) | **190 passed, 1 skipped** (the real-symlink test). Coverage **90.50%** of `slice/` only. `auth.py` and `settings.py` are **not measured** by this command (see Gaps) |
| Same tests with `--cov=portfolio_api.slice --cov=portfolio_api.auth --cov=portfolio_api.settings` (Windows host) | 190 passed, 1 skipped; **92.18%**: auth 99%, settings 100% |
| Same module-name command in `python:3.12-slim` (Linux, 3.12.15; repo mounted read-only) | **191 passed, 0 skipped**; coverage **92.54%**. mongo.py is 38% in unit runs and is exercised by the integration tests |
| `docker compose -f local/compose.yaml up -d mongo mongo-init` then `python -m pytest backend/tests/integration/slice` (approved) | **8 passed**: concurrent Publish (4 threads × 5 rounds, exactly one winner each) and the publish sequence (R-09) |
| `docker compose ... run --rm mongo-init` (second time) | "rs0 already initiated", "primary ready" (idempotent) |
| `python -m pytest local/fake-idp/tests` (approved) | **10 passed** (host and Linux container) |
| `npm --prefix web/slice-renderer exec -- vitest run --coverage` (approved, from repo root) | **Failed: 3 failed / 70 passed** over 12 files. It ran at the repo root, not the package (see Gaps) |
| `npm --prefix web/slice-renderer run test` (package-scoped equivalent) | **42 passed**; lines **98.62%** |
| `npm --prefix web/slice-renderer run check` (format, lint, tsc, test, CLI bundle) | Pass |
| `npm --prefix web/slice-studio exec -- vitest run --coverage` (approved, from repo root) | **Failed** for the same reason (3 failed / 70 passed, 12 files) |
| `npm --prefix web/slice-studio run test` (package-scoped) | **17 passed**; lines **99.23%** |
| `npm --prefix web/slice-studio run check` | Pass (format, lint, tsc, 17 tests, Vite build) |
| `docker compose -f local/compose.yaml build` / `up -d` | Built and healthy |
| Manual pass (curl): create, save, preview, publish | Works. Title escaped (`Manual &lt;check&gt;`); other subject gets 403; no token gets 401 |
| `scripts/scan_output.py` over a real release | OK: 8 files |
| `make slice-check` → `SLICE_API_PORT=8001 python local/slice_check.py` | **slice-check: OK** |

Slice-check detail (run after the review fixes):
1. Loopback-only ports asserted.
2. Stack rebuilt and started from an empty database (13.2 s).
3. Playwright **4 passed**: the W1 to W4 Studio journey, AC0.1, timings and the C9 headers.
4. Allow-list scan OK: **9 files**.

Measured timings were create 7 ms, save 5 ms, preview 3 ms and publish 101 ms, against limits of 1 s per API call and 10 s for Publish. The first run, before the fixes, also passed: 12, 14, 6 and 185 ms.

`make` is not installed, so the recipe was run directly. The API used host port 8001 because an
unrelated container (`zork-observatory`) holds 8000 (see Known Limitations). The stack was then
stopped with `docker compose -f local/compose.yaml down -v`.

## Real Code and Local-Only Fakes

**Real implementation code:**
- **S0:** `scripts/*.py`, `.github/workflows/*`, the configuration files and the `web/site` placeholder.
- **S1 and S2 back end:** `backend/portfolio_api/auth.py` and `settings.py`, plus `backend/portfolio_api/slice/`:
  - `models`, `errors`, `repositories` and `mongo`;
  - `snapshot`, `renderer` (the subprocess boundary), `site_store`, `publish` and `service`;
  - `observability`, `api` and `app`.
- **S2 renderer:** `web/slice-renderer/`.
- **S3:** `web/slice-studio/`, `web/slice-e2e/` and `local/slice_check.py`.
- **The local stack configuration:** `local/compose.yaml`, `local/nginx.conf`, `local/api.Dockerfile` and `local/mongo-init.js`.

**Local-only fakes, each with a header comment saying so:**
- `local/fake-idp/` is the fake identity provider. It carries the marker `AIDLC_LOCAL_ONLY_FAKE_IDP` and generates its ES256 key in memory at start-up. A test opens no file for writing during start-up or token issuance.
- `backend/tests/unit/slice/fakes.py` holds the in-memory repositories, a fixed renderer and the `PointerFileOps` link double. They are used only by unit tests, and `PointerFileOps` only on hosts without symlinks.
- `local/compose.env` holds placeholders only.
- `local/fixtures/` holds the placeholder image, drawn from code, with no EXIF data.

Production code contains no fake issuer URL. The settings validator holds only generic
local-class rules, and the URL lives only in `local/compose.env`.

## Paths by Bolt

`source-manifest.json` lists all 166 paths, grouped in order: S0 (59), S1 (28), S2 (50),
S3 (29). Paths added since the first build (the Codex review R1–R5 paths are listed in that
section below):

- **Review iteration 1:** `scripts/gate_results.py` and `tests/scripts/test_gate_results.py` (S0).
- **The verification entry point:**
  - `scripts/verify.py`, `scripts/verify-checks.toml`, `tests/scripts/test_verify.py` and `Makefile` (S0). `Makefile` moved from S3 to S0; its slice targets moved to `local/slice.mk`;
  - `local/slice.mk` and `local/compose.verify.yaml` (S3). The engine validates that file against a strict schema, so it cannot carry a `bolt`
field (`.claude/tools/aidlc-lib.ts`, `readUnitSourceManifest`). The boundaries are:
- **S0:** root configuration, `.github/`, `backend/README.md`, `backend/pyproject.toml`, `backend/portfolio_api/__init__.py` and `py.typed`, `contracts/`, `infra/`, `local/README.md`, `docs/security-reviews/README.md`, `scripts/`, `tests/`, `web/package*.json`, `web/eslint.config.js`, `web/.prettierignore` and `web/site/`.
- **S1:**
  - back end: `auth.py`, `settings.py`, `slice/__init__`, `errors`, `models`, `repositories` and `mongo`, plus `backend/requirements-slice.*`;
  - tests: `backend/tests/__init__.py`, `unit/__init__.py`, `unit/slice/__init__.py`, `test_auth`, `test_models`, `test_settings`, `tokens.py`, and `backend/tests/integration/**`;
  - `local/fake-idp/**`.
- **S2:**
  - back end: `slice/api`, `app`, `observability`, `publish`, `renderer`, `service`, `site_store` and `snapshot`;
  - unit tests: `conftest`, `fakes`, `test_api`, `test_observability`, `test_renderer_boundary`, `test_site_store` and `test_snapshot`;
  - `web/slice-renderer/**`;
  - local stack: `local/compose.yaml`, `compose.env`, `nginx.conf`, `api.Dockerfile` and its dockerignore, `mongo-init.js` and `local/fixtures/**`.
- **S3:** `web/slice-studio/**`, `web/slice-e2e/**`, `local/slice_check.py`, `local/.gitignore`, `local/SLICE.md`, `local/slice.mk` and `local/compose.verify.yaml`.

**Cross-Bolt dependency (from the plan's own ordering):** the S1 integration tests need the
MongoDB service from S2's `local/compose.yaml`, so they run once S2 is on the same branch.

## Gaps in the Approved Test Instructions

These are reported, not edited: the approved file was left unchanged.

1. **Back-end coverage arguments.** `--cov=backend/portfolio_api/auth.py` and `--cov=backend/portfolio_api/settings.py` are file paths. coverage.py accepts only directories or package names, so those two modules are silently not measured. The module-name form works: `--cov=portfolio_api.auth --cov=portfolio_api.settings`. CI and `local/SLICE.md` use the module-name form.
2. **TypeScript test commands.** `npm --prefix web/slice-renderer exec -- vitest run --coverage` (and the Studio twin) runs Vitest in the caller's directory with npm 11. From the repo root it collects all 12 test files with no config, and 3 site tests fail for lack of jsdom. The working, package-scoped form is `npm --prefix web/slice-renderer run test` (and the same for `web/slice-studio`).
3. **`make` is not installed on this host.**

## Key Decisions and Deviations

- **Separate dependency sets per Bolt.** To keep S0 and S1-S3 cleanly separable, the slice packages (`web/slice-renderer` and `web/slice-studio`) are standalone npm projects with their own lockfiles, and the slice back end has its own hashed `backend/requirements-slice.lock`. The Studio imports the renderer's source through a Vite alias with React and Ajv deduplicated, so preview and Publish use the same renderer (BR4.1).
- **ESLint configuration location.** `eslint.config.js` lives in `web/`, not the repo root, so its plugins resolve from `web/node_modules`.
- **Path filter.** The CI path filter is a plain `git diff` step rather than a third-party action, so it needs no extra token permission. Action SHAs come from public tags: checkout v7.0.1, setup-python v7.0.0, setup-node v7.1.0 and codeql-action v4.38.3.
- **Python locks.** All three locks pin `colorama` explicitly, so they install on Windows as well as on Linux CI.
- **Whole-site snapshots.** C2 snapshots are whole-site: each Publish includes the other projects' frozen exhibits. Reconciliation points `public` at the newest current version. The Publish lock is a `threading.Lock` (sync endpoints), not an `asyncio.Lock`; the serialization is the same.
- **Extra read routes.** `GET /slice/projects` and `GET /slice/projects/{id}` were added, both owner-protected, because the Studio list and the Reload action need them.
- **Preview images.** Preview images are returned as data addresses with the candidate, so the sandboxed frame needs no network access.
- **Link primitive.** `SiteStore` takes an injectable link primitive: real `os.symlink` plus atomic `os.replace` in production. On hosts without symlinks, the unit tests use the pointer-file double.
- **Overridable host ports.** `SLICE_*_PORT` override the host ports; the defaults are the designed 8000, 8080, 9000 and 27017.
- **Run instructions file.** The slice's run instructions are in `local/SLICE.md` (S3), and the S0 `local/README.md` points to it. Putting them in `local/README.md` would have mixed S0 and S3 content in one file.
- **Generation counter.** C2 `generation` increments per Publish, starting at 1.
- **Build bug found and fixed.** The Docker build did not copy `tsconfig.json`, so the bundled CLI used the classic JSX transform and Publish failed ("React is not defined"). The failure left the previous output in place. Fixed by setting `jsx: "automatic"` in `scripts/build-cli.mjs`.

## Code Review Iteration 1

Fixes for `reviews/review-01.md`. R-08 (the test instructions) and R-10 (the two extra read
routes against the plan and contract) are handled by the coordinator through the workflow,
and are not changed here.

| Finding | Change | Proven by |
| --- | --- | --- |
| R-01 (Major) | `.github/security-sensitive-paths.txt` now names the real layout: `settings.py`, `auth.py`, `slice/`, `web/slice-renderer/`, `web/slice-studio/src/`, `local/nginx.conf`, `local/compose.yaml`, `local/fake-idp/`, `contracts/`, `.github/`, `scripts/`, `infra/` | `test_r01_the_repository_list_covers_the_boundary_files` (22 files) and `test_r01_ordinary_files_are_not_listed` |
| R-02 (Major) | `check_security_review.py` reads the path list from the base ref. Only when the base has no list does it fall back to the head, and it prints a notice. It fails when any record for the patch identity is not READY. The `review-check` job runs the checker taken with `git show origin/$BASE_REF:scripts/...` into `$RUNNER_TEMP`, falling back to the head copy with a `::notice::` (bootstrap). The README records that the gate is protected only by the ruleset and Michael's review | `test_r02_the_list_is_read_from_the_base_not_the_head`, `..._deleting_the_list_in_the_pull_request_does_not_help`, `..._bootstrap_uses_the_head_list_with_a_notice`, `..._a_not_ready_record_beside_a_ready_one_fails`; actionlint 0 errors |
| R-03 | `JwksClient` keeps the last good key set until a refresh succeeds, and rate-limits every refresh attempt, failed or not, to one per 60 s. It still fails closed when no fresh keys exist; keys stay usable for at most 10 min | `test_r03_an_issuer_outage_causes_one_fetch_per_interval` (5 requests, 1 fetch), `..._a_failed_refresh_keeps_the_previous_keys`, `..._stale_keys_are_never_used_after_ten_minutes` |
| R-04 | One trailing dot is stripped from the host. Numeric IPv4 forms (`127.1`, `0x7f.1`, `0177.0.0.1`, `2130706433`, `0`) are parsed with inet_aton rules in code, so they behave the same on every OS, and IPv4-mapped IPv6 is unwrapped. Unspecified, reserved and multicast addresses count as local-class. `AUTH_JWKS_URL` gets the same rule and must be public https outside `APP_ENV=local` | `test_r04_trailing_dots_and_numeric_hosts_are_local_class` (14 forms), `..._public_numeric_and_trailing_dot_hosts_stay_public`, `..._malformed_numeric_hosts_are_names`, `..._jwks_url_must_be_public_https_outside_local` |
| R-05 | `--static-dir` is required and must exist, so every `assets/` file is compared byte for byte with its source. CDATA and unknown declarations are reported through `unknown_decl`; Python 3.13 routes `<![if …]>` to a comment, which is also a finding | `test_r05_static_dir_is_required`, `..._a_script_posing_as_a_hashed_asset_fails`, `..._cdata_and_unknown_declarations_fail` |
| R-06 | The marker `AIDLC_LOCAL_ONLY_FAKE_IDP` is rendered on the Studio's sign-in section (`config.ts`, `App.tsx`), so it survives bundling. The guard fails on the built Studio bundle (verified: exit 1, finding in `index-*.js`). Slice outputs are recorded as out of the CI guard's scope (see Skipped) | Studio test `marks its local-only sign-in with the fake-provider marker (R-06)`; guard run on `web/slice-studio/dist` |
| R-07 | The gate aggregation moved to `scripts/gate_results.py`. `ci.yml` checks out the repository and runs it | `tests/scripts/test_gate_results.py` (12 tests); `check_workflows.py` OK; actionlint 0 errors |
| R-09 | `SlicePublishedVersion.sequence`, taken from an atomic MongoDB counter (`slice_counters`, `$inc`) inside the serialized Publish and stored with the version. `site_version` orders by (sequence, published_at) | `test_r09_publishes_in_the_same_second_never_tie` (unit, fixed clock); `test_r09_publish_sequence_is_monotonic_and_stored` (integration) |
| R-11 | Dependabot entries for slice directories were added, then removed again under R-12 (review iteration 2): Dependabot reads `main`, and the slice code never reaches it. `.github/dependabot.yml` now lists only directories on `main` (`/` actions, `/web` npm, `/` pip), and later Bolts add an entry when their package directory lands. `tools/aidlc-observer` is untouched, and is not in the manifest | YAML parses (3 update entries); review iteration 2 R-12 |

## Owner-requested verification entry point

Michael asked for a permanent, project-wide verification command to replace the U0-only
command chain at the checkpoint. It is `scripts/verify.py`; the engine records
`.venv\Scripts\python.exe scripts\verify.py --strict`.

**Design:**

- **`scripts/verify.py`** (S0). Standard library only, strict mypy, ruff-clean. Python child
  commands use `sys.executable`; `{npm}` and `{npx}` are resolved with `shutil.which`, so
  `npm.cmd` works on Windows.
  - It streams each check's output and ends with a table: check, unit, kind, status (passed,
    failed, skipped, not applicable), seconds and reason.
  - Exit codes: 0 when nothing required failed; 1 on any failure, or with `--strict` when a
    required applicable check was skipped; 2 on usage or registry errors.
  - Options:
    - `--unit <slug>` runs only that unit's checks (the U0-specific target is `--unit walking-slice`);
    - `--kind` is repeatable;
    - `--list` shows applicability and prerequisite status without running any check (it does probe `docker info`);
    - `--strict`;
    - `--keep-running`.
- **`scripts/verify-checks.toml`** (S0). One registry, identical on `main` and the slice branch. Each `[[check]]` has:
  - `id`, `unit` and `kind` (static, unit, contract, integration, e2e or audit);
  - `argv`, `cwd`, `env`, `timeout` and `description`;
  - `applies_when`: when a path is missing, the check is *not applicable* and is not counted as a skip;
  - `requires`: `docker`, `services`, `path:`, `tool:`, `module:` and `free-port:`, which I added because the e2e check needs port 5173 free for the Vite server;
  - `required`: false for actionlint, gitleaks and the network audits.

  A new unit only adds entries.
- **Registered checks:**
  - **Project:** ruff check and format, mypy, the workflow lint, actionlint (optional), and the web workspace format, lint, typecheck, test (80% floor) and build. Also the scripts tests (80% floor), the guard's negative-fixture test, the backend wheel, the guard over the deployable outputs (`backend/dist`, `web/site/dist`, as in CI), and the optional `pip-audit`, `npm audit` and `gitleaks`.
  - **walking-slice:** the back-end unit tests, the fake issuer, the renderer and Studio `run check`, the MongoDB integration tests, the e2e slice check, and optional audits for the slice locks.
  - **Contract checks:** two walking-slice checks are tagged `contract`: the C2 schema and semantic rules plus the C11 output and CLI tests in the renderer, and the C2 allow-list model plus the C11 boundary tests in the API. They are subsets of the unit suites, run separately so they report on their own. No validator was invented for the README-only `contracts/`.
- **Data safety.** Integration and e2e checks share one isolated Compose project, `portfolio-verify`:
  - it uses `local/compose.yaml` plus `local/compose.verify.yaml` and verify-only host ports (18000, 18080, 19000, 27018), passed through `SLICE_*_PORT`, with `SLICE_IT_MONGO_URI` for the integration tests;
  - the override puts MongoDB's `/data/db` and `/data/configdb` on tmpfs (`volumes: !reset []`), so every recreated container starts with an empty database;
  - `verify.py` starts the stack once, with `up -d --build --force-recreate`, before the first check that needs it, and in a `finally` block runs `down` (containers and network only) unless `--keep-running`;
  - `compose_argv` refuses `-v`, `--volumes` and `--rmi`, and tests assert the composed argv;
  - `slice_check.py` refuses the project name `portfolio-slice`;
  - nothing it runs deletes volumes or files, except `slice_check.py` replacing its own gitignored `local/.slice-check/scan` folder.
- **`local/slice_check.py`** (S3). It honours `SLICE_COMPOSE_PROJECT`, `SLICE_COMPOSE_FILES`, the port variables and `SLICE_STACK_MANAGED`:
  - under `verify.py` it neither starts nor stops the stack;
  - standalone (`make slice-check`) it uses the same isolated project and ends with `down` (no `-v`) unless `--keep-running`;
  - its own `down -v` is removed. REL-0.2 is now met by the tmpfs database, and a new step asserts that the database is empty.
- **Makefile** (S0): `verify` and `verify-list`, plus `-include local/slice.mk`. `local/slice.mk` (S3) holds `slice-setup`, `slice-verify` (`--unit walking-slice`), `slice-check`, and `slice-down`, which stays the explicit, manually invoked cleanup of the developer's demo stack.

**Changes from the coordinator's design:**

- **Makefile split.** The Makefile became an S0 file with an optional include, so S0 and S3 never share a file.
- **Extra prerequisites.** `module:` and `free-port:` were added as prerequisite kinds.
- **Compose commands echoed.** The verifier prints its Compose command lines, so the teardown argv appears in the log.
- **Base compose fix.** `mongo-init` in `local/compose.yaml` now has tmpfs at `/data/db` and `/data/configdb`. Without it, every start of either stack left two anonymous volumes, because the mongo image declares those paths as volumes and `down` without `-v` keeps them.

**Leftover releases with an empty database.** The `site` volume of `portfolio-verify` keeps
releases between runs. Tested two ways:
- in a unit test, `test_empty_database_with_leftover_releases_reconciles_and_publishes`: `public` returns to the placeholder, and a new Publish serves only the new release, at generation 1;
- live: the `--unit walking-slice` run and the standalone run started on the previous run's releases with an empty database, and the e2e check and the scan of the new release passed.

No code change was needed.

**Runs (cmd.exe, repo root):**

| Run | Exit | Result |
| --- | --- | --- |
| `scripts\verify.py --strict` (final code; run three times in total, all exit 0) | 0 | 26 passed, 0 failed, 2 skipped (actionlint, gitleaks: optional, not on PATH), 0 not applicable; e2e timings create 8, save 9, preview 7, publish 209 ms; scan OK (9 files); teardown `docker compose -p portfolio-verify -f … -f … down` |
| `scripts\verify.py --unit walking-slice` | 0 | 11 passed, 0 failed, 0 skipped |
| `scripts\verify.py --list` | 0 | 28 checks; every check applies; actionlint and gitleaks not on PATH |
| `python local/slice_check.py` (standalone) | 0 | 5 steps passed; own `up` and `down`, no `-v` |
| `SLICE_COMPOSE_PROJECT=portfolio-slice python local/slice_check.py` | 2 | Refused |

**Docker resources:**

- **Before:** no `portfolio-slice` or `portfolio-verify` containers, and 73 volumes, none named `portfolio*`.
- **After every run:** `portfolio-slice` was never created or touched (`ps -a` empty), and no `portfolio*` containers remain.
- **Volumes now:** the 73 earlier ones, plus `portfolio-verify_site` (persistent, by design), plus the two anonymous volumes the first run leaked (`b9d8a16a…` and `fee48e01…`) before the `mongo-init` fix. They are empty and unused, and were left in place under the no-volume-removal rule; Michael may remove them with `docker volume rm`.
- **Later runs:** no volume changes.

## Codex review R1–R5

An independent Codex engineering review of U0 (`REVIEW-U0.md`, written against an older
snapshot, before `verify.py`) raised five findings. Each was confirmed against the current
code, fixed, given regression tests and re-verified. This section supersedes the fixed
`portfolio-verify` project and fixed verify-only ports described under "Owner-requested
verification entry point" above.

### R1 — Docker cleanup and isolation

Confirmed: `verify.py` and `slice_check.py` used the fixed project `portfolio-verify` and fixed
ports 18000/18080/19000/27018 (and Vite on 5173), so two worktrees shared one stack, and
`up --force-recreate` in one could disrupt the other. Codex's `down -v` finding was already
gone; CI's python job still ran `docker compose -f local/compose.yaml ... down -v` on the
default `portfolio-slice` project.

- **`scripts/compose_isolation.py` (new, S0)**, shared by both scripts:
  - the project is `portfolio-verify-<first 10 hex of sha256(normcase(resolved checkout path))>`
    (this checkout: `portfolio-verify-dab46a7030`); `portfolio-slice`, a bare
    `portfolio-verify-` and any name not starting with `portfolio-verify-` are refused;
  - free loopback ports per run (bind `127.0.0.1:0`, also checked free on `::1`);
  - an exclusive OS file lock per checkout, `.verify-work/verify.lock` (gitignored; released by
    the OS if the process dies, so no stale locks); a second run exits 2 at once;
  - every compose argv is refused if it contains `-v`, `--volumes`, `--rmi`, `--remove-orphans`,
    `prune` or the `rm` subcommand. Teardown is a plain `down`.
- **`scripts/verify.py`**: `[services]` no longer accepts `project`; it declares `ports`
  (`SLICE_API_PORT`, `SLICE_SITE_PORT`, `SLICE_IDP_PORT`, `SLICE_MONGO_PORT`, `SLICE_STUDIO_PORT`),
  and `{project}`/`{PORT}` placeholders fill `SLICE_COMPOSE_PROJECT`, `SLICE_IT_MONGO_URI` and the
  ready URLs. A `{compose}` argv placeholder (argv[0] only, services required) gives a check the
  isolated compose prefix; the arguments after it are checked for forbidden flags too.
- **`local/slice_check.py`**: same project rule, free ports for any port the caller did not pass,
  the same lock when standalone, `SLICE_STUDIO_PORT` for the Vite dev server; under
  `SLICE_STACK_MANAGED=1` it requires every port from the caller.
- **`local/compose.verify.yaml`**: `CORS_ORIGIN` for the API and the fake issuer follows
  `SLICE_STUDIO_PORT`; **`web/slice-e2e/playwright.config.ts`** starts Vite on that port. The
  `free-port:5173` prerequisite was removed from `slice-e2e`.
- **CI**: the python job's integration step (`down -v` on `portfolio-slice`) was removed; the
  integration tests now run in the `slice-e2e` job through `verify.py`.
- The per-checkout `site` volume (`portfolio-verify-<id>_site`) is reused across runs; MongoDB is
  on tmpfs. The existing unit test `test_empty_database_with_leftover_releases_reconciles_and_publishes`
  is kept and passes.

Regression tests:

- `tests/scripts/test_verify.py`: `test_r1_every_compose_argv_uses_the_checkout_project_and_no_forbidden_flag`
  (start, `{compose}` run, teardown; readiness URLs and check env use the chosen ports),
  `test_r1_worktrees_get_different_projects`, `test_r1_protected_and_foreign_projects_are_refused`
  (5 names), `test_r1_compose_argv_refuses_data_removing_arguments`,
  `test_r1_a_compose_check_with_a_forbidden_flag_fails_without_running`,
  `test_r1_ports_that_cannot_be_isolated_fail_the_check`, `test_r1_a_second_run_in_the_same_checkout_fails_clearly`,
  `test_r1_lock_is_exclusive_and_released`, `test_r1_free_loopback_ports_are_distinct_numbers`.
- `local/tests/test_slice_check.py` (new, S3): `test_r1_every_compose_argv_is_isolated_for_start_readiness_exec_and_teardown`
  (config, up, exec ×3, cp, down; readiness URLs), `test_r1_the_project_is_derived_per_checkout`,
  `test_r1_protected_and_foreign_projects_are_refused` (4 names, also through `main`),
  `test_r1_free_ports_are_chosen_and_given_ports_are_kept`, `test_r1_a_managed_stack_needs_every_port_from_the_caller`,
  `test_r1_a_managed_stack_is_neither_started_nor_stopped`, `test_r1_keep_running_prints_the_plain_down_command`,
  `test_r1_the_stack_refuses_data_removing_arguments` (5 flags), `test_r1_a_second_run_in_the_same_checkout_fails_clearly`.
- `tests/docker/test_services_isolation.py` (new, S0), registered as check
  `verify-docker-isolation` (kind integration, requires docker):
  `test_r1_a_services_cycle_keeps_every_volume_and_other_projects_containers`. It records
  `docker volume ls -q` and every other project's containers, runs the real services cycle
  (up, readiness, down) under project `portfolio-verify-<id>-isotest` and lock
  `verify-isotest.lock` (it runs inside a `verify.py` run that holds the main lock and stack,
  which counts as an "other project"), then asserts every earlier volume exists, no other
  container was removed or stopped, its own containers are gone and its `site` volume is kept.

### R2 — CI false passes and test-level skips

Confirmed: `gate_results.py` read `outputs.get(job) == "true"` and had no inventory.

- **`scripts/gate_results.py`**: `EXPECTED_JOBS` (changes, python, web, guard, audit, slice-e2e,
  workflow-lint, review-check, gitleaks); a missing or unexpected job fails. `PATH_GATED` maps each
  path-gated job to its output (`slice-e2e` → `slice_e2e`); each output must be exactly `"true"` or
  `"false"`, otherwise `changes` fails and the job is treated as required. `review-check` may be
  skipped only on `push` (an unknown event fails closed).
- **`scripts/check_workflows.py`**: for `ci.yml`, the gate's `needs:` must equal `EXPECTED_JOBS`,
  every other job must be in it, `changes` must declare each path-gated output, and each path-gated
  job's `if:` must test that output `== 'true'`. Every `actions/checkout` must set
  `persist-credentials: false`.
- **Test-level skips in `scripts/verify.py`**: a check with `report = "junit"` gets
  `PYTEST_ADDOPTS=--junitxml=".verify-work/junit/<id>.xml"` (forward slashes, so the shell-style
  split keeps Windows paths) and `VERIFY_JUNIT`, which the three Vitest configs read to add the
  `junit` reporter (`web/site`, `web/slice-renderer`, `web/slice-studio`). After exit 0, the report
  must exist and list at least one test; a skipped test fails the check under `--strict` unless
  `allowed_skips` lists it with a reason (and platform). Every pytest and Vitest check reports; the
  only allowed skip is `test_public_is_a_relative_symbolic_link` on `win32`. The containerized
  integration check writes its report through a bind mount of `.verify-work/junit`.

Regression tests:

- `tests/scripts/test_gate_results.py`: `test_r2_codex_reproduction_missing_outputs_no_longer_pass`,
  `test_r2_missing_job_fails_the_gate`, `test_r2_unexpected_job_fails_the_gate`,
  `test_r2_missing_outputs_fail_the_gate_even_when_every_job_succeeded`,
  `test_r2_one_missing_output_marks_its_job_required`, `test_r2_malformed_booleans_fail_the_gate`
  (`yes`, `""`, `TRUE`, `False`, `" true"`, `1`, null, JSON true, JSON 1),
  `test_r2_skipped_always_required_job_fails`, `test_r2_cancelled_path_gated_job_fails_even_when_not_needed`,
  `test_ac0_10_failed_or_cancelled_jobs_fail_the_gate`, `test_ac0_10_failed_change_detection_fails_the_gate`,
  `test_r2_failed_change_detection_with_valid_outputs_still_fails`,
  `test_r2_push_and_pull_request_judge_path_gated_jobs_the_same`, `test_ac0_10_review_check_skip_is_allowed_only_on_push`.
- `tests/scripts/test_check_workflows.py`: `test_r2_a_consistent_ci_gate_passes`,
  `test_r2_the_repository_gate_needs_every_job_and_slice_e2e`, `test_r2_a_job_missing_from_the_gate_needs_fails`,
  `test_r2_a_job_outside_the_inventory_fails`, `test_r2_a_gate_needing_an_unknown_job_fails`,
  `test_r2_missing_output_and_wrong_condition_fail`, `test_r2_ci_without_a_gate_fails`,
  `test_r2_gate_needs_as_a_single_string_is_read`, `test_r4_checkout_must_not_persist_credentials`.
- `tests/scripts/test_verify.py`: `test_r2_a_skipped_test_fails_strict_and_is_reported_otherwise`,
  `test_r2_an_allowed_skip_passes_strict_only_on_its_platform`, `test_r2_missing_broken_or_empty_reports_fail`,
  `test_r2_a_failing_command_is_not_judged_by_its_report`, `test_r2_the_report_variables_reach_the_command`,
  `test_r2_real_pytest_skips_are_caught_under_strict` (a real pytest run with a skipped test),
  `test_read_junit_handles_a_single_testsuite_root`, `test_repository_registry_is_valid_and_never_removes_data`
  (every pytest check reports).

### R3 — Unauthorized image bytes

Confirmed: `scan_output.py` checked only the magic prefix and the EXIF marker.

- **`local/fixtures/derivatives.sha256.json` (new, S2)**: trusted SHA-256 of
  `media/ast_SliceFixtureImage0001/w480.jpg` (`a79bd7be…`) and `w480.webp` (`f68b3a7f…`), computed
  once from the committed images. `local/fixtures/make_fixture.py` now writes it with the images.
- **`scripts/scan_output.py`**: required `--media-digests`; every `media/` and `files/` file must
  match the digest for its exact release key, and a file with no entry is a finding. `scan_file`
  without digests authorizes nothing (fail closed). The type and EXIF checks remain.
- **`local/slice_check.py`** passes `--media-digests local/fixtures/derivatives.sha256.json`.

Regression tests: `tests/scripts/test_scan_output.py` (synthetic, S0):
`test_r3_appended_private_note_is_a_finding`, `test_r3_changed_pixels_are_a_finding`,
`test_r3_non_exif_metadata_is_a_finding` (JPEG COM segment), `test_r3_trailing_data_after_the_end_marker_is_a_finding`,
`test_r3_a_media_file_without_a_digest_entry_is_a_finding`, `test_r3_without_a_manifest_no_media_is_authorized`,
`test_r3_a_digest_for_another_key_does_not_authorize_the_file`, `test_r3_downloads_need_an_authorized_digest_too`,
`test_r3_clean_authorized_derivatives_pass`, `test_r3_the_manifest_is_validated`,
`test_r3_main_requires_and_checks_the_manifest`. `local/tests/test_slice_check.py` (real fixture, S3):
`test_r3_codex_reproduction_on_the_real_fixture`, `test_r3_committed_digests_match_the_fixture_derivatives`,
`test_r3_the_scan_gets_the_authorized_media_digests`.

### R4 — End-to-end journey as a required CI job

Confirmed: no CI job ran Playwright or the scan, and the gate had no end-to-end dependency.

- **`.github/workflows/ci.yml`**: job `slice-e2e` on `ubuntu-24.04`, `permissions: contents: read`,
  head-SHA checkout with `persist-credentials: false`, SHA-pinned actions, 30 min. It installs
  `requirements.lock`, runs `npm ci` in `web` (Playwright comes from `web/package-lock.json`; the
  spec has no package of its own), `web/slice-renderer` and `web/slice-studio`, installs Chromium
  with `npx playwright install --with-deps chromium` (`PLAYWRIGHT_BROWSERS_PATH=0`), then runs
  `python scripts/verify.py --strict --kind e2e --kind integration` (slice-integration,
  verify-docker-isolation, slice-e2e).
- **`changes`** outputs `slice_e2e`: `"false"` when `local/compose.yaml` is absent (main after S0),
  even when the forcing rule turns the other jobs on; otherwise `"true"` when `backend/`,
  `web/slice-*`, `web/package*.json`, `local/`, `scripts/`, `tests/docker/`, `.github/`,
  `requirements*`, a lockfile, `.python-version` or `.nvmrc` changed, or when there is no usable
  base. The gate needs `slice-e2e` and judges it under the R2 rules.

Regression tests: `tests/scripts/test_ci_changes.py` (new, S0) runs the real `detect` script from
`ci.yml` with bash in throwaway git repositories: `test_r4_slice_paths_turn_slice_e2e_on_where_the_slice_exists`,
`test_r4_each_slice_dependency_turns_slice_e2e_on` (6 paths), `test_r4_unrelated_changes_leave_every_job_off`,
`test_r4_forcing_changes_never_turn_slice_e2e_on_without_the_slice`, `test_r4_forcing_changes_turn_slice_e2e_on_with_the_slice`,
`test_r4_a_push_without_a_usable_base_forces_jobs_only_where_the_slice_exists`; plus the R2 workflow tests above.
actionlint 1.7.12 (the locally present `rhysd/actionlint:1.7.12` image, with shellcheck): exit 0.

### R5 — Real MongoDB fault-injection tests

Confirmed: no integration test made a later write fail after an earlier one succeeded.

**`backend/tests/integration/slice/test_publish_faults.py` (new, S1).** Faults are injected
*inside* the real transactions by wrapping one collection handle that delegates to the real
collection and raises only at the chosen operation; a recording wrapper proves the earlier write
really ran.

- `test_r5_ac0_7_a_failed_version_insert_rolls_back_the_pointer_update` (AC0.7, REL-0.1, BR3.1):
  `commit_publish` updates the pointer first (`matched 1, modified 1` recorded), then the insert
  hits a pre-inserted document with the same id (E11000); pointer, revision and both collections
  are unchanged.
- `test_r5_ac0_9_a_failed_commit_writes_nothing_public`: the same collision through Publish; the
  new release folder is removed and `public` still serves the previous release.
- `test_r5_ac0_9_compensation_with_a_failed_delete_rolls_back_and_is_surfaced`: compensation is
  one transaction (restore pointer, then delete version). The restore really applies, the delete
  raises an injected `OperationFailure`; `compensate` raises `DatabaseUnavailableError`, the restore
  is rolled back (state unchanged and consistent), and a retry with the real repository converges.
- `test_r5_ac0_9_swap_failure_compensates_and_a_restart_agrees`: the commit succeeds, the real
  symlink swap fails, compensation restores the previous version; a fresh service (restart)
  reconciles and the database's current version equals the served `public` release.
- `test_r5_ac0_9_swap_and_compensation_failures_are_repaired_on_restart`: swap and compensation
  both fail; Publish raises `PublishFailedError`, the log records "compensation failed", the
  database still names the new version while `public` serves the old one; a restart reconciles
  `public` to the new version.

**Where they run.** Real symbolic links are unavailable on this Windows host, so the tests skip
there. `slice-integration` now runs the whole integration suite in a Linux container on the
verification stack's network: Compose service `slice-it` (profile `tests`) in
`local/compose.verify.yaml`, image `local/it.Dockerfile` (new, S3; the digest-pinned
`python:3.12-slim`, both hashed locks, user 10001 or the POSIX caller's uid), `backend/` mounted
read-only, only the JUnit folder writable, run with `docker compose ... --profile tests run --rm
--no-deps --build -T slice-it`. The image declares no volumes, so `--rm` removes only that one-off
container. It is the same command on every host and in CI, the simplest reliable option: no
symlink privilege needed, no second Python setup, and strict mode sees 13 tests and 0 skips.

### Commands run and results (this host, cmd.exe at the repository root)

| Command | Result |
| --- | --- |
| `ruff check .` / `ruff format --check .` / `mypy` | All passed; mypy: no issues in 23 source files (`mypy.ini` adds `scripts` to `mypy_path`) |
| `python -m pytest tests/scripts --cov=scripts --cov-fail-under=80` | 223 passed, coverage 96.76% (before `test_ci_changes.py` was added; 234 tests in the strict run) |
| `python -m pytest local/tests` | 19 passed |
| `.venv\Scripts\python.exe scripts\verify.py --strict` | **Exit 0**: 28 passed, 0 failed, 2 skipped (actionlint, gitleaks: optional, not on PATH), 0 not applicable |
| Codex's R2 reproduction (`NEEDS_JSON` without outputs, skipped python/web/guard/audit) | **Exit 1**: failing because of changes, python, web, guard, audit, slice-e2e |
| Codex's R3 reproduction (real `w480.jpg` + appended note) | Finding: "bytes differ from the authorized derivative (sha256 456fb83c0f45..., authorized a79bd7beac54...)"; the 4-argument call reports "no authorized derivative digest for this file" |
| Second `verify.py` while another ran in this checkout | **Exit 2**: "another verification run is using this checkout (lock ...\.verify-work\verify.lock is held)"; the first run finished with exit 0 |
| `docker volume ls -q` / `docker ps -a` before and after the strict run | 78 volumes and 5 containers (all running) before and after; sorted-list SHA-256 identical (`3e1eaeae…` volumes, `35154792…` containers) |

Strict run summary:

| check | unit | kind | status | seconds | reason |
| --- | --- | --- | --- | --- | --- |
| ruff-check | project | static | passed | 0.1 | |
| ruff-format | project | static | passed | 0.1 | |
| mypy | project | static | passed | 0.7 | |
| workflow-lint | project | static | passed | 0.2 | |
| actionlint | project | static | skipped | 0.0 | actionlint not on PATH (optional) |
| web-format | project | static | passed | 0.6 | |
| web-lint | project | static | passed | 4.1 | |
| web-typecheck | project | static | passed | 2.2 | |
| scripts-tests | project | unit | passed | 31.3 | 234 tests |
| guard-negative-fixture | project | unit | passed | 1.0 | 15 tests |
| web-test | project | unit | passed | 3.0 | 5 tests |
| web-build | project | static | passed | 2.4 | |
| backend-wheel | project | static | passed | 1.7 | |
| guard-build-outputs | project | static | passed | 0.2 | |
| slice-backend-unit | walking-slice | unit | passed | 7.1 | 192 tests; 1 allowed skip on win32: test_public_is_a_relative_symbolic_link |
| slice-fake-idp | walking-slice | unit | passed | 3.0 | 10 tests |
| slice-check-unit | walking-slice | unit | passed | 1.0 | 19 tests |
| slice-renderer-check | walking-slice | unit | passed | 12.2 | 42 tests |
| slice-studio-check | walking-slice | unit | passed | 21.1 | 17 tests |
| slice-c2-c11-contract-ts | walking-slice | contract | passed | 2.2 | 42 tests |
| slice-c2-c11-contract-py | walking-slice | contract | passed | 2.8 | 21 tests |
| slice-integration | walking-slice | integration | passed | 6.2 | 13 tests |
| verify-docker-isolation | project | integration | passed | 18.1 | 1 tests |
| slice-e2e | walking-slice | e2e | passed | 9.8 | |
| pip-audit | project | audit | passed | 2.2 | |
| npm-audit-web | project | audit | passed | 1.5 | |
| gitleaks | project | audit | skipped | 0.0 | gitleaks not on PATH (optional) |
| slice-pip-audit | walking-slice | audit | passed | 1.8 | |
| slice-npm-audit | walking-slice | audit | passed | 1.4 | |
| slice-npm-audit-studio | walking-slice | audit | passed | 1.3 | |

### New paths by Bolt

- **S0:** `scripts/compose_isolation.py`, `tests/scripts/test_ci_changes.py`, `tests/docker/conftest.py`,
  `tests/docker/pytest.ini`, `tests/docker/test_services_isolation.py`.
- **S1:** `backend/tests/integration/slice/test_publish_faults.py`.
- **S2:** `local/fixtures/derivatives.sha256.json`.
- **S3:** `local/it.Dockerfile`, `local/it.Dockerfile.dockerignore`, `local/tests/conftest.py`,
  `local/tests/pytest.ini`, `local/tests/test_slice_check.py`.

Changed existing paths: S0 `scripts/verify.py`, `scripts/verify-checks.toml`, `scripts/gate_results.py`,
`scripts/check_workflows.py`, `scripts/scan_output.py`, `.github/workflows/ci.yml`, `.gitignore`
(`.verify-work/`), `mypy.ini`, `README.md`, `web/site/vitest.config.ts`, and the tests in
`tests/scripts/`; S1 `backend/tests/integration/slice/conftest.py` (docstring); S2
`local/fixtures/make_fixture.py`, `web/slice-renderer/vitest.config.ts`; S3 `local/slice_check.py`,
`local/compose.verify.yaml`, `local/SLICE.md`, `local/slice.mk`, `web/slice-e2e/playwright.config.ts`,
`web/slice-studio/vitest.config.ts`. S0 files only refer to slice files through `applies_when`
gates or the `[ -f local/compose.yaml ]` test in CI.

### The initial empty release

There is no committed `releases/empty/` placeholder. `SiteStore.ensure_initial()`
(`backend/portfolio_api/slice/site_store.py`) creates `releases/empty/index.html` ("New work is
being installed.") and `404.html` in the site volume when the folder is missing, and points
`public` at it when no link exists. `PublishService` calls it on every reconcile: at API start-up
and at the start of every Publish.

### Not done or not demonstrable locally

- The `slice-e2e` CI job and the new gate have not run on GitHub; nothing was pushed. Evidence
  comes from the pull requests the conductor opens.
- actionlint and gitleaks are not on PATH, so the registry skips them (optional). actionlint was
  run separately from its local image (exit 0).
- The two parallel-worktree case was exercised through the derivation tests and the lock, not by
  creating a second worktree.
- The earlier fixed-project volume `portfolio-verify_site` and the two anonymous volumes from the
  first run are still present (no volume is removed automatically). This work added
  `portfolio-verify-dab46a7030_site` and `portfolio-verify-dab46a7030-isotest_site`, both kept
  and reused.

## GitHub CI Evidence (Draft Pull Requests)

The conductor committed the Bolts and opened draft pull requests against `main`. None is merged.

| Pull request | Head | Contents |
|---|---|---|
| #13 `u0-repo-and-ci-baseline` | `02b2f96` | S0 |
| #14 walking slice, "demonstration, do not merge" | `7dbb869` (S1), `425b81a` (S2), `f11464f` (S3), `661448b` (CodeQL fix) | S0 plus S1 to S3 |

**First CI runs:**
- **#14 at `f11464f`.** These passed: `changes`, `python`, `web`, `guard`, `audit`, `workflow-lint` and both CodeQL analyses. `slice-e2e` also passed: the full Docker stack, the Playwright create → save → preview → publish journey and the release scan, in 2 min 26 s. The gate failed only on `review-check`, as expected, because no security record had been committed yet.
- **#13.** The path-gated jobs passed and `slice-e2e` was correctly skipped (`slice_e2e=false`, no slice code). The gate failed only on `review-check`, as expected.

**Gate negative controls (Codex R2), PRs #15 to #18.** Each throwaway PR, branched off S0, broke one gate input. In every case the real `gate` job failed and named the intended reason, in addition to `review-check`:

| Variant | The gate's reason |
|---|---|
| A, malformed output | `output python='yes' is not 'true' or 'false'` |
| B, missing output | `output audit=None …`; `audit` skipped but required |
| C, skipped required job | `python` `FAILED (skipped, required)` |
| D, job missing from `needs` | `audit` `FAILED (missing, required; not in NEEDS_JSON)` |

All four PRs are closed without merging and their branches are deleted.

**CodeQL `js/polynomial-redos` (High), found on #14 and fixed.**
- **Where:** `web/slice-renderer/src/variants.ts` `downloadName` trimmed hyphens with the anchored regexes `/^-+|-+$/` and `/-+$/`.
- **Fix (`661448b`):** they are replaced by a linear `trimHyphens` loop, so the output is unchanged.
- **Test:** `slugs hostile hyphen-heavy labels in linear time` in `validate.test.ts`. The renderer `run check` passes with 43 tests at 98.67% lines.
- **The Python twins** (`scan_output.download_name`, `models` slug) use `str.strip("-")`, which runs in linear time.

## Security re-review findings

An independent security re-review of PR #13 (`bolt/u0-repo-and-ci-baseline`) and PR #14
(`slice/walking-slice`) returned READY with Medium and Low findings. Six are fixed here, each
with regression tests. S0-2, S0-6 and SL-2 are tracked by the conductor as follow-up
corrections and were not changed. The conductor's CodeQL `js/polynomial-redos` fix in
`web/slice-renderer/src/variants.ts` (and its test in `validate.test.ts`) is kept as it was.
This round added no new paths, so `source-manifest.json` is unchanged.

| Finding | Change | Regression tests |
| --- | --- | --- |
| S0-1 (Medium) | `scripts/check_security_review.py` uses `git patch-id --verbatim` (git 2.39 or later; it implies `--stable`) instead of `--stable`, which dropped whitespace. `docs/security-reviews/` stays excluded. The content-identical rebase rule still holds: `test_ac0_11_content_identical_rebase_still_passes` passes unchanged. `docs/security-reviews/README.md` updated | `test_s0_1_whitespace_only_changes_need_a_new_review` (4 cases: Python indentation, YAML indentation, a space inside a string, a tab inside a string). Each asserts the new identity differs, the check fails, and the old `--stable` identity would have been unchanged |
| S0-3 (Medium) | `.github/security-sensitive-paths.txt` adds `.pip-audit-ignore`, `backend/pyproject.toml`, `**/requirements*.in`, `**/requirements*.lock`, `**/package-lock.json`, `local/compose.env`, `local/compose.verify.yaml`, `local/fixtures/derivatives.sha256.json`, `local/slice_check.py`, `local/*.Dockerfile`, `local/*.Dockerfile.dockerignore`, `local/fake-idp/Dockerfile` and `backend/tests/` | `test_r01_the_repository_list_covers_the_boundary_files` gains 20 paths, covering every new entry (the three npm locks, the root, back-end and fake-issuer locks and inputs, the Dockerfiles and two back-end tests); `test_r01_ordinary_files_are_not_listed` still passes |
| S0-4 (Low) | `scripts/compose_isolation.py` normalises each argument: `--flag=value` is read as `--flag`; combined short flags are expanded, so `-tv`, `-fsv` and `-v=true` contain `-v`. `rm`, `prune`, `volume`, `volumes` and `system` are refused wherever they appear, including after global options such as `--profile x` | `tests/scripts/test_verify.py`: `test_s0_4_differently_spelled_forbidden_arguments_are_refused` (14 forms, each checked directly and through a verify.py `{compose}` check that must fail without running Docker); `test_s0_4_the_commands_verification_uses_are_still_allowed` (6). `local/tests/test_slice_check.py`: `test_s0_4_differently_spelled_forbidden_arguments_are_refused` (11 forms through `Stack.compose`); `test_s0_4_every_command_the_check_runs_is_still_allowed` |
| S0-5 (Low) | `scripts/check_workflows.py`: `write-all`, `read-all` or any other string fails at any level. The top level may grant only `contents: read`, and so may every job, except the explicit allow-list `JOB_PERMISSIONS[("codeql.yml", "analyze")]` = `contents: read`, `security-events: write`, `actions: read`. A path-gated job's `if:` must equal `needs.changes.outputs.<x> == 'true'` exactly | `test_s0_5_a_path_gated_condition_must_match_exactly` (4, including `... \|\| always()`), `test_s0_5_write_all_and_read_all_fail_at_any_level` (4), `test_s0_5_a_job_may_only_read_contents` (5), `test_s0_5_the_top_level_may_only_read_contents`, `test_s0_5_only_the_codeql_analyze_job_gets_its_extra_scopes`; the repository's own two workflows still pass |
| SL-1 (Low) | `backend/portfolio_api/slice/api.py`: no owner route declares a FastAPI body parameter any more; FastAPI would parse that before any dependency. Each body is `Depends(owner_body(Model))`, a dependency that itself depends on `require_owner`, then reads the body (refused over 64 KiB), validates it and turns errors into the usual 422 `VALIDATION_FAILED` | `test_sl_1_refused_callers_get_401_or_403_whatever_the_body` (6 owner routes × 5 bodies, each sent with all 9 bad-token cases: malformed JSON, not JSON, wrong shape, an array, a 200 KB body). Each case asserts 401 (403 for another subject), that no handler or service runs, and that `Request.body` was never called. Also `test_sl_1_every_owner_route_reads_its_body_only_after_authentication` (no route has FastAPI body parameters) and `test_sl_1_the_owner_still_gets_422_for_bad_bodies` |
| SL-3 (Low) | The fake issuer (`local/fake-idp/fake_idp/app.py`) adds `TrustedHostMiddleware` for `localhost`, `127.0.0.1` and `fake-idp.invalid`, on any port. The API reads `ALLOWED_HOSTS` (`backend/portfolio_api/settings.py`). With `APP_ENV=local` and no setting it defaults to `localhost`, `127.0.0.1` and `api` (the Compose service name). In any other environment a missing setting refuses start-up, and wildcards, ports and URLs are refused. `create_app` refuses an empty or `*` list and adds `TrustedHostMiddleware` outermost | Fake issuer: `test_sl_3_allowed_hosts_are_served` (5), `test_sl_3_a_foreign_host_gets_400_and_no_token` (5 hosts × 3 paths). API: `test_sl_3_a_foreign_host_gets_400_before_anything_runs` (4 hosts × 7 routes, with the owner's token; no handler runs), `test_sl_3_allowed_hosts_are_served` (3), `test_sl_3_create_app_refuses_an_empty_or_wildcard_allow_list`, `test_sl_3_local_settings_allow_the_compose_service_name`. Settings: `test_sl_3_a_missing_allow_list_outside_local_mode_refuses_start_up` (4), `test_sl_3_local_mode_defaults_to_loopback_and_the_service_name`, `test_sl_3_an_explicit_allow_list_is_used_as_given`, `test_sl_3_wildcards_ports_and_urls_are_refused` (4). The end-to-end slice check passes with both allow-lists active |

Test setup changes: the fake issuer's tests use `base_url="http://localhost"`. The API test
settings set `allowed_hosts=("testserver", "localhost")`, and `BASE_ENV` in the settings tests
sets `ALLOWED_HOSTS`.

**Results (cmd.exe, repository root):**

- `.venv\Scripts\python.exe scripts\verify.py --strict`: **exit 0**, "verify: OK (28 passed, 0
  failed, 2 skipped, 0 not applicable)". The two skips are actionlint and gitleaks (optional,
  not on PATH). Test counts from the reports:
  - scripts-tests 293;
  - slice-backend-unit 243 (1 allowed win32 skip);
  - slice-fake-idp 20;
  - slice-check-unit 31;
  - slice-integration 13 (0 skips);
  - verify-docker-isolation 1;
  - slice-e2e passed.
- **Coverage:**
  - `tests/scripts --cov=scripts`: 293 passed, **97%** total. Per module: check_security_review
    97%, check_workflows 97%, compose_isolation 92%, gate_results 99%, guard_fake_idp 97%,
    scan_output 97%, verify 97%.
  - Back-end unit tests with `--cov=portfolio_api.slice --cov=portfolio_api.auth
    --cov=portfolio_api.settings`: 242 passed, 1 skipped (that run was before the last test
    was added), **92.36%** (api.py 99%, app.py 87%).
- ruff, ruff format and strict mypy are clean.
- `docker volume ls -q` and `docker ps -a` before and after the run: 78 volumes; the
  sorted-list SHA-256 of each is identical.

**Changed files in this round, by Bolt** (no new paths):

- **S0:**
  - `scripts/check_security_review.py`
  - `scripts/compose_isolation.py`
  - `scripts/check_workflows.py`
  - `.github/security-sensitive-paths.txt`
  - `docs/security-reviews/README.md`
  - `tests/scripts/test_check_security_review.py`
  - `tests/scripts/test_verify.py`
  - `tests/scripts/test_check_workflows.py`
- **S1:**
  - `backend/portfolio_api/settings.py`
  - `backend/tests/unit/slice/test_settings.py`
  - `local/fake-idp/fake_idp/app.py`
  - `local/fake-idp/tests/test_fake_idp.py`
- **S2:**
  - `backend/portfolio_api/slice/api.py`
  - `backend/portfolio_api/slice/app.py`
  - `backend/tests/unit/slice/test_api.py`
  - `backend/tests/unit/slice/conftest.py`
- **S3:** `local/tests/test_slice_check.py`

## Skipped

- **One unit test on this Windows host.** `test_public_is_a_relative_symbolic_link` cannot run here, because the host cannot create symbolic links. It passed in the Linux container run (191 passed, 0 skipped).
- **CI on GitHub.** Superseded: CI has since run on GitHub (see "GitHub CI Evidence" above). Before that, the AC0.10 evidence was local:
  - the gate's aggregation logic is `scripts/gate_results.py`, unit-tested in `tests/scripts/test_gate_results.py` for success, skipped (needed and not needed), failed, cancelled, failed change detection and push-event cases;
  - actionlint, with shellcheck, and `check_workflows.py` pass on both workflows;
  - every component command was run locally.
- **CodeQL.** CodeQL cannot run locally.
- **Slice outputs are out of the CI guard's scope (R-06).** The CI `guard` job builds and scans the deployable S0 outputs: the backend wheel and `web/site`. The slice renderer CLI and the Studio bundle are not built there, because S1 to S3 never merge to `main` and are never deployed. A local scan does cover them, and the built Studio is flagged by its marker.

## Tracked Corrections (Carried Forward, Not Silently Accepted)

| ID | Severity | Item | Where it is resolved |
|---|---|---|---|
| S0-2 | Medium | A pull request supplies its own `ci.yml` and `gate_results.py`. These are protected only by the `main` ruleset and Michael's review. | CI Pipeline stage, together with the agent GitHub identity (team practice "Target control") |
| N-1 | Low | The workflow lint does not require `gate` to have `if: always()`, and does not refuse `continue-on-error`. | CI Pipeline stage |
| N-2 | Low | The path list misses `web/**/package.json`, the Vitest and Vite configuration files, `tests/scripts/`, `local/tests/`, `local/mongo-init.js`, `Makefile` and `local/slice.mk`. | CI Pipeline stage (the path list is still marked provisional) |
| S0-6 | Low | The scan does not check tag or attribute names, empty attribute values or non-string JSON values. The guard opens only one nested zip level. | The U8 publication scan (production publisher) |
| SL-2 | Low | The local-issuer refusal checks only `APP_ENV`. Loopback binding is enforced by Compose. | Local slice only. The real API (U3) uses Auth0 and has no local issuer. |
| R-08 | Minor | The approved unit-test instructions contain commands that do not work as written. | The owner-approved verification command `scripts/verify.py --strict` (and `--unit walking-slice`) runs the working forms. Owner decision at the U0 checkpoint. |
| R-10 | Minor | `GET /slice/projects` and `GET /slice/projects/{id}` are owner-only read routes that are not in the plan. | Owner decision at the U0 checkpoint |

The security review records are in `docs/security-reviews/` on each branch: `2026-10-12-*` (first pass) and `2026-10-14-*-rereview` (READY at `63cd8b04…` and `b4888bfd…`, verbatim patch identities).

## Known Limitations

- **Port conflict.** Port 8000 is held on this machine by an unrelated container. The slice check ran with `SLICE_API_PORT=8001`; the default remains 8000.
- **Python patch versions.** `.python-version` is 3.12.14, while the digest-pinned `python:3.12-slim` image is 3.12.15. Both are 3.12.
- **Preview styles.** Preview pages reference `/assets/site.<hash>.css`, which the Vite dev server does not serve, so the preview frame shows unstyled content. Content and marking are correct.
- **Dependabot coverage.** Only directories on `main` are listed (R-12). The slice locks, fake issuer, slice packages and local Docker images are unmonitored, because they live only on the demonstration branch; they are throwaway local code. Dependabot may not recognise `*.lock` files as pip-compile output; that is revisited when U1 adds the real back-end lock.
- **Review path list and record format.** `.github/security-sensitive-paths.txt` now names the real module layout (R-01), but the list and the record format still await confirmation in the CI Pipeline stage.
- **The gate is protected procedurally.** `.github/workflows/ci.yml` and `scripts/gate_results.py` come from the pull request, so they are protected only by the ruleset and Michael's review. This is recorded in `docs/security-reviews/README.md`.
- **Local guard and the Studio build.** A bare local `python scripts/guard_fake_idp.py` (default targets) fails whenever `web/slice-studio/dist` exists, by design, and `verify.py`'s Studio check rebuilds it. The registered guard check therefore scans the S0 deployable outputs explicitly (`backend/dist`, `web/site/dist`), as CI does.
- **Two leaked anonymous volumes.** The first verification run left two empty anonymous volumes (`b9d8a16a…`, `fee48e01…`), before the `mongo-init` tmpfs fix. Later runs left none. They were not removed, per the no-volume-removal rule.
- **Studio tests deprecation warning.** `starlette.testclient` warns that `httpx` is deprecated in favour of `httpx2`; it is a warning only.
- **Lock targets.** Python locks were compiled on Linux for Python 3.12. They install cleanly on Windows 3.13, apart from Windows-only extras now pinned (`colorama`).
- **Required checks (E13).** Michael must register `gate` and the two CodeQL checks as required on `main`. The note is in `README.md`.

## Sources

- `code-generation-plan.md` and `unit-test-instructions.md` (approved).
- `../functional-design/`, `../nfr-requirements/`, `../nfr-design/` and `../infrastructure-design/`.
- `inception/contract-design/contract-summary.md` (C1 errors, C2, C8, C9, C10, C11).
