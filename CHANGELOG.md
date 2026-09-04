# Changelog

## [0.3.0] - 2026-09-04

### Quality & Formats Release

- promoted the validated Quality & Formats release candidate to stable `0.3.0`;
- froze Dataset Contracts V2, Dataset profiling, and portable validation/profile report artifacts as the stable V0.3 quality surface;
- released structural parsers for CSV, JSON, NDJSON, Excel and Parquet behind one dependency-neutral `Dataset` contract;
- retained OpenPyXL and PyArrow as optional extras with lazy imports and explicit missing-extra errors;
- retained the materialized Dataset boundary and Parquet `max_rows` guardrail without claiming streaming semantics;
- froze six executable reference jobs covering the V0.2 acquisition baseline and V0.3 quality-format vertical slices;
- hardened the distribution gate to install the built wheel with Excel/Parquet extras and execute all six jobs in a fresh virtual environment;
- retained Python 3.11/3.12/3.13 CI coverage, offline acquisition tests, strict typing, security gates and clean-wheel validation.

## [0.3.0rc1] - 2026-09-04

### Release Candidate — Quality & Formats E2E

- added three complete quality-format reference jobs: `demo.ndjson_quality`, `demo.excel_quality`, and `demo.parquet_quality`;
- connected RAW -> parser -> Dataset -> DatasetContract V2 -> ValidationResult -> DatasetProfiler -> DatasetProfile -> quality reports for NDJSON, XLSX, and Parquet;
- expanded the installable demo pack from three to six reference entry points while retaining the V0.2 local/HTTP jobs;
- hardened wheel smoke testing to install the `excel` and `parquet` extras from the built framework wheel and execute all six jobs in a fresh environment;
- made the Python 3.11/3.12/3.13 CI matrix exercise real OpenPyXL and PyArrow availability;
- added deterministic quality-format E2E tests checking validation/profile reports, manifest references, metadata, and runtime events;
- removed a duplicate runtime timer initialization discovered during RC hardening;
- documented the materialized Dataset boundary and RC1 end-to-end architecture.

## [0.3.0b2] - 2026-09-04

### Beta 2 — Parquet

- added `ParquetParser` backed lazily by the optional `parquet` extra (`pyarrow`);
- preserved the dependency-neutral `Dataset` as the parser output contract;
- added structural column projection and an explicit `max_rows` materialization guardrail;
- kept PyArrow out of mandatory runtime dependencies and avoided eager imports;
- documented the in-memory Dataset boundary for large Parquet files;
- added parser and public dependency-boundary contract tests.

## [0.3.0b1] - 2026-09-04

### Beta 1 — NDJSON + Excel

- added `NdjsonParser` for newline-delimited JSON object streams with line-aware errors;
- added `ExcelParser` for XLSX worksheets through the optional `excel` extra (`openpyxl`);
- preserved JSON-native and Excel-native cell values without business coercion, trimming, renaming or enrichment;
- added explicit worksheet/header selection and structural header validation;
- kept Excel support out of mandatory core dependencies and retained the dependency-neutral `Dataset`;
- added parser unit tests and public API contracts for both formats.

## [0.3.0a2] - 2026-09-04

### Dataset Profiling + Quality Reports

- added engine-neutral `DatasetProfiler`, immutable `DatasetProfile`, and `FieldProfile`;
- added deterministic row/field/null/distinct/type/string-length/numeric-range/duplicate metrics without semantic inference;
- added `QualityReport` as an optional in-memory aggregate;
- materialized runtime validation evidence to `reports/validation.json`;
- materialized profiling evidence to `reports/profile.json`;
- added additive manifest report references plus `PROFILE_COMPLETED` and `QUALITY_REPORT_WRITTEN` events;
- exposed quality report references through `pyingest status` without adding a profiling SQL schema;
- added ADR-029, ADR-030 and profiling/report guides.

## [0.3.0a1] - 2026-09-04

### Quality Contracts V2

- extended `FieldContract` with allowed values, full-match regex, min/max value and string-length constraints;
- added dataset-level composite uniqueness through `unique_together`;
- added `primary_key` as a logical non-SQL dataset key;
- added bounded issue collection with explicit `issues_truncated`;
- enriched `ValidationIssue` with safe bounded value previews, constraint identity and compact context;
- retained V0.2 validation semantics, no coercion, no mutation, and no dataframe dependency;
- added ADR-028 and the Dataset Contracts V2 guide.

