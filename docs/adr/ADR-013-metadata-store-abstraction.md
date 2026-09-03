# ADR-013 — MetadataStore abstraction

**Status:** Accepted — V0.1.5

Queryable runtime state is persisted through the `MetadataStore` contract. `Runner` depends on that contract, never on SQLite/PostgreSQL directly.

`ArtifactStore` owns payload artifacts. `MetadataStore` owns queryable run state. Manifest and database metadata are complementary.
