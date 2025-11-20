"""Factories for CLI command handlers.

This module keeps the command-to-handler mapping separate from the CLI
configuration so :mod:`sim_api_wrapper.cli` can focus on argument parsing
and output formatting. The central ``build_command_handlers`` function acts
as a simple factory that wires command names to callables invoking
:class:`~sim_api_wrapper.client.SimApiClient` methods. Each handler also
reuses small helpers for common tasks such as reading piped values and
ensuring required arguments are present.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Callable, Sequence

from .client import SimApiClient
from .commands import COMMAND_SPECS, CommandArg, CommandSpec

CommandHandler = Callable[[argparse.Namespace, SimApiClient, argparse.ArgumentParser], Any]


def _stdin_or_values(values: list[str] | None) -> list[str]:
    """Return provided values or read newline separated tokens from stdin."""

    provided = [value for value in values or [] if value]
    if provided:
        return provided

    if not sys.stdin.isatty():
        piped = [line.strip() for line in sys.stdin if line.strip()]
        if piped:
            return piped

    return []


def _require_inputs(values: list[str] | None, parser: argparse.ArgumentParser, placeholder: str) -> list[str]:
    """Ensure at least one value is available from arguments or stdin."""

    resolved = _stdin_or_values(values)
    if not resolved:
        parser.error(
            f"{placeholder} is required (provide an argument or pipe values via stdin)."
        )
    return resolved


def _run_for_values(values: list[str], func: Callable[[str], Any]) -> Any:
    """Execute a function for each value and collapse single results."""

    results = [func(value) for value in values]
    if len(results) == 1:
        return results[0]
    return results


def build_command_handlers() -> dict[str, CommandHandler]:
    """Construct the mapping of command names to handler callables."""

    return {spec.name: _build_handler(spec) for spec in COMMAND_SPECS}


def _build_handler(spec: CommandSpec) -> CommandHandler:
    streaming_arg = _streaming_arg(spec.args)

    def handler(args: argparse.Namespace, client: SimApiClient, parser: argparse.ArgumentParser) -> Any:
        method = getattr(client, spec.client_method)

        if streaming_arg is None:
            call_args = [_argument_value(arg, args) for arg in spec.args]
            return method(*call_args)

        values = _prepare_streaming_values(streaming_arg, args, parser)

        def invoke(value: str) -> Any:
            resolved_args: list[Any] = []
            for arg in spec.args:
                if arg is streaming_arg:
                    resolved_args.append(value)
                    continue
                resolved_args.append(_argument_value(arg, args))
            return method(*resolved_args)

        return _run_for_values(values, invoke)

    return handler


def _argument_value(arg: CommandArg, args: argparse.Namespace) -> Any:
    dest = _argument_dest(arg)
    return getattr(args, dest)


def _argument_dest(arg: CommandArg) -> str:
    if arg.dest:
        return arg.dest
    flag = arg.flags[-1]
    return flag.lstrip("-").replace("-", "_")


def _streaming_arg(args: Sequence[CommandArg]) -> CommandArg | None:
    return next((arg for arg in args if arg.from_stdin), None)


def _prepare_streaming_values(arg: CommandArg, args: argparse.Namespace, parser: argparse.ArgumentParser) -> list[str]:
    values = _argument_value(arg, args)
    placeholder = arg.placeholder or _argument_dest(arg)
    if arg.required:
        return _require_inputs(values, parser, placeholder)
    return _stdin_or_values(values)


__all__ = ["CommandHandler", "build_command_handlers"]
