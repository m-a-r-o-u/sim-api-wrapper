"""Client implementation for the LRZ SIM API."""

from __future__ import annotations

import json
import logging
from contextlib import AbstractContextManager
from typing import Any, Dict, List, Optional, Tuple
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .auth import build_basic_auth_header, load_netrc_credentials
from .exceptions import SimApiError
from .models import Institution, Person, ProjectInstitutionLink, User

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://simapi.sim.lrz.de"
DEFAULT_TIMEOUT = 10


class SimApiClient(AbstractContextManager["SimApiClient"]):
    """High-level, extensible client for the LRZ SIM API."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int | float = DEFAULT_TIMEOUT,
        netrc_path: Optional[str] = None,
        use_netrc: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._auth_header: Optional[str] = None
        self._default_headers = {"Accept": "application/json"}

        if use_netrc or netrc_path:
            try:
                username, password = load_netrc_credentials(self.base_url, netrc_path)
            except FileNotFoundError:
                self.logger.debug("No netrc file found; continuing without authentication")
            except ValueError as exc:
                self.logger.debug("Skipping netrc credentials: %s", exc)
            else:
                self._auth_header = build_basic_auth_header(username, password)

    # -- context manager protocol -------------------------------------------------
    def __enter__(self) -> "SimApiClient":  # pragma: no cover - context convenience
        return self

    def __exit__(self, *exc_info: object) -> None:  # pragma: no cover - context convenience
        self.close()

    # -- public API methods -------------------------------------------------------
    def list_groups(self) -> List[str]:
        """Return all available project groups."""

        data = self._request_json("GET", "/service/AI/groups")
        if isinstance(data, list):
            return [str(item) for item in data]
        raise SimApiError("Unexpected response payload for groups endpoint")

    def get_group_members(self, group_name: str, *, solve: bool = False) -> List[str]:
        """Return the usernames assigned to the specified group."""

        endpoint = f"/service/AI/groups/{group_name}/members"
        params = {"solve": "true" if solve else "false"}
        data = self._request_json("GET", endpoint, params=params)
        if isinstance(data, list):
            return [str(item) for item in data]
        raise SimApiError("Unexpected response payload for group members endpoint")

    def get_project_institution_links(self, project_name: str) -> List[ProjectInstitutionLink]:
        """Return institution links for the given project name."""

        payload = self._request_json(
            "GET",
            "/einrichtung",
            params={"projektname": project_name},
        )
        entries = self._parse_wrapped_data(payload)
        return [ProjectInstitutionLink.from_dict(entry) for entry in entries]

    def get_institution(self, einrichtungs_id: str) -> Institution:
        """Fetch details about a specific institution."""

        payload = self._request_json("GET", f"/einrichtung/{einrichtungs_id}")
        data = self._parse_wrapped_data(payload, expect_single=True)
        return Institution.from_dict(data)

    def get_person(self, person_id: str) -> Person:
        """Fetch information about a person via their LRZ identifier."""

        payload = self._request_json("GET", f"/person/{person_id}")
        data = self._parse_wrapped_data(payload, expect_single=True)
        return Person.from_dict(data)

    def get_user(self, username: str) -> User:
        """Fetch information about a specific SIM user."""

        data = self._request_json("GET", f"/user/{username}")
        if isinstance(data, dict):
            return User.from_dict(data)
        raise SimApiError("Unexpected response payload for user endpoint")

    # -- internal helpers ---------------------------------------------------------
    def close(self) -> None:
        """Placeholder for compatibility with session-based clients."""

        self.logger.debug("Closing SIM API client")

    def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = self._build_url(endpoint, params)
        self.logger.debug("Performing %s request to %s", method.upper(), url)

        request = urllib_request.Request(url, method=method.upper())
        for header, value in self._default_headers.items():
            request.add_header(header, value)
        if self._auth_header:
            request.add_header("Authorization", self._auth_header)

        status, headers, body = self._open(request)
        self.logger.debug("Received response with status %s", status)
        if status >= 400:
            message = self._extract_error_message(body, headers, status)
            raise SimApiError(message, status_code=status)

        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - response should be JSON
            raise SimApiError("Expected JSON response") from exc

    def _build_url(self, endpoint: str, params: Optional[Dict[str, Any]]) -> str:
        base = f"{self.base_url}/{endpoint.lstrip('/')}"
        if not params:
            return base
        query = urllib_parse.urlencode({key: str(value) for key, value in params.items()})
        return f"{base}?{query}"

    def _open(self, request: urllib_request.Request) -> Tuple[int, Dict[str, str], bytes]:
        try:
            with urllib_request.urlopen(request, timeout=self.timeout) as response:
                status = response.getcode() or 0
                headers = dict(response.headers.items())
                body = response.read()
                return status, headers, body
        except urllib_error.HTTPError as exc:
            body = exc.read()
            headers = dict(exc.headers.items()) if exc.headers else {}
            return exc.code, headers, body
        except urllib_error.URLError as exc:
            self.logger.error("Request to %s failed: %s", request.full_url, exc.reason)
            raise SimApiError(f"Request to {request.full_url} failed: {exc.reason}") from exc

    def _parse_wrapped_data(self, payload: Dict[str, Any], *, expect_single: bool = False) -> Any:
        """SIM API responses commonly wrap data in a code/message/data structure."""

        if not isinstance(payload, dict):
            raise SimApiError("Unexpected response payload structure")

        code = payload.get("code")
        if code != 0:
            message = payload.get("message", "Unknown error")
            raise SimApiError(f"API returned error code {code}: {message}")

        data = payload.get("data")
        if expect_single:
            if isinstance(data, list):
                if len(data) != 1:
                    raise SimApiError("Expected exactly one result but received multiple")
                return data[0]
            if isinstance(data, dict):
                return data
            raise SimApiError("Unexpected response payload structure")

        if data is None:
            return []
        if isinstance(data, list):
            return data
        return [data]

    @staticmethod
    def _extract_error_message(body: bytes, headers: Dict[str, str], status: int) -> str:
        content_type = headers.get("Content-Type", "")
        text = body.decode("utf-8", errors="ignore") if body else ""
        if "application/json" in content_type:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                return str(payload.get("message") or payload.get("error") or text)
        return text or f"Request failed with status {status}"
