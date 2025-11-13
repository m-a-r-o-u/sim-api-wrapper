from __future__ import annotations

import pytest

from sim_app.ai_systems import (
    AiSystemsCollectionError,
    collect_ai_system_user_emails,
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

    def close(self):  # pragma: no cover - compatibility with context usage
        return None


def test_collect_ai_system_user_emails_success():
    client = FakeClient(
        groups=[
            "a1101-ai-c",
            "a1101-ai-h-mcml",
            "aisystems-h-mcml",
            "unrelated-group",
        ],
        members={
            "a1101-ai-c": ["zz99", "ga42qip"],
            "a1101-ai-h-mcml": ["ga42qip", "new01"],
            "aisystems-h-mcml": ["new01", "mcmluser"],
        },
        users={
            "ga42qip": User(
                kennung="ga42qip",
                daten={
                    "emailadressen": [
                        {"typ": "hauptemail", "adresse": "ga@example.com"}
                    ]
                },
            ),
            "new01": User(
                kennung="new01",
                daten={
                    "emailadressen": [
                        {"typ": "kontaktemail", "adresse": "new@example.com"}
                    ]
                },
            ),
            "mcmluser": User(
                kennung="mcmluser",
                daten={
                    "emailadressen": [
                        {"typ": "backup", "adresse": "ignore@example.com"}
                    ]
                },
            ),
        },
    )

    result = collect_ai_system_user_emails(client)

    assert result.emails == ["ga@example.com", "new@example.com"]
    assert (
        "No hauptemail or kontaktemail address available for user mcmluser." in result.issues
    )
    assert "Unexpected payload when retrieving user zz99." in result.issues


def test_collect_ai_system_user_emails_with_test_sample_size():
    client = FakeClient(
        groups=["a1101-ai-c", "a1102-ai-c", "a1103-ai-c"],
        members={
            "a1101-ai-c": ["ga42qip"],
            "a1102-ai-c": ["new01"],
            "a1103-ai-c": ["other"],
        },
        users={
            "ga42qip": User(
                kennung="ga42qip",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "ga@example.com"}]},
            ),
            "new01": User(
                kennung="new01",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "new@example.com"}]},
            ),
            "other": User(
                kennung="other",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "other@example.com"}]},
            ),
        },
    )

    result = collect_ai_system_user_emails(client, test_sample_size=2)

    assert result.emails == ["ga@example.com", "new@example.com"]
    assert "other@example.com" not in result.emails


def test_collect_ai_system_user_emails_handles_failures():
    client = FakeClient(
        groups=["a1101-ai-c"],
        members={"a1101-ai-c": SimApiError("boom")},
        users={},
    )

    result = collect_ai_system_user_emails(client)

    assert result.emails == []
    assert result.issues == ["Failed to fetch members for group a1101-ai-c: boom"]


def test_collect_ai_system_user_emails_requires_positive_sample():
    client = FakeClient(groups=["a1101-ai-c"], members={}, users={})

    result = collect_ai_system_user_emails(client, test_sample_size=0)

    assert result.emails == []
    assert result.issues == ["Test sample size must be a positive integer."]


def test_collect_ai_system_user_emails_no_groups():
    client = FakeClient(groups=["unrelated"], members={}, users={})

    result = collect_ai_system_user_emails(client)

    assert result.emails == []
    assert result.issues == [
        "No AI compute or MCML groups found. Expected suffixes: '-ai-c' or one of -ai-h-mcml, -h-mcml."
    ]


def test_collect_ai_system_user_emails_group_listing_failure():
    client = FakeClient(groups=SimApiError("boom"), members={}, users={})

    with pytest.raises(AiSystemsCollectionError):
        collect_ai_system_user_emails(client)
