"""Command line entry point for SIM app helper utilities."""

from __future__ import annotations

import argparse
import sys
from typing import List

from sim_api_wrapper.cli import configure_logging
from sim_api_wrapper.client import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, SimApiClient

from .ai_systems import (
    AiSystemsCollectionError,
    AiSystemsMcmlCollectionError,
    collect_ai_system_mcml_user_emails,
    collect_ai_system_user_emails,
)
from .institution_heads import (
    InstitutionHeadsCollectionError,
    collect_institution_heads,
)
from .mcml import McmlCollectionError, collect_mcml_master_user_emails
from .user_projects import (
    UserProjectsMembershipCollectionError,
    collect_user_projects_memberships,
)


_SubParsersAction = getattr(argparse, "_SubParsersAction")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Use --test <N> to sample and -v/--verbose for logs."),
        epilog="Example: sim-apps mcml-master-user-emails --test 2 -v",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="sim-apps COMMAND [OPTIONS]",
        prog="sim-apps",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (use -vv for debug logs).",
    )
    parser.add_argument(
        "--test",
        dest="test_sample_size",
        metavar="N_SAMPLES",
        type=int,
        default=None,
        help="Process only the first N items for quick runs.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Override the SIM API base URL.",
    )
    parser.add_argument(
        "--netrc",
        default=None,
        help="Path to a netrc file for authentication.",
    )
    parser.add_argument(
        "--no-netrc",
        action="store_true",
        help="Disable automatic loading of ~/.netrc credentials.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Timeout in seconds for API requests.",
    )

    subparsers = parser.add_subparsers(
        dest="command", required=True, title="commands", metavar="COMMAND"
    )

    all_users = subparsers.add_parser(
        "all-user-emails",
        help="All AI system user emails.",
    )
    all_users.add_argument(
        "--service",
        default="AI",
        help="Service identifier used to look up AI system groups (default: %(default)s).",
    )

    mcml_users = subparsers.add_parser(
        "mcml-user-emails",
        help="MCML user emails.",
    )
    mcml_users.add_argument(
        "--service",
        default="AI",
        help="Service identifier used to look up MCML groups (default: %(default)s).",
    )

    mcml = subparsers.add_parser(
        "mcml-master-user-emails",
        help="MCML master user emails.",
    )
    mcml.add_argument(
        "--service",
        default="AI",
        help="Service identifier used to look up MCML groups (default: %(default)s).",
    )

    membership = subparsers.add_parser(
        "user-projects-membership",
        help="AI system project memberships and emails.",
        prog=f"{parser.prog} user-projects-membership [OPTIONS]",
    )
    membership.add_argument(
        "--service",
        default="AI",
        help="Service identifier used to look up AI system groups (default: %(default)s).",
    )
    membership.add_argument(
        "--histogram",
        action="store_true",
        help="Summarise the distribution of project counts instead of individual rows.",
    )

    institution_heads = subparsers.add_parser(
        "list-institution-heads",
        help="Project institution heads for a service.",
    )
    institution_heads.add_argument(
        "service",
        nargs="?",
        default="AI",
        help="Service identifier used to look up project groups (default: %(default)s).",
    )

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(_normalise_global_options(parser, argv))

    configure_logging(args.verbose)

    try:
        client = SimApiClient(
            base_url=args.base_url,
            timeout=args.timeout,
            netrc_path=args.netrc,
            use_netrc=not args.no_netrc,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        print(f"Failed to initialise SIM API client: {exc}", file=sys.stderr)
        return 1

    try:
        if args.command == "all-user-emails":
            return _run_all_users_emails(
                client,
                service=args.service,
                test_sample_size=args.test_sample_size,
            )
        if args.command == "mcml-user-emails":
            return _run_mcml_user_emails(
                client,
                service=args.service,
                test_sample_size=args.test_sample_size,
            )
        if args.command == "mcml-master-user-emails":
            return _run_mcml_master_user_emails(
                client,
                service=args.service,
                test_sample_size=args.test_sample_size,
            )
        if args.command == "user-projects-membership":
            return _run_user_projects_membership(
                client,
                service=args.service,
                test_sample_size=args.test_sample_size,
                histogram=args.histogram,
            )
        if args.command == "list-institution-heads":
            return _run_institution_heads(
                client,
                service=args.service,
                test_sample_size=args.test_sample_size,
            )
    finally:
        client.close()

    parser.error(f"Unknown command: {args.command}")
    return 2


def _normalise_global_options(
    parser: argparse.ArgumentParser, argv: List[str] | None
) -> List[str]:
    """Allow global options to appear either before or after the subcommand."""

    arguments = list(argv) if argv is not None else sys.argv[1:]
    if not arguments:
        return arguments

    subcommands: set[str] = set()
    for action in parser._actions:  # pragma: no cover - argparse internals are stable
        if isinstance(action, _SubParsersAction):
            subcommands.update(action.choices)

    command_index = next(
        (index for index, token in enumerate(arguments) if token in subcommands),
        None,
    )
    if command_index is None:
        return arguments

    prefix = arguments[:command_index]
    command_and_tail = arguments[command_index:]

    reordered_globals: List[str] = []
    remainder: List[str] = [command_and_tail[0]]

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
    token: str, command_and_tail: List[str], index: int, reordered_globals: List[str]
) -> int:
    """Append recognised global options to ``reordered_globals``.

    Returns the number of tokens consumed (including ``token``) if the option is
    recognised, otherwise returns ``0``.
    """

    options_with_values = {
        "--base-url": 1,
        "--netrc": 1,
        "--timeout": 1,
        "--test": 1,
    }
    flag_options = {"--no-netrc", "--verbose"}

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


