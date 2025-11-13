"""Tests for the SIM app MCML helpers."""

from __future__ import annotations

import pytest

import warnings

from sim_app.mcml import McmlCollectionError, collect_mcml_master_user_emails
from sim_api_wrapper.models import User
from sim_api_wrapper.exceptions import SimApiError


class FakeClient:
    def __init__(self, *, groups, master_users, users):
        self._groups = groups
        self._master_users = master_users
        self._users = users

    def list_groups(self, service):
        if isinstance(self._groups, Exception):
            raise self._groups
        return self._groups

    def get_project_master_users(self, project):
        value = self._master_users.get(project)
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


def test_collect_mcml_master_user_emails_success():
    client = FakeClient(
        groups=[
            "pr92no-ai-h-mcml",
            "pr92no-ai-c",
            "pr92to-ai-h-mcml",
            "pr92to-ai-c",
        ],
        master_users={
            "pr92no": ["ga42qip", "ga42qip2"],
            "pr92to": ["ab12", "zz99"],
        },
        users={
            "ga42qip": User(kennung="ga42qip", daten={"emailadressen": [{"typ": "hauptemail", "adresse": "ga@example.com"}]}),
            "ab12": User(kennung="ab12", daten={"emailadressen": [{"typ": "hauptemail", "adresse": "ab@example.com"}]}),
            "zz99": User(kennung="zz99", daten={"emailadressen": [{"typ": "backup", "adresse": "zz@example.com"}]}),
        },
    )

    result = collect_mcml_master_user_emails(client)

    assert result.emails == ["ab@example.com", "ga@example.com"]
    assert (
        "No hauptemail or kontaktemail address available for user zz99." in result.issues
    )


def test_collect_mcml_master_user_emails_falls_back_to_kontaktemail():
    client = FakeClient(
        groups=["pr92no-ai-h-mcml"],
        master_users={"pr92no": ["ga42qip", "zz99"]},
        users={
            "ga42qip": User(
                kennung="ga42qip",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "ga@example.com"}]},
            ),
            "zz99": User(
                kennung="zz99",
                daten={"emailadressen": [{"typ": "kontaktemail", "adresse": "contact@example.com"}]},
            ),
        },
    )

    result = collect_mcml_master_user_emails(client)

    assert result.emails == ["contact@example.com", "ga@example.com"]
    assert result.issues == []


def test_collect_mcml_master_user_emails_with_project_limit():
    client = FakeClient(
        groups=[
            "pr92no-ai-h-mcml",
            "pr92to-ai-h-mcml",
            "pr93xy-ai-h-mcml",
        ],
        master_users={
            "pr92no": ["ga42qip"],
            "pr92to": ["ab12"],
            "pr93xy": ["zz99"],
        },
        users={
            "ga42qip": User(
                kennung="ga42qip",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "ga@example.com"}]},
            ),
            "ab12": User(
                kennung="ab12",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "ab@example.com"}]},
            ),
            "zz99": User(
                kennung="zz99",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "zz@example.com"}]},
            ),
        },
    )

    result = collect_mcml_master_user_emails(client, test_sample_size=2)

    assert result.emails == ["ab@example.com", "ga@example.com"]
    assert (
        "No hauptemail or kontaktemail address available for user zz99." not in result.issues
    )


def test_collect_mcml_master_user_emails_no_groups():
    client = FakeClient(groups=["pr92no-ai-c"], master_users={}, users={})

    result = collect_mcml_master_user_emails(client)

    assert result.emails == []
    assert result.issues == ["No MCML master groups ending with '-ai-h-mcml' found for service AI."]


def test_collect_mcml_master_user_emails_group_failure():
    client = FakeClient(groups=SimApiError("boom"), master_users={}, users={})

    with pytest.raises(McmlCollectionError):
        collect_mcml_master_user_emails(client)


def test_collect_mcml_master_user_emails_with_invalid_limit():
    client = FakeClient(
        groups=["pr92no-ai-h-mcml"],
        master_users={"pr92no": ["ga42qip"]},
        users={},
    )

    result = collect_mcml_master_user_emails(client, test_sample_size=0)

    assert result.emails == []
    assert result.issues == ["Test sample size must be a positive integer."]


def test_collect_mcml_master_user_emails_with_deprecated_project_limit():
    client = FakeClient(
        groups=[
            "pr92no-ai-h-mcml",
            "pr92to-ai-h-mcml",
        ],
        master_users={
            "pr92no": ["ga42qip"],
            "pr92to": ["ab12"],
        },
        users={
            "ga42qip": User(
                kennung="ga42qip",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "ga@example.com"}]},
            ),
            "ab12": User(
                kennung="ab12",
                daten={"emailadressen": [{"typ": "hauptemail", "adresse": "ab@example.com"}]},
            ),
        },
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        result = collect_mcml_master_user_emails(client, project_limit=1)

    assert result.emails == ["ga@example.com"]
    assert len(caught) == 1
    assert issubclass(caught[0].category, DeprecationWarning)
