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
