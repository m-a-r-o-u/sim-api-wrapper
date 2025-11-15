"""Utilities for collecting AI system user project memberships."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from sim_api_wrapper.client import SimApiClient
from sim_api_wrapper.exceptions import SimApiError

logger = logging.getLogger(__name__)

_TARGET_SUFFIXES = ("-ai-c", "-ai-h-mcml")


@dataclass(slots=True)
class UserProjectsMembership:
    """Container describing the projects associated with a user."""

    username: str
    projects: tuple[str, ...]

    @property
    def project_count(self) -> int:
        return len(self.projects)


@dataclass(slots=True)
class UserProjectsMembershipResult:
    """Aggregated result of the AI system user project membership collection."""

    memberships: list[UserProjectsMembership] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def extend_issues(self, messages: Iterable[str]) -> None:
        self.issues.extend(messages)

    def build_histogram(self) -> dict[int, int]:
        counts = Counter(membership.project_count for membership in self.memberships)
        return dict(sorted(counts.items()))


class UserProjectsMembershipCollectionError(RuntimeError):
    """Raised when the AI system user project membership collection fails."""


def collect_user_projects_memberships(
    client: SimApiClient,
    *,
    service: str = "AI",
    test_sample_size: int | None = None,
) -> UserProjectsMembershipResult:
    """Collect users associated with AI system projects."""

    result = UserProjectsMembershipResult()

    try:
        logger.info("Listing groups for service %s", service)
        groups = client.list_groups(service)
    except SimApiError as exc:  # pragma: no cover - defensive path
        message = f"Failed to list groups for service {service}: {exc}"
        logger.error(message)
        raise UserProjectsMembershipCollectionError(message) from exc

    target_groups = sorted(group for group in groups if _matches_target_suffix(group))
    logger.info("Identified %d relevant AI system group(s)", len(target_groups))

    if not target_groups:
        result.issues.append(
            "No AI system groups found. Expected suffixes: '-ai-c' or '-ai-h-mcml'."
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

    membership_mapping = _collect_memberships(client, service, target_groups, result)

    if not membership_mapping:
        if not result.issues:
            result.issues.append("No users collected from AI system groups.")
        return result

    logger.info(
        "Collected membership information for %d unique user(s)",
        len(membership_mapping),
    )

    resolved_memberships: list[UserProjectsMembership] = []
    for username in sorted(membership_mapping):
        projects = tuple(sorted(membership_mapping[username]))
        resolved_memberships.append(UserProjectsMembership(username=username, projects=projects))

    resolved_memberships.sort(key=lambda item: (-item.project_count, item.username))
    result.memberships.extend(resolved_memberships)

    return result


def _matches_target_suffix(group: str) -> bool:
    return any(group.endswith(suffix) for suffix in _TARGET_SUFFIXES)


def _collect_memberships(
    client: SimApiClient,
    service: str,
    groups: Sequence[str],
    result: UserProjectsMembershipResult,
) -> dict[str, set[str]]:
    membership_mapping: dict[str, set[str]] = {}

    for group in groups:
        project_id = _extract_project_identifier(group)
        if not project_id:
            logger.debug("Skipping group %s; unable to determine project identifier", group)
            continue

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

        for member in members:
            if not isinstance(member, str) or not member:
                continue
            membership_mapping.setdefault(member, set()).add(project_id)

    return membership_mapping


def _extract_project_identifier(group: str) -> str | None:
    for suffix in _TARGET_SUFFIXES:
        if group.endswith(suffix):
            identifier = group[: -len(suffix)]
            return identifier.rstrip("-")
    return None




__all__ = [
    "UserProjectsMembership",
    "UserProjectsMembershipResult",
    "UserProjectsMembershipCollectionError",
    "collect_user_projects_memberships",
]

