"""Client implementation for the LRZ SIM API."""

from __future__ import annotations

import json
import logging
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .auth import (
    DEFAULT_SIMAPI_ENV_PATH,
    TokenConfigurationError,
    build_basic_auth_header,
    load_netrc_credentials,
    load_simapi_token,
)
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
        token_path: Optional[str | Path] = None,
        netrc_path: Optional[str] = None,
        use_netrc: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._auth_header: Optional[str] = None
        self._default_headers = {"Accept": "application/json"}

        token_source = Path(token_path).expanduser() if token_path else DEFAULT_SIMAPI_ENV_PATH
        try:
            token = load_simapi_token(token_path)
        except TokenConfigurationError as exc:
            self.logger.error(
                "SIM API token misconfigured (%s). Falling back to netrc authentication if available.",
                exc,
            )
        else:
            if token:
                self._auth_header = f"Basic {token}"
                self.logger.info("Using SIM API token authentication from %s", token_source)
            else:
                if use_netrc or netrc_path:
                    message = "SIM API token not available at %s; attempting netrc authentication."
                else:
                    message = "SIM API token not available at %s; proceeding without authentication."
                self.logger.info(message, token_source)

        if not self._auth_header and (use_netrc or netrc_path):
            try:
                username, password = load_netrc_credentials(self.base_url, netrc_path)
            except FileNotFoundError:
                self.logger.warning(
                    "netrc file not found at %s; continuing without netrc authentication",
                    Path(netrc_path).expanduser() if netrc_path else Path("~/.netrc").expanduser(),
                )
            except ValueError as exc:
                self.logger.warning("Skipping netrc credentials: %s", exc)
            else:
                self._auth_header = build_basic_auth_header(username, password)
                self.logger.info("Using netrc-based authentication for %s", self.base_url)

    # -- context manager protocol -------------------------------------------------
    def __enter__(self) -> "SimApiClient":  # pragma: no cover - context convenience
        return self

    def __exit__(self, *exc_info: object) -> None:  # pragma: no cover - context convenience
        self.close()

    # -- public API methods -------------------------------------------------------
    def get_environment(self) -> Dict[str, Any]:
        """Return diagnostic information about the SIM backend environment."""

        data = self._request_json("GET", "/umgebung")
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for environment endpoint")

    def get_current_user(self) -> Dict[str, Any]:
        """Return information about the currently authenticated SIM identity."""

        data = self._request_json("GET", "/whoami")
        if isinstance(data, dict) and data.get("kennung"):
            return data
        raise SimApiError("Unexpected response payload for whoami endpoint")

    def get_service_characteristics(self, service: str) -> Dict[str, Any]:
        """Return group-related characteristics for the specified service."""

        endpoint = f"/service/{service}/egh"
        data = self._request_json("GET", endpoint)
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for service characteristics endpoint")

    def get_group_rights(self, service: str, group_name: str, username: str) -> Dict[str, Any]:
        """Return the rights metadata for a user within a given group."""

        endpoint = f"/service/{service}/group/{group_name}/user/{username}/grprights"
        data = self._request_json("GET", endpoint)
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for group rights endpoint")

    def get_permissions_metadata(self) -> Dict[str, Any]:
        """Return metadata describing all available SIM permissions."""

        payload = self._request_json("GET", "/permissions")
        data = self._parse_wrapped_data(payload, expect_single=True)
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for permissions metadata endpoint")

    def get_user_permissions(self, username: str) -> Dict[str, Any]:
        """Return the resolved permissions for the specified user."""

        payload = self._request_json("GET", f"/permissions/{username}")
        data = self._parse_wrapped_data(payload, expect_single=True)
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for user permissions endpoint")

    def list_groups(self, service: str) -> List[str]:
        """Return all available project groups for the given service."""

        endpoint = f"/service/{service}/groups"
        data = self._request_json("GET", endpoint)
        if isinstance(data, list):
            return [str(item) for item in data]
        raise SimApiError("Unexpected response payload for groups endpoint")

    def get_group_members(self, service: str, group_name: str) -> List[str]:
        """Return the usernames assigned to the specified group for a service."""

        endpoint = f"/service/{service}/groups/{group_name}/members"
        data = self._request_json("GET", endpoint)
        if isinstance(data, list):
            return [str(item) for item in data]
        raise SimApiError("Unexpected response payload for group members endpoint")

    def get_group_admins(self, service: str, group_name: str) -> List[str]:
        """Return the administrators assigned to the specified group."""

        endpoint = f"/service/{service}/groups/{group_name}/grpadmins"
        data = self._request_json("GET", endpoint)
        if isinstance(data, list):
            return [str(item) for item in data]
        raise SimApiError("Unexpected response payload for group admins endpoint")

    def get_group_details(self, service: str, group_name: str) -> Dict[str, Any]:
        """Return metadata about a specific group within a service."""

        endpoint = f"/service/{service}/group/{group_name}"
        data = self._request_json("GET", endpoint)
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for group details endpoint")

    def is_group_member(self, service: str, group_name: str, username: str) -> bool:
        """Return whether the given user is a member of the specified group."""

        endpoint = f"/service/{service}/group/{group_name}/members/{username}"
        data = self._request_json("GET", endpoint)
        if isinstance(data, bool):
            return data
        raise SimApiError("Unexpected response payload for group membership endpoint")

    def is_group_master_user(self, service: str, group_name: str, username: str) -> bool:
        """Return whether the given user is a master user of the specified group."""

        endpoint = f"/service/{service}/group/{group_name}/masteruser/{username}"
        data = self._request_json("GET", endpoint)
        if isinstance(data, bool):
            return data
        raise SimApiError("Unexpected response payload for group master user endpoint")

    def is_group_admin(self, service: str, group_name: str, username: str) -> bool:
        """Return whether the given user is an administrator of the specified group."""

        endpoint = f"/service/{service}/group/{group_name}/grpadmin/{username}"
        data = self._request_json("GET", endpoint)
        if isinstance(data, bool):
            return data
        raise SimApiError("Unexpected response payload for group admin endpoint")

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

    def list_org_projects(self, org: str) -> List[str]:
        """Return the projects that belong to the specified top-level organisation."""

        payload = self._request_json("GET", f"/org/{org}/projects")
        entries = self._parse_wrapped_data(payload)
        if isinstance(entries, list):
            return [str(item) for item in entries]
        raise SimApiError("Unexpected response payload for organisation projects endpoint")

    def get_org_project_details(self, org: str, project: str) -> Dict[str, Any]:
        """Return detailed information for a project belonging to an organisation."""

        payload = self._request_json("GET", f"/org/{org}/project/{project}")
        data = self._parse_wrapped_data(payload, expect_single=True)
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for organisation project details endpoint")

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

    def get_project_master_users(self, project: str) -> List[str]:
        """Return master user identifiers for the specified project."""

        endpoint = f"/project/{project}/mudusers"
        data = self._request_json("GET", endpoint)
        if isinstance(data, list):
            return [str(item) for item in data]
        raise SimApiError("Unexpected response payload for project master users endpoint")

    def list_service_projects(self, service: str) -> List[Dict[str, Any]]:
        """Return projects that currently have a quota for the specified service."""

        endpoint = f"/project/service/{service}"
        data = self._request_json("GET", endpoint)
        if isinstance(data, list) and all(isinstance(item, dict) for item in data):
            return [dict(item) for item in data]
        raise SimApiError("Unexpected response payload for service projects endpoint")

    def list_org_types(self) -> List[str]:
        """Return all available organisation types."""

        payload = self._request_json("GET", "/auswahlliste/orgtypes")
        entries = self._parse_wrapped_data(payload)
        if isinstance(entries, list):
            return [str(item) for item in entries]
        raise SimApiError("Unexpected response payload for organisation types endpoint")

    def get_vweb_user(self, username: str) -> Dict[str, Any]:
        """Return vWEB service information for the specified user."""

        payload = self._request_json("GET", f"/service/vweb/user/{username}/vwebserver")
        data = self._parse_wrapped_data(payload, expect_single=True)
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for vweb user endpoint")

    def list_personal_homepages(self) -> Dict[str, Any]:
        """Return all personal homepages registered in SIM."""

        data = self._request_json("GET", "/persHomepage")
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for personal homepages endpoint")

    def is_service_admin(self, service: str, username: str) -> bool:
        """Return whether the given user is a service administrator."""

        endpoint = f"/service/{service}/serviceadmin/{username}"
        data = self._request_json("GET", endpoint)
        if isinstance(data, bool):
            return data
        raise SimApiError("Unexpected response payload for service admin endpoint")

    def list_managed_groups(self, service: str, username: str) -> List[str]:
        """Return the groups the user can manage for the specified service."""

        endpoint = f"/service/{service}/user/{username}/managedgroups"
        data = self._request_json("GET", endpoint)
        if isinstance(data, list):
            return [str(item) for item in data]
        raise SimApiError("Unexpected response payload for managed groups endpoint")

    def list_group_memberships(self, service: str, username: str) -> List[str]:
        """Return the groups the user is a member of for the specified service."""

        endpoint = f"/service/{service}/user/{username}/groupmembership"
        data = self._request_json("GET", endpoint)
        if isinstance(data, list):
            return [str(item) for item in data]
        raise SimApiError("Unexpected response payload for group membership list endpoint")

    def list_user_services(self, username: str) -> List[Dict[str, Any]]:
        """Return the services associated with the specified user."""

        data = self._request_json("GET", f"/user/{username}/services")
        if isinstance(data, list) and all(isinstance(item, dict) for item in data):
            return [dict(item) for item in data]
        raise SimApiError("Unexpected response payload for user services endpoint")

    def get_password_metadata(self) -> Dict[str, Any]:
        """Return password policy metadata for the SIM platform."""

        data = self._request_json("GET", "/pwd")
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for password metadata endpoint")

    def get_user_password_metadata(self, username: str) -> Dict[str, Any]:
        """Return password-related metadata for the specified user."""

        payload = self._request_json("GET", f"/user/{username}/pwd")
        data = self._parse_wrapped_data(payload, expect_single=True)
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for user password metadata endpoint")

    def is_password_pwned(self, username: str) -> bool:
        """Return whether the specified user's password is known to be compromised."""

        payload = self._request_json("GET", f"/user/{username}/pwned")
        data = self._parse_wrapped_data(payload, expect_single=True)
        if isinstance(data, dict) and "pwned" in data:
            return bool(data["pwned"])
        raise SimApiError("Unexpected response payload for password breach endpoint")

    def list_exchange_distributions(self) -> List[str]:
        """Return all Exchange distribution lists."""

        data = self._request_json("GET", "/v2/verteiler")
        if isinstance(data, list):
            return [str(item) for item in data]
        raise SimApiError("Unexpected response payload for Exchange distributions endpoint")

    def get_exchange_distribution(self, list_name: str) -> Dict[str, Any]:
        """Return details for a specific Exchange distribution list."""

        endpoint = f"/v2/verteiler/{list_name}"
        data = self._request_json("GET", endpoint)
        if isinstance(data, dict):
            return data
        raise SimApiError("Unexpected response payload for Exchange distribution details endpoint")

    def get_exchange_distribution_admins(self, list_name: str) -> List[str]:
        """Return the Exchange administrators for the specified distribution list."""

        endpoint = f"/v2/verteiler/{list_name}/exchangeadmin"
        data = self._request_json("GET", endpoint)
        if isinstance(data, list):
            return [str(item) for item in data]
        raise SimApiError("Unexpected response payload for Exchange distribution admins endpoint")

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
        self.logger.info("SIM API call: %s %s", method.upper(), url)
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
