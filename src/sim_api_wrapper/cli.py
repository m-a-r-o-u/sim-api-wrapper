"""Command line entry point for interacting with the SIM API wrapper."""

from __future__ import annotations

import argparse
import codecs
import logging
import textwrap
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


class CustomHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Formatter that keeps newlines and shows argument defaults."""


COMMAND_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "General",
        [
            ("environment", "Show SIM backend environment information."),
            ("current-user", "Show the currently authenticated SIM identity."),
            ("service-characteristics", "Display service-specific group characteristics."),
        ],
    ),
    (
        "Groups",
        [
            ("groups", "List all available project groups."),
            ("group-info", "Show metadata for a project group."),
            ("group-rights", "Show resolved rights for a user within a project group."),
            ("group-members", "List members of a project group."),
            ("group-admins", "List administrators of a project group."),
        ],
    ),
    (
        "Group membership checks",
        [
            ("is-group-member", "Check if a user is member of a project group."),
            ("is-group-master", "Check if a user is a master user of a project group."),
            ("is-group-admin", "Check if a user administers a project group."),
            ("project-master-users", "List master user identifiers for a project."),
        ],
    ),
    (
        "Services",
        [
            ("service-projects", "List projects that currently have a quota for a service."),
            ("managed-groups", "List groups a user can manage for a service."),
            ("group-memberships", "List groups a user belongs to for a service."),
            ("user-services", "List services associated with a user."),
            ("is-service-admin", "Check if a user administers a service."),
        ],
    ),
    (
        "Organisations",
        [
            ("org-projects", "List projects associated with a top-level organisation."),
            ("org-project-details", "Show details for an organisation project."),
            ("org-types", "List all available organisation types."),
        ],
    ),
    (
        "Accounts",
        [
            ("permissions-metadata", "Show platform-wide permissions metadata."),
            ("user-permissions", "Show resolved permissions for a user."),
            ("vweb-user", "Show vWEB details for a user."),
            ("personal-homepages", "List personal homepages registered in SIM."),
        ],
    ),
    (
        "Passwords",
        [
            ("password-metadata", "Show SIM-wide password policy metadata."),
            ("user-password", "Show password metadata for a user."),
            ("is-password-pwned", "Check if a user's password is known to be compromised."),
        ],
    ),
    (
        "Exchange",
        [
            ("exchange-distributions", "List all Exchange distributions."),
            ("exchange-distribution", "Show details for an Exchange distribution."),
            ("exchange-admins", "List Exchange administrators for a distribution."),
        ],
    ),
    (
        "Institutions",
        [
            ("project-institution", "Resolve institution links for a project."),
            ("institution", "Fetch institution details by ID."),
        ],
    ),
    (
        "Identities",
        [
            ("person", "Fetch person details by LRZ ID."),
            ("user", "Fetch user details by username."),
        ],
    ),
]

COMMAND_HELP = {name: description for _, commands in COMMAND_GROUPS for name, description in commands}


def _build_description() -> str:
    lines = ["Interact with the LRZ SIM API.", "", "Command overview:"]
    longest = max(len(name) for name in COMMAND_HELP)
    for group, commands in COMMAND_GROUPS:
        lines.append(f"  {group}:")
        for name, description in commands:
            lines.append(f"    {name.ljust(longest)}  {description}")
        lines.append("")
    lines.append("Use 'sim-api COMMAND --help' for command-specific options.")
    return "\n".join(lines).rstrip()


def configure_logging(verbosity: int) -> None:
    """Configure the root logger according to the desired verbosity."""

    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def build_parser() -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    common = argparse.ArgumentParser(add_help=False, formatter_class=CustomHelpFormatter)
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

    common._optionals.title = "Global options"

    parser = argparse.ArgumentParser(
        description=_build_description(),
        epilog=textwrap.dedent(
            """
            Examples:
              sim-api environment
              sim-api group-members AI my-group
              sim-api user --format table --fields username,email
            """
        ),
        parents=[common],
        formatter_class=CustomHelpFormatter,
    )
    parser._optionals.title = "Help options"

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
        title="Commands",
        help="Run 'sim-api COMMAND --help' to inspect the command's options.",
    )

    subparsers.add_parser("environment", help=COMMAND_HELP["environment"], formatter_class=CustomHelpFormatter)

    subparsers.add_parser(
        "current-user", help=COMMAND_HELP["current-user"], formatter_class=CustomHelpFormatter
    )

    characteristics = subparsers.add_parser(
        "service-characteristics",
        help=COMMAND_HELP["service-characteristics"],
        formatter_class=CustomHelpFormatter,
    )
    characteristics.add_argument("service", help="Service identifier, e.g. AI.")

    groups = subparsers.add_parser(
        "groups", help=COMMAND_HELP["groups"], formatter_class=CustomHelpFormatter
    )
    groups.add_argument("service", help="Service identifier, e.g. AI.")

    members = subparsers.add_parser(
        "group-members",
        help=COMMAND_HELP["group-members"],
        formatter_class=CustomHelpFormatter,
    )
    members.add_argument("service", help="Service identifier, e.g. AI.")
    members.add_argument("group_name", help="Name of the group to inspect.")
    members.add_argument(
        "--solve",
        action="store_true",
        help="Resolve nested group memberships via the 'solve' query parameter.",
    )

    admins = subparsers.add_parser(
        "group-admins", help=COMMAND_HELP["group-admins"], formatter_class=CustomHelpFormatter
    )
    admins.add_argument("service", help="Service identifier, e.g. AI.")
    admins.add_argument("group_name", help="Name of the group to inspect.")

    group_info = subparsers.add_parser(
        "group-info", help=COMMAND_HELP["group-info"], formatter_class=CustomHelpFormatter
    )
    group_info.add_argument("service", help="Service identifier, e.g. AI.")
    group_info.add_argument("group_name", help="Name of the group to inspect.")

    group_rights = subparsers.add_parser(
        "group-rights",
        help=COMMAND_HELP["group-rights"],
        formatter_class=CustomHelpFormatter,
    )
    group_rights.add_argument("service", help="Service identifier, e.g. AI.")
    group_rights.add_argument("group_name", help="Name of the group to inspect.")
    group_rights.add_argument("username", help="SIM username / Kennung.")

    subparsers.add_parser(
        "permissions-metadata",
        help=COMMAND_HELP["permissions-metadata"],
        formatter_class=CustomHelpFormatter,
    )

    user_permissions = subparsers.add_parser(
        "user-permissions",
        help=COMMAND_HELP["user-permissions"],
        formatter_class=CustomHelpFormatter,
    )
    user_permissions.add_argument("username", help="SIM username / Kennung.")

    check_member = subparsers.add_parser(
        "is-group-member",
        help=COMMAND_HELP["is-group-member"],
        formatter_class=CustomHelpFormatter,
    )
    check_member.add_argument("service", help="Service identifier, e.g. AI.")
    check_member.add_argument("group_name", help="Name of the group to inspect.")
    check_member.add_argument("username", help="SIM username / Kennung.")

    check_master = subparsers.add_parser(
        "is-group-master",
        help=COMMAND_HELP["is-group-master"],
        formatter_class=CustomHelpFormatter,
    )
    check_master.add_argument("service", help="Service identifier, e.g. AI.")
    check_master.add_argument("group_name", help="Name of the group to inspect.")
    check_master.add_argument("username", help="SIM username / Kennung.")

    check_admin = subparsers.add_parser(
        "is-group-admin",
        help=COMMAND_HELP["is-group-admin"],
        formatter_class=CustomHelpFormatter,
    )
    check_admin.add_argument("service", help="Service identifier, e.g. AI.")
    check_admin.add_argument("group_name", help="Name of the group to inspect.")
    check_admin.add_argument("username", help="SIM username / Kennung.")

    master_users = subparsers.add_parser(
        "project-master-users",
        help=COMMAND_HELP["project-master-users"],
        formatter_class=CustomHelpFormatter,
    )
    master_users.add_argument("project", help="Project identifier, e.g. pn69ju.")

    service_projects = subparsers.add_parser(
        "service-projects",
        help=COMMAND_HELP["service-projects"],
        formatter_class=CustomHelpFormatter,
    )
    service_projects.add_argument("service", help="Service identifier, e.g. AI.")

    org_projects = subparsers.add_parser(
        "org-projects",
        help=COMMAND_HELP["org-projects"],
        formatter_class=CustomHelpFormatter,
    )
    org_projects.add_argument("organisation", help="Organisation identifier, e.g. TUM.")

    org_project_details = subparsers.add_parser(
        "org-project-details",
        help=COMMAND_HELP["org-project-details"],
        formatter_class=CustomHelpFormatter,
    )
    org_project_details.add_argument("organisation", help="Organisation identifier, e.g. TUM.")
    org_project_details.add_argument("project", help="Project identifier, e.g. uk431.")

    subparsers.add_parser(
        "org-types", help=COMMAND_HELP["org-types"], formatter_class=CustomHelpFormatter
    )

    vweb = subparsers.add_parser(
        "vweb-user", help=COMMAND_HELP["vweb-user"], formatter_class=CustomHelpFormatter
    )
    vweb.add_argument("username", help="SIM username / Kennung.")

    subparsers.add_parser(
        "personal-homepages",
        help=COMMAND_HELP["personal-homepages"],
        formatter_class=CustomHelpFormatter,
    )

    service_admin = subparsers.add_parser(
        "is-service-admin",
        help=COMMAND_HELP["is-service-admin"],
        formatter_class=CustomHelpFormatter,
    )
    service_admin.add_argument("service", help="Service identifier, e.g. AI.")
    service_admin.add_argument("username", help="SIM username / Kennung.")

    managed_groups = subparsers.add_parser(
        "managed-groups",
        help=COMMAND_HELP["managed-groups"],
        formatter_class=CustomHelpFormatter,
    )
    managed_groups.add_argument("service", help="Service identifier, e.g. AI.")
    managed_groups.add_argument("username", help="SIM username / Kennung.")

    memberships = subparsers.add_parser(
        "group-memberships",
        help=COMMAND_HELP["group-memberships"],
        formatter_class=CustomHelpFormatter,
    )
    memberships.add_argument("service", help="Service identifier, e.g. AI.")
    memberships.add_argument("username", help="SIM username / Kennung.")

    user_services = subparsers.add_parser(
        "user-services",
        help=COMMAND_HELP["user-services"],
        formatter_class=CustomHelpFormatter,
    )
    user_services.add_argument("username", help="SIM username / Kennung.")

    subparsers.add_parser(
        "password-metadata",
        help=COMMAND_HELP["password-metadata"],
        formatter_class=CustomHelpFormatter,
    )

    user_password = subparsers.add_parser(
        "user-password",
        help=COMMAND_HELP["user-password"],
        formatter_class=CustomHelpFormatter,
    )
    user_password.add_argument("username", help="SIM username / Kennung.")

    password_pwned = subparsers.add_parser(
        "is-password-pwned",
        help=COMMAND_HELP["is-password-pwned"],
        formatter_class=CustomHelpFormatter,
    )
    password_pwned.add_argument("username", help="SIM username / Kennung.")

    subparsers.add_parser(
        "exchange-distributions",
        help=COMMAND_HELP["exchange-distributions"],
        formatter_class=CustomHelpFormatter,
    )

    exchange_distribution = subparsers.add_parser(
        "exchange-distribution",
        help=COMMAND_HELP["exchange-distribution"],
        formatter_class=CustomHelpFormatter,
    )
    exchange_distribution.add_argument("list_name", help="Distribution list identifier.")

    exchange_admins = subparsers.add_parser(
        "exchange-admins",
        help=COMMAND_HELP["exchange-admins"],
        formatter_class=CustomHelpFormatter,
    )
    exchange_admins.add_argument("list_name", help="Distribution list identifier.")

    project = subparsers.add_parser(
        "project-institution",
        help=COMMAND_HELP["project-institution"],
        formatter_class=CustomHelpFormatter,
    )
    project.add_argument("project_name", help="Project identifier, e.g. pn69ju.")

    institution = subparsers.add_parser(
        "institution", help=COMMAND_HELP["institution"], formatter_class=CustomHelpFormatter
    )
    institution.add_argument("institution_id", help="Institution LRZ identifier.")

    person = subparsers.add_parser(
        "person", help=COMMAND_HELP["person"], formatter_class=CustomHelpFormatter
    )
    person.add_argument("person_id", help="LRZ identifier for the person.")

    user = subparsers.add_parser(
        "user", help=COMMAND_HELP["user"], formatter_class=CustomHelpFormatter
    )
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
        if args.command == "environment":
            result = client.get_environment()
        elif args.command == "current-user":
            result = client.get_current_user()
        elif args.command == "service-characteristics":
            result = client.get_service_characteristics(args.service)
        elif args.command == "groups":
            result = client.list_groups(args.service)
        elif args.command == "group-members":
            result = client.get_group_members(args.service, args.group_name, solve=args.solve)
        elif args.command == "group-admins":
            result = client.get_group_admins(args.service, args.group_name)
        elif args.command == "group-info":
            result = client.get_group_details(args.service, args.group_name)
        elif args.command == "group-rights":
            result = client.get_group_rights(args.service, args.group_name, args.username)
        elif args.command == "permissions-metadata":
            result = client.get_permissions_metadata()
        elif args.command == "user-permissions":
            result = client.get_user_permissions(args.username)
        elif args.command == "is-group-member":
            result = client.is_group_member(args.service, args.group_name, args.username)
        elif args.command == "is-group-master":
            result = client.is_group_master_user(args.service, args.group_name, args.username)
        elif args.command == "is-group-admin":
            result = client.is_group_admin(args.service, args.group_name, args.username)
        elif args.command == "project-master-users":
            result = client.get_project_master_users(args.project)
        elif args.command == "service-projects":
            result = client.list_service_projects(args.service)
        elif args.command == "org-projects":
            result = client.list_org_projects(args.organisation)
        elif args.command == "org-project-details":
            result = client.get_org_project_details(args.organisation, args.project)
        elif args.command == "org-types":
            result = client.list_org_types()
        elif args.command == "vweb-user":
            result = client.get_vweb_user(args.username)
        elif args.command == "personal-homepages":
            result = client.list_personal_homepages()
        elif args.command == "is-service-admin":
            result = client.is_service_admin(args.service, args.username)
        elif args.command == "managed-groups":
            result = client.list_managed_groups(args.service, args.username)
        elif args.command == "group-memberships":
            result = client.list_group_memberships(args.service, args.username)
        elif args.command == "user-services":
            result = client.list_user_services(args.username)
        elif args.command == "password-metadata":
            result = client.get_password_metadata()
        elif args.command == "user-password":
            result = client.get_user_password_metadata(args.username)
        elif args.command == "is-password-pwned":
            result = client.is_password_pwned(args.username)
        elif args.command == "exchange-distributions":
            result = client.list_exchange_distributions()
        elif args.command == "exchange-distribution":
            result = client.get_exchange_distribution(args.list_name)
        elif args.command == "exchange-admins":
            result = client.get_exchange_distribution_admins(args.list_name)
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
