# LOCAL-ONLY test runner for the walking slice's back-end integration tests (R5). Built by
# local/compose.verify.yaml (service slice-it, profile "tests"); never pushed or deployed.
# Build context: the repository root (only the two lockfiles are sent, see the dockerignore).
#
# It holds Python 3.12, the slice runtime lock and the tooling lock (pytest), installed with
# --require-hashes. The back-end source and tests are mounted read-only at run time, so the
# tests always exercise the working tree. It runs on Linux, so symbolic links are real.

FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /deps
COPY backend/requirements-slice.lock requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-slice.lock \
 && python -m pip install --no-cache-dir --require-hashes -r requirements.lock
WORKDIR /repo
USER 10001
CMD ["python", "-m", "pytest", "backend/tests/integration/slice"]
