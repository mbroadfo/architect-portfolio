# Infrastructure Specification — U0 walking-slice

**Inputs:**
- U0 NFR design: `../nfr-design/`, the security, reliability and logical-components files;
- NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- components and contract-summary;
- team-practices (Way of Working, Deployment, Code Style);
- `infrastructure-design-questions.md`.

U0 uses **no cloud infrastructure**. S1 to S3 run on a local Docker stack, and S0 merges the CI pipeline. Every cloud resource belongs to U2 and the owning units, and needs Michael's approval (E1, E2).

## Deployment

| Facet | Choice | Rationale |
|---|---|---|
| Compute model | Docker Compose services on the developer's machine | Slice only, never deployed (bolt-plan Phase A) |
| Networking | One Compose bridge network. The fake issuer has the network alias `fake-idp.invalid`, which the API uses to fetch the JWKS. Host ports are published **only on 127.0.0.1**: API `127.0.0.1:8000`, nginx `127.0.0.1:8080`, fake issuer `127.0.0.1:9000`. The browser's Studio page gets its token from `http://localhost:9000/token`. The token's `iss` claim is always `http://fake-idp.invalid`, whichever URL served it, so the API's issuer check is unaffected. The Vite dev server is at `localhost:5173` | NFR1.2 (host exposure), CORS origin, the Studio token flow |
| Storage | Named volumes: `mongo-data`, which can be thrown away, and `site`, holding `releases/` and the `public` relative symbolic link | REL-0.1, REL-0.2 |
| Environments | `local` only (`APP_ENV=local`) | NFR1.2 |
| Infrastructure as code | `local/compose.yaml` and `local/compose.env` (placeholders, no secrets), plus `local/nginx.conf` | Reviewed with S1 |
| Sizing | Default container resources; one API process | Single-user demonstration |
| Cost | $0: local, plus GitHub Actions free for public repositories | NFR4.1 |

## Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| `mongo` | Database | `mongo:7` with `--replSet rs0 --bind_ip_all`. Its health check pings the server **and** checks that the node is primary. The one-shot `mongo-init` service is idempotent: if `rs.status()` reports a valid replica set it exits 0; otherwise it runs `rs.initiate({_id: "rs0", members: [{_id: 0, host: "mongo:27017"}]})` and waits for the node to become primary | Transactions for Publish (REL-0.1). This works on a fresh or a surviving `mongo-data` volume |
| `fake-idp` | Identity (local only) | Built from `local/fake-idp/`; ES256 key in memory; serves the JWKS and a token endpoint | Absent from every non-local artifact (NFR1.3) |
| `api` | Application | Built from `backend/`, with a Node runtime for the renderer CLI; binds `0.0.0.0:8000` in the container and is published on `127.0.0.1:8000`; mounts `site` read-write. It waits for `mongo` (`service_healthy`), `mongo-init` (`service_completed_successfully`) and `fake-idp` (`service_healthy`) | `APP_ENV=local` |
| `nginx` | Static server | `nginx:alpine` mounting `site` **read-only**. It serves `site/public` with the C9 headers, except HSTS (the local server is `http`). Every `add_header` is declared once at server level with `always`, and no `location` block declares its own (which would discard the inherited headers). 404 responses (`404.html`) therefore carry the headers too | `make slice-check` asserts the headers on a 200 and on a 404 |

Every image above is pinned by digest in `compose.yaml`. Dependabot proposes updates.

## Assumptions & Open Questions

- No cloud resource is designed or created here. U2's Infrastructure Design covers preview and production.
