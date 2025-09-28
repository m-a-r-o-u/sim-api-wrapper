"""Authentication helpers for the SIM API client."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
import logging

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
