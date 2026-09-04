# ADR-036 — Dataset snapshots use versioned typed JSON

## Status
Accepted — V0.4.0-b1.

Dataset versions are persisted as JSON snapshots with explicit type tags. Pickle is forbidden. The codec preserves the V0.3 Dataset boundary, sparse-field semantics, bytes, Decimal, date/datetime and nested JSON-like values, and fails explicitly on unsupported types.
