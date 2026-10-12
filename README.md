# Architect's Portfolio

Personal portfolio of Michael Broadfoot — Systems Architect · Engineer · Maker.

**Status:** Inception. Requirements and architecture are being defined using the
[AWS Labs AI-DLC](https://github.com/awslabs/aidlc-workflows) methodology.
Workflow records live under `aidlc/`; the AI-DLC runtime under `.claude/` is
vendored from aidlc-workflows (MIT-0).

## Repository layout

| Path | What it holds |
| --- | --- |
| `backend/` | The Python package host for the Studio API (`portfolio_api`). U0 ships a placeholder package. |
| `web/` | The TypeScript npm workspace: `web/site` (the public site, a placeholder until U7 and U8), later the renderer and the Studio. |
| `contracts/` | Placeholder for U1 (the shared contracts). |
| `infra/` | Placeholder for U2 (Terraform). No cloud resource exists yet. |
| `local/` | The local development stack, local-only and never deployed. |
| `scripts/` | CI scripts: the fake identity provider guard, the workflow lint, the security-review check and the public-output scan. |
| `tests/` | Tests for the CI scripts and the guard's fixtures. |
| `.github/` | Workflows, Dependabot configuration and `security-sensitive-paths.txt`. |
| `docs/security-reviews/` | Independent security review records (see below). |

## Prerequisites

- git
- Python 3.12 or later (CI uses the exact release in `.python-version`)
- Node 22 (the exact release is in `.nvmrc`) and npm
- Docker with Compose v2, only for the local stack and the integration tests

Set up the Python tooling in a project-local virtual environment, and the web workspace:

```sh
python -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock   # Windows: .venv\Scripts\python
npm --prefix web ci
```

Run every check that applies, project-wide (`make verify`, or without make):

```sh
python scripts/verify.py --strict     # Windows: .venv\Scripts\python.exe scripts\verify.py --strict
python scripts/verify.py --list       # what is registered, what applies, what is missing
python scripts/verify.py --unit <unit-slug>
```

**What it runs.** The checks are registered in `scripts/verify-checks.toml`. Units add their own
entries as they are implemented. They cover formatting, linting, type checking, tests with the
coverage floors, contract tests, the fake identity provider guard on the build outputs,
integration and end-to-end tests, and audits.

**When a check runs:**

- A check whose unit is not on this branch is *not applicable*.
- A check with a missing prerequisite (Docker, a tool, `node_modules`) is *skipped*, with the reason.
- With `--strict`, a skipped required check fails the run, and so does a skipped *test* inside a
  check that writes a JUnit report (pytest and Vitest checks), unless the registry allows that
  skip with a reason.

**Data safety.** Integration and end-to-end checks share one Compose project per checkout,
`portfolio-verify-<checkout id>`, so parallel worktrees never share a stack. Its host ports are
chosen free for each run, its database is on tmpfs, and a lock file in the gitignored
`.verify-work/` stops two runs in the same checkout from overlapping. It never deletes Docker
volumes or developer data, and never touches `portfolio-slice` or another project.

The final table lists every check with its status and reason. The exit code is 0 when nothing
required failed, 1 otherwise, and 2 for a usage, registry or lock error.

Or run the individual checks CI runs:

```sh
ruff check . && ruff format --check . && mypy
python -m pytest tests/scripts --cov=scripts --cov-fail-under=80
npm --prefix web run format:check && npm --prefix web run lint
npm --prefix web run typecheck && npm --prefix web run test && npm --prefix web run build
```

Python dependencies are pinned with hashes in `requirements.lock`, compiled from
`requirements.in` with `pip-compile --generate-hashes --allow-unsafe --strip-extras`.
npm dependencies are pinned in `web/package-lock.json` and installed with `npm ci`.

## How CI works

`.github/workflows/ci.yml` runs on every pull request to `main` and on every push to `main`.

- **`changes`** compares the pull request head with its merge base and decides which
  path-gated jobs must run. A change under `.github/` or `scripts/`, to a lockfile,
  `.python-version` or `.nvmrc` forces every job to run.
- **Path-gated jobs:** `python` (Ruff, mypy, pytest with an 80% line-coverage floor),
  `web` (Prettier, ESLint, `tsc`, Vitest with an 80% line-coverage floor, Vite build),
  `guard` (builds the wheel and the web bundle, then runs `scripts/guard_fake_idp.py`) and
  `audit` (`npm audit --audit-level=high` and `pip-audit` over the hashed lockfiles).
- **Always-run jobs:** `workflow-lint` (actionlint and `scripts/check_workflows.py`),
  `gitleaks`, and, on pull requests, `review-check` (`scripts/check_security_review.py`).
- **`gate`** needs every job and always runs. It fails if any job failed or was cancelled,
  or was skipped although its paths changed. It writes each check's result to the job
  summary. `gate` is the single required status check.

`.github/workflows/codeql.yml` runs CodeQL for Python and JavaScript/TypeScript on every
pull request and push to `main`, with no path filter.

Every workflow declares least-privilege `permissions:` (`contents: read`; only CodeQL adds
`security-events: write` and `actions: read`), pins every action to a full commit SHA, and
never uses `pull_request_target`. No secrets or cloud credentials are used.

> **For Michael (E13):** after the first CI run on a pull request, register `gate` and the two
> CodeQL checks (`analyze (python)` and `analyze (javascript-typescript)`) as required status
> checks in the `main` ruleset. Agents never change rulesets.

## How to record a security review

A pull request that changes a path listed in `.github/security-sensitive-paths.txt` needs an
independent AI security review, from a session that did not write the change, recorded for
its exact content. The `review-check` job fails until a record in `docs/security-reviews/`
carries the pull request's current patch identity and `verdict: READY`. The record format
and the steps are in [`docs/security-reviews/README.md`](docs/security-reviews/README.md).
The path list and the record format are provisional until the CI Pipeline stage confirms them.
