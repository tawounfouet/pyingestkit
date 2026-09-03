# ADR-008 — Metadata model

**Status:** Superseded by ADR-013 and ADR-014 in V0.1.5

## Historical decision

Early V0.1 persisted run metadata only in the portable run manifest and deferred a dedicated MetadataStore.

## Superseding decision

V0.1.5 keeps the manifest but adds a distinct queryable `MetadataStore` contract, with SQLite as the default CLI backend and PostgreSQL as an optional adapter. Manifest and metadata remain complementary.
