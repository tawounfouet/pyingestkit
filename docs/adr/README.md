# Architecture Decision Records

- ADR-001 Product scope
- ADR-002 Zero third-party dependency core — **Superseded by ADR-010**
- ADR-003 Plugin discovery via Python entry points
- ADR-004 External orchestration boundary
- ADR-005 Artifact lifecycle
- ADR-006 Atomic publication semantics
- ADR-007 Result and error model
- ADR-008 Metadata model
- ADR-009 Secret handling policy
- ADR-010 Production-grade dependency policy
- ADR-011 Logging policy
- ADR-012 Unified workspace layout
- ADR-013 MetadataStore abstraction
- ADR-014 SQLite as default metadata backend
- ADR-015 Operational logs vs runtime events
- ADR-016 Declarative decorator API
- ADR-017 Decorator API compiles to imperative model

- ADR-018 SQLAlchemy metadata persistence engine
- ADR-019 One persistence engine — no Peewee
- ADR-020 Foundation verify gate
- ADR-021 Schema evolution — no Alembic before demonstrated need

- ADR-022 HTTPX as default HTTP transport
- ADR-023 Retry policy, idempotency and Retry-After
- ADR-024 HTTP → immutable RAW provenance boundary
- ADR-025 Dataset as a dependency-neutral Python container
- ADR-026 Parser, normalizer and dataset contract boundaries
- [ADR-027 — ValidationResult runtime observation](ADR-027-validation-result-runtime-observation.md)

- [ADR-028 — Dataset Contracts V2 semantics](ADR-028-dataset-contracts-v2-semantics.md)
- [ADR-029 — Dataset profiling is descriptive, not semantic inference](ADR-029-dataset-profiling-descriptive-not-semantic.md)
- [ADR-030 — Quality reports are run artifacts](ADR-030-quality-reports-are-run-artifacts.md)

- [ADR-031 — NDJSON and Excel are structural parser adapters](ADR-031-ndjson-and-excel-structural-parsers.md)

- [ADR-032 — Parquet is an optional materializing parser adapter](ADR-032-parquet-optional-materializing-adapter.md)
- [ADR-033 — V0.3 materialized Dataset boundary](ADR-033-materialized-dataset-boundary.md)

- [ADR-034 — Dataset fingerprint canonical identity](ADR-034-dataset-fingerprint-canonical-identity.md)
- [ADR-035 — Keyed and keyless diff semantics](ADR-035-keyed-and-keyless-diff-semantics.md)

- [ADR-036 — Dataset snapshots use versioned typed JSON](ADR-036-dataset-snapshots-versioned-json.md)
- [ADR-037 — Dataset version IDs are content-addressed](ADR-037-dataset-version-id-is-content-addressed.md)
- [ADR-038 — PublishedDataset atomic pointer](ADR-038-published-dataset-atomic-pointer.md)

- [ADR-039 — Strict replay from historical RAW](ADR-039-replay-strict-historical-raw.md)
- [ADR-040 — Replay lineage and verification](ADR-040-replay-lineage-and-verification.md)

## V0.4.0 stable format freeze

V0.4.0 freezes the ADR-034 canonical Dataset fingerprint codec at version `1` and the ADR-036
Dataset snapshot format at `snapshot_version = "1"`. Portable diff reports are frozen at
`report_version = "1"` as documented by the V0.4 release validation guide.

## V0.5 PostgreSQL persistence targets

- [ADR-041 — Target abstraction exposes one atomic load operation](ADR-041-target-abstraction-atomic-load-lifecycle.md)
- [ADR-042 — PostgresTarget uses SQLAlchemy Core with psycopg and no ORM](ADR-042-postgres-target-sqlalchemy-core-psycopg-boundary.md)
- [ADR-043 — PostgreSQL Dataset type mapping is deterministic and conservative](ADR-043-postgres-dataset-type-mapping-policy.md)
- [ADR-044 — psycopg 3 COPY is the PostgreSQL production bulk-load path](ADR-044-postgres-copy-primary-bulk-load-path.md)
- [ADR-045 — Target-load metadata is an additive run-linked capability](ADR-045-target-load-metadata-additive-capability.md)
- [ADR-046 — PostgreSQL content load modes share one atomic transaction boundary](ADR-046-postgres-load-mode-transaction-semantics.md)
- [ADR-047 — Target-load idempotency is history-driven and remains outside Target](ADR-047-target-load-idempotency-history-driven.md)

## V0.6 Object Storage

- [ADR-048 — Artifact URI and local materialization are separate identities](ADR-048-artifact-uri-and-local-materialization.md)
- [ADR-049 — ArtifactStore URI support is additive](ADR-049-artifact-store-uri-contract-is-additive.md)
- [ADR-050 — S3ArtifactStore owns remote RAW and local cache](ADR-050-s3-artifact-store-owns-remote-raw-and-local-cache.md)
- [ADR-051 — S3 RAW is immutable and integrity-checked](ADR-051-s3-raw-immutability-and-integrity.md)
- [ADR-052 — StoredArtifact is an additive durable run-artifact reference](ADR-052-stored-artifact-additive-run-artifact-contract.md)
- [ADR-053 — S3 JSON run artifacts follow run-scoped lifecycle semantics](ADR-053-s3-json-run-artifact-lifecycle.md)
- [ADR-054 — S3 DatasetVersion storage is immutable; publication is one mutable pointer](ADR-054-s3-dataset-version-publication.md)

## V1 Stable Framework Contract

- [ADR-055 — V1 public API and product scope are governed by an explicit manifest](ADR-055-v1-public-api-and-scope-governance.md)
- [ADR-056 — V1 compatibility is enforced at logical contracts and versioned persistence boundaries](ADR-056-v1-compatibility-contract-and-persistent-schema-policy.md)
- [ADR-057 — V1 operational surfaces are frozen by explicit behavioral contracts](ADR-057-v1-operational-surfaces-stability.md)
- [ADR-058 — V1 readiness is demonstrated by representative pilots and executable documentation contracts](ADR-058-v1-pilot-qualification-and-documentation.md)
