# `sim-app` automation helpers

The `sim-app` entry point builds on the low-level `sim-api` client to deliver automation workflows
that solve common operational tasks. Each helper focuses on a specific workflow and reuses the same
authentication and configuration options as the base CLI.

## `mcml-master-user-emails`

The first helper discovers all MCML project master users for a service and prints their primary
("hauptemail") addresses. Use it to notify account owners, audit responsibility assignments or share
important service updates.

```bash
sim-app mcml-master-user-emails
```

Pass `--test` to sample a subset of projects while developing or testing new integrations. For
example, `sim-app mcml-master-user-emails --test 2` only processes the first two MCML projects that
match the selected service. Combine this with `--verbose` (or `-v`) to print each step the helper
executes for easier debugging.

The command shares the same authentication flags as `sim-api` (`--netrc`, `--no-netrc`, `--base-url`
and `--timeout`). Diagnostic information is emitted on `stderr` whenever a project is missing master
users, a user account cannot be resolved, or no hauptemail address exists for a master user. The
process continues whenever possible so partial results can still be retrieved.

## Selecting and exporting data

Helpers accept the familiar `--fields` option to extract targeted properties from each record using a
JMESPath-inspired syntax. That makes it easy to pipe results into downstream systems without post-
processing:

```bash
sim-app mcml-master-user-emails \
  --fields "kennung,daten.emailadressen[?contains(typ,'hauptemail')].adresse | [0]" \
  --format delimited --sep ';'
```

The example produces a semicolon-delimited CSV stream containing project identifiers, user IDs and
primary email addresses.

## Extending `sim-app`

New helpers can be added alongside `mcml-master-user-emails`. Reuse the underlying `SimApiClient`
methods and focus on the control flow that turns API responses into a repeatable automation. Because
the helpers run through the same CLI dispatcher, they automatically inherit logging, authentication
and output formatting features from the core implementation.
