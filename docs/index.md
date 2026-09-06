# PyIngestKit

**Reliable, traceable batch ingestion for Python.**

PyIngestKit is a focused framework for turning external sources into validated, reproducible and publishable datasets without rebuilding ingestion plumbing for every job.

!!! info "Stable release"
    The current stable framework contract is **V1.0.0**. Stable public surfaces are governed for the 1.x line; explicitly experimental surfaces remain outside that promise.

[Get started](getting-started/installation.md){ .md-button .md-button--primary }
[Quickstart](getting-started/quickstart.md){ .md-button }
[API reference](reference/api.md){ .md-button }

## What PyIngestKit owns

PyIngestKit owns **how to ingest**. External orchestrators own **when to run**.

```text
source
  -> acquire immutable RAW
  -> parse
  -> validate / profile
  -> normalize
  -> fingerprint / diff
  -> version / publish
  -> load target
  -> replay from durable history
```

It is intentionally not a scheduler, distributed worker platform, IAM system, data catalog or cloud-provisioning framework.

## Stable V1 capabilities

- immutable RAW with SHA-256 provenance;
- CSV, JSON, NDJSON, Excel and Parquet parsing;
- dataset contracts, validation, profiling and quality reports;
- deterministic fingerprints and dataset diff;
- immutable DatasetVersion snapshots and PublishedDataset pointers;
- strict replay without live reacquisition;
- PostgreSQL metadata and transactional target loads;
- S3-compatible artifact and version storage;
- deterministic plugin discovery and fail-closed configuration;
- governed CLI, error and observability behavior;
- clean-wheel and real V0.6 -> V1 upgrade qualification.

## Start here

### New users

1. [Install PyIngestKit](getting-started/installation.md).
2. Run the [Quickstart](getting-started/quickstart.md).
3. Continue with the full [V1 quickstart](guides/v1-quickstart.md).
4. Package your own ingestion logic with the [plugin guide](guides/package-a-job-plugin.md).

### Production evaluation

- [Production-like PostgreSQL + S3 pilot](guides/v1-production-pilot.md)
- [Configure PostgreSQL metadata](guides/configure-postgres-metadata.md)
- [Configure S3-compatible object storage](guides/configure-object-storage.md)
- [Cloudflare R2 configuration](guides/configure-cloudflare-r2.md)
- [Replay](guides/replay.md)

### Compatibility and governance

- [Stable 1.x contract](reference/stable-contract-v1.md)
- [Public API contract](reference/public-api.md)
- [Compatibility contract](reference/compatibility-v1.md)
- [Operational stability contract](reference/stability-v1.md)
- [V1 product scope](architecture/product-scope-v1.md)

## Architecture

- [Architecture overview](architecture/overview.md)
- [Ingestion lifecycle](architecture/ingestion-lifecycle.md)
- [Workspace model](architecture/workspace.md)
- [Metadata store](architecture/metadata-store.md)
- [Plugin model](architecture/plugin-model.md)
- [Logging and observability](architecture/logging.md)
- [Architecture Decision Records](adr/README.md)

## Release history

The online documentation is versioned with **Mike**. `latest` follows the maintained 1.x documentation, while the `1.0` version preserves the V1.0 documentation line.

- [V1.0.0 release notes](releases/v1.0.0.md)
- [V0.6 -> V1 migration guide](guides/migrate-v0.6-to-v1.md)
