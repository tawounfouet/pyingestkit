# Changelog

All notable changes to PyIngestKit are documented here.

## [0.6.0] - 2026-09-05

### Object Storage Release

- promoted the fully qualified V0.6 RC1 to stable `0.6.0` without adding a new runtime capability;
- froze the V0.6 public API, S3 configuration schema and framework-owned storage/replay error hierarchy;
- released portable `ArtifactURI` / `StoredArtifact` references, `S3ArtifactStore`, remote RAW/reports/manifests and `S3DatasetVersionStore`;
- released immutable content-addressed remote DatasetVersion snapshots plus the mutable remote `PublishedDataset.current` pointer;
- qualified S3-compatible behavior against real MinIO while keeping boto3 optional behind the `s3` extra and the local filesystem backend first-class;
- proved full cross-host replay after deleting the original workspace, with historical RAW resolved from durable S3 `storage_uri`, strict fingerprint equality and no live source acquisition;
- preserved PostgreSQL V0.5 load semantics and proved idempotent `SKIP` survives a host/workspace change;
- hardened stable CI by pinning the qualified MinIO image digest and generating random ephemeral MinIO credentials instead of static defaults;
- finalized object-storage configuration/security guidance, stable contract documentation and release validation procedures;
- retained Python 3.11/3.12/3.13, PostgreSQL 16, MinIO/S3, Ruff/Mypy, Bandit/`pip-audit`, wheel/sdist build and clean-wheel smoke gates across nine reference jobs.

## [0.6.0rc1] - 2026-09-05

### Release Candidate — Full Cross-Host Object Storage E2E

- added `demo.versioned_s3` as the ninth installable reference job;
- combined remote RAW, validation/profile/diff reports, remote DatasetVersion snapshots, remote publication, PostgreSQL target loading and PostgreSQL metadata in one scenario;
- proved V1 `EXECUTE`, V2 `RELOAD`, deletion of workspace A, replay from workspace B and idempotent target `SKIP`;
- proved the remote V2 diff remains readable after workspace A disappears and `PublishedDataset` remains V2;
- proved strict replay reconstructs `actual_fingerprint == expected_fingerprint == V2` with the original RAW SHA-256;
- retained the B2 public API unchanged and extended clean-wheel qualification to all nine jobs.

## [0.6.0b2] - 2026-09-05

### Beta 2 — Remote DatasetVersion + Publication

- added `S3DatasetVersionStore` under the existing `DatasetVersionStore` contract;
- stored immutable content-addressed snapshot/version objects and SHA-256 verified them on read;
- represented publication as one replaceable remote `current.json` pointer while preserving immutable history;
- made version listing/loading and `published` inspection independent from runner-local filesystem state;
- added missing/corrupt snapshot rejection and shared filesystem/S3 behavioral contract qualification.

## [0.6.0b1] - 2026-09-05

### Beta 1 — Remote Artifact Lifecycle

- added additive `StoredArtifact` references for non-RAW run artifacts;
- persisted reports and manifests to deterministic S3 keys while retaining local parser/operator materialization;
- preserved create-once RAW semantics and run-scoped rewritable report/manifest semantics;
- added remote report/manifest integrity verification and remote `status` recovery.

## [0.6.0a2] - 2026-09-05

### Alpha 2 — S3ArtifactStore + Remote RAW

- added optional `pyingestkit[s3]` support through boto3;
- added `S3ArtifactStore` with AWS S3 and custom S3-compatible endpoint support;
- made remote RAW immutable, SHA-256 annotated and integrity-verified on materialization;
- persisted durable `storage_uri` independently from local cache paths;
- qualified replay after deleting local cached RAW against real MinIO.

## [0.6.0a1] - 2026-09-05

### Alpha 1 — ArtifactStore Contract Hardening + URI

- added credential-free `ArtifactURI` for `file://` and `s3://` locations;
- separated durable artifact identity from parser-facing local materialization;
- added URI-aware artifact resolution and replay while preserving the existing abstract `ArtifactStore` surface;
- added artifact-location metadata and path/key traversal hardening without introducing an S3 dependency.

## [0.5.1] - 2026-09-05

### PostgreSQL Persistence Release Hygiene

- preserved the immutable `v0.5.0` release and moved post-release hygiene into the `0.5.1` maintenance line;
- kept `python-dotenv` as the local CLI DX path while loading only `./.env` from the current working directory and never overriding already-injected OS environment variables;
- hardened the `demo.versioned_postgres` fixture-only target table bootstrap by using SQLAlchemy schema objects instead of interpolated SQL identifiers;
- extended PostgreSQL E2E coverage so `demo.versioned_postgres` proves automatic target-table creation from an absent table for both SQLite and PostgreSQL metadata backends;
- added CLI contract tests for `.env` precedence and for refusing implicit parent-directory `.env` discovery;
- corrected Ruff formatting for the V0.5 PostgreSQL reference-job enhancement so the full release quality gate can pass again;
- retained all V0.5 Target, MetadataStore, COPY, load-mode, idempotency, versioning and replay public contracts unchanged.

## [0.5.0] - 2026-09-05

### PostgreSQL Persistence Targets Release

