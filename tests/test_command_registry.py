from __future__ import annotations

import argparse

import pytest

from sim import cli, command_handlers
from sim.commands import COMMAND_SPECS, CommandArg, CommandSpec


def _argument_dest(arg: CommandArg) -> str:
    if arg.dest:
        return arg.dest
    return arg.flags[-1].lstrip("-").replace("-", "_")


def _build_args(parser: argparse.ArgumentParser, spec: CommandSpec) -> argparse.Namespace:
    tokens = [spec.name]
    for arg in spec.args:
        tokens.append(f"{_argument_dest(arg)}-value")
    return parser.parse_args(tokens)


def test_parser_contains_all_registered_commands():
    parser = cli.build_parser()
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    assert set(subparsers.choices) == {spec.name for spec in COMMAND_SPECS}


def test_handlers_dispatch_to_expected_client_methods(monkeypatch: pytest.MonkeyPatch):
    handlers = command_handlers.build_command_handlers()
    parser = cli.build_parser()

    class RecordingClient:
        def __init__(self):
            self.calls: list[tuple[str, tuple, dict]] = []

        def __getattr__(self, name: str):
            def recorder(*args, **kwargs):
                self.calls.append((name, args, kwargs))
                return name

            return recorder

    for spec in COMMAND_SPECS:
        assert spec.name in handlers
        args = _build_args(parser, spec)
        client = RecordingClient()

        result = handlers[spec.name](args, client, parser)

        assert client.calls, f"Handler for {spec.name} did not call the client"
        called_method, call_args, call_kwargs = client.calls[0]
        assert called_method == spec.client_method
        assert call_kwargs == {}
        assert result == spec.client_method
