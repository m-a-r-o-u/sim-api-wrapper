"""Command line entry point for SIM app helper utilities."""

from __future__ import annotations

import argparse
import sys
from typing import List

from sim_api_wrapper.cli import configure_logging
from sim_api_wrapper.client import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, SimApiClient

from .mcml import McmlCollectionError, collect_mcml_master_user_emails


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="High-level helper commands built on top of the SIM API wrapper.",
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
        type=int,
        default=None,
        help=(
            "Limit SIM app processing to the first N items for quick test runs. "
            "Applies uniformly across all sim-app commands."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    mcml = subparsers.add_parser(
        "mcml-master-user-emails",
        help="Collect hauptemail addresses of MCML master users.",
    )
    mcml.add_argument(
        "--service",
        default="AI",
        help="Service identifier used to look up MCML groups (default: %(default)s).",
    )

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

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
        if args.command == "mcml-master-user-emails":
            return _run_mcml_master_user_emails(
                client,
                service=args.service,
                test_sample_size=args.test_sample_size,
            )
    finally:
        client.close()

    parser.error(f"Unknown command: {args.command}")
    return 2


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


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
