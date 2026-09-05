# Plugin model

Job packs are independent Python distributions discovered through `importlib.metadata` entry points
under the stable V1 group:

```text
pyingestkit.jobs
```

Accepted entry-point values are `JobDefinition`, `Job`, `Job` subclasses and zero-argument factories
returning `Job`/`JobDefinition`.

V1.0.0-b1 freezes deterministic discovery order by `(entry_point.name, entry_point.value)`. Broken
plugins are isolated. If two packages expose the same logical `job.id`, the first deterministic entry
point is kept and the later duplicate is reported as `PluginFailure`.

Library discovery is strict by default:

```python
from pyingestkit.plugins import discover_jobs

jobs = discover_jobs()  # raises PluginError if any plugin failed
```

CLI-facing registry loading is intentionally tolerant so an unrelated broken third-party plugin does
not make healthy jobs unusable. Use `load_registry_with_diagnostics()` when diagnostics are needed.

See [V1 operational stability contract](../reference/stability-v1.md).
