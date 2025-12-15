import pytest

from sim_app.institution_heads import (
    InstitutionHeadsCollectionError,
    collect_institution_heads,
)
from sim.exceptions import SimApiError
from sim.models import Institution, Person, ProjectInstitutionLink


class FakeClient:
    def __init__(self, *, groups, links, institutions, people):
        self._groups = groups
        self._links = links
        self._institutions = institutions
        self._people = people

    def list_groups(self, service):
        if isinstance(self._groups, Exception):
            raise self._groups
        return self._groups

    def get_project_institution_links(self, project):
        value = self._links.get(project, [])
        if isinstance(value, Exception):
            raise value
        return value

    def get_institution(self, institution_id):
        value = self._institutions.get(institution_id)
        if isinstance(value, Exception):
            raise value
        return value

    def get_person(self, person_id):
        value = self._people.get(person_id)
        if isinstance(value, Exception):
            raise value
        return value


def test_collect_institution_heads_success():
    client = FakeClient(
        groups=["pn25hu-ai-c", "pn25hu-ai-h-mcml", "pn30ab-ai-c", "ignored-group"],
        links={
            "pn25hu": [ProjectInstitutionLink("pn25hu", "inst1", "")],
            "pn30ab": [ProjectInstitutionLink("pn30ab", "inst2", "")],
        },
        institutions={
            "inst1": Institution(lrz_id="inst1", chef_lrz_id="head1"),
            "inst2": Institution(lrz_id="inst2", chef_lrz_id="head2"),
        },
        people={
            "head1": Person(
                lrz_id="head1",
                benutzername="lu24bak",
                titel_pre="Prof. Dr.",
                rufname="Thomas",
                nachname="Augustin",
            ),
            "head2": Person(lrz_id="head2", benutzername="user2", rufname="Jane", nachname="Doe"),
        },
    )

    result = collect_institution_heads(client)

    assert [(head.project_id, head.formatted_name) for head in result.heads] == [
        ("pn25hu", "Prof. Dr. Thomas Augustin (lu24bak)"),
        ("pn30ab", "Jane Doe (user2)"),
    ]
    assert result.issues == []


def test_collect_institution_heads_falls_back_to_parent():
    client = FakeClient(
        groups=["pn25hu-ai-c"],
        links={"pn25hu": [ProjectInstitutionLink("pn25hu", "inst1", "")]},
        institutions={
            "inst1": Institution(lrz_id="inst1", chef_lrz_id="", parent_ids=["parent1"]),
            "parent1": Institution(lrz_id="parent1", chef_lrz_id="head1"),
        },
        people={"head1": Person(lrz_id="head1", benutzername="user1", nachname="Doe")},
    )

    result = collect_institution_heads(client)

    assert [(head.project_id, head.formatted_name) for head in result.heads] == [
        ("pn25hu", "Doe (user1)"),
    ]
    assert result.issues == [
        "No institution head set on institution inst1 for project pn25hu; searching parent institutions: parent1.",
        "No institution head set on institution inst1 for project pn25hu; using parent institution parent1.",
    ]


def test_collect_institution_heads_multiple_heads():
    client = FakeClient(
        groups=["pn25hu-ai-c"],
        links={"pn25hu": [ProjectInstitutionLink("pn25hu", "inst1", "")]},
        institutions={"inst1": Institution(lrz_id="inst1", chef_lrz_id="head1;head2 ; head3")},
        people={
            "head1": Person(lrz_id="head1", benutzername="user1", rufname="Jane"),
            "head2": Person(lrz_id="head2", benutzername="user2", nachname="Doe"),
            "head3": SimApiError(None),
        },
    )

    result = collect_institution_heads(client)

    assert [(head.project_id, head.formatted_name) for head in result.heads] == [
        ("pn25hu", "Jane (user1), Doe (user2)"),
    ]
    assert result.issues == [
        "Failed to retrieve person head3 for project pn25hu: None",
    ]


def test_collect_institution_heads_parent_search_fails():
    client = FakeClient(
        groups=["pn25hu-ai-c"],
        links={"pn25hu": [ProjectInstitutionLink("pn25hu", "inst1", "")]},
        institutions={
            "inst1": Institution(lrz_id="inst1", chef_lrz_id="", parent_ids=["parent1"]),
            "parent1": Institution(lrz_id="parent1", chef_lrz_id=None),
        },
        people={},
    )

    result = collect_institution_heads(client)

    assert result.heads == []
    assert result.issues == [
        "No institution head set on institution inst1 for project pn25hu; searching parent institutions: parent1.",
        "No institution head found for institution inst1 or its parents (project pn25hu).",
    ]


def test_collect_institution_heads_test_sample_size():
    client = FakeClient(
        groups=["pn25hu-ai-c", "pn30ab-ai-c"],
        links={"pn25hu": [ProjectInstitutionLink("pn25hu", "inst1", "")]},
        institutions={"inst1": Institution(lrz_id="inst1", chef_lrz_id="head1")},
        people={"head1": Person(lrz_id="head1", benutzername="user1", rufname="Jane")},
    )

    result = collect_institution_heads(client, test_sample_size=1)

    assert [head.project_id for head in result.heads] == ["pn25hu"]
    assert result.issues == []


def test_collect_institution_heads_handles_errors():
    client = FakeClient(
        groups=["pn25hu-ai-c"],
        links={"pn25hu": SimApiError("boom")},
        institutions={},
        people={},
    )

    result = collect_institution_heads(client)

    assert result.heads == []
    assert result.issues == ["Failed to fetch institution links for project pn25hu: boom"]


def test_collect_institution_heads_group_listing_failure():
    client = FakeClient(
        groups=SimApiError("boom"), links={}, institutions={}, people={}
    )

    with pytest.raises(InstitutionHeadsCollectionError):
        collect_institution_heads(client)


def test_collect_institution_heads_requires_positive_sample():
    client = FakeClient(groups=["pn25hu-ai-c"], links={}, institutions={}, people={})

    result = collect_institution_heads(client, test_sample_size=0)

    assert result.heads == []
    assert result.issues == ["Test sample size must be a positive integer."]
