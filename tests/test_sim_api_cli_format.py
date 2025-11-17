"""Tests for sim-api CLI argument handling."""

from __future__ import annotations

import pytest

from sim_api_wrapper import cli


class DummyClient:
    def __init__(self, *_, **__):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.closed = True

    def get_group_members(self, service: str, group_name: str, solve: bool = False):
        self.service = service
        self.group_name = group_name
        self.solve = solve
        return ["user-a", "user-b"]


def test_global_format_flag_after_subcommand(monkeypatch: pytest.MonkeyPatch, capsys):
    instances: list[DummyClient] = []

    def factory(*args, **kwargs):
        client = DummyClient(*args, **kwargs)
        instances.append(client)
        return client

    monkeypatch.setattr(cli, "SimApiClient", factory)

    exit_code = cli.main(["group-members", "AI", "pn69ju", "--format", "plain"])

    assert exit_code == 0
    stdout = capsys.readouterr().out.splitlines()
    assert stdout == ["user-a", "user-b"]

    assert instances[0].service == "AI"
    assert instances[0].group_name == "pn69ju"
    assert instances[0].solve is False
    assert instances[0].closed is True
