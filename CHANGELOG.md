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

## [0.3.0] - 2026-09-04

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
- connected successful HTTP response bytes to immutable RAW storage and SHA-256 hashing;
- added persisted HTTP acquisition provenance: `source_uri`, `resolved_url`, `status_code`, `content_type`, `etag`, `last_modified`, `retrieved_at`, `size_bytes`, `sha256`;
- added `artifact_http_provenance` as a one-to-one MetadataStore table while keeping the generic `artifacts` table backward-compatible;
- sanitized effective request/final URLs before persistence and prevented arbitrary request/response headers from entering artifacts, manifests or metadata;
- added explicit redaction for secret-looking query parameters supplied through `HttpRequest.params`;
- made `HttpxClient` send the same merged effective URI represented by `HttpRequest`, preserving query parameters already present in the base URL;
- added offline end-to-end HTTP → RAW → manifest → SQLite tests using `httpx.MockTransport`;
- added persistence tests proving credentials/tokens are absent from manifest/metadata surfaces;
- fixed the Alpha 1 Ruff import-order packaging quirk that caused `make quality` / `make verify` to fail on the delivered ZIP;
- added ADR-024.

## [0.2.0a1] - 2026-09-03

### Acquisition Alpha 1 — HTTP + Retry

- added framework-owned `HttpRequest`, `HttpResponse` and `HttpClient` contracts;
- added `HttpxClient` as the default synchronous HTTP adapter behind the framework protocol;
- added bounded request timeouts and redirect control;
- added `HttpSource.fetch_response()` as the Alpha 1 transport acquisition surface;
- added `RetryPolicy` backed internally by Tenacity;
- default retries are conservative: GET/HEAD and transient HTTP status allowlist only;
- added bounded exponential backoff, optional jitter and `Retry-After` support;
- mapped HTTPX timeouts/transport failures to PyIngestKit exceptions;
- added URL/header redaction at representation/error/logging boundaries;
- added offline HTTP tests based on `httpx.MockTransport`;
- added ADR-022 and ADR-023;
- preserved the V0.1.6 Foundation public API and deferred HTTP → RAW integration to Alpha 2.

## [0.1.6] - 2026-09-03

### Foundation Persistence & Quality Hardening

- adopted SQLAlchemy 2.x Core as the single internal metadata persistence engine;
- retained `MetadataStore` as the stable framework contract and plain dataclass records as the domain-facing metadata model;
- refactored SQLite and PostgreSQL metadata adapters onto shared SQLAlchemy tables/statements;
- kept SQLite as the default backend with foreign keys, WAL mode and bounded busy timeout;
- normalized standard PostgreSQL DSNs to the psycopg SQLAlchemy dialect while keeping `psycopg` optional via `[postgres]`;
- explicitly rejected Peewee as a second ORM and deferred Alembic until schema migration requirements are demonstrated;
- removed hand-built dynamic SQL from the PostgreSQL adapter, eliminating the V0.1.5 Bandit B608 root cause;
- modernized Python 3.11+ code patterns (`datetime.UTC`, `StrEnum`, `collections.abc`, `Self`) and documented justified broad-exception isolation boundaries;
- modernized project licensing metadata to PEP 639 / SPDX form;
- added explicit Ruff lint policy, Ruff formatting gate, Mypy strict gate, Bandit and pip-audit gates;
- added aggregate `make verify` as the release/foundation-freeze criterion;
- added ADR-021 to defer Alembic until a released schema change requires compatible in-place migration;
- added SQLAlchemy persistence tests and SQLite WAL/foreign-key checks;
- preserved the public top-level API and the existing SQLite table names (`runs`, `steps`, `artifacts`, `validations`, `publications`, `events`).

All notable changes to PyIngestKit are documented here.

## [0.1.5] - 2026-09-03

### Foundation consolidation

- Unified the default workspace on `.pyingest/`; the demo no longer creates `.pyingest-demo/`.
- Added `MetadataStore` as a runtime persistence contract distinct from `ArtifactStore`.
- Added SQLite as the default CLI metadata backend at `.pyingest/state/pyingest.sqlite3`.
- Added an optional PostgreSQL adapter contract and `postgres` installation extra using lazy Psycopg loading.
- Persisted runs, steps, artifacts, validations, publications and structural runtime events.
- Added `pyingest runs` and `pyingest status` with JSON modes and run-ID prefix resolution.
- Added the declarative `@step` / `@job` API with `StepDefinition`, `StepInvocation`, `JobDefinition` and deterministic `PipelineBuilder`.
- Kept the imperative `Job` / `Step` / `Pipeline` API as the low-level contract; decorators compile to it.
- Migrated the bundled demo job pack to decorators and entry-point `JobDefinition` discovery.
- Added `.fn(...)` as the explicit direct unit-test surface for decorated steps.
- Added plugin failure isolation so a broken plugin does not hide healthy plugins.
- Added `-v/--verbose` and `-q/--quiet` logging controls.
- Stabilized terminal logs as local `YYYY-MM-DD HH:mm:ss`, colored level, short run ID, job and optional step context.
- Changed step lifecycle boundaries to INFO; implementation details remain DEBUG.
- Kept full UUIDs and timezone-aware ISO-8601 timestamps in JSON logs and metadata.
- Added recursive secret-key redaction for persisted runtime parameters.
- Enforced RAW immutability within a run by refusing silent overwrite.
- Automatically registers RAW artifacts in both `manifest.json` and MetadataStore.
- Critical lifecycle-hook failures now converge to a failed `RunResult` and persisted failure state when possible.
- Added validation/publication metadata tables/contracts without forcing a universal business workflow.
- Added new ADRs 012–017 and foundation architecture/guides.
- Added CI/security workflow definitions and wheel-oriented smoke-test guidance.
- Moved package version to a single `_version.py` source consumed dynamically by setuptools.

## [0.1.4] - 2026-09-03

### Added

- Production-grade logging configuration based on the Python standard `logging` API.
- Rich, plain-text, and structured JSON console log formats.
- Optional rotating file logging with independent level and format.
- Context propagation for `run_id`, `job_id`, and `step` using `contextvars`.
- Basic credential redaction for common password/token/API-key patterns.
- Runtime lifecycle logging in the runner, artifact store, and plugin discovery.
- `--log-level` and `--log-format` CLI overrides.
- ADR-011 documenting the logging policy and the decision not to impose Loguru on framework plugins.

## [0.1.3] - 2026-09-03

- Added a real installable demo job package and `pyingestkit.jobs` entry point.
- Added repeatable typed `--param/-p KEY=VALUE` runtime parameters.

## [0.1.2] - 2026-09-03

- Replaced the artificial zero-third-party-dependency rule with governed production-grade dependencies.
- Added Pydantic/PyYAML configuration and machine-safe CLI JSON output.

## [0.1.1] - 2026-09-03

- Replaced argparse with Typer and Rich.

## [0.1.0] - 2026-09-03

- Initial MVP foundation: core/runtime, LocalSource, RAW, SHA-256, manifest, validation, atomic publication, plugins and CLI.
