# Dataset profiling

V0.3.0-a2 adds an engine-neutral descriptive profiler:

```python
from pyingestkit import DatasetProfiler

profile = DatasetProfiler().profile(dataset)
```

The profiler reports structural observations only: row/field counts, nulls, exact
distinct counts, stable Python type names, string length bounds, safe numeric min/max,
and duplicate full rows. It performs no semantic inference or coercion and collects no
sample values in Alpha 2.
