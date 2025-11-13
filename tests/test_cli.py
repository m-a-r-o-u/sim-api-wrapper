"""Tests for the sim-app CLI entry point."""

from __future__ import annotations

from typing import List

import pytest

from sim_app import cli


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


def test_all_users_global_test_flag_before_subcommand(
    monkeypatch: pytest.MonkeyPatch, stub_client
):
    captured = _capture_all_users(monkeypatch)

    exit_code = cli.main(["--test", "2", "all-users-emails"])

    assert exit_code == 0
    assert captured == {"service": "AI", "test": 2}
    assert stub_client[0].closed is True


def test_all_users_global_test_flag_after_subcommand(
    monkeypatch: pytest.MonkeyPatch, stub_client
):
    captured = _capture_all_users(monkeypatch)

    exit_code = cli.main(["all-users-emails", "--test", "2"])

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
