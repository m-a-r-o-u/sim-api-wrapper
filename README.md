# SIM API Wrapper

A lightweight, extensible Python wrapper for the [LRZ SIM API](https://simapi.sim.lrz.de). The
client makes it straightforward to retrieve information about projects, groups, institutions,
people and users while keeping the implementation easy to read and extend.

## Features

- 🔌 **Extensible** – add new endpoints by implementing a single method.
- ♻️ **Reusable** – ship it as a Python package and reuse it across projects.
- 📝 **Understandable** – strong typing via dataclasses and consistent error handling.
- 🛠️ **Tooling friendly** – comes with tests, logging and a CLI for quick inspection.

## Getting started

This project is configured for the [uv](https://github.com/astral-sh/uv) package manager.

```bash
# Create (or reuse) a virtual environment using uv
uv venv

# Activate the virtual environment (Linux/macOS)
source .venv/bin/activate

# Install the package in editable mode together with test dependencies
uv pip install -e ".[test]"

# Run the unit tests
pytest
```

## Authentication

The wrapper supports two authentication mechanisms and will automatically pick the most secure
option available when it starts:

1. **Token authentication** – Create a file at `~/.simapi.env` containing a line in the format
   `SIMAPI_TOKEN=xxxx`. The client will read the token using [`python-dotenv`](https://github.com/theskumar/python-dotenv)
   and inject the HTTP header `Authorization: Basic <SIMAPI_TOKEN>` for every request.
   This method takes precedence when the file exists and contains a valid token.
2. **netrc authentication** – If no token is available (or the token file is malformed), the client
   falls back to credentials stored in a `.netrc` file (defaulting to `~/.netrc`). You can still pass
   a custom path when instantiating the client or via the CLI's `--netrc` option.

If neither mechanism is configured, requests are issued without authentication and the API will
likely reject them. Clear log messages are emitted whenever authentication details are missing or
need attention.

## Usage

### Python

```python
from sim_api_wrapper import SimApiClient

with SimApiClient() as client:
    environment = client.get_environment()
    groups = client.list_groups("AI")
    members = client.get_group_members("AI", "pn69ju-ai-c")
    links = client.get_project_institution_links("pn69ju")
    institution = client.get_institution("0000000000E4EE4B")
    permissions = client.get_user_permissions("di38qex")
    person = client.get_person("00000000001F17E0")
    user = client.get_user("di38qex")

print(environment)
print(groups)
print(members)
print(permissions)
print(institution)
```

Common lookups now have dedicated helpers:

- `get_environment()` – inspect the SIM backend state, including quota summaries.
- `get_service_characteristics(service)` – read the LDAP attributes for a service root group.
- `get_group_members(service, group_name, solve=False)` – enumerate direct (or resolved) group members.
- `get_user_permissions(username)` – expand all permission grants for a SIM identity.
- `list_exchange_distributions()` / `get_exchange_distribution(name)` – explore Exchange distribution lists.

Each method returns either a native Python type (such as a list of strings) or a dataclass with
structured access to the response payload.

### Command line interface

A small CLI is bundled for quick lookups:

```bash
# General information
sim-api environment
sim-api current-user
sim-api service-characteristics AI

# Group exploration
sim-api groups AI
sim-api group-info AI pn69ju-ai-c
sim-api group-members AI pn69ju-ai-c
sim-api group-members AI pn69ju-ai-c --solve
sim-api group-admins AI pn69ju-ai-c
sim-api group-rights AI pn69ju-ai-c di38qex

# Membership checks
sim-api is-group-member AI pn69ju-ai-c di38qex
sim-api is-group-master AI pn69ju-ai-c di38qex
sim-api is-group-admin AI pn69ju-ai-c di38qex
sim-api project-master-users pn69ju

# Service-centric lookups
sim-api service-projects AI
sim-api managed-groups AI di38qex
sim-api group-memberships AI di38qex
sim-api user-services di38qex
sim-api is-service-admin AI di38qex

# Organisation data
sim-api org-projects TUM
sim-api org-project-details TUM uk431
sim-api org-types

# Account metadata
sim-api permissions-metadata
sim-api user-permissions di38qex
sim-api vweb-user di38qex
sim-api personal-homepages

# Password tooling
sim-api password-metadata
sim-api user-password di38qex
sim-api is-password-pwned di38qex

# Exchange distributions
sim-api exchange-distributions
sim-api exchange-distribution AI-announce
sim-api exchange-admins AI-announce

# Institutions and identities
sim-api project-institution pn69ju
sim-api institution 0000000000E4EE4B
sim-api person 00000000001F17E0
sim-api user di38qex
```

Use `--help` to inspect all options. The CLI respects `--netrc` and `--no-netrc` if you need to
control authentication explicitly. Response formatting is controlled by `--format`:

- **Default JSON** – omit `--format` to receive pretty-printed JSON that is easy to pipe into tools
  such as `jq`. The existing `--fields` selector works the same way across all formats.
- `--format yaml` – produce valid YAML that can be copied into configuration files while keeping the
  nested structure intact.
- `--format plain` – emit newline separated values. When the payload is a mapping, the formatter
  automatically falls back to the YAML view. Lists (including nested ones) are flattened, which makes
  it perfect for shell pipelines.
- `--format delimited` – export rows via Python's CSV writer. Lists are rendered as single delimited
  values and dictionaries default to JSON strings for compatibility.

The `--sep` option customises the delimiter for `delimited` output only (defaults to a comma, but
escape sequences such as `\t` are supported). Combine all formats with `--fields` to project or
filter values before rendering.

### SIM app helpers

The package also provides higher-level automation commands via the `sim-app` entry point. The
first available helper, `mcml-master-user-emails`, discovers all MCML project master users and
prints their primary ("hauptemail") addresses:

```bash
sim-app mcml-master-user-emails
```

Pass `--test` to sample a subset of projects while developing or testing new
integrations. For example, `sim-app mcml-master-user-emails --test 2` only processes the
first two MCML projects that match the selected service. Combine this with `--verbose` (or `-v`) to
print each step the helper executes for easier debugging.

The command shares the same authentication flags as `sim-api` (`--netrc`, `--no-netrc`, `--base-url`
and `--timeout`). Diagnostic information is emitted on `stderr` whenever a project is missing master
users, a user account cannot be resolved, or no hauptemail address exists for a master user. The
process continues whenever possible so partial results can still be retrieved.

#### Selecting fields with JMESPath-like expressions

The `--fields` option understands a JMESPath-inspired syntax, so you can use filters, projections
and pipes to extract exactly the values you care about. The parser keeps commas inside parentheses
or string literals intact, making it safe to pass complex expressions without additional quoting.

- Access nested properties: `--fields daten.emailadressen[0].adresse`
- Apply string filters via `contains`: `--fields "daten.emailadressen[?contains(typ,'hauptemail')]"`
- Chain projections with the pipe operator: `--fields "daten.emailadressen[].adresse | [0]"`
- Reduce to a single value in streaming output: `--format plain --fields "daten.emailadressen[?contains(typ,'hauptemail')].adresse | [0]"`
- Extract multiple unrelated values at once: `--fields "daten.adressen[].ort, rollen[?contains(status,'aktiv')].kennung"`

Need a refresher? The [JMESPath tutorial](https://jmespath.org/tutorial.html) explains the full
syntax in depth, and while the CLI implements the most commonly used parts today, the examples are a
great source of inspiration for constructing practical selectors.

```bash
# Default JSON output
sim-api institution 0000000000E4EE4B | jq '.anschriften[0].ort'

# Pick specific fields in a delimited export
sim-api institution 0000000000E4EE4B \
  --format delimited --sep '\t' \
  --fields lrz_id,name,bezeichnung,status \
| tee /tmp/inst.tsv

# Human-friendly YAML for nested structures
sim-api institution 0000000000E4EE4B \
  --format yaml \
  --fields lrz_id,name,bezeichnung,status

# Extract nested address fields
sim-api institution 0000000000E4EE4B \
  --format delimited --sep '\t' \
  --fields anschriften[0].strasse,anschriften[0].plz,anschriften[0].ort,anschriften[0].land

# Filter and project using JMESPath and return the first match as plain text
sim-api user di38qex \
  --format plain \
  --fields "daten.emailadressen[?contains(typ,'hauptemail')].adresse | [0]"

# Combine multiple JMESPath expressions when exporting CSV
sim-api user di38qex \
  --format delimited --sep ';' \
  --fields "kennung,daten.emailadressen[?contains(typ,'hauptemail')].adresse | [0],rollen[?status=='aktiv'].bezeichnung"

# Stream identifiers line by line for shell pipelines
sim-api groups AI --format plain \
| xargs -n1 -I{} sim-api group-info {} --format delimited --sep '\t' --fields id,owner,count
```

## Extending the client

Adding new endpoints is as simple as defining another method on `SimApiClient` and, where useful,
adding a matching dataclass inside `sim_api_wrapper.models`. The helper `_request_json` handles
request execution, error handling and logging for you.

## Testing

The test-suite stubs HTTP responses so you can quickly verify endpoint integration logic without
hitting the real service. Run ``pytest`` as shown above to execute the checks.
