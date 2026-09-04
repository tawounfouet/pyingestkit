# V0.3.0-rc1 — Quality & Formats E2E

The release candidate integrates all V0.3 quality and format capabilities into executable vertical slices.

```text
fixture / RAW
      ↓
NDJSON / Excel / Parquet Parser
      ↓
Dataset
      ↓
DatasetContract V2
      ↓
ValidationResult
      ↓
DatasetProfiler
      ↓
DatasetProfile
      ↓
validation.json + profile.json
      ↓
Manifest + Metadata + Events
```

## Reference jobs

The installable demo pack now exposes six jobs:

- `demo.local_file`;
- `demo.http_csv`;
- `demo.http_json`;
- `demo.ndjson_quality`;
- `demo.excel_quality`;
- `demo.parquet_quality`.

The first three are V0.2 non-regression slices. The latter three exercise the complete V0.3 quality-format lifecycle.

## Distribution gate

`make wheel-smoke` creates a clean venv, removes `PYTHONPATH`, installs the built framework wheel with `excel` and `parquet` extras plus the demo-job wheel, then executes all six jobs. This makes optional-format packaging part of the release contract rather than relying only on editable installs.

## Dataset size boundary

V0.3 keeps the Dataset materialized in memory. Parquet may use projection and `max_rows` metadata guardrails, but it does not return a streaming Arrow object. NDJSON similarly parses complete content. This keeps the current parser/validation/profiling contracts deterministic while leaving room for a distinct streaming/buffered Dataset abstraction later.
