# `sim-api` client and CLI

`sim-api` provides both a programmatic Python interface and a command line utility for exploring the
LRZ SIM platform. This document expands on the quick overview in the project README and highlights
the most useful workflows.

## Python usage

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
- `get_group_members(service, group_name)` – enumerate group members.
- `get_user_permissions(username)` – expand all permission grants for a SIM identity.
- `list_exchange_distributions()` / `get_exchange_distribution(name)` – explore Exchange distribution lists.

Each method returns either a native Python type (such as a list of strings) or a dataclass with
structured access to the response payload.

## Command line interface

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

### General CLI options

Use `--help` to inspect all options. The CLI respects `--netrc` and `--no-netrc` if you need to
control authentication explicitly. Response formatting is primarily governed by `--format`; the
general flags come first, followed by dedicated sections for `--format` and `--fields`.

### Output formats with `--format`

- **Default JSON** – omit `--format` to receive pretty-printed JSON that is easy to pipe into tools
  such as `jq`. The existing `--fields` selector works the same way across all formats.
- `--format yaml` – produce valid YAML that can be copied into configuration files while keeping the
  nested structure intact.
- `--format plain` – emit newline separated values. When the payload is a mapping, the formatter
  automatically falls back to the YAML view. Lists (including nested ones) are flattened, which makes
  it perfect for shell pipelines.
- `--format delimited` – export rows via Python's CSV writer. Lists are rendered as single delimited
  values and dictionaries default to JSON strings for compatibility. Use `--sep` to swap the
  delimiter (comma by default; escape sequences such as `\t` are supported).

Combine all formats with `--fields` to project or filter values before rendering.

### Selecting fields with JMESPath-like expressions

The `--fields` option understands a JMESPath-inspired syntax, so you can use filters, projections
and pipes to extract exactly the values you care about. The parser keeps commas inside parentheses
or string literals intact, making it safe to pass complex expressions without additional quoting.

- Access nested properties: `--fields daten.emailadressen[0].adresse`
- Apply string filters via `contains`: `--fields "daten.emailadressen[?contains(typ,'hauptemail') || contains(typ,'kontaktemail')]"`
- Chain projections with the pipe operator: `--fields "daten.emailadressen[].adresse | [0]"`
- Reduce to a single value in streaming output: `--format plain --fields "daten.emailadressen[?contains(typ,'hauptemail') || contains(typ,'kontaktemail')].adresse | [0]"`
- Extract multiple unrelated values at once: `--fields "daten.adressen[].ort, rollen[?contains(status,'aktiv')].kennung"`

Need a refresher? The [JMESPath tutorial](https://jmespath.org/tutorial.html) explains the full
syntax in depth, and while the CLI implements the most commonly used parts today, the examples are a
great source of inspiration for constructing practical selectors.

### Formatting examples

```bash
# Default JSON output
sim-api institution 0000000000E4EE4B | jq '.anschriften[0].ort'

# Pick specific fields in a delimited export
sim-api institution 0000000000E4EE4B --format plain --fields lrz_id,name,bezeichnung,status \
| tee /tmp/inst.tsv

# Human-friendly YAML for nested structures
sim-api institution 0000000000E4EE4B --format yaml --fields lrz_id,name,bezeichnung,status

# Extract nested address fields
sim-api institution 0000000000E4EE4B --format plain \
  --fields anschriften[0].strasse,anschriften[0].plz,anschriften[0].ort,anschriften[0].land

# Filter and project using JMESPath and return the first match as plain text
sim-api user di38qex --format plain \
  --fields "daten.emailadressen[?contains(typ,'hauptemail') || contains(typ,'kontaktemail')].adresse | [0]"

# Stream identifiers line by line for shell pipelines
sim-api groups AI --format plain | sim-api group-info AI --format plain --fields id,owner,count
```

## Extending the client

Adding new endpoints is as simple as defining another method on `SimApiClient` and, where useful,
adding a matching dataclass inside `sim_api_wrapper.models`. The helper `_request_json` handles
request execution, error handling and logging for you.

## Testing

The test-suite stubs HTTP responses so you can quickly verify endpoint integration logic without
hitting the real service. Run `pytest` from an activated virtual environment to execute the checks.
