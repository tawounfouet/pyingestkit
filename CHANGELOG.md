# Changelog

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
