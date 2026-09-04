# V0.3.0-rc1 — Quality & Formats E2E

The release candidate closes the V0.3 vertical slice across all supported structured formats.

```text
Local / HTTP / deterministic fixture
                ↓
          immutable RAW
                ↓
 CSV / JSON / NDJSON / XLSX / Parquet
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
 Manifest / Metadata / Runtime Events
```

## Six reference jobs

```text
demo.local_file
demo.http_csv
demo.http_json
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
```

The three V0.3 quality jobs each execute four steps: fetch deterministic RAW fixture, parse structurally, validate with Contract V2, then profile. `Runner` observes the validation and profile objects and persists portable quality evidence.

## Optional-format distribution gate

The RC wheel-smoke installs the built framework wheel using its declared `excel` and `parquet` extras, installs the built demo wheel, then executes all six jobs in a fresh virtual environment with no editable install or `PYTHONPATH` dependency.

The CI matrix validates OpenPyXL and PyArrow wheels on Python 3.11, 3.12 and 3.13. If an upstream wheel stops being available, the release gate must fail explicitly rather than silently skipping the adapter.
