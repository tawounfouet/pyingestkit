# ADR-040 — Replay lineage and fingerprint verification are explicit

## Status
Accepted — V0.4.0-b2.

Replay records source/executed job versions, source/new RAW lineage, logical `as_of`, safe parameter fingerprint, and expected/actual Dataset fingerprints. Same-version replay is strict when a prior DatasetVersion is known; pre-V0.4 history is best-effort and `--no-verify` is explicit.
