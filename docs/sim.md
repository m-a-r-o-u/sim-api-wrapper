# `sim` client and CLI

`sim` provides both a programmatic Python interface and a command line utility for exploring the
LRZ SIM platform. This document expands on the quick overview in the project README and highlights
the most useful workflows.

## Python usage

```python
from sim import SimApiClient

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
sim environment
sim current-user
sim service-characteristics AI

# Group exploration
sim groups AI
sim group-info AI pn69ju-ai-c
sim group-members AI pn69ju-ai-c
sim group-admins AI pn69ju-ai-c
sim group-rights AI pn69ju-ai-c di38qex

# Membership checks
sim is-group-member AI pn69ju-ai-c di38qex
sim is-group-master AI pn69ju-ai-c di38qex
sim is-group-admin AI pn69ju-ai-c di38qex
sim project-master-users pn69ju

# Service-centric lookups
sim service-projects AI
sim managed-groups AI di38qex
sim group-memberships AI di38qex
sim user-services di38qex
sim is-service-admin AI di38qex

# Organisation data
sim org-projects TUM
sim org-project-details TUM uk431
sim org-types

# Account metadata
sim permissions-metadata
sim user-permissions di38qex
sim vweb-user di38qex
sim personal-homepages

# Password tooling
sim password-metadata
sim user-password di38qex
sim is-password-pwned di38qex

# Exchange distributions
sim exchange-distributions
sim exchange-distribution AI-announce
sim exchange-admins AI-announce

# Institutions and identities
sim project-institution pn69ju
sim institution 0000000000E4EE4B
sim person 00000000001F17E0
sim user di38qex
```

### General CLI options

Use `--help` to inspect all options. The CLI respects `--netrc` and `--no-netrc` if you need to
control authentication explicitly. Response formatting is primarily governed by `--format`; the
general flags come first, followed by dedicated sections for `--format` and `--fields`.

### Output formats with `--format`

| Flag | Purpose |
| --- | --- |
| *(default)* | Pretty JSON; works with `--fields` and is easy to pipe into `jq`. |
| `--format yaml` | Valid YAML suitable for config files; preserves nesting. |
| `--format plain` | Newline-separated values; maps fall back to YAML, lists (even nested) are flattened for shell pipelines. |
| `--format delimited` | CSV-style rows; lists become single delimited values, dictionaries default to JSON strings; tweak delimiter with `--sep` (comma default, escapes like `\t` supported). |

Combine any format with `--fields` to project or filter before rendering.

### Selecting fields with JMESPath-like expressions

The `--fields` flag accepts a JMESPath-inspired syntax for filters, projections and pipes; commas inside parentheses or strings are preserved, so complex expressions pass through safely.

- Nested property access: `--fields daten.emailadressen[0].adresse`
- String filters with `contains`: `--fields "daten.emailadressen[?contains(typ,'hauptemail') || contains(typ,'kontaktemail')]"`
- Chained projections: `--fields "daten.emailadressen[].adresse | [0]"`
- Single value for streaming output: `--format plain --fields "daten.emailadressen[?contains(typ,'hauptemail') || contains(typ,'kontaktemail')].adresse | [0]"`
- Multiple unrelated values: `--fields "daten.adressen[].ort, rollen[?contains(status,'aktiv')].kennung"`

Need more examples? The [JMESPath tutorial](https://jmespath.org/tutorial.html) covers the full syntax and inspires practical selectors.

### Formatting examples

```bash
# Default JSON output
sim institution 0000000000E4EE4B | jq '.anschriften[0].ort'

# Pick specific fields in a delimited export
sim institution 0000000000E4EE4B --format plain --fields lrz_id,name,bezeichnung,status \
| tee /tmp/inst.tsv

# Human-friendly YAML for nested structures
sim institution 0000000000E4EE4B --format yaml --fields lrz_id,name,bezeichnung,status

# Extract nested address fields
sim institution 0000000000E4EE4B --format plain \
  --fields anschriften[0].strasse,anschriften[0].plz,anschriften[0].ort,anschriften[0].land

# Filter and project using JMESPath and return the first match as plain text
sim user di38qex --format plain \
  --fields "daten.emailadressen[?contains(typ,'hauptemail') || contains(typ,'kontaktemail')].adresse | [0]"

# Stream identifiers line by line for shell pipelines
sim groups AI --format plain | sim group-info AI --format plain --fields id,owner,count
```

## Extending the client

Adding new endpoints is as simple as defining another method on `SimApiClient` and, where useful,
adding a matching dataclass inside `sim.models`. The helper `_request_json` handles
request execution, error handling and logging for you.

## Testing

The test-suite stubs HTTP responses so you can quickly verify endpoint integration logic without
hitting the real service. Run `pytest` from an activated virtual environment to execute the checks.
