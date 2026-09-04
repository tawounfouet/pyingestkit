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
