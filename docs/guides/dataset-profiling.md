# Dataset profiling

`DatasetProfiler` computes deterministic descriptive statistics over the existing neutral `Dataset`.

```python
from pyingestkit.profiling import DatasetProfiler

profile = DatasetProfiler().profile(dataset)
print(profile.row_count)
print(profile.fields[0].null_count)
```

Dataset-level metrics:

- `row_count`;
- `field_count`;
- `duplicate_row_count`.

Field-level metrics:

- `present_count` / `missing_count`;
- `null_count` / `non_null_count`;
- `distinct_count`;
- stable `observed_types`;
- string `min_length` / `max_length`;
- numeric `min_value` / `max_value` when values are comparable.

Profiling does not sample raw values, infer semantic types, or transform rows. Exact distinct and duplicate tracking is intentionally in memory in V0.3 because the Dataset contract itself is materialized. A future streaming profile contract may choose explicit approximate/bounded algorithms instead of silently changing this behavior.
