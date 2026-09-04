# ADR-031 — NDJSON and Excel are structural parser adapters

## Status

Accepted — V0.3.0-b1.

## Decision

`NdjsonParser` and `ExcelParser` extend the existing `RawArtifact -> Dataset` parser boundary.

NDJSON is implemented with the Python standard library and accepts one JSON object per non-empty line. Excel uses OpenPyXL through the optional `excel` extra and reads worksheet values in `read_only` / `data_only` mode by default.

Neither parser performs business normalization, trimming, enrichment or schema coercion. Excel native scalar/date values are preserved as returned by OpenPyXL; NDJSON preserves JSON-native values.

OpenPyXL is imported lazily. Constructing/importing PyIngestKit without the `excel` extra must remain valid.
