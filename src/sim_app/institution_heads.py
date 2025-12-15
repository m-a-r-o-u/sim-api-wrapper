"""Utilities for listing institution heads per AI project."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from sim.client import SimApiClient
from sim.exceptions import SimApiError
from sim.models import Institution, Person, ProjectInstitutionLink

logger = logging.getLogger(__name__)

_TARGET_SUFFIXES = ("-ai-c", "-ai-h-mcml")


@dataclass(slots=True)
class InstitutionHead:
    """Representation of an institution head for a project."""

    project_id: str
    formatted_name: str


@dataclass(slots=True)
class InstitutionHeadsResult:
    """Aggregated result of the institution head collection."""

    heads: list[InstitutionHead] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def extend_issues(self, messages: Iterable[str]) -> None:
        self.issues.extend(messages)


class InstitutionHeadsCollectionError(RuntimeError):
    """Raised when collecting institution heads cannot proceed."""


def collect_institution_heads(
    client: SimApiClient,
    *,
    service: str = "AI",
    test_sample_size: int | None = None,
) -> InstitutionHeadsResult:
    """Collect institution heads for projects belonging to a service."""

    result = InstitutionHeadsResult()

    try:
        logger.info("Listing groups for service %s", service)
        groups = client.list_groups(service)
    except SimApiError as exc:  # pragma: no cover - defensive path
        message = f"Failed to list groups for service {service}: {exc}"
        logger.error(message)
        raise InstitutionHeadsCollectionError(message) from exc

    project_ids = sorted({project for project in (_extract_project_identifier(g) for g in groups) if project})
    logger.info("Identified %d project(s) for service %s", len(project_ids), service)

    if not project_ids:
        result.issues.append(
            "No AI system groups found. Expected suffixes: '-ai-c' or '-ai-h-mcml'."
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
        logger.info("Fetching institution links for project %s", project_id)
        try:
            institution_links = client.get_project_institution_links(project_id)
        except SimApiError as exc:
            message = f"Failed to fetch institution links for project {project_id}: {exc}"
            logger.warning(message)
            result.issues.append(message)
            continue

        institution_id = _first_institution_id(institution_links)
        if not institution_id:
            result.issues.append(f"No institution link found for project {project_id}.")
            continue

        logger.info("Fetching institution %s for project %s", institution_id, project_id)
        try:
            institution = client.get_institution(institution_id)
        except SimApiError as exc:
            message = f"Failed to retrieve institution {institution_id} for project {project_id}: {exc}"
            logger.warning(message)
            result.issues.append(message)
            continue

        head_ids = _resolve_head_ids(client, institution, result, project_id)
        if not head_ids:
            continue

        formatted_names: list[str] = []
        for head_id in head_ids:
            logger.info("Fetching person %s for project %s", head_id, project_id)
            try:
                person = client.get_person(head_id)
            except SimApiError as exc:
                message = f"Failed to retrieve person {head_id} for project {project_id}: {exc}"
                logger.warning(message)
                result.issues.append(message)
                continue

            formatted_names.append(_format_person(person))

        if formatted_names:
            formatted_name = ", ".join(formatted_names)
            result.heads.append(
                InstitutionHead(project_id=project_id, formatted_name=formatted_name)
            )
        else:
            result.issues.append(
                f"No institution head details available for institution {institution_id} (project {project_id})."
            )

    return result


def _extract_project_identifier(group: str) -> str | None:
    for suffix in _TARGET_SUFFIXES:
        if group.endswith(suffix):
            identifier = group[: -len(suffix)]
            return identifier.rstrip("-")
    return None


def _first_institution_id(links: Sequence[ProjectInstitutionLink]) -> str | None:
    for link in links:
        if isinstance(link, ProjectInstitutionLink) and link.einrichtungs_id:
            return link.einrichtungs_id
    return None


def _resolve_head_ids(
    client: SimApiClient,
    institution: Institution,
    result: InstitutionHeadsResult,
    project_id: str,
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


__all__ = [
    "InstitutionHead",
    "InstitutionHeadsResult",
    "InstitutionHeadsCollectionError",
    "collect_institution_heads",
]
