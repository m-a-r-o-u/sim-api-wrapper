from __future__ import annotations

import pytest

from sim_app.ai_systems import (
    AiSystemsCollectionError,
    AiSystemsMcmlCollectionError,
    collect_ai_system_mcml_user_emails,
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
            "aisystems-main-ai-h-mcml",
            "unrelated-group",
        ],
        members={
            "a1101-ai-c": ["zz99", "ga42qip"],
            "a1101-ai-h-mcml": ["ga42qip", "new01"],
            "aisystems-main-ai-h-mcml": ["new01", "mcmluser"],
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
        "No AI compute or MCML groups found. Expected suffixes: '-ai-c' or '-ai-h-mcml'."
    ]


def test_collect_ai_system_user_emails_group_listing_failure():
    client = FakeClient(groups=SimApiError("boom"), members={}, users={})

    with pytest.raises(AiSystemsCollectionError):
        collect_ai_system_user_emails(client)


def test_collect_ai_system_mcml_user_emails_success():
    client = FakeClient(
        groups=[
            "central-ai-h-mcml",
            "ops-ai-h-mcml",
            "aisystems-other",
            "a1101-ai-h-mcml",
        ],
        members={
            "central-ai-h-mcml": ["mcml1", "mcml2"],
            "ops-ai-h-mcml": ["mcml2", "mcml3"],
            "a1101-ai-h-mcml": ["mcml4"],
        },
        users={
            "mcml1": User(
                kennung="mcml1",
                daten={
                    "emailadressen": [
                        {"typ": "hauptemail", "adresse": "one@example.com"}
                    ]
                },
            ),
            "mcml2": User(
                kennung="mcml2",
                daten={
                    "emailadressen": [
                        {"typ": "kontaktemail", "adresse": "two@example.com"}
                    ]
                },
            ),
            "mcml3": User(
                kennung="mcml3",
                daten={
                    "emailadressen": [
                        {"typ": "kontaktemail", "adresse": "three@example.com"}
                    ]
                },
            ),
            "mcml4": User(
                kennung="mcml4",
                daten={"emailadressen": [{"typ": "backup", "adresse": "skip"}]},
            ),
        },
    )

    result = collect_ai_system_mcml_user_emails(client)

    assert result.emails == [
        "one@example.com",
        "three@example.com",
        "two@example.com",
    ]
    assert (
        "No hauptemail or kontaktemail address available for user mcml4." in result.issues
    )


def test_collect_ai_system_mcml_user_emails_with_test_sample_size():
    client = FakeClient(
        groups=[
            "central-ai-h-mcml",
            "ops-ai-h-mcml",
            "aisystems-ai-h-mcml",
        ],
        members={
            "central-ai-h-mcml": ["mcml1"],
            "ops-ai-h-mcml": ["mcml2"],
            "aisystems-ai-h-mcml": ["mcml3"],
        },
        users={
            "mcml1": User(
                kennung="mcml1",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "one@example.com"}]},
            ),
            "mcml2": User(
                kennung="mcml2",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "two@example.com"}]},
            ),
            "mcml3": User(
                kennung="mcml3",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "three@example.com"}]},
            ),
        },
    )

    result = collect_ai_system_mcml_user_emails(client, test_sample_size=2)

    assert result.emails == ["one@example.com", "three@example.com"]
    assert "two@example.com" not in result.emails


def test_collect_ai_system_mcml_user_emails_requires_positive_sample():
    client = FakeClient(groups=["central-ai-h-mcml"], members={}, users={})

    result = collect_ai_system_mcml_user_emails(client, test_sample_size=0)

    assert result.emails == []
    assert result.issues == ["Test sample size must be a positive integer."]


def test_collect_ai_system_mcml_user_emails_no_groups():
    client = FakeClient(groups=["aisystems"], members={}, users={})

    result = collect_ai_system_mcml_user_emails(client)

    assert result.emails == []
    assert result.issues == [
        "No AI Systems MCML groups found. Expected names ending with '-ai-h-mcml'."
    ]


def test_collect_ai_system_mcml_user_emails_group_listing_failure():
    client = FakeClient(groups=SimApiError("boom"), members={}, users={})

    with pytest.raises(AiSystemsMcmlCollectionError):
        collect_ai_system_mcml_user_emails(client)
