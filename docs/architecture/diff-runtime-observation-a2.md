# V0.4.0-a2 — Diff Reports + Runtime / Metadata Observation

Alpha 2 connects the pure Alpha 1 comparison result to durable run evidence.

```text
previous Dataset ─┐
                  ├─ DatasetDiffer ─→ DatasetDiff
candidate Dataset ┘                    │
                                       ▼
                                    Runner
                    ┌──────────────────┼───────────────────┐
                    ▼                  ▼                   ▼
             reports/diff.json   RunManifest.reports   DIFF_* events
                    │                                      │
                    └──────────────┬───────────────────────┘
                                   ▼
                         DiffMetadataCapability
                                   │
                         dataset_diffs (optional)
```

The Runner observes only a diff already produced by user/job code. It does not choose previous datasets, keys or diff policies. This keeps runtime orchestration policy out of the framework and preserves the V0.3 execution model.

Until the B1 version registry exists, `previous_version_id` is the previous Dataset fingerprint ID and `dataset_id` defaults to the current job ID. These identifiers can be enriched later without changing Alpha 2 report/count semantics.
