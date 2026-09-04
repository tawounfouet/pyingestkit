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

## Reviews

- [Stabilisation Qualité et Qualification Finale (v0.2.0)](reviews/v0.2.0-quality-and-release-stabilization.md)
- [Stabilisation Qualité, Typage et Sécurité (v0.1.6)](reviews/quality-and-security-stabilization.md)
