"""Command line entry point for interacting with the SIM API wrapper."""

from __future__ import annotations

import argparse
import codecs
import logging
import sys
import textwrap
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Iterable

from .client import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, SimApiClient
from .command_handlers import build_command_handlers
from .commands import COMMAND_SPECS, CommandSpec
from .formatters import emit_delimited, emit_json, emit_plain, emit_yaml, parse_fields


class CustomHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Formatter that keeps newlines and shows argument defaults."""

    def _format_action(self, action: argparse.Action) -> str:
        if isinstance(action, argparse._SubParsersAction):
            return ""
        return super()._format_action(action)

def _build_description() -> str:
    lines = ["Interact with the LRZ SIM API.", "", "Command overview:"]
    longest = max(len(spec.name) for spec in COMMAND_SPECS)
    for group, specs in _grouped_specs():
        lines.append(f"  {group}:")
        for spec in specs:
            lines.append(f"    {spec.name.ljust(longest)}  {spec.description}")
        lines.append("")
    lines.append("Use 'sim COMMAND --help' for command-specific options.")
    return "\n".join(lines).rstrip()


def _grouped_specs() -> Iterable[tuple[str, list[CommandSpec]]]:
    ordered_groups: list[str] = []
    grouped: dict[str, list[CommandSpec]] = {}

    for spec in COMMAND_SPECS:
        if spec.group not in grouped:
            ordered_groups.append(spec.group)
            grouped[spec.group] = []
        grouped[spec.group].append(spec)

    return [(group, grouped[group]) for group in ordered_groups]


def configure_logging(verbosity: int) -> None:
    """Configure the root logger according to the desired verbosity."""

    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        add_help=False,
        usage="sim COMMAND [OPTIONS]",
        description=_build_description(),
        epilog=textwrap.dedent(
            """
            Examples:
              sim environment
              sim group-members AI my-group
              sim user USERID --format yaml --fields username,email
            """
        ),
        formatter_class=CustomHelpFormatter,
    )
    parser._optionals.title = "Options"
    parser.add_argument("-h", "--help", action="help", help="Show this help message and exit")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (use -vv for debug logs).",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Override the API base URL.")
    parser.add_argument("--netrc", default=None, help="Path to a netrc file for authentication.")
    parser.add_argument(
        "--no-netrc",
        action="store_true",
        help="Disable automatic loading of ~/.netrc credentials.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Timeout in seconds for API requests (default: %(default)s).",
    )
    parser.add_argument(
        "--format",
        choices=("yaml", "plain", "delimited"),
        default="json",
        metavar="FORMAT",
        help="Output format like {yaml,plain,delimited}.",
    )
    parser.add_argument(
        "--sep",
        default=",",
        help="Separator used when formatting delimited lists (default: '%(default)s').",
    )
    parser.add_argument(
        "--fields",
        default=None,
        help="Comma-separated list of fields to include in the output.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
    )

    for spec in COMMAND_SPECS:
        subparser = subparsers.add_parser(
            spec.name,
            help=spec.description,
            formatter_class=CustomHelpFormatter,
        )
        for arg in spec.args:
            kwargs: dict[str, Any] = {"help": arg.help}
            dest = arg.dest
            if dest:
                kwargs["dest"] = dest
            if arg.placeholder:
                kwargs["metavar"] = arg.placeholder
            nargs = arg.nargs if arg.nargs is not None else ("*" if arg.from_stdin else None)
            if nargs is not None:
                kwargs["nargs"] = nargs
            subparser.add_argument(*arg.flags, **kwargs)

    return parser


def _normalise_global_options(
    parser: argparse.ArgumentParser, argv: list[str] | None
) -> list[str]:
    """Allow global options to appear either before or after the subcommand."""

    arguments = list(argv) if argv is not None else sys.argv[1:]
    if not arguments:
        return arguments

    subcommands: set[str] = set()
    for action in parser._actions:  # pragma: no cover - argparse internals are stable
        if isinstance(action, argparse._SubParsersAction):
            subcommands.update(action.choices)

    command_index = next(
        (index for index, token in enumerate(arguments) if token in subcommands),
        None,
    )
    if command_index is None:
        return arguments

    prefix = arguments[:command_index]
    command_and_tail = arguments[command_index:]

    reordered_globals: list[str] = []
    remainder: list[str] = [command_and_tail[0]]

    index = 1
    while index < len(command_and_tail):
        token = command_and_tail[index]

        consumed = _consume_global_option(token, command_and_tail, index, reordered_globals)
        if consumed:
            index += consumed
            continue

        remainder.append(token)
        index += 1

    return prefix + reordered_globals + remainder


def _consume_global_option(
    token: str, command_and_tail: list[str], index: int, reordered_globals: list[str]
) -> int:
    """Append recognised global options to ``reordered_globals``.

    Returns the number of tokens consumed (including ``token``) if the option is
    recognised, otherwise returns ``0``.
    """

    options_with_values = {
        "--base-url": 1,
        "--netrc": 1,
        "--timeout": 1,
        "--format": 1,
        "--sep": 1,
        "--fields": 1,
    }
    flag_options = {"--no-netrc"}

    for option, value_count in options_with_values.items():
        if token == option:
            reordered_globals.append(token)
            for offset in range(1, value_count + 1):
                if index + offset < len(command_and_tail):
                    reordered_globals.append(command_and_tail[index + offset])
            return 1 + value_count
        if value_count and token.startswith(f"{option}="):
            reordered_globals.append(token)
            return 1

    if token in flag_options or _is_verbose_short_option(token):
        reordered_globals.append(token)
        return 1

    return 0


def _is_verbose_short_option(token: str) -> bool:
    """Return whether ``token`` represents the ``-v``/``-vv`` verbosity flags."""

    return token.startswith("-") and token.lstrip("-") and set(token.lstrip("-")) == {"v"}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(_normalise_global_options(parser, argv))
    configure_logging(args.verbose)
    handlers = build_command_handlers()

    handler = handlers.get(args.command)
    if handler is None:  # pragma: no cover - argparse ensures this is unreachable
        parser.error(f"Unknown command: {args.command}")

    with SimApiClient(
        base_url=args.base_url,
        netrc_path=args.netrc,
        timeout=args.timeout,
        use_netrc=not args.no_netrc,
    ) as client:
        result = handler(args, client, parser)

    payload = _prepare_payload(result)
    formatter = _select_formatter(args.format, payload)
    fields = parse_fields(args.fields)
    separator = _decode_separator(args.sep)
    text = formatter(
        payload,
        fields=fields,
        separator=separator,
    )
    print(text)
    return 0


def _prepare_payload(result: Any) -> Any:
    if is_dataclass(result):
        return asdict(result)
    if isinstance(result, list) and result and is_dataclass(result[0]):
        return [asdict(item) for item in result]
    return result


def _select_formatter(fmt: str | None, payload: Any) -> Callable[..., str]:
    mapping: dict[str | None, Callable[..., str]] = {
        None: emit_json,
        "json": emit_json,
        "yaml": emit_yaml,
        "plain": emit_plain,
        "delimited": emit_delimited,
    }
    if fmt == "delimited" and isinstance(payload, dict):
        fmt = None
    try:
        return mapping[fmt]
    except KeyError:  # pragma: no cover - argparse restricts format
        raise ValueError(f"Unsupported format: {fmt}")


def _decode_separator(value: str) -> str:
    """Interpret escape sequences in separators from CLI arguments."""

    try:
        return codecs.decode(value, "unicode_escape")
    except Exception:
        return value


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
