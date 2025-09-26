"""Authentication helpers for the SIM API client."""

from __future__ import annotations

from base64 import b64encode
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse
import logging
import netrc

logger = logging.getLogger(__name__)


def load_netrc_credentials(base_url: str, netrc_path: Optional[str | Path] = None) -> Tuple[str, str]:
    """Load credentials for the given base URL from a netrc file."""

    path = Path(netrc_path).expanduser() if netrc_path else Path("~/.netrc").expanduser()
    try:
        parsed = netrc.netrc(path)
    except FileNotFoundError as exc:  # pragma: no cover - defensive branch
        raise FileNotFoundError(f"netrc file not found at {path!s}") from exc

    host = urlparse(base_url).hostname
    if not host:
        raise ValueError(f"Could not parse host from base URL {base_url!r}")

    creds = parsed.authenticators(host)
    if creds is None:
        raise ValueError(f"No credentials for host {host!r} in {path!s}")

    login, _, password = creds
    if not login or not password:
        raise ValueError(f"Incomplete credentials for host {host!r} in {path!s}")

    logger.debug("Loaded netrc credentials for %s", host)
    return login, password


def build_basic_auth_header(username: str, password: str) -> str:
    """Return the HTTP Basic authorization header for the given credentials."""

    token = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"
