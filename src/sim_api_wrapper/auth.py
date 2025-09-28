"""Authentication helpers for the SIM API client."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple
import logging
import base64

try:  # pragma: no cover - import guard for optional dependency
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback for test environments
    def load_dotenv(path: Path | str) -> bool:  # type: ignore[override]
        """Minimal fallback implementation if python-dotenv is unavailable."""

        path_obj = Path(path)
        if not path_obj.exists():
            return False

        for line in path_obj.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
        return True

logger = logging.getLogger(__name__)

_DEFAULT_ENV_PATH = Path("~/.simapi.env").expanduser()
_ENV_VARIABLE = "SIMAPI_TOKEN"
_USERNAME_VARIABLE = "SIMAPI_USERNAME"
_PASSWORD_VARIABLE = "SIMAPI_PASSWORD"


def load_token_from_env_file(env_path: Optional[str | Path] = None) -> str:
    """Load the SIM API token from a dotenv-style file.

    Parameters
    ----------
    env_path:
        Optional path to the dotenv file. When omitted, ``~/.simapi.env`` is used.

    Returns
    -------
    str
        The token read from the ``SIMAPI_TOKEN`` environment variable.

    Raises
    ------
    FileNotFoundError
        If the specified dotenv file does not exist.
    ValueError
        If ``SIMAPI_TOKEN`` is missing or empty in the loaded environment.
    """

    path = Path(env_path).expanduser() if env_path else _DEFAULT_ENV_PATH
    if not path.exists():
        raise FileNotFoundError(f"Environment file not found at {path!s}")

    load_dotenv(path)
    token = os.getenv(_ENV_VARIABLE)
    if not token:
        raise ValueError(
            f"Environment variable {_ENV_VARIABLE} is not set in {path!s}"
        )

    logger.debug("Loaded SIM API token from %s", path)
    return token


def build_bearer_auth_header(token: str) -> str:
    """Return the HTTP Bearer authorization header for the given token."""

    if not token:
        raise ValueError("Token must be a non-empty string")
    return f"Bearer {token}"


def load_basic_auth_from_env_file(env_path: Optional[str | Path] = None) -> Tuple[str, str]:
    """Load SIM API basic authentication credentials from a dotenv-style file.

    Parameters
    ----------
    env_path:
        Optional path to the dotenv file. When omitted, ``~/.simapi.env`` is used.

    Returns
    -------
    Tuple[str, str]
        The username and password read from ``SIMAPI_USERNAME`` and
        ``SIMAPI_PASSWORD``.

    Raises
    ------
    FileNotFoundError
        If the specified dotenv file does not exist.
    ValueError
        If either variable is missing or empty in the loaded environment.
    """

    path = Path(env_path).expanduser() if env_path else _DEFAULT_ENV_PATH
    if not path.exists():
        raise FileNotFoundError(f"Environment file not found at {path!s}")

    load_dotenv(path)
    username = os.getenv(_USERNAME_VARIABLE)
    password = os.getenv(_PASSWORD_VARIABLE)
    if not username or not password:
        raise ValueError(
            "Environment variables "
            f"{_USERNAME_VARIABLE} and {_PASSWORD_VARIABLE} must both be set in {path!s}"
        )

    logger.debug("Loaded SIM API basic auth credentials from %s", path)
    return username, password


def build_basic_auth_header(username: str, password: str) -> str:
    """Return the HTTP Basic authorization header for the given credentials."""

    if not username:
        raise ValueError("Username must be a non-empty string")
    if not password:
        raise ValueError("Password must be a non-empty string")

    user_pass = f"{username}:{password}".encode("utf-8")
    encoded = base64.b64encode(user_pass).decode("ascii")
    return f"Basic {encoded}"
