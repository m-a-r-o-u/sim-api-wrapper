"""Utilities for collecting AI system user email addresses."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from sim_api_wrapper.client import SimApiClient
from sim_api_wrapper.exceptions import SimApiError
from sim_api_wrapper.models import User

logger = logging.getLogger(__name__)

_AI_COMPUTE_SUFFIX = "-ai-c"
_MCML_SUFFIXES = ("-ai-h-mcml",)


@dataclass(slots=True)
class AiSystemsEmailCollectionResult:
    """Aggregated result of the AI system user email collection."""

    emails: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def extend_issues(self, messages: Iterable[str]) -> None:
        self.issues.extend(messages)


class AiSystemsCollectionError(RuntimeError):
    """Raised when the AI system email collection cannot proceed."""


class AiSystemsMcmlCollectionError(AiSystemsCollectionError):
    """Raised when the AI Systems MCML email collection cannot proceed."""


def collect_ai_system_user_emails(
    client: SimApiClient,
    *,
    service: str = "AI",
    test_sample_size: int | None = None,
) -> AiSystemsEmailCollectionResult:
    """Collect hauptemail or kontaktemail addresses of AI system users."""

    result = AiSystemsEmailCollectionResult()

    try:
        logger.info("Listing groups for service %s", service)
        groups = client.list_groups(service)
    except SimApiError as exc:  # pragma: no cover - defensive path
        message = f"Failed to list groups for service {service}: {exc}"
        logger.error(message)
        raise AiSystemsCollectionError(message) from exc

    target_groups = sorted(
        group
        for group in groups
        if _is_ai_compute_group(group) or _is_mcml_group(group)
    )
    logger.info("Identified %d relevant AI system group(s)", len(target_groups))

    if not target_groups:
        result.issues.append(
            "No AI compute or MCML groups found. Expected suffixes: "
            f"'{_AI_COMPUTE_SUFFIX}' or '{_MCML_SUFFIXES[0]}'."
        )
        return result

    if test_sample_size is not None:
        if test_sample_size <= 0:
            result.issues.append("Test sample size must be a positive integer.")
            return result
        logger.info(
            "Applying test sample size; limiting AI system groups to %d entry/entries: %s",
            test_sample_size,
            ", ".join(target_groups[:test_sample_size]),
        )
        target_groups = target_groups[:test_sample_size]

    usernames = _collect_group_members(client, service, target_groups, result)

    if not usernames:
        if not result.issues:
            result.issues.append("No users collected from AI system groups.")
        return result

    unique_usernames = sorted(set(usernames))
    logger.info(
        "Collected %d unique username(s) across %d group(s)",
        len(unique_usernames),
        len(target_groups),
    )

    unique_emails: dict[str, str] = {}
    for username in unique_usernames:
        logger.info("Fetching user record for %s", username)
        try:
            user = client.get_user(username)
        except SimApiError as exc:
            message = f"Failed to retrieve user {username}: {exc}"
            logger.warning(message)
            result.issues.append(message)
            continue

        if not isinstance(user, User):
            message = f"Unexpected payload when retrieving user {username}."
            logger.warning(message)
            result.issues.append(message)
            continue

        email = _extract_preferred_email(user)
        if email:
            logger.debug("Resolved email for %s: %s", username, email)
            unique_emails.setdefault(email.casefold(), email)
        else:
            result.issues.append(
                f"No hauptemail or kontaktemail address available for user {username}."
            )

    if not unique_emails:
        result.issues.append(
            "No hauptemail or kontaktemail addresses resolved for AI system users."
        )
        return result

    result.emails.extend(sorted(unique_emails.values(), key=str.casefold))
    logger.info("Collected %d email address(es)", len(result.emails))
    return result


def collect_ai_system_mcml_user_emails(
    client: SimApiClient,
    *,
    service: str = "AI",
    test_sample_size: int | None = None,
) -> AiSystemsEmailCollectionResult:
    """Collect hauptemail or kontaktemail addresses of AI Systems MCML users."""

    result = AiSystemsEmailCollectionResult()

    try:
        logger.info("Listing groups for service %s", service)
        groups = client.list_groups(service)
    except SimApiError as exc:  # pragma: no cover - defensive path
        message = f"Failed to list groups for service {service}: {exc}"
        logger.error(message)
        raise AiSystemsMcmlCollectionError(message) from exc

    target_groups = sorted(
        group
        for group in groups
        if _is_mcml_group(group) and group.casefold().startswith("aisystems")
    )
    logger.info("Identified %d AI Systems MCML group(s)", len(target_groups))

    if not target_groups:
        result.issues.append(
            "No AI Systems MCML groups found. Expected names starting with 'aisystems' "
            f"and ending with '{_MCML_SUFFIXES[0]}'."
        )
        return result

    if test_sample_size is not None:
        if test_sample_size <= 0:
            result.issues.append("Test sample size must be a positive integer.")
            return result
        logger.info(
            "Applying test sample size; limiting AI Systems MCML groups to %d entry/entries: %s",
            test_sample_size,
            ", ".join(target_groups[:test_sample_size]),
        )
        target_groups = target_groups[:test_sample_size]

    usernames = _collect_group_members(client, service, target_groups, result)

    if not usernames:
        if not result.issues:
            result.issues.append("No users collected from AI Systems MCML groups.")
        return result

    unique_usernames = sorted(set(usernames))
    logger.info(
        "Collected %d unique username(s) across %d AI Systems MCML group(s)",
        len(unique_usernames),
        len(target_groups),
    )

    unique_emails: dict[str, str] = {}
    for username in unique_usernames:
        logger.info("Fetching user record for %s", username)
        try:
            user = client.get_user(username)
        except SimApiError as exc:
            message = f"Failed to retrieve user {username}: {exc}"
            logger.warning(message)
            result.issues.append(message)
            continue

        if not isinstance(user, User):
            message = f"Unexpected payload when retrieving user {username}."
            logger.warning(message)
            result.issues.append(message)
            continue

        email = _extract_preferred_email(user)
        if email:
            logger.debug("Resolved email for %s: %s", username, email)
            unique_emails.setdefault(email.casefold(), email)
        else:
            result.issues.append(
                f"No hauptemail or kontaktemail address available for user {username}."
            )

    if not unique_emails:
        result.issues.append(
            "No hauptemail or kontaktemail addresses resolved for AI Systems MCML users."
        )
        return result

    result.emails.extend(sorted(unique_emails.values(), key=str.casefold))
    logger.info("Collected %d email address(es)", len(result.emails))
    return result


def _is_ai_compute_group(group: str) -> bool:
    return group.endswith(_AI_COMPUTE_SUFFIX)


def _is_mcml_group(group: str) -> bool:
    return any(group.endswith(suffix) for suffix in _MCML_SUFFIXES)


def _collect_group_members(
    client: SimApiClient,
    service: str,
    groups: Sequence[str],
    result: AiSystemsEmailCollectionResult,
) -> list[str]:
    usernames: list[str] = []
    for group in groups:
        logger.info("Fetching members for group %s", group)
        try:
            members = client.get_group_members(service, group)
        except SimApiError as exc:
            message = f"Failed to fetch members for group {group}: {exc}"
            logger.warning(message)
            result.issues.append(message)
            continue

        logger.debug("Retrieved %d member(s) for %s", len(members), group)
        if not members:
            result.issues.append(f"No members returned for group {group}.")
            continue

        usernames.extend(member for member in members if isinstance(member, str) and member)

    return usernames


def _extract_preferred_email(user: User) -> str | None:
    daten = user.daten if isinstance(user.daten, dict) else {}
    emails = daten.get("emailadressen") if isinstance(daten, dict) else None
    if not isinstance(emails, list):
        return None

    preferred_types = ("hauptemail", "kontaktemail")

    for target in preferred_types:
        for entry in emails:
            if not isinstance(entry, dict):
                continue
            typ = entry.get("typ")
            adresse = entry.get("adresse")
            if (
                isinstance(typ, str)
                and target in typ.lower()
                and isinstance(adresse, str)
            ):
                return adresse

    return None

