"""Utilities for exporting AI project list metadata to CSV."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, Sequence

from sim.client import SimApiClient
from sim.exceptions import SimApiError
from sim.models import Institution, ProjectInstitutionLink

logger = logging.getLogger(__name__)

_TARGET_SUFFIXES = ("-ai-c", "-ai-h-mcml")
_MCML_SUFFIX = "-ai-h-mcml"


@dataclass(slots=True)
class ProjectListEntry:
    """Single row in the project list export."""

    project_id: str
    partner: str
    institution: str


@dataclass(slots=True)
class ProjectListResult:
    """Aggregated result of project list collection."""

    entries: list[ProjectListEntry] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def extend_issues(self, messages: Iterable[str]) -> None:
        self.issues.extend(messages)


class ProjectListCollectionError(RuntimeError):
    """Raised when collecting project list entries cannot proceed."""


def collect_project_list(
    client: SimApiClient,
    *,
    service: str = "AI",
    test_sample_size: int | None = None,
    group_filter: str | None = None,
) -> ProjectListResult:
    """Collect project list entries for a service."""

    result = ProjectListResult()

    try:
        groups = client.list_groups(service)
    except SimApiError as exc:  # pragma: no cover - defensive path
        message = f"Failed to list groups for service {service}: {exc}"
        logger.error(message)
        raise ProjectListCollectionError(message) from exc

    if group_filter:
        groups = [group for group in groups if fnmatch(group, group_filter)]

    projects = _extract_projects(groups)
    project_ids = sorted(projects)

    if test_sample_size is not None:
        if test_sample_size <= 0:
            result.issues.append("Test sample size must be a positive integer.")
            return result
        project_ids = project_ids[:test_sample_size]

    for project_id in project_ids:
        partner = "mcml" if projects.get(project_id, False) else ""
        institution_name = _resolve_top_institution_name(client, project_id, result)
        if not institution_name:
            institution_name = ""

        result.entries.append(
            ProjectListEntry(
                project_id=project_id,
                partner=partner,
                institution=institution_name,
            )
        )

    return result


def write_project_list_csv(entries: Sequence[ProjectListEntry], output_path: Path) -> None:
    """Write project list entries to the target CSV file."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ProjectID", "Partner", "Institution"])
        for entry in entries:
            writer.writerow([entry.project_id, entry.partner, entry.institution])


def default_project_list_output_path(today) -> Path:
    """Build default output path for project list CSV."""

    return Path("output") / today.isoformat() / "project-list.csv"


def _extract_projects(groups: Sequence[str]) -> dict[str, bool]:
    projects: dict[str, bool] = {}
    for group in groups:
        project_id = _extract_project_id(group)
        if not project_id:
            continue
        is_mcml = group.endswith(_MCML_SUFFIX)
        projects[project_id] = projects.get(project_id, False) or is_mcml
    return projects


def _extract_project_id(group: str) -> str | None:
    for suffix in _TARGET_SUFFIXES:
        if group.endswith(suffix):
            return group[: -len(suffix)].rstrip("-")
    return None


def _resolve_top_institution_name(
    client: SimApiClient,
    project_id: str,
    result: ProjectListResult,
) -> str | None:
    try:
        links = client.get_project_institution_links(project_id)
    except SimApiError as exc:
        result.issues.append(
            f"Failed to fetch institution links for project {project_id}: {exc}"
        )
        return None

    institution_id = _first_institution_id(links)
    if not institution_id:
        result.issues.append(f"No institution link found for project {project_id}.")
        return None

    visited: set[str] = set()
    current_id: str | None = institution_id
    top_bezeichnung: str | None = None

    while current_id and current_id not in visited:
        visited.add(current_id)
        try:
            institution = client.get_institution(current_id)
        except SimApiError as exc:
            result.issues.append(
                f"Failed to retrieve institution {current_id} for project {project_id}: {exc}"
            )
            break

        bezeichnung = (institution.bezeichnung or "").strip()
        if bezeichnung:
            top_bezeichnung = bezeichnung

        parent_ids = [parent_id for parent_id in institution.parent_ids if parent_id]
        current_id = parent_ids[0] if parent_ids else None

    return top_bezeichnung


def _first_institution_id(links: Sequence[ProjectInstitutionLink]) -> str | None:
    for link in links:
        if isinstance(link, ProjectInstitutionLink) and link.einrichtungs_id:
            return link.einrichtungs_id
    return None


__all__ = [
    "ProjectListCollectionError",
    "ProjectListEntry",
    "ProjectListResult",
    "collect_project_list",
    "default_project_list_output_path",
    "write_project_list_csv",
]
