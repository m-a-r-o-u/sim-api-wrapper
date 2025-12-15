# `sim-app` automation helpers

The `sim-app` entry point builds on the low-level `sim` client to deliver automation workflows
that solve common operational tasks. Each helper focuses on a specific workflow and reuses the same
authentication and configuration options as the base CLI.

## `all-user-emails`

Use this helper to collect the primary email addresses of everyone who can access an AI system.
It merges users from both AI compute projects and MCML groups, deduplicates them and prints the
first matching `hauptemail` or `kontaktemail` entry for each person. This gives you a single
distribution list that covers all stakeholders of an AI deployment.

```bash
sim-app all-user-emails
```

Provide `--service` when you need to target a specific SIM service identifier. The command defaults
to `AI`, meaning `sim-app all-user-emails --service=XX` will switch to service `XX`. The helper also
understands the global options shared across `sim-app` commands, including authentication flags and
the `--test` sampling mode.

During collection the helper emits warnings on `stderr` whenever a group member is missing, a user
cannot be resolved or no primary email address exists. Processing continues so you still receive
partial results for the remaining users.

## `mcml-master-user-emails`

This helper discovers all MCML project master users for a service and prints their primary
("hauptemail" or "kontaktemail") addresses. Use it to notify account owners, audit responsibility
assignments or share important service updates.

```bash
sim-app mcml-master-user-emails
```

Pass `--test` to sample a subset of projects while developing or testing new integrations. For
example, `sim-app mcml-master-user-emails --test 2` only processes the first two MCML projects that
match the selected service. Combine this with `--verbose` (or `-v`) to print each step the helper
executes for easier debugging.

The command shares the same authentication flags as `sim` (`--netrc`, `--no-netrc`, `--base-url`
and `--timeout`). Diagnostic information is emitted on `stderr` whenever a project is missing master
users, a user account cannot be resolved, or neither a hauptemail nor a kontaktemail address exists
for a master user. The process continues whenever possible so partial results can still be
retrieved.

## `mcml-user-emails`

Use this helper to focus on MCML users that belong to the central AI Systems project. It filters
service groups whose names start with `aisystems` and end with the `-ai-h-mcml` suffix, aggregates the
members, deduplicates them and prints each person's primary ("hauptemail" or "kontaktemail")
address. The output is perfect for distributing targeted notices to the shared MCML environment
users.

```bash
sim-app mcml-user-emails
```

Like the other helpers, you can pass `--service` to inspect a different SIM service and `--test` to
sample only the first _n_ matching groups when experimenting. Increase verbosity with `--verbose` or
`-vv` to trace the underlying API calls and see intermediate progress messages.

## Selecting and exporting data

Helpers accept the familiar `--fields` option to extract targeted properties from each record using a
JMESPath-inspired syntax. That makes it easy to pipe results into downstream systems without post-
processing:

```bash
sim-app mcml-master-user-emails \
  --fields "kennung,daten.emailadressen[?contains(typ,'hauptemail') || contains(typ,'kontaktemail')].adresse | [0]" \
  --format delimited --sep ';'
```

The example produces a semicolon-delimited CSV stream containing project identifiers, user IDs and
primary email addresses.

## Extending `sim-app`

New helpers can be added alongside `mcml-master-user-emails`. Reuse the underlying `SimApiClient`
methods and focus on the control flow that turns API responses into a repeatable automation. Because
the helpers run through the same CLI dispatcher, they automatically inherit logging, authentication
and output formatting features from the core implementation.
