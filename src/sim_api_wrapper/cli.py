"""Command line entry point for interacting with the SIM API wrapper."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from .client import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, SimApiClient


def configure_logging(verbosity: int) -> None:
    """Configure the root logger according to the desired verbosity."""

    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interact with the LRZ SIM API.")
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
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (use -vv for debug logs).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("groups", help="List all available project groups.")

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    with SimApiClient(
        base_url=args.base_url,
        netrc_path=args.netrc,
        timeout=args.timeout,
        use_netrc=not args.no_netrc,
    ) as client:
        if args.command == "groups":
            result = client.list_groups()
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

    _print_result(result)
    return 0


def _print_result(result: Any) -> None:
    if is_dataclass(result):
        payload = asdict(result)
    elif isinstance(result, list) and result and is_dataclass(result[0]):
        payload = [asdict(item) for item in result]
    else:
        payload = result

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
