# ADR-051 — Remote RAW uses conditional create plus SHA-256 integrity

## Status
Accepted for V0.6.0-a2.

## Decision

Remote RAW follows the same immutability rule as local RAW:

1. inspect the deterministic object key;
2. refuse an already-existing object;
3. cache bytes locally with exclusive create;
4. `PutObject` with `If-None-Match: *` to close the concurrent-create race;
5. persist `pyingestkit-sha256` and artifact id as object metadata;
6. verify SHA-256 whenever historical remote RAW is materialized locally.

If upload fails, the newly-created local cache entry is removed. A remote location is never silently overwritten by a run.

ETag is not treated as a content hash. PyIngestKit SHA-256 remains the framework integrity identity.
