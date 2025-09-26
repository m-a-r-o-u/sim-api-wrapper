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

The client expects SIM API credentials to be stored in a `.netrc` file (by default `~/.netrc`).
You can pass a custom path when instantiating the client or via the CLI's `--netrc` option.

## Usage

### Python

```python
from sim_api_wrapper import SimApiClient

with SimApiClient() as client:
    groups = client.list_groups()
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
sim-api groups
sim-api group-members pn69ju-ai-c
sim-api project-institution pn69ju
sim-api institution 0000000000E4EE4B
sim-api person 00000000001F17E0
sim-api user di38qex
```

Use `--help` to inspect all options. The CLI respects `--netrc` and `--no-netrc` if you need to
control authentication explicitly.

## Extending the client

Adding new endpoints is as simple as defining another method on `SimApiClient` and, where useful,
adding a matching dataclass inside `sim_api_wrapper.models`. The helper `_request_json` handles
request execution, error handling and logging for you.

## Testing

The test-suite stubs HTTP responses so you can quickly verify endpoint integration logic without
hitting the real service. Run ``pytest`` as shown above to execute the checks.
