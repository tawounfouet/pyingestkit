# ADR-039 — Replay reuses historical RAW and never falls back to live acquisition silently

## Status
Accepted — V0.4.0-b2.

`pyingest replay` creates a new run and materializes new RAW artifacts from historical RAW bytes. `HttpSource` performs zero network calls and `LocalSource` does not reread the current file. Missing or corrupted historical RAW fails replay explicitly; live fallback is forbidden.
