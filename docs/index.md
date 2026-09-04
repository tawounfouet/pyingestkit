# PyIngestKit documentation

## Foundation

- [Architecture overview](architecture/overview.md)
- [Foundation stabilization V0.1.x](architecture/foundation-stabilization-v0.1xx.md)
- [Product scope](architecture/product-scope.md)
- [Ingestion lifecycle](architecture/ingestion-lifecycle.md)
- [Unified workspace](architecture/workspace.md)
- [MetadataStore](architecture/metadata-store.md)
- [SQLAlchemy persistence](architecture/persistence-sqlalchemy.md)
- [Runtime events](architecture/runtime-events.md)
- [Logging](architecture/logging.md)
- [Declarative API](architecture/declarative-api.md)
- [Plugin model](architecture/plugin-model.md)
- [ADR index](adr/README.md)
- [HTTP → RAW provenance decision](adr/ADR-024-http-raw-provenance-boundary.md)
- [Dataset, parsers and contracts — Beta 1](architecture/dataset-parsers-contracts-beta1.md)
- [Acquisition vertical slice — RC1](architecture/acquisition-e2e-rc1.md)
- [Dataset representation decision](adr/ADR-025-dataset-neutral-python-container.md)
- [Parser/normalizer/contract boundary decision](adr/ADR-026-parser-normalizer-contract-boundaries.md)

## Guides

- [Write a job with decorators](guides/write-a-job-with-decorators.md)
- [Write a job with the imperative API](guides/write-a-job-imperative.md)
- [Configure MetadataStore](guides/configure-metadata-store.md)
- [Configure PostgreSQL metadata](guides/configure-postgres-metadata.md)
- [Inspect run history](guides/inspect-run-history.md)
- [Package a job plugin](guides/package-a-job-plugin.md)
- [Demo plugin tutorial](tutorials/demo-plugin.md)
- [V0.2.0 release validation](guides/release-validation-v0.2.0.md)

## V0.3 — Quality & Formats

- [V0.3 architecture plan](architecture/quality-formats-v0.3.md)
- [Dataset Contracts V2](guides/dataset-contracts-v2.md)
- [Dataset profiling](guides/dataset-profiling.md)
- [Quality reports](guides/quality-reports.md)
- [NDJSON + Excel](guides/ndjson-excel.md)
- [Parquet](guides/parquet.md)

## V0.3.0 RC1

- [Quality & Formats E2E architecture](architecture/quality-formats-e2e-rc1.md)
- [ADR-033 — Materialized Dataset boundary](adr/ADR-033-materialized-dataset-boundary.md)
- [RC1 technical review](reviews/v0.3.0-rc1-quality-formats-e2e-review.md)

## V0.3.0 stable release

- [Quality & Formats release architecture](architecture/quality-formats-release-v0.3.0.md)
- [Release validation guide](guides/release-validation-v0.3.0.md)
- [Stable release technical review](reviews/v0.3.0-quality-formats-release-review.md)

## V0.4 — Diff / Replay / Versioning

- [Architecture & implementation plan](architecture/diff-replay-versioning-v0.4.md)
- [Dataset fingerprints and diff](guides/dataset-diff.md)
- [V0.4.0-a1 technical review](reviews/v0.4.0-a1-diff-engine-review.md)
- [V0.4.0-a2 diff runtime observation](architecture/diff-runtime-observation-a2.md)
- [Diff reports runtime guide](guides/diff-reports-runtime.md)
- [V0.4.0-a2 technical review](reviews/v0.4.0-a2-diff-reports-runtime-review.md)

## V0.4.0 Beta 1 — Dataset Versioning

- [Dataset versioning guide](guides/dataset-versioning.md)
- [ADR-036 — Typed JSON snapshots](adr/ADR-036-dataset-snapshots-versioned-json.md)
- [ADR-037 — Content-addressed version IDs](adr/ADR-037-dataset-version-id-is-content-addressed.md)
- [ADR-038 — Atomic PublishedDataset pointer](adr/ADR-038-published-dataset-atomic-pointer.md)
- [Beta 1 technical review](reviews/v0.4.0-b1-versioning-review.md)

## V0.4.0 Beta 2 — Replay

- [Replay guide](guides/replay.md)
- [ADR-039 — Strict historical RAW replay](adr/ADR-039-replay-strict-historical-raw.md)
- [ADR-040 — Replay lineage and verification](adr/ADR-040-replay-lineage-and-verification.md)
- [Beta 2 technical review](reviews/v0.4.0-b2-replay-lineage-review.md)

## V0.4.0 RC1

- [Diff / Replay / Versioning E2E architecture](architecture/diff-replay-versioning-e2e-rc1.md)
- [RC1 technical review](reviews/v0.4.0-rc1-diff-replay-versioning-e2e-review.md)

## V0.4.0 stable release

- [Stable release architecture](architecture/diff-replay-versioning-release-v0.4.0.md)
- [Release validation guide](guides/release-validation-v0.4.0.md)
- [Stable release technical review](reviews/v0.4.0-diff-replay-versioning-release-review.md)
