# ADR-038 — PublishedDataset is an atomic pointer to an immutable version

## Status
Accepted — V0.4.0-b1.

`versions/` is immutable history. `published/<dataset>/current.json` is the filesystem source of truth for the mutable current pointer and is replaced atomically. A successful run is not automatically a publication, and publishing identical content is an idempotent no-op.