## [0.2.0] - 2026-09-04

### Acquisition Release

- promoted the validated acquisition vertical slice from `0.2.0rc1` to stable `0.2.0`;
- promoted the bundled demo job pack to `0.2.0` and its dependency to `pyingestkit>=0.2.0,<0.3`;
- froze the reference job versions at `0.2.0` for `demo.local_file`, `demo.http_csv`, and `demo.http_json`;
- retained fully offline HTTP tests, including socket-blocked E2E tests and deterministic `503 -> retry -> 200` fixture flows;
- retained runtime validation evidence across manifest, MetadataStore, and lifecycle events;
- added a release wheel-smoke gate that installs the framework and demo-job wheels into a fresh virtual environment before running the three reference jobs;
- defined clean source ZIP and validation-evidence ZIP release artifacts with SHA-256 checksums;
- completed the V0.2 acquisition milestone without reopening the frozen V0.1.6 Foundation contracts.

## [0.2.0rc1] - 2026-09-04

### Release Candidate — acquisition vertical slice E2E

- added `demo.http_csv` and `demo.http_json` reference jobs alongside `demo.local_file`;
- connected `HttpSource -> RetryPolicy -> RAW -> Parser -> Dataset -> DatasetContract -> ValidationResult`;
- made `ValidationResult` observable by `Runner` through manifest, MetadataStore, and `VALIDATION_COMPLETED` events;
- made ERROR validation results fail the producing step only after validation evidence is persisted;
- exposed persisted validations through `pyingest status` and `pyingest status --json`;
- added deterministic fixture HTTP transport in the demo plugin that exercises a 503 -> retry -> 200 sequence;
- added socket-blocked reference job tests proving HTTP tests remain fully offline;
- added CI smoke runs for all three reference jobs;
- folded in the two Ruff formatting corrections reported against the delivered Beta 1 ZIP;
- added ADR-027 and the RC1 E2E architecture note.

## [0.2.0b1] - 2026-09-04

### Beta 1 — Dataset + CSV/JSON + Contracts

- added framework-owned `Dataset` as a dependency-neutral tabular container;
- explicitly kept Pandas, Polars, and Arrow out of the core Dataset contract;
- added `Parser` as the structural `RawArtifact -> Dataset` boundary;
- added `CsvParser` with explicit encoding/delimiter/quote configuration and no business type coercion;
- added `JsonParser` for object/array records with optional structural `records_path` selection;
- preserved CSV values as strings and JSON native values without trimming, coercion, renaming, flattening, or enrichment;
- added `FieldContract` and `DatasetContract` for schema, nullability, runtime type, uniqueness, extra-field, and row-count validation;
- added immutable `ValidationResult` while retaining the V0.1 `ValidationReport` compatibility API;
- enriched `ValidationIssue` with optional field/row coordinates without breaking its original constructor;
- linked parsed datasets to the originating RAW artifact via `source_artifact_id`;
- added RawArtifact -> CSV/JSON Parser -> Dataset -> DatasetContract integration tests;
- added contract tests enforcing the no-Pandas/no-Polars/no-Arrow guardrail;
- folded in the five Ruff formatting corrections reported against the delivered Alpha 2 ZIP;
- added ADR-025 and ADR-026.

## [0.2.0a2] - 2026-09-03

### Acquisition Alpha 2 — HTTP → RAW + provenance

- made `HttpSource` a framework `Source` and added `fetch(context) -> RawArtifact`;
- preserved `fetch_response()` as the lower-level transport surface;
- wrote successful response bytes immutably through the run `ArtifactStore`;
- computed SHA-256 and persisted source URI, resolved URL, status, content type, ETag,
  Last-Modified, retrieval timestamp and size;
- added one-to-one `artifact_http_provenance` metadata persistence while keeping the
  generic artifact table stable;
- kept legacy SQLite databases usable through additive `create_all()` schema evolution;
- redacted secret-looking query values and prevented request/response headers from entering
  persisted provenance;
- added offline integration tests covering `HttpSource -> RAW -> manifest -> SQLite metadata`;
- added missing public artifact imports and compatibility aliases surfaced by contract tests;
- fixed step metadata consistency when a critical event hook fails after step execution;
- aligned `pyingest run` return-code/help behavior with the CLI contract;
- added ADR-024 and the Alpha 2 architecture note.

## [0.2.0a1] - 2026-09-03

### Acquisition Alpha 1

