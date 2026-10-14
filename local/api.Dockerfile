# LOCAL-ONLY image of the slice API for the walking slice stack (built by local/compose.yaml;
# never pushed or deployed). Build context: the repository root.
# It holds the API package, the bundled renderer CLI, its static assets and the fixture image.
# It contains no fake identity provider code and no secrets.

FROM node:22-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392 AS renderer
WORKDIR /build
COPY web/slice-renderer/package.json web/slice-renderer/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/slice-renderer/scripts ./scripts
COPY web/slice-renderer/src ./src
COPY web/slice-renderer/assets ./assets
RUN node scripts/hash-assets.mjs && node scripts/build-cli.mjs

FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# The renderer runs on Node as a subprocess (NFR Design Q1); copy the runtime binary only.
COPY --from=renderer /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements-slice.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-slice.lock
COPY backend/portfolio_api ./portfolio_api
COPY --from=renderer /build/dist/cli.cjs ./renderer/cli.cjs
COPY --from=renderer /build/assets ./renderer/assets
COPY local/fixtures/fixture.json ./fixtures/fixture.json
COPY local/fixtures/ast_SliceFixtureImage0001 ./fixtures/ast_SliceFixtureImage0001
RUN mkdir -p /site && chown 10001:10001 /site

USER 10001
EXPOSE 8000
HEALTHCHECK --interval=3s --timeout=3s --retries=20 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]
CMD ["uvicorn", "--factory", "portfolio_api.slice.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
