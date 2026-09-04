# ADR-037 — Dataset version IDs are content-addressed

## Status
Accepted — V0.4.0-b1.

`version_id` equals the deterministic Dataset fingerprint (`sha256-<hex>`). Producing identical logical content therefore reuses the immutable version directory while recording the additional producing run in metadata.
