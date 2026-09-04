# Diff reports and runtime observation — V0.4.0-a2

PyIngestKit does not automatically diff every Dataset. A job explicitly computes a `DatasetDiff`; Runner then observes that value when it appears directly or inside common nested step outputs.

```text
DatasetDiffer.compare(...)
        ↓
DatasetDiff
        ↓
Runner
  ├── reports/diff.json
  ├── manifest reports[]
  ├── DIFF_STARTED
  ├── DIFF_COMPLETED
  ├── DIFF_REPORT_WRITTEN
  └── dataset_diffs metadata when supported
```

The report schema has its own `report_version: "1"`. The first diff is written to `reports/diff.json`; additional diffs use deterministic numbered filenames to prevent overwrite.

By default `DiffPolicy.capture_values=False`, so entries contain kind/key/changed-field evidence rather than complete rows. If value capture is explicitly enabled, report serialization redacts secret-looking fields and bounds strings. Event and metadata payloads contain only fingerprints, counts, paths and identifiers.

`DiffMetadataCapability` is optional and separate from `MetadataStore`. Built-in Memory, SQLite and PostgreSQL stores support it; a legacy custom store can continue to run and will simply omit queryable diff metadata while retaining report/manifest/event evidence.
