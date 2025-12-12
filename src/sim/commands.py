"""Central registry of CLI commands and their argument metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class CommandArg:
    """Metadata for a single command-line argument."""

    flags: Sequence[str]
    help: str
    dest: str | None = None
    nargs: str | int | None = None
    from_stdin: bool = False
    required: bool = False
    placeholder: str | None = None


@dataclass(frozen=True)
class CommandSpec:
    """Description of a CLI command, including arguments and dispatch target."""

    name: str
    description: str
    client_method: str
    args: Sequence[CommandArg]
    group: str = "General"


COMMAND_SPECS: List[CommandSpec] = [
    CommandSpec(
        name="environment",
        description="Show SIM backend environment information.",
        client_method="get_environment",
        args=(),
        group="General",
    ),
    CommandSpec(
        name="current-user",
        description="Show the currently authenticated SIM identity.",
        client_method="get_current_user",
        args=(),
        group="General",
    ),
    CommandSpec(
        name="service-characteristics",
        description="Display service-specific group characteristics.",
        client_method="get_service_characteristics",
        args=(
            CommandArg(
                ("service",),
                help="Service identifier, e.g. AI.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="service",
            ),
        ),
        group="General",
    ),
    CommandSpec(
        name="groups",
        description="List all available project groups.",
        client_method="list_groups",
        args=(
            CommandArg(
                ("service",),
                help="Service identifier, e.g. AI.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="service",
            ),
        ),
        group="Groups",
    ),
    CommandSpec(
        name="group-info",
        description="Show metadata for a project group.",
        client_method="get_group_details",
        args=(
            CommandArg(("service",), help="Service identifier, e.g. AI."),
            CommandArg(
                ("group_name",),
                help="Name of the group to inspect.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="group_name",
            ),
        ),
        group="Groups",
    ),
    CommandSpec(
        name="group-rights",
        description="Show resolved rights for a user within a project group.",
        client_method="get_group_rights",
        args=(
            CommandArg(("service",), help="Service identifier, e.g. AI."),
            CommandArg(("group_name",), help="Name of the group to inspect."),
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Groups",
    ),
    CommandSpec(
        name="group-members",
        description="List members of a project group.",
        client_method="get_group_members",
        args=(
            CommandArg(("service",), help="Service identifier, e.g. AI."),
            CommandArg(
                ("group_name",),
                help="Name of the group to inspect.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="group_name",
            ),
        ),
        group="Groups",
    ),
    CommandSpec(
        name="group-admins",
        description="List administrators of a project group.",
        client_method="get_group_admins",
        args=(
            CommandArg(("service",), help="Service identifier, e.g. AI."),
            CommandArg(
                ("group_name",),
                help="Name of the group to inspect.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="group_name",
            ),
        ),
        group="Groups",
    ),
    CommandSpec(
        name="is-group-member",
        description="Check if a user is member of a project group.",
        client_method="is_group_member",
        args=(
            CommandArg(("service",), help="Service identifier, e.g. AI."),
            CommandArg(("group_name",), help="Name of the group to inspect."),
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Group membership checks",
    ),
    CommandSpec(
        name="is-group-master",
        description="Check if a user is a master user of a project group.",
        client_method="is_group_master_user",
        args=(
            CommandArg(("service",), help="Service identifier, e.g. AI."),
            CommandArg(("group_name",), help="Name of the group to inspect."),
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Group membership checks",
    ),
    CommandSpec(
        name="is-group-admin",
        description="Check if a user administers a project group.",
        client_method="is_group_admin",
        args=(
            CommandArg(("service",), help="Service identifier, e.g. AI."),
            CommandArg(("group_name",), help="Name of the group to inspect."),
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Group membership checks",
    ),
    CommandSpec(
        name="project-master-users",
        description="List master user identifiers for a project.",
        client_method="get_project_master_users",
        args=(
            CommandArg(
                ("project",),
                help="Project identifier, e.g. pn69ju.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="project",
            ),
        ),
        group="Group membership checks",
    ),
    CommandSpec(
        name="service-projects",
        description="List projects that currently have a quota for a service.",
        client_method="list_service_projects",
        args=(
            CommandArg(
                ("service",),
                help="Service identifier, e.g. AI.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="service",
            ),
        ),
        group="Services",
    ),
    CommandSpec(
        name="managed-groups",
        description="List groups a user can manage for a service.",
        client_method="list_managed_groups",
        args=(
            CommandArg(("service",), help="Service identifier, e.g. AI."),
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Services",
    ),
    CommandSpec(
        name="group-memberships",
        description="List groups a user belongs to for a service.",
        client_method="list_group_memberships",
        args=(
            CommandArg(("service",), help="Service identifier, e.g. AI."),
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Services",
    ),
    CommandSpec(
        name="user-services",
        description="List services associated with a user.",
        client_method="list_user_services",
        args=(
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Services",
    ),
    CommandSpec(
        name="is-service-admin",
        description="Check if a user administers a service.",
        client_method="is_service_admin",
        args=(
            CommandArg(("service",), help="Service identifier, e.g. AI."),
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Services",
    ),
    CommandSpec(
        name="org-projects",
        description="List projects associated with a top-level organisation.",
        client_method="list_org_projects",
        args=(
            CommandArg(
                ("organisation",),
                help="Organisation identifier, e.g. TUM.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="organisation",
            ),
        ),
        group="Organisations",
    ),
    CommandSpec(
        name="org-project-details",
        description="Show details for an organisation project.",
        client_method="get_org_project_details",
        args=(
            CommandArg(("organisation",), help="Organisation identifier, e.g. TUM."),
            CommandArg(
                ("project",),
                help="Project identifier, e.g. uk431.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="project",
            ),
        ),
        group="Organisations",
    ),
    CommandSpec(
        name="org-types",
        description="List all available organisation types.",
        client_method="list_org_types",
        args=(),
        group="Organisations",
    ),
    CommandSpec(
        name="permissions-metadata",
        description="Show platform-wide permissions metadata.",
        client_method="get_permissions_metadata",
        args=(),
        group="Accounts",
    ),
    CommandSpec(
        name="user-permissions",
        description="Show resolved permissions for a user.",
        client_method="get_user_permissions",
        args=(
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Accounts",
    ),
    CommandSpec(
        name="vweb-user",
        description="Show vWEB details for a user.",
        client_method="get_vweb_user",
        args=(
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Accounts",
    ),
    CommandSpec(
        name="personal-homepages",
        description="List personal homepages registered in SIM.",
        client_method="list_personal_homepages",
        args=(),
        group="Accounts",
    ),
    CommandSpec(
        name="password-metadata",
        description="Show SIM-wide password policy metadata.",
        client_method="get_password_metadata",
        args=(),
        group="Passwords",
    ),
    CommandSpec(
        name="user-password",
        description="Show password metadata for a user.",
        client_method="get_user_password_metadata",
        args=(
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Passwords",
    ),
    CommandSpec(
        name="is-password-pwned",
        description="Check if a user's password is known to be compromised.",
        client_method="is_password_pwned",
        args=(
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Passwords",
    ),
    CommandSpec(
        name="exchange-distributions",
        description="List all Exchange distributions.",
        client_method="list_exchange_distributions",
        args=(),
        group="Exchange",
    ),
    CommandSpec(
        name="exchange-distribution",
        description="Show details for an Exchange distribution.",
        client_method="get_exchange_distribution",
        args=(
            CommandArg(
                ("list_name",),
                help="Distribution list identifier.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="list_name",
            ),
        ),
        group="Exchange",
    ),
    CommandSpec(
        name="exchange-admins",
        description="List Exchange administrators for a distribution.",
        client_method="get_exchange_distribution_admins",
        args=(
            CommandArg(
                ("list_name",),
                help="Distribution list identifier.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="list_name",
            ),
        ),
        group="Exchange",
    ),
    CommandSpec(
        name="project-institution",
        description="Resolve institution links for a project.",
        client_method="get_project_institution_links",
        args=(
            CommandArg(
                ("project_name",),
                help="Project identifier, e.g. pn69ju.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="project_name",
            ),
        ),
        group="Institutions",
    ),
    CommandSpec(
        name="institution",
        description="Fetch institution details by ID.",
        client_method="get_institution",
        args=(
            CommandArg(
                ("institution_id",),
                help="Institution LRZ identifier.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="institution_id",
            ),
        ),
        group="Institutions",
    ),
    CommandSpec(
        name="person",
        description="Fetch person details by LRZ ID.",
        client_method="get_person",
        args=(
            CommandArg(
                ("person_id",),
                help="LRZ identifier for the person.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="person_id",
            ),
        ),
        group="Identities",
    ),
    CommandSpec(
        name="user",
        description="Fetch user details by username.",
        client_method="get_user",
        args=(
            CommandArg(
                ("username",),
                help="SIM username / Kennung.",
                nargs="*",
                from_stdin=True,
                required=True,
                placeholder="username",
            ),
        ),
        group="Identities",
    ),
]

__all__ = ["CommandArg", "CommandSpec", "COMMAND_SPECS"]
