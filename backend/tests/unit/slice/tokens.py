"""Test-only token helpers: key pairs generated in memory for each test run.

Unit tests sign their own tokens; nothing calls an identity provider (team practice).
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

ISSUER = "https://issuer.test.example"
AUDIENCE = "portfolio-studio-api"
OWNER = "owner-subject"


@dataclass
class SigningKey:
    """A test key pair and its public JWK."""

    kid: str
    algorithm: str
    private_key: Any
    jwk: dict[str, Any] = field(default_factory=dict)


def ec_key(kid: str = "ec-1") -> SigningKey:
    private_key = ec.generate_private_key(ec.SECP256R1())
    jwk = ECAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    return SigningKey(kid, "ES256", private_key, {**jwk, "kid": kid, "alg": "ES256", "use": "sig"})


def rsa_key(kid: str = "rsa-1") -> SigningKey:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    return SigningKey(kid, "RS256", private_key, {**jwk, "kid": kid, "alg": "RS256", "use": "sig"})


def claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    base: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": OWNER,
        "iat": now,
        "exp": now + 600,
    }
    base.update(overrides)
    return {key: value for key, value in base.items() if value is not None}


def sign(key: SigningKey, payload: dict[str, Any] | None = None, kid: str | None = None) -> str:
    return jwt.encode(
        payload if payload is not None else claims(),
        key.private_key,
        algorithm=key.algorithm,
        headers={"kid": kid or key.kid},
    )


def _b64(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def unsigned(kid: str = "ec-1") -> str:
    """A token with ``alg: none`` and an empty signature."""
    return f"{_b64({'alg': 'none', 'typ': 'JWT', 'kid': kid})}.{_b64(claims())}."


def hs256(kid: str = "ec-1") -> str:
    """A token signed with a shared secret instead of the issuer's key."""
    return jwt.encode(
        claims(), "a-shared-secret-of-sufficient-length!", algorithm="HS256", headers={"kid": kid}
    )


def jwks(*keys: SigningKey) -> dict[str, Any]:
    return {"keys": [key.jwk for key in keys]}
