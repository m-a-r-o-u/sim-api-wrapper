"""Tests for the sim-apps CLI entry point."""

from __future__ import annotations

import argparse
from typing import List

import pytest

from sim_app import cli
from sim_app.user_projects import UserProjectsMembership, UserProjectsMembershipResult


class DummyClient:
    def __init__(self, *, base_url, timeout, netrc_path, use_netrc):
        self.base_url = base_url
        self.timeout = timeout
        self.netrc_path = netrc_path
        self.use_netrc = use_netrc
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def stub_client(monkeypatch: pytest.MonkeyPatch) -> List[DummyClient]:
    instances: List[DummyClient] = []

    def factory(**kwargs):
        client = DummyClient(**kwargs)
        instances.append(client)
        return client

    monkeypatch.setattr(cli, "SimApiClient", factory)
    return instances


def _capture_all_users(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def runner(client, *, service: str, test_sample_size: int | None):
        captured["service"] = service
        captured["test"] = test_sample_size
        return 0

    monkeypatch.setattr(cli, "_run_all_users_emails", runner)
    return captured


def _capture_mcml(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def runner(client, *, service: str, test_sample_size: int | None):
        captured["service"] = service
        captured["test"] = test_sample_size
        return 0

    monkeypatch.setattr(cli, "_run_mcml_master_user_emails", runner)
    return captured


def _capture_mcml_users(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def runner(client, *, service: str, test_sample_size: int | None):
        captured["service"] = service
        captured["test"] = test_sample_size
        return 0

    monkeypatch.setattr(cli, "_run_mcml_user_emails", runner)
    return captured


def _capture_user_memberships(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def runner(
        client,
        *,
        service: str,
        test_sample_size: int | None,
        histogram: bool,
    ):
        captured["service"] = service
        captured["test"] = test_sample_size
        captured["histogram"] = histogram
        return 0

    monkeypatch.setattr(cli, "_run_user_projects_membership", runner)
    return captured


def _capture_institution_heads(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def runner(client, *, service: str, test_sample_size: int | None):
        captured["service"] = service
        captured["test"] = test_sample_size
        return 0

    monkeypatch.setattr(cli, "_run_institution_heads", runner)
    return captured


def test_all_users_global_test_flag_before_subcommand(
    monkeypatch: pytest.MonkeyPatch, stub_client
):
    captured = _capture_all_users(monkeypatch)

    exit_code = cli.main(["--test", "2", "all-user-emails"])

    assert exit_code == 0
    assert captured == {"service": "AI", "test": 2}
    assert stub_client[0].closed is True


def test_all_users_global_test_flag_after_subcommand(
    monkeypatch: pytest.MonkeyPatch, stub_client
):
    captured = _capture_all_users(monkeypatch)

    exit_code = cli.main(["all-user-emails", "--test", "2"])

    assert exit_code == 0
    assert captured == {"service": "AI", "test": 2}
    assert stub_client[0].closed is True


def test_global_test_flag_before_subcommand(monkeypatch: pytest.MonkeyPatch, stub_client):
    captured = _capture_mcml(monkeypatch)

    exit_code = cli.main(["--test", "2", "mcml-master-user-emails"])

    assert exit_code == 0
    assert captured == {"service": "AI", "test": 2}
    assert stub_client[0].closed is True


def test_global_test_flag_after_subcommand(monkeypatch: pytest.MonkeyPatch, stub_client):
    captured = _capture_mcml(monkeypatch)

    exit_code = cli.main(["mcml-master-user-emails", "--test", "2"])

    assert exit_code == 0
    assert captured == {"service": "AI", "test": 2}
    assert stub_client[0].closed is True


def test_verbose_short_option_is_reordered(monkeypatch: pytest.MonkeyPatch, stub_client):
    captured = _capture_mcml(monkeypatch)

    exit_code = cli.main(["mcml-master-user-emails", "-vv", "--test", "1"])

    assert exit_code == 0
    assert captured == {"service": "AI", "test": 1}
    assert stub_client[0].closed is True


def test_mcml_users_global_test_flag(monkeypatch: pytest.MonkeyPatch, stub_client):
    captured = _capture_mcml_users(monkeypatch)

    exit_code = cli.main(["mcml-user-emails", "--test", "3"])

    assert exit_code == 0
    assert captured == {"service": "AI", "test": 3}
    assert stub_client[0].closed is True


def test_mcml_users_custom_service(monkeypatch: pytest.MonkeyPatch, stub_client):
    captured = _capture_mcml_users(monkeypatch)

    exit_code = cli.main(["mcml-user-emails", "--service", "AIS", "--test", "1"])

    assert exit_code == 0
    assert captured == {"service": "AIS", "test": 1}
    assert stub_client[0].closed is True


def test_user_projects_membership_invocation(monkeypatch: pytest.MonkeyPatch, stub_client):
    captured = _capture_user_memberships(monkeypatch)

    exit_code = cli.main(["user-projects-membership", "--service", "AI", "--histogram"])

    assert exit_code == 0
    assert captured == {"service": "AI", "test": None, "histogram": True}
    assert stub_client[0].closed is True


def test_user_projects_membership_respects_test_flag(
    monkeypatch: pytest.MonkeyPatch, stub_client
):
    captured = _capture_user_memberships(monkeypatch)

    exit_code = cli.main(["user-projects-membership", "--test", "5"])

    assert exit_code == 0
    assert captured == {"service": "AI", "test": 5, "histogram": False}
    assert stub_client[0].closed is True


def test_institution_heads_invocation(monkeypatch: pytest.MonkeyPatch, stub_client):
    captured = _capture_institution_heads(monkeypatch)

    exit_code = cli.main(["list-institution-heads", "AIS"])

    assert exit_code == 0
    assert captured == {"service": "AIS", "test": None}
    assert stub_client[0].closed is True


def test_institution_heads_respects_test_flag(
    monkeypatch: pytest.MonkeyPatch, stub_client
):
    captured = _capture_institution_heads(monkeypatch)

    exit_code = cli.main(["--test", "2", "list-institution-heads"])

    assert exit_code == 0
    assert captured == {"service": "AI", "test": 2}
    assert stub_client[0].closed is True


def test_user_projects_membership_histogram_output(
    monkeypatch: pytest.MonkeyPatch, stub_client, capsys: pytest.CaptureFixture[str]
):
    memberships_result = UserProjectsMembershipResult(
        memberships=[
            UserProjectsMembership(username="user1", projects=("project-a", "project-b")),
            UserProjectsMembership(username="user2", projects=("project-c",)),
        ]
    )

    monkeypatch.setattr(cli, "collect_user_projects_memberships", lambda *_, **__: memberships_result)

    exit_code = cli.main(["user-projects-membership", "--histogram"])

    assert exit_code == 0
    assert stub_client[0].closed is True
    output = capsys.readouterr().out.splitlines()
    assert output == [
        "# Number of Projects - Number of Users",
        "1 1",
        "2 1",
    ]


def test_user_projects_membership_help_usage(monkeypatch: pytest.MonkeyPatch):
    parser = cli.build_parser()
    parser.prog = "sim-apps"

    sub_action = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    membership_parser = sub_action.choices["user-projects-membership"]

    assert (
        membership_parser.format_usage()
        == "usage: sim-apps user-projects-membership [OPTIONS] [-h]"
        " [--service SERVICE] [--histogram]\n"
    )
