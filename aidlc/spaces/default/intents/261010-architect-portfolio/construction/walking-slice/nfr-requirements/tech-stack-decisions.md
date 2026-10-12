# Tech Stack Decisions — U0 walking-slice

**Inputs:**
- functional-spec, rules and entities: `../functional-design/`;
- requirements (NFR1 to NFR17);
- contract-summary (C2, C9, C11);
- team-practices (Testing Posture, Code Style, Deployment);
- `bolt-plan.md` Phase A;
- `nfr-requirements-questions.md`.

U0 is the delivery-only walking slice. S0 merges; S1 to S3 run only on a local stack and are never deployed. Every requirement row carries its inception NFR ID with a sub-number.

## Decisions

| Area | Choice | Rationale |
|---|---|---|
| API language | Python 3.12 | Charter §6, a Python API on Lambda; team practice tooling (Ruff, mypy, pytest) |
| API framework | FastAPI, with a Lambda adapter (Mangum) when deployed | Generates OpenAPI, matching contract C1. U3 confirms it |
| Token verification | PyJWT with JWKS fetching; algorithm allow-list RS256 and ES256 | Mature, minimal; supports BR1.1 |
| Database | MongoDB 7 in Docker as a **single-node replica set** (`--replSet rs0`, initiated at start-up) locally and in CI, because BR3.1 needs multi-document transactions; later MongoDB Atlas M0, free, which is a replica set; the official Python driver | Charter §6; team practice (CI uses a throwaway container) |
| Front end | React 18, TypeScript (strict), Vite | Charter §6; Units Generation Q6 |
| Static rendering | React `renderToStaticMarkup` in Node, used by the slice renderer | Units Generation constraint 2, the runtime-neutral renderer |
| Tests | pytest with coverage; Vitest with React Testing Library; Playwright for the slice check | Team practice, Testing Posture |
| Lint and format | Ruff (lint and format) and mypy; ESLint (typescript-eslint, react-hooks, jsx-a11y) and Prettier | Team practice, Code Style |
| Dependencies | `npm ci` with `package-lock.json`; Python requirements locked with hashes | Team practice |
| CI | GitHub Actions: aggregate job, CodeQL, gitleaks, `npm audit`, `pip-audit` | Team practice; free for public repositories |
| Local stack | Docker Compose: MongoDB, the fake issuer (FastAPI, in-memory key), and a static file server for the output | Bolt-plan Phase A |

No new paid service is introduced (NFR4).

## Assumptions & Open Questions

- The production NFR targets are set on the owning units (U3, U7, U8, U9, U11). The slice demonstrates the path; it does not measure it.
