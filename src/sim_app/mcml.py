"""Utilities for MCML related SIM app workflows."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Sequence

from sim_api_wrapper.client import SimApiClient
from sim_api_wrapper.exceptions import SimApiError
from sim_api_wrapper.models import User

logger = logging.getLogger(__name__)

_MCML_SUFFIX = "-ai-h-mcml"


@dataclass(slots=True)
class McmlEmailCollectionResult:
    """Aggregated result of the MCML master user email collection."""

    emails: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def extend_issues(self, messages: Iterable[str]) -> None:
        self.issues.extend(messages)


class McmlCollectionError(RuntimeError):
    """Raised when the MCML email collection cannot proceed."""


def collect_mcml_master_user_emails(
    client: SimApiClient,
    *,
    service: str = "AI",
) -> McmlEmailCollectionResult:
    """Collect hauptemail addresses of MCML master users for a service."""

    result = McmlEmailCollectionResult()

    try:
        groups = client.list_groups(service)
    except SimApiError as exc:  # pragma: no cover - defensive path
        message = f"Failed to list groups for service {service}: {exc}"
        logger.error(message)
        raise McmlCollectionError(message) from exc

    mcml_groups = [group for group in groups if group.endswith(_MCML_SUFFIX)]
    if not mcml_groups:
        result.issues.append(
            f"No MCML master groups ending with '{_MCML_SUFFIX}' found for service {service}."
        )
        return result

    projects = sorted({group[: -len(_MCML_SUFFIX)] for group in mcml_groups})
    if not projects:
        result.issues.append("Resolved MCML project list is empty after processing group names.")
        return result

    master_users: list[str] = []
    for project in projects:
        try:
            users = client.get_project_master_users(project)
        except SimApiError as exc:
            message = f"Failed to fetch master users for project {project}: {exc}"
            logger.warning(message)
            result.issues.append(message)
            continue

        if not users:
            result.issues.append(f"No master users returned for project {project}.")
            continue

        master_users.extend(user for user in users if isinstance(user, str) and user)

    if not master_users:
        result.issues.append("No master users collected from MCML projects.")
        return result

    unique_users = _deduplicate_master_users(master_users)
    if not unique_users:
        result.issues.append("Master user list empty after deduplication.")
        return result

    emails: list[str] = []
    for username in unique_users:
        try:
            user = client.get_user(username)
        except SimApiError as exc:
            message = f"Failed to retrieve user {username}: {exc}"
            logger.warning(message)
            result.issues.append(message)
            continue

        email = _extract_hauptemail(user)
        if email:
            emails.append(email)
        else:
            result.issues.append(f"No hauptemail address available for user {username}.")

    if not emails:
        result.issues.append("No hauptemail addresses resolved for MCML master users.")
        return result

    result.emails.extend(sorted(emails))
    return result


def _deduplicate_master_users(usernames: Sequence[str]) -> List[str]:
    """Remove duplicates while preferring IDs without trailing numerals."""

    selection: dict[str, str] = {}
    for username in usernames:
        base = _strip_trailing_digits(username)
        chosen = selection.get(base)
        if chosen is None:
            selection[base] = username
            continue

        if chosen != base and username == base:
            selection[base] = username
        elif username != base and chosen != base and len(username) < len(chosen):
            selection[base] = username

    return sorted(selection.values())


def _strip_trailing_digits(value: str) -> str:
    return re.sub(r"\d+$", "", value)


def _extract_hauptemail(user: User) -> str | None:
    daten = user.daten if isinstance(user.daten, dict) else {}
    emails = daten.get("emailadressen") if isinstance(daten, dict) else None
    if not isinstance(emails, list):
        return None

    for entry in emails:
        if not isinstance(entry, dict):
            continue
        typ = entry.get("typ")
        adresse = entry.get("adresse")
        if isinstance(typ, str) and "hauptemail" in typ.lower() and isinstance(adresse, str):
            return adresse
    return None
