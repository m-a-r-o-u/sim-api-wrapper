import pytest

from sim_app.project_details import (
    ProjectDetailsCollectionError,
    collect_project_details,
)
from sim.exceptions import SimApiError
from sim.models import Institution, Person, ProjectInstitutionLink, User


class FakeClient:
    def __init__(
        self,
        *,
        groups,
        links,
        institutions,
        people,
        master_users,
        users,
        members,
    ):
        self._groups = groups
        self._links = links
        self._institutions = institutions
        self._people = people
        self._master_users = master_users
        self._users = users
        self._members = members

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

    def get_project_master_users(self, project):
        value = self._master_users.get(project, [])
        if isinstance(value, Exception):
            raise value
        return value

    def get_user(self, username):
        value = self._users.get(username)
        if isinstance(value, Exception):
            raise value
        return value

    def get_group_members(self, service, group_name):
        value = self._members.get(group_name, [])
        if isinstance(value, Exception):
            raise value
        return value


def test_collect_project_details_success():
    client = FakeClient(
        groups=["pn1-ai-c", "pn1-ai-h-mcml", "pn2-mcml-ai-h"],
        links={
            "pn1": [ProjectInstitutionLink("pn1", "inst1", "")],
            "pn2": [ProjectInstitutionLink("pn2", "inst2", "")],
        },
        institutions={
            "inst1": Institution(lrz_id="inst1", chef_lrz_id="head1"),
            "inst2": Institution(lrz_id="inst2", chef_lrz_id="head2"),
        },
        people={
            "head1": Person(
                lrz_id="head1",
                benutzername="user1",
                titel_pre="Prof.",
                rufname="Ada",
                nachname="Lovelace",
            ),
            "head2": Person(lrz_id="head2", benutzername="user2", rufname="Grace"),
        },
        master_users={
            "pn1": ["mu1", "mu2"],
            "pn2": ["mu3"],
        },
        users={
            "mu1": User(
                kennung="mu1",
                daten={"titelPre": "Prof.", "vorname": "Ada", "nachname": "Lovelace"},
            ),
            "mu2": User(kennung="mu2", daten={"nachname": "Doe"}),
            "mu3": User(kennung="mu3", daten={"vorname": "Grace", "nachname": "Hopper"}),
        },
        members={
            "pn1-ai-c": ["user1", "user2"],
            "pn1-ai-h-mcml": ["user2", "user3"],
            "pn2-mcml-ai-h": ["user4"],
        },
    )

    result = collect_project_details(client)

    assert [(entry.project_id, entry.head_of_institution) for entry in result.entries] == [
        ("pn1", "Prof. Ada Lovelace (user1)"),
        ("pn2", "Grace (user2)"),
    ]
    assert [entry.master_users for entry in result.entries] == [
        ("Prof. Ada Lovelace (mu1)", "Doe (mu2)"),
        ("Grace Hopper (mu3)",),
    ]
    assert [entry.users for entry in result.entries] == [
        ("user1", "user2", "user3"),
        ("user4",),
    ]
    assert [entry.is_mcml for entry in result.entries] == [True, False]
    assert result.issues == []


def test_collect_project_details_filter_and_sample():
    client = FakeClient(
        groups=["pn1-ai-c", "pn1-ai-h-mcml", "pn2-mcml-ai-h", "pn3-ai-c"],
        links={"pn1": [ProjectInstitutionLink("pn1", "inst1", "")]},
        institutions={"inst1": Institution(lrz_id="inst1", chef_lrz_id="head1")},
        people={"head1": Person(lrz_id="head1", benutzername="user1", nachname="Doe")},
        master_users={"pn1": ["mu1"]},
        users={"mu1": User(kennung="mu1", daten={"nachname": "Doe"})},
        members={"pn1-ai-h-mcml": ["user1"]},
    )

    result = collect_project_details(client, group_filter="*mcml*", test_sample_size=1)

    assert [entry.project_id for entry in result.entries] == ["pn1"]
    assert [entry.is_mcml for entry in result.entries] == [True]
    assert result.issues == []


def test_collect_project_details_invalid_sample_size():
    client = FakeClient(
        groups=["pn1-ai-c"],
        links={},
        institutions={},
        people={},
        master_users={},
        users={},
        members={},
    )

    result = collect_project_details(client, test_sample_size=0)

    assert result.entries == []
    assert result.issues == ["Test sample size must be a positive integer."]


def test_collect_project_details_group_listing_failure():
    client = FakeClient(
        groups=SimApiError("boom"),
        links={},
        institutions={},
        people={},
        master_users={},
        users={},
        members={},
    )

    with pytest.raises(ProjectDetailsCollectionError):
        collect_project_details(client)
