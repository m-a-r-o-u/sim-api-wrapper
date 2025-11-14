from __future__ import annotations

import pytest

from sim_app.user_projects import (
    UserProjectsMembershipCollectionError,
    collect_user_projects_memberships,
)
from sim_api_wrapper.exceptions import SimApiError
from sim_api_wrapper.models import User


class FakeClient:
    def __init__(self, *, groups, members, users):
        self._groups = groups
        self._members = members
        self._users = users

    def list_groups(self, service):
        if isinstance(self._groups, Exception):
            raise self._groups
        return self._groups

    def get_group_members(self, service, group):
        value = self._members.get(group)
        if isinstance(value, Exception):
            raise value
        return value

    def get_user(self, username):
        value = self._users.get(username)
        if isinstance(value, Exception):
            raise value
        return value


def test_collect_user_projects_memberships_success():
    client = FakeClient(
        groups=[
            "a1101-ai-c",
            "a1101-ai-h-mcml",
            "a1102-ai-c",
            "b9999-ai-h-mcml",
            "ignored-group",
        ],
        members={
            "a1101-ai-c": ["user1", "user2"],
            "a1101-ai-h-mcml": ["user2"],
            "a1102-ai-c": ["user3"],
            "b9999-ai-h-mcml": ["user1", "user4"],
        },
        users={
            "user1": User(
                kennung="user1",
                daten={
                    "emailadressen": [
                        {"typ": "hauptemail", "adresse": "user1@example.com"}
                    ]
                },
            ),
            "user2": User(
                kennung="user2",
                daten={
                    "emailadressen": [
                        {"typ": "kontaktemail", "adresse": "user2@example.com"}
                    ]
                },
            ),
            "user3": User(
                kennung="user3",
                daten={
                    "emailadressen": [
                        {"typ": "hauptemail", "adresse": "user3@example.com"}
                    ]
                },
            ),
            "user4": User(
                kennung="user4",
                daten={"emailadressen": [{"typ": "backup", "adresse": "unused"}]},
            ),
        },
    )

    result = collect_user_projects_memberships(client)

    assert [membership.username for membership in result.memberships] == [
        "user1",
        "user2",
        "user3",
        "user4",
    ]
    assert result.memberships[0].projects == ("a1101", "b9999")
    assert result.memberships[1].projects == ("a1101",)
    assert result.memberships[2].projects == ("a1102",)
    assert result.memberships[3].projects == ("b9999",)
    assert result.memberships[0].email == "user1@example.com"
    assert result.memberships[3].email is None
    assert (
        "No hauptemail or kontaktemail address available for user user4." in result.issues
    )


def test_collect_user_projects_memberships_test_sample_size():
    client = FakeClient(
        groups=["a1101-ai-c", "a1102-ai-c", "a1103-ai-c"],
        members={
            "a1101-ai-c": ["user1"],
            "a1102-ai-c": ["user2"],
            "a1103-ai-c": ["user3"],
        },
        users={
            "user1": User(
                kennung="user1",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "one"}]},
            ),
            "user2": User(
                kennung="user2",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "two"}]},
            ),
            "user3": User(
                kennung="user3",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "three"}]},
            ),
        },
    )

    result = collect_user_projects_memberships(client, test_sample_size=2)

    assert [membership.username for membership in result.memberships] == ["user1", "user2"]
    assert all("a1103" not in membership.projects for membership in result.memberships)


def test_collect_user_projects_memberships_handles_group_failure():
    client = FakeClient(
        groups=["a1101-ai-c"],
        members={"a1101-ai-c": SimApiError("boom")},
        users={},
    )

    result = collect_user_projects_memberships(client)

    assert result.memberships == []
    assert result.issues == ["Failed to fetch members for group a1101-ai-c: boom"]


def test_collect_user_projects_memberships_requires_positive_sample():
    client = FakeClient(groups=["a1101-ai-c"], members={}, users={})

    result = collect_user_projects_memberships(client, test_sample_size=0)

    assert result.memberships == []
    assert result.issues == ["Test sample size must be a positive integer."]


def test_collect_user_projects_memberships_group_listing_failure():
    client = FakeClient(groups=SimApiError("boom"), members={}, users={})

    with pytest.raises(UserProjectsMembershipCollectionError):
        collect_user_projects_memberships(client)

