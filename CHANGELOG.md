# Changelog

All notable changes to PyIngestKit are documented here.

## [0.4.0] - 2026-09-04

### Diff / Replay / Versioning Release

- promoted the fully qualified V0.4 release candidate to stable `0.4.0` without adding new runtime features;
- froze the public top-level API and CLI command surface for the V0.4 release line;
- froze Dataset fingerprint canonical codec version `1`, Dataset snapshot version `1`, and diff report version `1`;
- released deterministic Dataset fingerprints and keyed/keyless diff semantics with portable `reports/diff.json` evidence;
- released typed-JSON Dataset snapshots, content-addressed immutable versions, and atomic `PublishedDataset` pointers;
- released strict replay from historical immutable RAW with explicit lineage and fingerprint verification;
- froze seven executable reference jobs, including `demo.versioned_ndjson` proving V1 -> V2 -> diff -> publish -> strict replay;
- retained additive SQLite/PostgreSQL metadata evolution and compatibility with custom MetadataStore implementations lacking optional V0.4 capabilities;
- retained Python 3.11/3.12/3.13 qualification, Ruff/Mypy quality gates, Bandit/pip-audit security gates, package builds, and clean-wheel smoke validation.

## [0.4.0rc1] - 2026-09-04

### Release Candidate — Diff / Replay / Versioning E2E

- fixed the V0.4 demo-package dependency contract and promoted framework/demo versions to `0.4.0rc1`;
- added `demo.versioned_ndjson` as the seventh reference job;
- added deterministic revision 1 / revision 2 fixtures producing one added, removed, changed, and unchanged row;
- proved content-addressed V1/V2 version creation and atomic publication of V2;
- proved strict replay of revision 2 from historical RAW with no live source acquisition and matching Dataset fingerprint;
- extended clean-wheel smoke validation to all seven jobs with real OpenPyXL and PyArrow extras;
- qualified the RC on Python 3.11/3.12/3.13 and the Security workflow.

## [0.4.0b2] - 2026-09-04

### Beta 2 — Replay From RAW + Lineage

- added strict replay contexts/services over historical immutable RAW artifacts;
- added zero-network HTTP replay and local-file replay independent of current source state;
- verified origin and newly materialized RAW SHA-256 values;
- added replay lineage/reproducibility metadata, manifest evidence and REPLAY events;
- added same-version Dataset fingerprint verification with best-effort pre-V0.4 fallback;
- added `pyingest replay`, `--allow-version-change` and `--no-verify`;
- preserved redacted historical secrets instead of attempting secret restoration.

## [0.4.0b1] - 2026-09-04

### Beta 1 — Dataset Snapshots + Version Registry + PublishedDataset

- added versioned typed-JSON Dataset snapshots with deterministic round-trip semantics and no pickle;
- added content-addressed `DatasetVersion` identity from Dataset fingerprints;
- added `FilesystemDatasetVersionStore` with immutable history under `versions/`;
- added atomic `PublishedDataset` current pointers under `published/`;
- added additive version/run/publication metadata capabilities and SQL tables;
- added `pyingest versions` and `pyingest published`;
- retained V0.3 Dataset neutrality and V0.4 A1/A2 diff contracts.

## [0.4.0a2] - 2026-09-04

### Diff Reports + Runtime / Metadata Observation

- added portable schema-v1 `reports/diff.json` artifacts written atomically by ArtifactStore;
- made Runner observe explicit `DatasetDiff` step outputs without auto-computing comparisons;
- added additive manifest diff report references and compact `DIFF_STARTED`, `DIFF_COMPLETED`, and `DIFF_REPORT_WRITTEN` events;
- added optional `DiffMetadataCapability` so legacy third-party MetadataStore implementations remain valid;
- added `DiffRecord` and the additive `dataset_diffs` table to Memory/SQLite/PostgreSQL built-in stores;
- exposed persisted diff summaries through `pyingest status` and `--json`;
- kept raw before/after rows out of reports by default and redacted secret-looking fields when value capture is explicitly enabled.

## [0.4.0a1] - 2026-09-04

### Dataset Fingerprints + Diff Engine

- added deterministic type-aware Dataset fingerprints distinct from RAW artifact hashes;
- added explicit order-sensitive and order-insensitive fingerprint policies;
- added canonical encoding for nested Python/JSON values plus bytes, Decimal, date/datetime and special floats;
- added keyed Dataset diff with exact ADDED/REMOVED/CHANGED/UNCHANGED counts;
- added keyless multiset diff preserving duplicate multiplicity;
- added schema diff, bounded deterministic entries, missing-vs-null semantics and opt-in value capture;
- added no dataframe or external diff dependency and retained the V0.3 materialized Dataset contract.

## [0.3.0] - 2026-09-04

### Quality & Formats Release

- promoted the validated Quality & Formats release candidate to stable `0.3.0`;
- froze Dataset Contracts V2, Dataset profiling, and portable validation/profile report artifacts;
- released structural parsers for CSV, JSON, NDJSON, Excel and Parquet behind one dependency-neutral `Dataset` contract;
- retained OpenPyXL and PyArrow as optional extras with lazy imports and explicit missing-extra errors;
- froze six executable reference jobs and clean-wheel validation with Excel/Parquet extras;
- retained Python 3.11/3.12/3.13 CI coverage, strict typing and security gates.

## [0.3.0rc1] - 2026-09-04

