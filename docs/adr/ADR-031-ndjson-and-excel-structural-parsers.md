# ADR-031 — NDJSON and Excel are structural parser adapters

## Status
Accepted — V0.3.0-b1.

## Decision
`NdjsonParser` and `ExcelParser` produce the existing dependency-neutral `Dataset`. They preserve source-native primitive values and do not perform business normalization. XLSX support is an optional extra backed by openpyxl and imported lazily.

## Consequences
- NDJSON remains a lightweight stdlib parser.
- Excel does not become a mandatory framework dependency.
- worksheet/header selection is structural configuration, not business mapping.
- formula calculation, cell renaming, trimming and semantic coercion remain outside the parser boundary.