- promoted the fully qualified PostgreSQL persistence release candidate to stable `0.5.0` without adding new runtime features;
- froze the V0.5 `Target`, `TargetLoadRequest`, `TargetLoadResult`, `LoadMode`, capability and idempotency surfaces;
- released `PostgresTarget` with deterministic schema compatibility, psycopg 3 COPY, transactional `APPEND`, `TRUNCATE_LOAD`, and `REPLACE`;
- released additive target-load lineage for Memory, SQLite and PostgreSQL metadata backends;
- released history-driven `EXECUTE`, `SKIP`, `RETRY`, and `RELOAD` decisions outside the Target contract;
- froze eight executable reference jobs, including `demo.versioned_postgres` proving V1 -> V2 -> diff -> PostgreSQL -> publish -> strict RAW replay -> idempotent SKIP;
- qualified SQLite metadata + PostgreSQL target and PostgreSQL metadata + PostgreSQL target against PostgreSQL 16;
- retained Python 3.11/3.12/3.13, Ruff/Mypy, Bandit/pip-audit, wheel/sdist build and clean-wheel smoke gates.

## [0.5.0rc1] - 2026-09-05

### Release Candidate — Full PostgreSQL Persistence E2E

- added `demo.versioned_postgres` as the eighth installable reference job;
- proved deterministic V1 -> V2 -> diff -> DatasetVersion -> PostgreSQL `COPY` -> publish;
- proved `RELOAD` for V2 and idempotent `SKIP` during strict replay of the already materialized V2;
- proved replay uses historical RAW with live HTTP acquisition forbidden and fingerprint equality preserved;
- qualified the same reference slice with SQLite metadata + PostgreSQL target and PostgreSQL metadata + PostgreSQL target;
- kept target/metadata wiring explicit in the reference job through non-secret backend parameters and environment-variable DSN indirection;
- retained the A2 COPY, B1 target-load metadata, B2 load-mode/rollback/idempotency regression suites on PostgreSQL 16.

## [0.5.0b2] - 2026-09-05

### Beta 2 — Load Modes + Transaction Semantics + Idempotency

- added stable `APPEND`, `TRUNCATE_LOAD`, and `REPLACE` load modes to `PostgresTarget`;
- made destructive PostgreSQL modes validate destination compatibility before mutation and share one transaction with COPY;
- proved rollback restores prior target contents when destructive loads fail;
- added `TargetLoadExecutor`, `IdempotencyPolicy`, `IdempotencyAction`, and deterministic `EXECUTE` / `SKIP` / `RETRY` / `RELOAD` decisions;
- kept idempotency history outside `Target` and keyed equivalence by target, dataset version, destination and mode;
- extended target-load metadata filtering for version/destination/mode history lookup.

## [0.5.0b1] - 2026-09-05

### Beta 1 — PostgreSQL Metadata Hardening + Target Load Records

- added additive `TargetLoadMetadataCapability` and persistent `TargetLoadRecord`;
- added `target_loads` to Memory, SQLite and PostgreSQL metadata stores without changing the abstract `MetadataStore` contract;
- linked load attempts to run, logical target, dataset/version, destination, mode/status, row counts and timing;
- hardened PostgreSQL metadata diagnostics with credential-redacted DSNs;
- qualified target-load persistence/update/query behavior on PostgreSQL 16.

## [0.5.0a2] - 2026-09-05

### Alpha 2 — Dataset Schema Mapping + PostgreSQL COPY

- added deterministic Dataset-to-PostgreSQL type planning and conservative existing-table compatibility validation;
- adopted psycopg 3 `COPY ... FROM STDIN` as the production PostgreSQL bulk-load path;
- preserved `Decimal`, Unicode, NULL, date/time, timezone-aware datetime and BYTEA values without silent coercion;
- added real PostgreSQL 16 COPY and rollback qualification.

## [0.5.0a1] - 2026-09-04

### Alpha 1 — Target Contract + PostgreSQL Target Foundation

- added the framework-owned `Target`, `TargetLoadRequest`, `TargetLoadResult`, `TargetCapabilities`, `LoadMode`, and `TargetLoadStatus` contracts;
- added `PostgresTarget` on the existing SQLAlchemy Core + optional psycopg dependency line, without introducing ORM semantics;
- added explicit target open/close behavior, atomic transaction boundaries, rollback-on-failure, credential-redacted diagnostics, and strict PostgreSQL identifier validation;
- added a conservative parameterized `APPEND` foundation while deliberately leaving PostgreSQL `COPY`, staging, `TRUNCATE_LOAD`, and `REPLACE` for later V0.5 milestones;
- added PostgreSQL target configuration through environment-variable indirection so DSNs are not serialized into project YAML;
- kept MetadataStore independent from Target and preserved all V0.4 Diff / Versioning / Replay contracts and seven reference jobs;
- extended public-API and wheel-smoke gates to the V0.5.0-a1 prerelease and the optional `postgres` extra.

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

- defined the framework-owned job registry and plugin loading boundary;
- added project configuration loader and CLI job listing/inspection;
- documented the Foundation public contract and compatibility policy.

## [0.1.1] - 2026-09-03

- added packaging and CI gates for the Foundation milestone;
- added offline deterministic smoke tests.

## [0.1.0] - 2026-09-03

### Foundation

- established `src/pyingestkit` package layout, typed public API and semantic versioning;
- added imperative `Job` / `Step` / `Pipeline` execution model;
- added local immutable RAW artifact storage, SHA-256 identity and atomic writes;
- added run manifests, lifecycle events and structured logging context;
- introduced plugin discovery and a stable demo job package.
