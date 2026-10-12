"""AIDLC_LOCAL_ONLY_FAKE_IDP

LOCAL-ONLY FAKE identity provider (U0 walking slice; NFR1.3, BR1.2, BR1.3).

- Its ES256 signing key is generated in memory at start-up and never written to disk or
  committed (the repository is public). Each start gets a new key.
- It serves ``/.well-known/jwks.json`` (public key only) and ``/token?sub=<subject>`` for the
  configured owner subject and test subjects. This replaces the real sign-in flow locally.
- The ``iss`` claim is the configured ``AUTH_ISSUER`` (``http://fake-idp.invalid`` in
  ``local/compose.env``), whichever URL served the token.

The API refuses this issuer unless ``APP_ENV=local`` (BR1.3).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Mapping
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from jwt.algorithms import ECAlgorithm

from fake_idp import MARKER

TOKEN_LIFETIME_SECONDS = 600
DEFAULT_CORS_ORIGIN = "http://localhost:5173"


class FakeIdpConfigurationError(RuntimeError):
    """The fake issuer refuses to start without its local configuration."""


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise FakeIdpConfigurationError(f"{MARKER}: {key} is required")
    return value


def _subjects(env: Mapping[str, str]) -> frozenset[str]:
    owner = _required(env, "OWNER_SUBJECT")
    extra = [s.strip() for s in env.get("FAKE_IDP_TEST_SUBJECTS", "").split(",") if s.strip()]
    return frozenset([owner, *extra])


def _public_jwk(private_key: ec.EllipticCurvePrivateKey) -> dict[str, Any]:
    jwk: dict[str, Any] = dict(ECAlgorithm.to_jwk(private_key.public_key(), as_dict=True))
    canonical = json.dumps(
        {"crv": jwk["crv"], "kty": jwk["kty"], "x": jwk["x"], "y": jwk["y"]},
        separators=(",", ":"),
        sort_keys=True,
    )
    kid = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return {**jwk, "kid": kid, "alg": "ES256", "use": "sig"}


def create_app(env: Mapping[str, str] | None = None) -> FastAPI:
    """Build the fake issuer with a fresh in-memory key."""
    source = os.environ if env is None else env
    issuer = _required(source, "AUTH_ISSUER").rstrip("/")
    audience = _required(source, "AUTH_AUDIENCE")
    subjects = _subjects(source)
    cors_origin = source.get("CORS_ORIGIN", "").strip() or DEFAULT_CORS_ORIGIN

    # The private key exists only in this closure, in memory.
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_jwk = _public_jwk(private_key)

    app = FastAPI(
        title=f"{MARKER} local fake issuer", docs_url=None, redoc_url=None, openapi_url=None
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cors_origin],
        allow_methods=["GET"],
        allow_headers=[],
        allow_credentials=False,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/.well-known/jwks.json")
    def jwks() -> dict[str, list[dict[str, Any]]]:
        return {"keys": [public_jwk]}

    @app.get("/token")
    def token(sub: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        if sub not in subjects:
            raise HTTPException(status_code=400, detail="unknown subject for this local issuer")
        now = int(time.time())
        claims = {
            "iss": issuer,
            "aud": audience,
            "sub": sub,
            "iat": now,
            "exp": now + TOKEN_LIFETIME_SECONDS,
        }
        access_token = jwt.encode(
            claims, private_key, algorithm="ES256", headers={"kid": public_jwk["kid"]}
        )
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": TOKEN_LIFETIME_SECONDS,
        }

    return app
