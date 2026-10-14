# AIDLC_LOCAL_ONLY_FAKE_IDP
# LOCAL-ONLY FAKE identity provider image for the walking slice. Built only by
# local/compose.yaml; never pushed or deployed. The signing key is generated in memory at
# start-up; nothing secret is in this image.
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock
COPY fake_idp ./fake_idp

USER 10001
EXPOSE 80
HEALTHCHECK --interval=5s --timeout=3s --retries=12 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1/health', timeout=2).status == 200 else 1)"]
CMD ["uvicorn", "--factory", "fake_idp.app:create_app", "--host", "0.0.0.0", "--port", "80"]
