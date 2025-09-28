"""Authentication helpers for the SIM API client."""

from __future__ import annotations

import logging
from base64 import b64encode
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import netrc

try:  # pragma: no cover - optional dependency
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover - handled gracefully at runtime
    dotenv_values = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DEFAULT_SIMAPI_ENV_PATH = Path("~/.simapi.env").expanduser()


class TokenConfigurationError(RuntimeError):
    """Raised when the SIM API token file exists but is invalid."""


def load_simapi_token(env_path: Optional[str | Path] = None) -> Optional[str]:
    """Load the SIM API token from a dotenv file if available."""

    path = Path(env_path).expanduser() if env_path else DEFAULT_SIMAPI_ENV_PATH
    if not path.exists():
        logger.debug("SIM API token file not found at %s", path)
        return None

    try:
        values = _load_env_values(path)
    except OSError as exc:  # pragma: no cover - defensive guard
        raise TokenConfigurationError(
            f"Could not read SIM API token file at {path!s}: {exc}"
        ) from exc

    token = values.get("SIMAPI_TOKEN")
    if token is None:
        raise TokenConfigurationError(
            f"SIMAPI_TOKEN not defined in {path!s}. Ensure the file contains 'SIMAPI_TOKEN=...'."
        )

    token = token.strip()
    if not token:
        raise TokenConfigurationError(
            f"SIMAPI_TOKEN in {path!s} is empty. Provide a valid token value."
        )

    logger.debug("Loaded SIM API token from %s", path)
    return token


def _load_env_values(path: Path) -> Dict[str, str]:
    """Return key/value pairs from a dotenv-style file."""

    if dotenv_values is not None:
        values = dotenv_values(path)
        return {key: value for key, value in values.items() if value is not None}

    content: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise TokenConfigurationError(
                    f"Invalid line {line_no} in {path!s}: expected 'KEY=VALUE' format."
                )
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key:
                raise TokenConfigurationError(
                    f"Invalid entry on line {line_no} in {path!s}: missing key name."
                )
            content[key] = value
    return content


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
