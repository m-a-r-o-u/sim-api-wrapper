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

    subparsers.add_parser("environment", help="Show SIM backend environment information.")

    subparsers.add_parser("current-user", help="Show the currently authenticated SIM identity.")

    characteristics = subparsers.add_parser(
        "service-characteristics",
        help="Display service-specific group characteristics.",
    )
    characteristics.add_argument("service", help="Service identifier, e.g. AI.")

    groups = subparsers.add_parser("groups", help="List all available project groups.")
    groups.add_argument("service", help="Service identifier, e.g. AI.")

    members = subparsers.add_parser("group-members", help="List members of a project group.")
    members.add_argument("service", help="Service identifier, e.g. AI.")
    members.add_argument("group_name", help="Name of the group to inspect.")
    members.add_argument(
        "--solve",
        action="store_true",
        help="Resolve nested group memberships via the 'solve' query parameter.",
    )

    admins = subparsers.add_parser("group-admins", help="List administrators of a project group.")
    admins.add_argument("service", help="Service identifier, e.g. AI.")
    admins.add_argument("group_name", help="Name of the group to inspect.")

    group_info = subparsers.add_parser("group-info", help="Show metadata for a project group.")
    group_info.add_argument("service", help="Service identifier, e.g. AI.")
    group_info.add_argument("group_name", help="Name of the group to inspect.")

    group_rights = subparsers.add_parser(
        "group-rights",
        help="Show resolved rights for a user within a project group.",
    )
    group_rights.add_argument("service", help="Service identifier, e.g. AI.")
    group_rights.add_argument("group_name", help="Name of the group to inspect.")
    group_rights.add_argument("username", help="SIM username / Kennung.")

    subparsers.add_parser("permissions-metadata", help="Show platform-wide permissions metadata.")

    user_permissions = subparsers.add_parser(
        "user-permissions",
        help="Show resolved permissions for a user.",
    )
    user_permissions.add_argument("username", help="SIM username / Kennung.")

    check_member = subparsers.add_parser(
        "is-group-member",
        help="Check if a user is member of a project group.",
    )
    check_member.add_argument("service", help="Service identifier, e.g. AI.")
    check_member.add_argument("group_name", help="Name of the group to inspect.")
    check_member.add_argument("username", help="SIM username / Kennung.")

    check_master = subparsers.add_parser(
        "is-group-master",
        help="Check if a user is a master user of a project group.",
    )
    check_master.add_argument("service", help="Service identifier, e.g. AI.")
    check_master.add_argument("group_name", help="Name of the group to inspect.")
    check_master.add_argument("username", help="SIM username / Kennung.")

    check_admin = subparsers.add_parser(
        "is-group-admin",
        help="Check if a user administers a project group.",
    )
    check_admin.add_argument("service", help="Service identifier, e.g. AI.")
    check_admin.add_argument("group_name", help="Name of the group to inspect.")
    check_admin.add_argument("username", help="SIM username / Kennung.")

    master_users = subparsers.add_parser(
        "project-master-users",
        help="List master user identifiers for a project.",
    )
    master_users.add_argument("project", help="Project identifier, e.g. pn69ju.")

    service_projects = subparsers.add_parser(
        "service-projects",
        help="List projects that currently have a quota for a service.",
    )
    service_projects.add_argument("service", help="Service identifier, e.g. AI.")

    org_projects = subparsers.add_parser(
        "org-projects",
        help="List projects associated with a top-level organisation.",
    )
    org_projects.add_argument("organisation", help="Organisation identifier, e.g. TUM.")

    org_project_details = subparsers.add_parser(
        "org-project-details",
        help="Show details for an organisation project.",
    )
    org_project_details.add_argument("organisation", help="Organisation identifier, e.g. TUM.")
    org_project_details.add_argument("project", help="Project identifier, e.g. uk431.")

    subparsers.add_parser("org-types", help="List all available organisation types.")

    vweb = subparsers.add_parser("vweb-user", help="Show vWEB details for a user.")
    vweb.add_argument("username", help="SIM username / Kennung.")

    subparsers.add_parser("personal-homepages", help="List personal homepages registered in SIM.")

    service_admin = subparsers.add_parser(
        "is-service-admin",
        help="Check if a user administers a service.",
    )
    service_admin.add_argument("service", help="Service identifier, e.g. AI.")
    service_admin.add_argument("username", help="SIM username / Kennung.")

    managed_groups = subparsers.add_parser(
        "managed-groups",
        help="List groups a user can manage for a service.",
    )
    managed_groups.add_argument("service", help="Service identifier, e.g. AI.")
    managed_groups.add_argument("username", help="SIM username / Kennung.")

    memberships = subparsers.add_parser(
        "group-memberships",
        help="List groups a user belongs to for a service.",
    )
    memberships.add_argument("service", help="Service identifier, e.g. AI.")
    memberships.add_argument("username", help="SIM username / Kennung.")

    user_services = subparsers.add_parser(
        "user-services",
        help="List services associated with a user.",
    )
    user_services.add_argument("username", help="SIM username / Kennung.")

    subparsers.add_parser("password-metadata", help="Show SIM-wide password policy metadata.")

    user_password = subparsers.add_parser(
        "user-password",
        help="Show password metadata for a user.",
    )
    user_password.add_argument("username", help="SIM username / Kennung.")

    password_pwned = subparsers.add_parser(
        "is-password-pwned",
        help="Check if a user's password is known to be compromised.",
    )
    password_pwned.add_argument("username", help="SIM username / Kennung.")

    subparsers.add_parser("exchange-distributions", help="List all Exchange distributions.")

    exchange_distribution = subparsers.add_parser(
        "exchange-distribution",
        help="Show details for an Exchange distribution.",
    )
    exchange_distribution.add_argument("list_name", help="Distribution list identifier.")

    exchange_admins = subparsers.add_parser(
        "exchange-admins",
        help="List Exchange administrators for a distribution.",
    )
    exchange_admins.add_argument("list_name", help="Distribution list identifier.")

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
