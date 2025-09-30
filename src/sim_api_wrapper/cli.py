"""Command line entry point for interacting with the SIM API wrapper."""

from __future__ import annotations

import argparse
import codecs
import logging
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

from .client import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, SimApiClient
from .formatters import (
    emit_delimited,
    emit_json,
    emit_kv,
    emit_lines,
    emit_table,
    parse_fields,
)


def configure_logging(verbosity: int) -> None:
    """Configure the root logger according to the desired verbosity."""

    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def build_parser() -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Override the API base URL.")
    common.add_argument("--netrc", default=None, help="Path to a netrc file for authentication.")
    common.add_argument(
        "--no-netrc",
        action="store_true",
        help="Disable automatic loading of ~/.netrc credentials.",
    )
    common.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Timeout in seconds for API requests (default: %(default)s).",
    )
    common.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (use -vv for debug logs).",
    )

    common.add_argument(
        "--format",
        choices=("json", "kv", "lines", "delimited", "table"),
        default="json",
        help="Output format for the response (default: %(default)s).",
    )
    common.add_argument(
        "--sep",
        default=",",
        help="Separator used for delimited and table formats (default: '%(default)s').",
    )
    common.add_argument(
        "--fields",
        default=None,
        help="Comma-separated list of fields to include in the output.",
    )
    common.add_argument(
        "--no-header",
        action="store_true",
        help="Omit header row when using delimited or table formats.",
    )

    parser = argparse.ArgumentParser(description="Interact with the LRZ SIM API.", parents=[common])
    subparsers = parser.add_subparsers(dest="command", required=True)

    groups = subparsers.add_parser("groups", help="List all available project groups.")
    groups.add_argument("service", help="Service identifier, e.g. AI.")

    members = subparsers.add_parser("group-members", help="List members of a project group.")
    members.add_argument("group_name", help="Name of the group to inspect.")
    members.add_argument(
        "--solve",
        action="store_true",
        help="Resolve nested group memberships via the 'solve' query parameter.",
    )

    project = subparsers.add_parser("project-institution", help="Resolve institution links for a project.")
    project.add_argument("project_name", help="Project identifier, e.g. pn69ju.")

    institution = subparsers.add_parser("institution", help="Fetch institution details by ID.")
    institution.add_argument("institution_id", help="Institution LRZ identifier.")

    person = subparsers.add_parser("person", help="Fetch person details by LRZ ID.")
    person.add_argument("person_id", help="LRZ identifier for the person.")

    user = subparsers.add_parser("user", help="Fetch user details by username.")
    user.add_argument("username", help="SIM username / Kennung.")

    return parser, common


def main(argv: list[str] | None = None) -> int:
    parser, common = build_parser()
    global_args, remaining = common.parse_known_args(argv)
    args = parser.parse_args(remaining, namespace=global_args)
    configure_logging(args.verbose)

    with SimApiClient(
        base_url=args.base_url,
        netrc_path=args.netrc,
        timeout=args.timeout,
        use_netrc=not args.no_netrc,
    ) as client:
        if args.command == "groups":
            result = client.list_groups(args.service)
        elif args.command == "group-members":
            result = client.get_group_members(args.group_name, solve=args.solve)
        elif args.command == "project-institution":
            result = client.get_project_institution_links(args.project_name)
        elif args.command == "institution":
            result = client.get_institution(args.institution_id)
        elif args.command == "person":
            result = client.get_person(args.person_id)
        elif args.command == "user":
            result = client.get_user(args.username)
        else:  # pragma: no cover - argparse ensures this is unreachable
            parser.error(f"Unknown command: {args.command}")

    payload = _prepare_payload(result)
    formatter = _select_formatter(args.format)
    fields = parse_fields(args.fields)
    separator = _decode_separator(args.sep)
    text = formatter(
        payload,
        fields=fields,
        separator=separator,
        include_header=not args.no_header,
    )
    print(text)
    return 0


def _prepare_payload(result: Any) -> Any:
    if is_dataclass(result):
        return asdict(result)
    if isinstance(result, list) and result and is_dataclass(result[0]):
        return [asdict(item) for item in result]
    return result


def _select_formatter(fmt: str) -> Callable[..., str]:
    mapping: dict[str, Callable[..., str]] = {
        "json": emit_json,
        "kv": emit_kv,
        "lines": emit_lines,
        "delimited": emit_delimited,
        "table": emit_table,
    }
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
    raise SystemExit(main())