def _run_all_users_emails(
    client: SimApiClient,
    *,
    service: str,
    test_sample_size: int | None = None,
) -> int:
    try:
        result = collect_ai_system_user_emails(
            client,
            service=service,
            test_sample_size=test_sample_size,
        )
    except AiSystemsCollectionError as exc:
        print(exc, file=sys.stderr)
        return 1

    for issue in result.issues:
        print(f"NOTE: {issue}", file=sys.stderr)

    for email in result.emails:
        print(email)

    return 0 if result.emails else 1


def _run_mcml_user_emails(
    client: SimApiClient,
    *,
    service: str,
    test_sample_size: int | None = None,
) -> int:
    try:
        result = collect_ai_system_mcml_user_emails(
            client,
            service=service,
            test_sample_size=test_sample_size,
        )
    except AiSystemsMcmlCollectionError as exc:
        print(exc, file=sys.stderr)
        return 1

    for issue in result.issues:
        print(f"NOTE: {issue}", file=sys.stderr)

    for email in result.emails:
        print(email)

    return 0 if result.emails else 1


def _run_mcml_master_user_emails(
    client: SimApiClient,
    *,
    service: str,
    test_sample_size: int | None = None,
) -> int:
    try:
        result = collect_mcml_master_user_emails(
            client,
            service=service,
            test_sample_size=test_sample_size,
        )
    except McmlCollectionError as exc:
        print(exc, file=sys.stderr)
        return 1

    for issue in result.issues:
        print(f"NOTE: {issue}", file=sys.stderr)

    for email in result.emails:
        print(email)

    return 0 if result.emails else 1


def _run_user_projects_membership(
    client: SimApiClient,
    *,
    service: str,
    test_sample_size: int | None = None,
    histogram: bool = False,
) -> int:
    try:
        result = collect_user_projects_memberships(
            client,
            service=service,
            test_sample_size=test_sample_size,
        )
    except UserProjectsMembershipCollectionError as exc:
        print(exc, file=sys.stderr)
        return 1

    for issue in result.issues:
        print(f"NOTE: {issue}", file=sys.stderr)

    if histogram:
        print("# Number of Projects - Number of Users")
        histogram_data = result.build_histogram()
        for project_count, user_count in sorted(histogram_data.items()):
            print(f"{project_count} {user_count}")
        return 0 if result.memberships else 1

    for membership in result.memberships:
        parts = [membership.username]
        if membership.projects:
            parts.append(", ".join(membership.projects))
        print(" ".join(parts))

    return 0 if result.memberships else 1


def _run_institution_heads(
    client: SimApiClient, *, service: str, test_sample_size: int | None
) -> int:
    try:
        result = collect_institution_heads(
            client, service=service, test_sample_size=test_sample_size
        )
    except InstitutionHeadsCollectionError as exc:
        print(exc, file=sys.stderr)
        return 1

    for issue in result.issues:
        print(f"NOTE: {issue}", file=sys.stderr)

    for entry in result.heads:
        print(f"{entry.project_id} {entry.formatted_name}")

    return 0 if result.heads else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
