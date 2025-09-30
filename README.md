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
    groups = client.list_groups("AI")
    members = client.get_group_members("pn69ju-ai-c")
    links = client.get_project_institution_links("pn69ju")
    institution = client.get_institution("0000000000E4EE4B")
    person = client.get_person("00000000001F17E0")
    user = client.get_user("di38qex")

print(groups)
print(members)
print(institution)
```

Each method returns either a native Python type (such as a list of strings) or a dataclass with
structured access to the response payload.

### Command line interface

A small CLI is bundled for quick lookups:

```bash
sim-api groups AI
sim-api group-members pn69ju-ai-c
sim-api project-institution pn69ju
sim-api institution 0000000000E4EE4B
sim-api person 00000000001F17E0
sim-api user di38qex
```

Use `--help` to inspect all options. The CLI respects `--netrc` and `--no-netrc` if you need to
control authentication explicitly. Responses can be rendered in multiple formats via `--format`
(`json`, `kv`, `lines`, `delimited`, `table`). Combine them with `--fields` (JMESPath expressions),
`--sep` for custom separators and `--no-header` to suppress headers for delimited outputs.

#### Selecting fields with JMESPath-like expressions

The `--fields` option understands a JMESPath-inspired syntax, so you can use filters, projections
and pipes to extract exactly the values you care about. The parser keeps commas inside parentheses
or string literals intact, making it safe to pass complex expressions without additional quoting.

- Access nested properties: `--fields daten.emailadressen[0].adresse`
- Apply string filters via `contains`: `--fields "daten.emailadressen[?contains(typ,'hauptemail')]"`
- Chain projections with the pipe operator: `--fields "daten.emailadressen[].adresse | [0]"`
- Reduce to a single value in streaming output: `--format lines --fields "daten.emailadressen[?contains(typ,'hauptemail')].adresse | [0]"`
- Extract multiple unrelated values at once: `--fields "daten.adressen[].ort, rollen[?contains(status,'aktiv')].kennung"`

Need a refresher? The [JMESPath tutorial](https://jmespath.org/tutorial.html) explains the full
syntax in depth, and while the CLI implements the most commonly used parts today, the examples are a
great source of inspiration for constructing practical selectors.

```bash
# Default JSON output
sim-api institution 0000000000E4EE4B --format json | jq '.anschriften[0].ort'

# Pick specific fields in a delimited export
sim-api institution 0000000000E4EE4B \
  --format delimited --sep '\t' \
  --fields lrz_id,name,bezeichnung,status \
| tee /tmp/inst.tsv

# Aligned table output for humans
sim-api institution 0000000000E4EE4B \
  --format table \
  --fields lrz_id,name,bezeichnung,status

# Extract nested address fields without a header
sim-api institution 0000000000E4EE4B \
  --format delimited --sep '\t' --no-header \
  --fields anschriften[0].strasse,anschriften[0].plz,anschriften[0].ort,anschriften[0].land

# Filter and project using JMESPath and return the first match as a single line
sim-api user di38qex \
  --format lines \
  --fields "daten.emailadressen[?contains(typ,'hauptemail')].adresse | [0]"

# Combine multiple JMESPath expressions when exporting CSV
sim-api user di38qex \
  --format delimited --sep ';' \
  --fields "kennung,daten.emailadressen[?contains(typ,'hauptemail')].adresse | [0],rollen[?status=='aktiv'].bezeichnung"

# Stream identifiers line by line for shell pipelines
sim-api groups AI --format lines \
| xargs -n1 -I{} sim-api group-info {} --format delimited --sep '\t' --fields id,owner,count

# Keep compatibility with existing consumers expecting key=value pairs
sim-api institution 0000000000E4EE4B --format kv | grep '^status='
```

## Extending the client

Adding new endpoints is as simple as defining another method on `SimApiClient` and, where useful,
adding a matching dataclass inside `sim_api_wrapper.models`. The helper `_request_json` handles
request execution, error handling and logging for you.

## Testing

The test-suite stubs HTTP responses so you can quickly verify endpoint integration logic without
hitting the real service. Run ``pytest`` as shown above to execute the checks.