### Release Candidate — Quality & Formats E2E

- added `demo.ndjson_quality`, `demo.excel_quality`, and `demo.parquet_quality`;
- connected RAW -> parser -> Dataset -> Contract V2 -> validation -> profiling -> quality reports;
- expanded the demo pack to six reference entry points;
- hardened wheel smoke testing to install real OpenPyXL and PyArrow extras in a fresh environment;
- added deterministic quality-format E2E tests and documented the materialized Dataset boundary.

## [0.3.0b2] - 2026-09-04

### Beta 2 — Parquet

- added lazy optional `ParquetParser` backed by PyArrow;
- retained the dependency-neutral `Dataset` output contract;
- added structural column projection and explicit `max_rows` materialization guardrail;
- kept PyArrow out of mandatory runtime dependencies.

## [0.3.0b1] - 2026-09-04

### Beta 1 — NDJSON + Excel

- added `NdjsonParser` and optional `ExcelParser` through the `excel` extra;
- preserved source-native values without business coercion;
- added worksheet/header selection and structural validation;
- retained the dependency-neutral `Dataset`.

## [0.3.0a2] - 2026-09-04

### Dataset Profiling + Quality Reports

- added `DatasetProfiler`, immutable `DatasetProfile`, `FieldProfile`, and `QualityReport`;
- materialized validation/profile evidence to portable reports;
- added profile/report manifest references and runtime events;
- kept profiling descriptive rather than semantic inference.

## [0.3.0a1] - 2026-09-04

### Quality Contracts V2

- extended `FieldContract` with value, regex, range and length constraints;
- added composite uniqueness and logical `primary_key`;
- added bounded issue collection with safe previews;
- retained no-coercion/no-mutation semantics.

## [0.2.0] - 2026-09-04

### Acquisition Release

- promoted the acquisition vertical slice to stable `0.2.0`;
- froze local/HTTP reference jobs and offline deterministic acquisition tests;
- retained runtime validation evidence across manifest, MetadataStore and lifecycle events;
- added a release wheel-smoke gate for framework/demo wheels.

## [0.2.0rc1] - 2026-09-04

### Release Candidate — Acquisition E2E

- added `demo.http_csv` and `demo.http_json` alongside `demo.local_file`;
- connected HttpSource -> RetryPolicy -> RAW -> Parser -> Dataset -> Contract -> ValidationResult;
- added persisted validations and status inspection;
- added deterministic fixture HTTP transport and socket-blocked tests.

## [0.2.0b1] - 2026-09-04

### Beta 1 — Dataset + CSV/JSON + Contracts

- added framework-owned dependency-neutral `Dataset`;
- added `CsvParser`, `JsonParser`, `FieldContract`, `DatasetContract`, and immutable `ValidationResult`;
- linked parsed datasets to originating RAW artifacts;
- enforced no-Pandas/no-Polars/no-Arrow core guardrails.

## [0.2.0a2] - 2026-09-03

### Acquisition Alpha 2 — HTTP -> RAW + provenance

- made `HttpSource` a framework `Source` with `fetch(context) -> RawArtifact`;
- connected successful HTTP bytes to immutable RAW storage and SHA-256 hashing;
- added persisted HTTP provenance with URL sanitization and secret protection;
- added offline HTTP -> RAW -> manifest -> SQLite integration tests.

## [0.2.0a1] - 2026-09-03

### Acquisition Alpha 1 — HTTP + Retry

- added framework-owned HTTP request/response/client contracts and HTTPX adapter;
- added bounded timeouts, redirect control and Tenacity-backed retry policy;
- added conservative idempotent retry defaults and `Retry-After` support;
- mapped transport errors into PyIngestKit exceptions and added redaction boundaries.

## [0.1.6] - 2026-09-03

### Foundation Persistence & Quality Hardening

- adopted SQLAlchemy 2.x Core as the single internal metadata persistence engine;
- retained `MetadataStore` as the stable domain-facing persistence contract;
- kept SQLite as default and PostgreSQL via optional `psycopg` extra;
- added Ruff, Mypy strict, Bandit, pip-audit and aggregate `make verify` gates;
- preserved the existing public API and additive metadata schema strategy.

## [0.1.5] - 2026-09-03

### Foundation consolidation

- unified the default workspace on `.pyingest/`;
- added MetadataStore, SQLite default state, optional PostgreSQL, run history and status CLI;
- added declarative `@step` / `@job` API compiling to the imperative model;
- added plugin isolation, runtime logging controls, RAW immutability and metadata persistence;
- stabilized terminal log and structured metadata conventions.

## [0.1.4] - 2026-09-03

- added production-grade logging configuration, Rich/plain/JSON formats, context propagation, secret redaction, rotating file logging and CLI log controls;
- documented the logging policy without imposing Loguru on plugins.

## [0.1.3] - 2026-09-03

- added a real installable demo job package, entry-point discovery and typed repeatable runtime parameters.

## [0.1.2] - 2026-09-03

- replaced the artificial zero-third-party-dependency rule with governed production-grade dependencies;
- added Pydantic/PyYAML configuration and machine-safe CLI JSON output.

## [0.1.1] - 2026-09-03

- replaced argparse with Typer and Rich.

## [0.1.0] - 2026-09-03

- initial MVP foundation: core/runtime, LocalSource, RAW, SHA-256, manifest, validation, atomic publication, plugins and CLI.
