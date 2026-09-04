# ADR-036 — Dataset snapshots use versioned typed JSON

## Status
Accepted — V0.4.0 stable (introduced in V0.4.0-b1).

Dataset versions are persisted as JSON snapshots with explicit type tags. Pickle is forbidden. The codec preserves the V0.3 Dataset boundary, sparse-field semantics, bytes, Decimal, date/datetime and nested JSON-like values, and fails explicitly on unsupported types.

V0.4.0 stable freezes `snapshot_version` at `"1"`. Any incompatible snapshot encoding change must use a new explicit snapshot version; existing V1 snapshots are never silently reinterpreted.
