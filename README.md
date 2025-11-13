# SIM API Wrapper

A lightweight, extensible Python wrapper for the [LRZ SIM API](https://simapi.sim.lrz.de). The
client makes it straightforward to retrieve information about projects, groups, institutions,
people and users while keeping the implementation easy to read and extend.

## Features

- 🔌 **Extensible** – add new endpoints by implementing a single method.
- ♻️ **Reusable** – ship it as a Python package and reuse it across projects.
- 📝 **Understandable** – strong typing via dataclasses and consistent error handling.
- 🛠️ **Tooling friendly** – comes with tests, logging and a CLI for quick inspection.

## Installation

The wrapper uses the [uv](https://github.com/astral-sh/uv) package manager so you can get the
tooling, dependencies and tests in a single step:

```bash
# Create (or reuse) a virtual environment managed by uv
uv venv

# Activate the virtual environment (Linux/macOS)
source .venv/bin/activate

# Install the package in editable mode together with the optional test extras
uv pip install -e ".[test]"
```

Once the installation succeeds you can immediately run the test-suite via `pytest` to verify that
everything is wired up correctly.

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

## What is `sim-api`?

`sim-api` is a Python client and CLI for the LRZ SIM platform. It wraps common REST calls with typed
helpers so you can explore services, groups, institutions and identities without hand-rolling HTTP
requests. Typical use cases include scripting account audits, exporting membership lists and
retrieving metadata for reporting.

### Quick examples

In Python you can combine the high-level helpers to gather information in a few lines of code:

```python
from sim_api_wrapper import SimApiClient

with SimApiClient() as client:
    members = client.get_group_members("AI", "pn69ju-ai-c")
    permissions = client.get_user_permissions("di38qex")

print(members)
print(permissions)
```

Prefer the terminal? The CLI mirrors the same capabilities so you can inspect data without writing
code:

```bash
sim-api group-members AI pn69ju-ai-c --solve
```

Consult the dedicated guide for a full list of commands and output formats.

## What is `sim-app`?

`sim-app` bundles higher-level automation workflows on top of the raw API client so you can turn
common tasks into repeatable scripts. For example, the `mcml-master-user-emails` helper discovers all
MCML project master users for a service and prints their primary ("hauptemail" or "kontaktemail")
addresses—ideal for notifications or audits.

```bash
sim-app mcml-master-user-emails --test 2 --verbose
```

The snippet above samples two projects while printing detailed progress information. `sim-app` uses
the same authentication flags as `sim-api`, making it easy to move between both tools.

## Additional documentation

- [Deep dive into the `sim-api` client and CLI](docs/sim-api.md)
- [Automation recipes with `sim-app`](docs/sim-app.md)
