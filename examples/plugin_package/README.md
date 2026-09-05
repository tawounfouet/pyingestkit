# PyIngestKit Demo Jobs

This directory is an independently installable job pack demonstrating the recommended declarative
API, Python entry-point discovery and the representative workflows qualified for V1.

```bash
python -m pip install -e examples/plugin_package
pyingest jobs
```

The pack exposes **nine** `JobDefinition` entry points built with `@job` / `@step`:

```text
demo.local_file
demo.http_csv
demo.http_json
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
demo.versioned_ndjson
demo.versioned_postgres
demo.versioned_s3
```

Discovery compiles each definition into the imperative `Job` / `Pipeline` model before Runner
execution. Runtime values come from `RunContext.parameters`; plugin discovery does not require
execution-time constructor arguments.

The demo uses the normal configured PyIngestKit workspace and does not create a separate framework
runtime.

## Local operator slice

```bash
pyingest inspect demo.local_file
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest runs --config examples/plugin_package/demo.yml
pyingest status --config examples/plugin_package/demo.yml
```

## HTTP and quality slices

```bash
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
pyingest run demo.ndjson_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.excel_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.parquet_quality --config examples/plugin_package/demo-quality.yml
```

These jobs use deterministic fixtures and are intended as executable end-to-end contracts, not
production data sources.

## Local versioning / diff / replay slice

```bash
pyingest run demo.versioned_ndjson \
  --config examples/plugin_package/demo-versioned.yml \
  --param revision=1

pyingest run demo.versioned_ndjson \
  --config examples/plugin_package/demo-versioned.yml \
  --param revision=2

pyingest versions demo.versioned_ndjson \
  --config examples/plugin_package/demo-versioned.yml
pyingest published demo.versioned_ndjson \
  --config examples/plugin_package/demo-versioned.yml
pyingest replay --config examples/plugin_package/demo-versioned.yml
```

## Service-backed slices

`demo.versioned_postgres` qualifies PostgreSQL metadata/targets, load modes and idempotency.
`demo.versioned_s3` qualifies S3-compatible durable artifacts/versioning plus strict replay from a
fresh workspace using shared durable state.

Their executable configs are:

```text
examples/plugin_package/demo-versioned-postgres.yml
examples/plugin_package/demo-versioned-s3.yml
```

The repository CI runs these against PostgreSQL 16 and pinned MinIO rather than requiring those
services for the offline demo tests.

See `docs/reference/pilots-v1.md` for the V1.0.0-b2 qualification matrix.
