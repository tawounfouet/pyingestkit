# Dataset fingerprints and diff — V0.4.0-a1

```python
from pyingestkit import DatasetDiffer, DatasetFingerprinter, DiffPolicy

fingerprint = DatasetFingerprinter().fingerprint(candidate)

result = DatasetDiffer(
    DiffPolicy(
        key_fields=("id",),
        ignore_fields=("updated_at",),
        max_entries=1_000,
    )
).compare(previous, candidate)
```

`DatasetFingerprint.id` is `sha256-<digest>` and is not the RAW artifact hash. The default fingerprint ignores row order but preserves field order, exact types, values and duplicate multiplicity.

Keyed diff reports `ADDED`, `REMOVED`, `CHANGED` and exact unchanged counts. Keys must be present, non-null and unique in both datasets. Keyless diff is an exact multiset comparison and therefore reports only added/removed rows.

Detailed diff entries are bounded by `max_entries`; counts are not. `capture_values=False` is the default so comparison evidence does not retain complete rows accidentally. Runtime reports and metadata observation are intentionally deferred to V0.4.0-a2.
