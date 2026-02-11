"""Tests for project list CSV export helpers."""

from __future__ import annotations

from datetime import date

from sim.models import Institution, ProjectInstitutionLink
from sim_app.project_list import (
    collect_project_list,
    default_project_list_output_path,
    write_project_list_csv,
)


class DummyProjectListClient:
    def __init__(self) -> None:
        self.institutions = {
            "inst-child": Institution(
                lrz_id="inst-child",
                bezeichnung="[TUINI15] Chair",
                parent_ids=["inst-parent"],
            ),
            "inst-parent": Institution(
                lrz_id="inst-parent",
                bezeichnung="TUM",
                parent_ids=[],
            ),
            "inst-lmu": Institution(
                lrz_id="inst-lmu",
                bezeichnung="LMU",
                parent_ids=[],
            ),
        }

    def list_groups(self, service: str):
        assert service == "AI"
        return [
            "pr28to-ai-c",
            "pr28to-ai-h-mcml",
            "pr99xy-ai-c",
            "other-group",
        ]

    def get_project_institution_links(self, project_name: str):
        links = {
            "pr28to": [
                ProjectInstitutionLink(
                    projektname="pr28to",
                    einrichtungs_id="inst-child",
                    link="",
                )
            ],
            "pr99xy": [
                ProjectInstitutionLink(
                    projektname="pr99xy",
                    einrichtungs_id="inst-lmu",
                    link="",
                )
            ],
        }
        return links[project_name]

    def get_institution(self, institution_id: str):
        return self.institutions[institution_id]


def test_collect_project_list_derives_partner_and_top_institution():
    client = DummyProjectListClient()

    result = collect_project_list(client, service="AI")

    assert result.issues == []
    assert [(entry.project_id, entry.partner, entry.institution) for entry in result.entries] == [
        ("pr28to", "mcml", "TUM"),
        ("pr99xy", "", "LMU"),
    ]


def test_collect_project_list_test_sample_size_validation():
    client = DummyProjectListClient()

    result = collect_project_list(client, service="AI", test_sample_size=0)

    assert result.entries == []
    assert result.issues == ["Test sample size must be a positive integer."]


def test_write_project_list_csv_creates_default_folder(tmp_path):
    entries = []
    output_path = tmp_path / "output" / "2026-02-11" / "project-list.csv"

    write_project_list_csv(entries, output_path)

    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").strip() == "ProjectID,Partner,Institution"


def test_default_project_list_output_path_uses_today_date():
    assert (
        default_project_list_output_path(date(2026, 2, 11)).as_posix()
        == "output/2026-02-11/project-list.csv"
    )
