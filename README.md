# PyIngestKit

PyIngestKit is a reusable Python ingestion framework focused on **reliable, traceable, validated, reproducible, and publishable datasets** without forcing users to rewrite ingestion plumbing.

This repository contains **V0.3.0 — Quality & Formats Release**, built on the frozen V0.2.0 Acquisition Release. It extends the stable HTTP/RAW/provenance pipeline with Dataset Contracts V2, deterministic dataset profiling, portable quality-report artifacts, and structural parsers for NDJSON, XLSX, and Parquet while keeping the framework dependency-neutral at its Dataset boundary.

## Product boundary

PyIngestKit owns **HOW TO INGEST**. External orchestrators own **WHEN TO RUN**.

It is not Airflow, Dagster, Prefect, Celery, a distributed DAG scheduler, a Data Platform, Catalog, IAM system, AI/RAG framework, SaaS integration platform, or universal connector marketplace.

## V0.3.0 stable surface

### Quality

- `FieldContract` V2: required/null/type/unique plus allowed values, full-match regex, min/max value, min/max string length;
- `DatasetContract` V2: row-count bounds, extra-field policy, composite uniqueness, logical primary key, bounded issue collection;
- immutable `ValidationIssue` / `ValidationResult` with safe bounded previews and explicit truncation;
- dependency-neutral `DatasetProfiler`, `DatasetProfile`, and `FieldProfile`;
- portable `reports/validation.json` and `reports/profile.json` artifacts;
- manifest references plus `VALIDATION_COMPLETED`, `PROFILE_COMPLETED`, and `QUALITY_REPORT_WRITTEN` events.

### Formats

- CSV and JSON from V0.2;
- NDJSON parser;
- XLSX parser behind `pyingestkit[excel]` / OpenPyXL;
- Parquet parser behind `pyingestkit[parquet]` / PyArrow;
- no Pandas or Polars dependency in the framework core;
- Parquet remains materialized into the neutral `Dataset` with explicit projection and `max_rows` guardrails.

### Reference jobs

The bundled demo plugin exposes six executable jobs:

```text
demo.local_file
demo.http_csv
demo.http_json
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
```

The three quality-format jobs exercise the full V0.3 vertical slice:

```text
RAW
 ↓
Parser
 ↓
Dataset
 ↓
DatasetContract V2
 ↓
ValidationResult
 ↓
DatasetProfiler
 ↓
DatasetProfile
 ↓
validation.json + profile.json
 ↓
Manifest + Metadata + Events
```

## Installation

Core:

```bash
python -m pip install pyingestkit
```

Excel:

```bash
python -m pip install "pyingestkit[excel]"
```

Parquet:

```bash
python -m pip install "pyingestkit[parquet]"
```

Development / complete format verification:

```bash
python -m pip install -e ".[dev]"
python -m pip install -e examples/plugin_package
```

## CLI

```bash
pyingest --version
pyingest jobs
pyingest inspect demo.ndjson_quality
pyingest run demo.ndjson_quality --config examples/plugin_package/demo-quality.yml
pyingest status <run-id>
pyingest status <run-id> --json
pyingest runs
```

## Quality reports

A quality-aware run may contain:

```text
.pyingest/
└── runs/<namespace>/<job>/<run-id>/
    ├── raw/
    ├── reports/
    │   ├── validation.json
    │   └── profile.json
    └── manifest.json
```

Report files are run artifacts. They are not new SQL entities and do not require a V0.3 metadata migration.

## Materialization boundary

V0.3 deliberately keeps `Dataset` materialized in memory. This is a product boundary, not an accidental promise that every source is small.

```text
Dataset != Pandas DataFrame
Dataset != Polars DataFrame
Dataset != PyArrow Table
Dataset != streaming abstraction
```

Parquet supports structural projection and an explicit `max_rows` pre-materialization check based on Parquet metadata. Future streaming/batched representations may be added behind a separate explicit contract rather than changing V0.3 semantics silently.

## Release gate

The stable release gate is:

```bash
make release-check
```

It combines source validation (`make verify`) and a distribution smoke test (`make wheel-smoke`). The wheel smoke installs the **built framework wheel with Excel and Parquet extras** plus the demo-job wheel into an isolated venv, then executes all six reference jobs.

The CI matrix covers Python 3.11, 3.12 and 3.13 and explicitly imports OpenPyXL and PyArrow before running checks.

See `docs/guides/release-validation-v0.3.0.md` for the final release procedure.
