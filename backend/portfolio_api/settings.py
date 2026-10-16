"""Runtime settings for the Studio API, read from the environment.

BR1.3 / NFR1.2: an issuer is *local-class* when it uses ``http``, has a host under
``.invalid``, ``.local`` or ``localhost`` (one trailing dot ignored), has a single-label host
(such as a Compose service name), or is a loopback, private, link-local, unspecified,
reserved or multicast address in any numeric form (``127.1``, ``0x7f.1``, ``0177.0.0.1``,
``2130706433``, IPv4-mapped IPv6). A local-class issuer, or a local-class key-set address
(``AUTH_JWKS_URL``), is refused at start-up unless ``APP_ENV=local`` is set. The validator
holds only these generic rules, never the local fake issuer's URL, which lives only in
``local/compose.env``.

SL-3 (security re-review): the API answers only requests whose ``Host`` is in
``ALLOWED_HOSTS`` (comma-separated host names, any port), so a hostile page cannot reach it
through DNS rebinding. With ``APP_ENV=local`` and no setting, the allow-list is ``localhost``,
``127.0.0.1`` and ``api`` (the Compose service name). In any other environment the setting
is required; without it the API refuses to start. ``*`` is never accepted.
"""

from __future__ import annotations

import ipaddress
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

LOCAL_ENV = "local"
LOCAL_SUFFIXES: tuple[str, ...] = (".invalid", ".local", ".localhost")
DEFAULT_CORS_ORIGIN = "http://localhost:5173"
# SL-3: the Host names the API answers in APP_ENV=local when ALLOWED_HOSTS is not set.
LOCAL_ALLOWED_HOSTS: tuple[str, ...] = ("localhost", "127.0.0.1", "api")
HOST_NAME = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9-]{1,63}\.?$")


class ConfigurationError(RuntimeError):
    """The API refuses to start with this configuration."""


NUMERIC_PART = re.compile(r"^(0[xX][0-9a-fA-F]*|0[0-7]*|[1-9][0-9]*)$")


def _numeric_ipv4(host: str) -> ipaddress.IPv4Address | None:
    """Parse the numeric IPv4 forms ``inet_aton`` accepts: one to four parts, each decimal,
    octal (leading 0) or hexadecimal (0x), the last part filling the remaining bytes.
    ``127.1``, ``0x7f.1``, ``0177.0.0.1`` and ``2130706433`` all mean 127.0.0.1."""
    parts = host.split(".")
    if not 1 <= len(parts) <= 4 or not all(NUMERIC_PART.match(p) for p in parts):
        return None
    values = []
    for part in parts:
        if part[:2].lower() == "0x":
            values.append(int(part[2:] or "0", 16))
        elif part.startswith("0") and len(part) > 1:
            values.append(int(part, 8))
        else:
            values.append(int(part))
    *leading, last = values
    if any(v > 255 for v in leading) or last >= 256 ** (4 - len(leading)):
        return None
    number = last
    for index, value in enumerate(leading):
        number += value << (8 * (3 - index))
    return ipaddress.IPv4Address(number)


def _is_non_public_address(host: str) -> bool | None:
    """True or False for an IP host (in any numeric form); None when the host is a name."""
    address: ipaddress.IPv4Address | ipaddress.IPv6Address | None
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = _numeric_ipv4(host)
    if address is None:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_unspecified
        or address.is_reserved
        or address.is_multicast
    )


def is_local_class_issuer(issuer: str) -> bool:
    """Return True when the URL can only point at a local or private service.

    One trailing dot is stripped from the host first (``localhost.`` is ``localhost``).
    """
    parts = urlsplit(issuer)
    host = (parts.hostname or "").lower()
    if host.endswith("."):
        host = host[:-1]
    if parts.scheme != "https" or not host:
        return True
    if host == "localhost" or host.endswith(LOCAL_SUFFIXES):
        return True
    non_public = _is_non_public_address(host)
    if non_public is not None:
        return non_public
    return "." not in host


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise ConfigurationError(f"{key} is required")
    return value


@dataclass(frozen=True)
class Settings:
    """Validated API settings (OwnerIdentity is configuration, not stored data)."""

    app_env: str
    auth_issuer: str
    auth_audience: str
    owner_subject: str
    jwks_url: str
    mongo_uri: str
    mongo_db: str
    site_dir: Path
    fixture_dir: Path
    renderer_command: tuple[str, ...]
    renderer_assets_dir: Path
    site_owner_name: str
    site_github_url: str
    cors_origin: str = DEFAULT_CORS_ORIGIN
    allowed_hosts: tuple[str, ...] = ()

    @property
    def is_local(self) -> bool:
        """True only for the explicit local environment."""
        return self.app_env == LOCAL_ENV


def parse_allowed_hosts(value: str, app_env: str) -> tuple[str, ...]:
    """SL-3: the Host allow-list; refuse a missing list outside local mode, and wildcards."""
    hosts = tuple(h.strip().lower() for h in value.split(",") if h.strip())
    if not hosts:
        if app_env == LOCAL_ENV:
            return LOCAL_ALLOWED_HOSTS
        raise ConfigurationError(
            "ALLOWED_HOSTS is required outside APP_ENV=local (comma-separated host names)"
        )
    bad = [h for h in hosts if not HOST_NAME.match(h)]
    if bad:
        raise ConfigurationError(
            f"ALLOWED_HOSTS entries must be plain host names without port or wildcard: {bad}"
        )
    return hosts


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Read and validate the settings; raise ConfigurationError to refuse start-up."""
    source = os.environ if env is None else env
    app_env = source.get("APP_ENV", "").strip()
    issuer = _required(source, "AUTH_ISSUER").rstrip("/")
    if is_local_class_issuer(issuer) and app_env != LOCAL_ENV:
        raise ConfigurationError(
            "AUTH_ISSUER is a local-class issuer; it is accepted only with APP_ENV=local"
        )
    jwks_url = source.get("AUTH_JWKS_URL", "").strip() or f"{issuer}/.well-known/jwks.json"
    if is_local_class_issuer(jwks_url) and app_env != LOCAL_ENV:
        raise ConfigurationError(
            "AUTH_JWKS_URL must be a public https address; a local-class key-set address "
            "is accepted only with APP_ENV=local"
        )
    renderer = _required(source, "RENDERER_COMMAND").split()
    allowed_hosts = parse_allowed_hosts(source.get("ALLOWED_HOSTS", ""), app_env)
    return Settings(
        app_env=app_env,
        auth_issuer=issuer,
        auth_audience=_required(source, "AUTH_AUDIENCE"),
        owner_subject=_required(source, "OWNER_SUBJECT"),
        jwks_url=jwks_url,
        mongo_uri=_required(source, "MONGO_URI"),
        mongo_db=source.get("MONGO_DB", "").strip() or "portfolio_slice",
        site_dir=Path(_required(source, "SITE_DIR")),
        fixture_dir=Path(_required(source, "FIXTURE_DIR")),
        renderer_command=tuple(renderer),
        renderer_assets_dir=Path(_required(source, "RENDERER_ASSETS_DIR")),
        site_owner_name=_required(source, "SITE_OWNER_NAME"),
        site_github_url=_required(source, "SITE_GITHUB_URL"),
        cors_origin=source.get("CORS_ORIGIN", "").strip() or DEFAULT_CORS_ORIGIN,
        allowed_hosts=allowed_hosts,
    )
