"""Utilities for collecting AI system project details."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Callable, Iterable, Sequence

from sim.client import SimApiClient
from sim.exceptions import SimApiError
from sim.models import Institution, Person, ProjectInstitutionLink, User

logger = logging.getLogger(__name__)

_AI_COMPUTE_SUFFIX = "-ai-c"
_MCML_SUFFIXES = ("-ai-h-mcml", "-mcml-ai-h")
_TARGET_SUFFIXES = (_AI_COMPUTE_SUFFIX, *_MCML_SUFFIXES)


@dataclass(slots=True)
class ProjectDetailsEntry:
    """Representation of a project details row."""

    project_id: str
    head_of_institution: str
    master_users: tuple[str, ...]
    users: tuple[str, ...]
    is_mcml: bool


@dataclass(slots=True)
class ProjectDetailsResult:
    """Aggregated project details results."""

    entries: list[ProjectDetailsEntry] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def extend_issues(self, messages: Iterable[str]) -> None:
        self.issues.extend(messages)


class ProjectDetailsCollectionError(RuntimeError):
    """Raised when project details cannot be collected."""


def collect_project_details(
    client: SimApiClient,
    *,
    service: str = "AI",
    group_filter: str | None = None,
    test_sample_size: int | None = None,
    debug_commands: bool = False,
    emit_entry: Callable[[ProjectDetailsEntry], None] | None = None,
) -> ProjectDetailsResult:
    """Collect project details for AI system projects."""

    result = ProjectDetailsResult()

    try:
        _debug_command(debug_commands, f"sim-api groups {service}")
        logger.info("Listing groups for service %s", service)
        groups = client.list_groups(service)
    except SimApiError as exc:  # pragma: no cover - defensive path
        message = f"Failed to list groups for service {service}: {exc}"
        logger.error(message)
        raise ProjectDetailsCollectionError(message) from exc

    if group_filter:
        groups = [group for group in groups if fnmatch(group, group_filter)]
        logger.info(
            "Filtered groups with pattern %s; %d group(s) remain",
            group_filter,
            len(groups),
        )

    project_groups = _collect_project_groups(groups)
    project_ids = sorted(project_groups)
    logger.info("Identified %d AI system project(s)", len(project_ids))

    if not project_ids:
        if group_filter:
            result.issues.append(f"No groups matched filter pattern {group_filter}.")
        result.issues.append(
            "No AI system groups found. Expected suffixes: '-ai-c', '-ai-h-mcml', or '-mcml-ai-h'."
        )
        return result

    if test_sample_size is not None:
        if test_sample_size <= 0:
            result.issues.append("Test sample size must be a positive integer.")
            return result
        logger.info(
            "Applying test sample size; limiting projects to %d entry/entries: %s",
            test_sample_size,
            ", ".join(project_ids[:test_sample_size]),
        )
        project_ids = project_ids[:test_sample_size]

    for project_id in project_ids:
        logger.info("Collecting details for project %s", project_id)
        head_name = _collect_head_of_institution(
            client, project_id, result, debug_commands=debug_commands
        )
        master_users = _collect_master_users(
            client, project_id, result, debug_commands=debug_commands
        )
        users = _collect_project_users(
            client,
            service,
            project_groups[project_id],
            result,
            debug_commands=debug_commands,
        )

        entry = ProjectDetailsEntry(
            project_id=project_id,
            head_of_institution=head_name,
            master_users=tuple(master_users),
            users=tuple(users),
            is_mcml=_has_mcml_group(project_groups[project_id]),
        )
        if emit_entry is not None:
            emit_entry(entry)
        result.entries.append(entry)

    return result


def _collect_project_groups(groups: Sequence[str]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for group in groups:
        project_id = _extract_project_identifier(group)
        if not project_id:
            continue
        mapping.setdefault(project_id, []).append(group)
    return mapping


def _extract_project_identifier(group: str) -> str | None:
    for suffix in _TARGET_SUFFIXES:
        if group.endswith(suffix):
            identifier = group[: -len(suffix)]
            return identifier.rstrip("-")
    return None


def _has_mcml_group(groups: Sequence[str]) -> bool:
    return any(group.endswith(_MCML_SUFFIXES[0]) for group in groups)


def _collect_head_of_institution(
    client: SimApiClient,
    project_id: str,
    result: ProjectDetailsResult,
    *,
    debug_commands: bool,
) -> str:
    try:
        _debug_command(debug_commands, f"sim-api project-institution-links {project_id}")
        institution_links = client.get_project_institution_links(project_id)
    except SimApiError as exc:
        message = f"Failed to fetch institution links for project {project_id}: {exc}"
        logger.warning(message)
        result.issues.append(message)
        return ""

    institution_id = _first_institution_id(institution_links)
    if not institution_id:
        result.issues.append(f"No institution link found for project {project_id}.")
        return ""

    try:
        _debug_command(debug_commands, f"sim-api institution {institution_id}")
        institution = client.get_institution(institution_id)
    except SimApiError as exc:
        message = f"Failed to retrieve institution {institution_id} for project {project_id}: {exc}"
        logger.warning(message)
        result.issues.append(message)
        return ""

    head_ids = _resolve_head_ids(client, institution, result, project_id, debug_commands)
    if not head_ids:
        return ""

    formatted_names: list[str] = []
    for head_id in head_ids:
        try:
            _debug_command(debug_commands, f"sim-api person {head_id}")
            person = client.get_person(head_id)
        except SimApiError as exc:
            message = f"Failed to retrieve person {head_id} for project {project_id}: {exc}"
            logger.warning(message)
            result.issues.append(message)
            continue

        formatted_names.append(_format_person(person))

    if not formatted_names:
        result.issues.append(
            f"No institution head details available for institution {institution_id} (project {project_id})."
        )
        return ""

    return ", ".join(formatted_names)


def _collect_master_users(
    client: SimApiClient,
    project_id: str,
    result: ProjectDetailsResult,
    *,
    debug_commands: bool,
) -> list[str]:
    try:
        _debug_command(
            debug_commands, f"sim-api project-master-users {project_id} --format plain"
        )
        master_users = client.get_project_master_users(project_id)
    except SimApiError as exc:
        message = f"Failed to fetch master users for project {project_id}: {exc}"
        logger.warning(message)
        result.issues.append(message)
        return []

    if not master_users:
        result.issues.append(f"No master users returned for project {project_id}.")
        return []

    formatted: list[str] = []
    for username in sorted({user for user in master_users if isinstance(user, str) and user}):
        try:
            _debug_command(debug_commands, f"sim-api user {username}")
            user = client.get_user(username)
        except SimApiError as exc:
            message = f"Failed to retrieve user {username}: {exc}"
            logger.warning(message)
            result.issues.append(message)
            continue

        formatted.append(_format_user(user))

    return formatted


def _collect_project_users(
    client: SimApiClient,
    service: str,
    groups: Sequence[str],
    result: ProjectDetailsResult,
    *,
    debug_commands: bool,
) -> list[str]:
    users: set[str] = set()
    for group in groups:
        try:
            _debug_command(debug_commands, f"sim-api group-members {service} {group}")
            members = client.get_group_members(service, group)
        except SimApiError as exc:
            if str(exc) == "Expected JSON response":
                logger.info("No members returned for group %s", group)
                continue
            message = f"Failed to fetch members for group {group}: {exc}"
            logger.warning(message)
            result.issues.append(message)
            continue

        if not members:
            continue

        for member in members:
            if isinstance(member, str) and member:
                users.add(member)

    return sorted(users)


def _first_institution_id(links: Sequence[ProjectInstitutionLink]) -> str | None:
    for link in links:
        if isinstance(link, ProjectInstitutionLink) and link.einrichtungs_id:
            return link.einrichtungs_id
    return None


def _resolve_head_ids(
    client: SimApiClient,
    institution: Institution,
    result: ProjectDetailsResult,
    project_id: str,
    debug_commands: bool,
) -> list[str]:
    visited: set[str] = set()
    queue: list[Institution] = [institution]
    searched_parents = False
    origin_id = institution.lrz_id or "<unknown>"

    while queue:
        current = queue.pop(0)
        head_ids = _extract_head_ids(current)
        if head_ids:
            if current is not institution:
                result.issues.append(
                    (
                        f"No institution head set on institution {origin_id} for project {project_id}; "
                        f"using parent institution {current.lrz_id}."
                    )
                )
            return head_ids

        parent_ids = list(current.parent_ids or [])
        if current is institution and parent_ids:
            searched_parents = True
            parent_list = ", ".join(parent_ids)
            result.issues.append(
                (
                    f"No institution head set on institution {origin_id} for project {project_id}; "
                    f"searching parent institutions: {parent_list}."
                )
            )

        for parent_id in parent_ids:
            if not parent_id or parent_id in visited:
                continue
            visited.add(parent_id)
            searched_parents = True
            logger.info("Fetching parent institution %s for project %s", parent_id, project_id)
            try:
                _debug_command(debug_commands, f"sim-api institution {parent_id}")
                parent_institution = client.get_institution(parent_id)
            except SimApiError as exc:
                message = (
                    f"Failed to retrieve parent institution {parent_id} for project {project_id}: {exc}"
                )
                logger.warning(message)
                result.issues.append(message)
                continue

            queue.append(parent_institution)

    if searched_parents:
        result.issues.append(
            f"No institution head found for institution {origin_id} or its parents (project {project_id})."
        )
    else:
        result.issues.append(
            f"No institution head available for institution {origin_id} (project {project_id})."
        )

    return []


def _extract_head_ids(institution: Institution) -> list[str]:
    if not isinstance(institution, Institution):
        return []

    head_id = institution.chef_lrz_id
    if not isinstance(head_id, str):
        return []

    head_ids = [entry.strip() for entry in head_id.split(";") if entry.strip()]
    return head_ids


def _format_person(person: Person) -> str:
    if not isinstance(person, Person):
        return "<unknown>"

    parts = []
    if person.titel_pre:
        parts.append(str(person.titel_pre).strip())
    if person.rufname:
        parts.append(str(person.rufname).strip())
    if person.nachname:
        parts.append(str(person.nachname).strip())
    if person.titel_post:
        parts.append(str(person.titel_post).strip())

    name = " ".join(part for part in parts if part)
    username = person.benutzername or person.lrz_id

    if username:
        username = str(username).strip()
    if name and username:
        return f"{name} ({username})"
    if name:
        return name
    if username:
        return f"<unknown name> ({username})"
    return "<unknown>"


def _format_user(user: User) -> str:
    if not isinstance(user, User):
        return "<unknown>"

    daten = user.daten if isinstance(user.daten, dict) else {}
    parts = []
    for key in ("titelPre", "vorname", "nachname", "titelPost"):
        value = daten.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())

    name = " ".join(parts)
    username = user.kennung or user.lrz_id

    if username:
        username = str(username).strip()
    if name and username:
        return f"{name} ({username})"
    if name:
        return name
    if username:
        return f"<unknown name> ({username})"
    return "<unknown>"


def _debug_command(enabled: bool, command: str) -> None:
    if enabled:
        print(f"DEBUG: {command}", file=sys.stderr)


__all__ = [
    "ProjectDetailsEntry",
    "ProjectDetailsResult",
    "ProjectDetailsCollectionError",
    "collect_project_details",
]
