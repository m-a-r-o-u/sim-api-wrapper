from __future__ import annotations

import pytest

from sim_app.user_projects import (
    UserProjectsMembershipCollectionError,
    collect_user_projects_memberships,
)
from sim_api_wrapper.exceptions import SimApiError


class FakeClient:
    def __init__(self, *, groups, members):
        self._groups = groups
        self._members = members

    def list_groups(self, service):
        if isinstance(self._groups, Exception):
            raise self._groups
        return self._groups

    def get_group_members(self, service, group):
        value = self._members.get(group)
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
    assert result.issues == []


def test_collect_user_projects_memberships_test_sample_size():
    client = FakeClient(
        groups=["a1101-ai-c", "a1102-ai-c", "a1103-ai-c"],
        members={
            "a1101-ai-c": ["user1"],
            "a1102-ai-c": ["user2"],
            "a1103-ai-c": ["user3"],
        },
    )

    result = collect_user_projects_memberships(client, test_sample_size=2)

    assert [membership.username for membership in result.memberships] == ["user1", "user2"]
    assert all("a1103" not in membership.projects for membership in result.memberships)


def test_collect_user_projects_memberships_handles_group_failure():
    client = FakeClient(
        groups=["a1101-ai-c"],
        members={"a1101-ai-c": SimApiError("boom")},
    )

    result = collect_user_projects_memberships(client)

    assert result.memberships == []
    assert result.issues == ["Failed to fetch members for group a1101-ai-c: boom"]


def test_collect_user_projects_memberships_requires_positive_sample():
    client = FakeClient(groups=["a1101-ai-c"], members={})

    result = collect_user_projects_memberships(client, test_sample_size=0)

    assert result.memberships == []
    assert result.issues == ["Test sample size must be a positive integer."]


def test_collect_user_projects_memberships_group_listing_failure():
    client = FakeClient(groups=SimApiError("boom"), members={})

    with pytest.raises(UserProjectsMembershipCollectionError):
        collect_user_projects_memberships(client)

