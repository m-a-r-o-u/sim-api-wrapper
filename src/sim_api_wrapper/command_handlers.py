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
from typing import Any, Callable

from .client import SimApiClient

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
    """Construct the mapping of command names to handler callables.

    The resulting dictionary lets the CLI dispatch a parsed command name to
    the appropriate callable without hard-coding the logic inline. This is a
    straightforward factory: ``build_command_handlers`` returns a fresh
    mapping each time it is called, which keeps handler setup isolated and
    easy to inspect.

    Usage example::

        handlers = build_command_handlers()
        handler = handlers[args.command]
        result = handler(args, client, parser)

    Each handler takes ``argparse`` arguments plus an active
    :class:`SimApiClient` instance and returns raw data, leaving formatting to
    the caller.
    """

    return {
        "environment": lambda args, client, parser: client.get_environment(),
        "current-user": lambda args, client, parser: client.get_current_user(),
        "service-characteristics": lambda args, client, parser: _run_for_values(
            _require_inputs(args.service, parser, "service"),
            lambda service: client.get_service_characteristics(service),
        ),
        "groups": lambda args, client, parser: _run_for_values(
            _require_inputs(args.service, parser, "service"),
            client.list_groups,
        ),
        "group-members": lambda args, client, parser: _run_for_values(
            _require_inputs(args.group_name, parser, "group_name"),
            lambda group_name: client.get_group_members(args.service, group_name),
        ),
        "group-admins": lambda args, client, parser: _run_for_values(
            _require_inputs(args.group_name, parser, "group_name"),
            lambda group_name: client.get_group_admins(args.service, group_name),
        ),
        "group-info": lambda args, client, parser: _run_for_values(
            _require_inputs(args.group_name, parser, "group_name"),
            lambda group_name: client.get_group_details(args.service, group_name),
        ),
        "group-rights": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            lambda username: client.get_group_rights(args.service, args.group_name, username),
        ),
        "permissions-metadata": lambda args, client, parser: client.get_permissions_metadata(),
        "user-permissions": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            client.get_user_permissions,
        ),
        "is-group-member": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            lambda username: client.is_group_member(args.service, args.group_name, username),
        ),
        "is-group-master": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            lambda username: client.is_group_master_user(args.service, args.group_name, username),
        ),
        "is-group-admin": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            lambda username: client.is_group_admin(args.service, args.group_name, username),
        ),
        "project-master-users": lambda args, client, parser: _run_for_values(
            _require_inputs(args.project, parser, "project"),
            client.get_project_master_users,
        ),
        "service-projects": lambda args, client, parser: _run_for_values(
            _require_inputs(args.service, parser, "service"),
            client.list_service_projects,
        ),
        "org-projects": lambda args, client, parser: _run_for_values(
            _require_inputs(args.organisation, parser, "organisation"),
            client.list_org_projects,
        ),
        "org-project-details": lambda args, client, parser: _run_for_values(
            _require_inputs(args.project, parser, "project"),
            lambda project: client.get_org_project_details(args.organisation, project),
        ),
        "org-types": lambda args, client, parser: client.list_org_types(),
        "vweb-user": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            client.get_vweb_user,
        ),
        "personal-homepages": lambda args, client, parser: client.list_personal_homepages(),
        "is-service-admin": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            lambda username: client.is_service_admin(args.service, username),
        ),
        "managed-groups": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            lambda username: client.list_managed_groups(args.service, username),
        ),
        "group-memberships": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            lambda username: client.list_group_memberships(args.service, username),
        ),
        "user-services": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            client.list_user_services,
        ),
        "password-metadata": lambda args, client, parser: client.get_password_metadata(),
        "user-password": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            client.get_user_password_metadata,
        ),
        "is-password-pwned": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            client.is_password_pwned,
        ),
        "exchange-distributions": lambda args, client, parser: client.list_exchange_distributions(),
        "exchange-distribution": lambda args, client, parser: _run_for_values(
            _require_inputs(args.list_name, parser, "list_name"),
            client.get_exchange_distribution,
        ),
        "exchange-admins": lambda args, client, parser: _run_for_values(
            _require_inputs(args.list_name, parser, "list_name"),
            client.get_exchange_distribution_admins,
        ),
        "project-institution": lambda args, client, parser: _run_for_values(
            _require_inputs(args.project_name, parser, "project_name"),
            client.get_project_institution_links,
        ),
        "institution": lambda args, client, parser: _run_for_values(
            _require_inputs(args.institution_id, parser, "institution_id"),
            client.get_institution,
        ),
        "person": lambda args, client, parser: _run_for_values(
            _require_inputs(args.person_id, parser, "person_id"),
            client.get_person,
        ),
        "user": lambda args, client, parser: _run_for_values(
            _require_inputs(args.username, parser, "username"),
            client.get_user,
        ),
    }


__all__ = ["CommandHandler", "build_command_handlers"]
