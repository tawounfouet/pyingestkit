# PyIngestKit documentation

## Foundation

- [Architecture overview](architecture/overview.md)
- [Product scope](architecture/product-scope.md)
- [Ingestion lifecycle](architecture/ingestion-lifecycle.md)
- [Unified workspace](architecture/workspace.md)
- [MetadataStore](architecture/metadata-store.md)
- [Configuration](architecture/configuration.md)
- [Logging](architecture/logging.md)
- [Plugin model](architecture/plugin-model.md)
- [ADR index](adr/README.md)

## Guides

- [Write a job with decorators](guides/write-a-job-with-decorators.md)
- [Write a job with the imperative API](guides/write-a-job-imperative.md)
- [Configure MetadataStore](guides/configure-metadata-store.md)
- [Configure PostgreSQL metadata](guides/configure-postgres-metadata.md)
- [Inspect run history](guides/inspect-run-history.md)
- [Package a job plugin](guides/package-a-job-plugin.md)

## V0.3 — Quality & Formats

- [Dataset Contracts V2](guides/dataset-contracts-v2.md)
- [Dataset profiling](guides/dataset-profiling.md)
- [Quality reports](guides/quality-reports.md)
- [NDJSON + Excel](guides/ndjson-excel.md)
- [Parquet](guides/parquet.md)
- [V0.3.0 release validation](guides/release-validation-v0.3.0.md)

## V0.4 — Diff / Replay / Versioning

- [Architecture & implementation plan](architecture/diff-replay-versioning-v0.4.md)
- [Dataset fingerprints and diff](guides/dataset-diff.md)
- [Dataset versioning](guides/dataset-versioning.md)
- [Replay](guides/replay.md)
- [V0.4.0 stable architecture](architecture/diff-replay-versioning-release-v0.4.0.md)
- [V0.4.0 release validation](guides/release-validation-v0.4.0.md)

## V0.5 — PostgreSQL Persistence Targets

- [Target foundation](architecture/postgres-target-foundation-a1.md)
- [COPY bulk load](architecture/postgres-bulk-load-a2.md)
- [PostgreSQL metadata + target loads](architecture/postgres-metadata-target-loads-b1.md)
- [Load modes + idempotency](architecture/postgres-load-modes-idempotency-b2.md)
- [V0.5 RC1 E2E](architecture/postgres-persistence-e2e-rc1.md)

## V0.6 — Object Storage

- [A1 — ArtifactStore + URI](architecture/object-storage-a1.md)
- [A2 — S3ArtifactStore + Remote RAW](architecture/object-storage-a2.md)
- [B1 — Remote reports/manifests](architecture/object-storage-b1.md)
- [B2 — Remote DatasetVersion + publication](architecture/object-storage-b2.md)
- [RC1 — Full cross-host E2E](architecture/object-storage-rc1.md)
- [V0.6.0 stable contract](architecture/object-storage-release-v0.6.0.md)
- [Configure S3-compatible storage](guides/configure-object-storage.md)
- [V0.6.0 release validation](guides/release-validation-v0.6.0.md)

## V1 — Stable Framework Contract

- [Public API reference](reference/public-api.md)
- [Compatibility contract](reference/compatibility-v1.md)
- [Operational stability contract](reference/stability-v1.md)
- [V1 product scope](architecture/product-scope-v1.md)

## Engineering Reviews

- [V0.5.0 — PostgreSQL Persistence & CLI Enhancements](reviews/v0.5.0-postgres-persistence-enhancements-review.md)
- [V0.6.0 — Config Auto-Discovery & Fail-Fast Validation](reviews/v0.6.0-config-autodiscovery-and-failfast-review.md)
- [V0.6.0 — Multi-Environment Profiles & Cloud Object Storage](reviews/v0.6.0-multienv-profiles-and-s3-object-storage-review.md)
- [V0.6.0 — Environment Management, Project Hygiene & Observability](reviews/v0.6.0-environment-management-and-project-hygiene-review.md)
- [V0.6.0 — Live Configuration Inspection & Origin Tracing](reviews/v0.6.0-live-config-inspection-review.md)
- [V0.6.0 — CLI Ergonomics, Parameter Defaults & Shell Resilience](reviews/v0.6.0-cli-ergonomics-and-subcommand-resilience-review.md)