- added framework-owned synchronous HTTP transport contracts;
- added `HttpxClient` on `httpx`;
- added `HttpSource.fetch_response()` as the acquisition surface;
- added explicit connect/read/write/pool timeout configuration;
- added conservative retry policy using Tenacity;
- added `Retry-After` handling for delta-seconds and HTTP-date values;
- added idempotence-aware retry behavior;
- added URL and header sanitization helpers;
- added deterministic `httpx.MockTransport` tests;
- added HTTP acquisition architecture documentation and ADRs 022/023;
- kept pagination, cache, conditional GET, async, XML/Excel/Parquet and database loading out of scope.

## [0.1.6] - 2026-09-03

### Foundation Freeze

- froze the V0.1.x Foundation at `0.1.6` after the SQLite→SQLAlchemy migration and
  Foundation stabilization review;
- replaced the separate Peewee persistence stack with one SQLAlchemy Core engine shared by
  SQLite and PostgreSQL adapters;
- added the PostgreSQL metadata adapter and `postgres` optional dependency group;
- retained `SQLiteMetadataStore`, `PostgresMetadataStore`, and `MemoryMetadataStore` behind
  the stable `MetadataStore` boundary;
- added a canonical metadata schema module and compatibility table exports;
- fixed nested manifest datetime serialization;
- split verification into `check`, `quality`, `security`, and `build` gates and made
  `make verify` their aggregate release command;
- expanded CI to Python 3.11, 3.12, and 3.13 plus a dedicated Python 3.12 Foundation
  verification job;
- added `pip-audit` and retained Bandit as release gates;
- documented the persistence architecture, schema-evolution posture, and Foundation freeze.

## [0.1.5] - 2026-09-03

### Foundation hardening

- added `MetadataStore` abstraction and removed direct runner coupling to SQLite;
- added `MemoryMetadataStore` and kept SQLite as the default persistent adapter;
- moved SQLite to the unified `.pyingest/state/pyingest.sqlite3` workspace;
- added global `--metadata-dsn` and `PYINGEST_METADATA_DSN` support;
- added `pyingest status` with SQLite and JSON outputs;
- added standard-library operational logging with Rich terminal rendering;
- added rotating JSON file logs under `.pyingest/logs/pyingest.log`;
- added run/job/step correlation and secret redaction filters;
- added declarative `@job` / `@step` API compiled back to the imperative `Job`/`Step` model;
- added `pyingest job scaffold --api declarative|imperative`;
- added CLI verbosity controls (`-v`, `-q`) and logging tests;
- added declarative API, logging, and workspace ADRs/guides.

## [0.1.4] - 2026-09-03

### Foundation hardening

- added SQLite-backed metadata history under `.pyingest/state/pyingest.sqlite3`;
- added `pyingest status <run-id>` with human and JSON rendering;
- removed in-memory global run history from the CLI;
- wired runtime events and artifacts into persistent metadata;
- added SQLite schema contract tests and multi-process CLI persistence tests;

## [0.1.3] - 2026-09-03

### Foundation hardening

- added no-op event bus by default;
- isolated subscriber failures as warnings;
- made manifest writing and final lifecycle hooks fail the run;
- added YAML/DSN password redaction and query sanitization;
- introduced atomic JSON writes in ArtifactStore;
- hardened metadata and pipeline contract validation;

## [0.1.2] - 2026-09-03

### Security hardening

- added recursive configuration secret redaction;
- sanitized DSN passwords in errors;
- added atomic publication staging and rollback cleanup;
- prevented plugin discovery failures from breaking unrelated plugins;
- added path traversal protection for run/workspace paths;
- added CI security workflow with Bandit.

## [0.1.1] - 2026-09-03

### Foundation hardening

- fixed multi-process run history by persisting run summaries in `.pyingest/state/runs.json`;
- aligned `manifest.json` lifecycle fields with the final `RunResult`;
- resolved YAML job-relative local file sources;
- fixed stale package metadata in the demo pack;
- added package markers for bundled demo tests;

## [0.1.0] - 2026-09-03

### Foundation

- created src-layout Python package and CLI;
- added imperative ingestion runtime;
- added job registry and plugin entry-point discovery;
- added YAML configuration loader;
- added local file source and filesystem artifacts;
- added immutable RAW artifacts and SHA-256 provenance;
- added validation and atomic publication primitives;
- added run manifest and structured events;
- added installable demo job package;
- added unit, integration, contract tests and CI.
