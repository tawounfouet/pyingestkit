# V0.3.0 — Quality & Formats Release Architecture

V0.3.0 freezes the quality and structured-format layer built incrementally on top of V0.2.0 Acquisition.

```text
DISCOVER
   ↓
FETCH
   ↓
RAW + PROVENANCE
   ↓
PARSE
   ├── CSV
   ├── JSON
   ├── NDJSON
   ├── XLSX (optional OpenPyXL)
   └── Parquet (optional PyArrow)
   ↓
Dataset
   ├── DatasetContract V2 → ValidationResult → validation.json
   └── DatasetProfiler → DatasetProfile → profile.json
   ↓
Manifest / Metadata / Events
```

## Stable quality contracts

V0.3 stabilizes:

- value and structural field constraints;
- logical/composite uniqueness;
- bounded issue reporting;
- deterministic descriptive profiling;
- run-scoped quality evidence.

Validation does not normalize data. Profiling does not infer business semantics.

## Stable format contracts

All parsers terminate at the dependency-neutral `Dataset`. CSV/JSON/NDJSON use the standard library. XLSX and Parquet adapters are optional extras and lazy-load their mature backend libraries.

## Operational boundary

Quality reports are artifacts referenced by the manifest rather than new normalized metadata tables. Existing validation metadata remains available. This keeps V0.3 schema evolution additive and avoids an unnecessary migration layer.

## Scale boundary

The V0.3 Dataset is materialized. Parquet supports projection plus an explicit row guardrail. Streaming, chunked validation, approximation and dataframe engines remain future opt-in architecture rather than implicit V0.3 behavior.
