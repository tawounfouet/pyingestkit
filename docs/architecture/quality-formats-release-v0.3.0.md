# V0.3.0 — Quality & Formats Release Architecture

V0.3.0 freezes the second major framework capability layer above V0.2 Acquisition.

```text
DISCOVER / FETCH
      ↓
immutable RAW + provenance
      ↓
CSV / JSON / NDJSON / XLSX / Parquet
      ↓
dependency-neutral Dataset
      ↓
DatasetContract V2
      ↓
ValidationResult
      ↓
DatasetProfiler
      ↓
DatasetProfile
      ↓
validation.json / profile.json
      ↓
Manifest / Metadata / Runtime Events
```

## Stable V0.3 surfaces

- `FieldContract` and `DatasetContract` V2 constraints;
- `ValidationIssue` enriched diagnostics with bounded/redacted previews;
- `DatasetProfiler`, `DatasetProfile`, and `FieldProfile`;
- `QualityReport` portable aggregate;
- `NdjsonParser`;
- `ExcelParser` through `pyingestkit[excel]`;
- `ParquetParser` through `pyingestkit[parquet]`;
- quality report artifact references in manifests and CLI status output.

## Frozen boundaries

V0.3 does not turn `Dataset` into Pandas, Polars or Arrow. Parsers remain structural and do not perform business normalization. Profiling is descriptive rather than semantic inference. Parquet remains materialized in memory and may be bounded with `max_rows`.

## Reference release jobs

```text
demo.local_file
demo.http_csv
demo.http_json
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
```

The last three reference jobs exercise the complete V0.3 path from RAW acquisition through format parsing, Contract V2 validation, profiling and persisted quality evidence.
