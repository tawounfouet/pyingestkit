# V1 Quickstart — From install to traceable ingestion

This guide exercises the stable V1 contract using the maintained demo job pack. It is intentionally
local-first and requires no PostgreSQL or object-storage service.

PyIngestKit 1.0.0 is the stable package line. The repository release discipline still requires the
annotated `v1.0.0` tag to point at the exact post-merge-qualified stable SHA before publication.

## 1. Create an isolated environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,excel,parquet]"
python -m pip install -e examples/plugin_package
```

Confirm the CLI and installed job pack:

```bash
pyingest --version
pyingest jobs
```

The maintained reference pack exposes nine jobs:

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

## 2. Inspect a job before running it

```bash
pyingest inspect demo.local_file
```

`inspect` is an operator-facing contract: use it to verify the logical job ID, version, pipeline and
backend requirements before execution.

## 3. Run the smallest local pilot

```bash
pyingest run demo.local_file \
  --config examples/plugin_package/demo.yml
```

The config supplies the fixture path and uses filesystem artifacts, SQLite metadata and the `.pyingest`
workspace. The run creates immutable RAW plus metadata under the configured workspace.

## 4. Inspect history and status

```bash
pyingest runs --config examples/plugin_package/demo.yml
pyingest status --config examples/plugin_package/demo.yml
```

`status` defaults to the latest run when no run ID is supplied. To inspect a known run explicitly:

```bash
pyingest status <run-id> --config examples/plugin_package/demo.yml
```

## 5. Exercise HTTP + quality without public network access

```bash
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
pyingest run demo.ndjson_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.excel_quality --config examples/plugin_package/demo-quality.yml
pyingest run demo.parquet_quality --config examples/plugin_package/demo-quality.yml
```

These maintained reference jobs use deterministic fixture transports/data and exercise RAW provenance,
parsing, validation, profiling and portable reports.

## 6. Exercise versioning, diff and publication

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
```

The second revision produces a deterministic diff against the previously published dataset and then
publishes the new version.

## 7. Strict replay

```bash
pyingest replay --config examples/plugin_package/demo-versioned.yml
```

Or select a run explicitly:

```bash
pyingest replay <run-id> \
  --config examples/plugin_package/demo-versioned.yml
```

Replay consumes historical RAW; it does not reacquire the live source. The versioned reference job
uses a network-forbidden client during replay so an accidental live fetch fails loudly.

## 8. Understand configuration precedence

Configuration-file resolution is:

```text
--config
  -> PYINGEST_CONFIG
  -> PYINGEST_ENV -> pyingest.yml.<env>
  -> default project config files
  -> in-memory defaults
```

Workspace resolution is:

```text
--workspace
  -> PYINGEST_WORKSPACE
  -> runtime.workspace
  -> .pyingest
```

Explicit selectors fail closed. If `PYINGEST_CONFIG` or `PYINGEST_ENV` points to a missing selection,
PyIngestKit does not silently fall back to a different environment.

## 9. Machine-readable operator output

Use `--json` where a command exposes it and another program needs the result. Successful structured
payloads go to stdout; operational logs and controlled errors remain on stderr. Normal configuration
inspection masks secret-bearing values.

## 10. Move to a production-like pilot

Continue with:

- `docs/guides/v1-production-pilot.md` for PostgreSQL + S3-compatible object storage;
- `docs/reference/pilots-v1.md` for the five representative qualification scenarios;
- `docs/reference/stable-contract-v1.md` for the effective 1.x promise;
- `docs/reference/public-api.md` for the historical governed Python inventory;
- `docs/reference/compatibility-v1.md` and `docs/reference/stability-v1.md` for compatibility details.
