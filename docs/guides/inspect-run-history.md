# Inspect run history

Run history is authoritative runtime metadata, distinct from operational log files. Use `runs` to list
historical executions and `status` to inspect one run in detail.

## List runs

```bash
pyingest runs
```

Filter by job and status:

```bash
pyingest runs --job demo.local_file --status FAILED
```

Select the same project configuration used by the job when metadata is not in the default workspace:

```bash
pyingest runs --config examples/plugin_package/demo-versioned.yml
```

## Inspect the latest run

With no run ID, `status` resolves the latest run visible through the active `MetadataStore`:

```bash
pyingest status --config examples/plugin_package/demo-versioned.yml
```

This is intended for operator convenience after a known ingestion command.

## Inspect a specific run

Use the full UUID or a unique prefix:

```bash
pyingest status <full-uuid-or-unique-prefix> \
  --config examples/plugin_package/demo-versioned.yml
```

Ambiguous or unknown lookup selections are controlled CLI errors rather than implicit guesses.

## Machine-readable output

Both commands support `--json`:

```bash
pyingest runs --json --config examples/plugin_package/demo-versioned.yml
pyingest status --json --config examples/plugin_package/demo-versioned.yml
```

Use JSON for automation. Human Rich formatting is presentation-level output and should not be parsed by
scripts.

## What status represents

Status/history is read through the `MetadataStore` abstraction. Depending on the run and backend, the
record can include:

- run identity, job/version and timestamps;
- terminal run state;
- step records;
- durable artifact references;
- lineage and replay relationships;
- validation/profile/diff observations where recorded;
- target-load history for capable metadata backends.

Operational logs are useful diagnostic evidence but are not the authoritative source for run state.

## Cross-host operation

With PostgreSQL metadata, history is not tied to one local workspace. A fresh operator process can
inspect durable runs so long as it selects the same metadata backend and has the required credentials.

For a complete production-like journey see `docs/guides/v1-production-pilot.md`.
