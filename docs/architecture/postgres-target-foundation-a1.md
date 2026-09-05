# PyIngestKit V0.5.0-a1 — PostgreSQL Target Foundation

V0.5.0-a1 introduces the destination boundary that follows the V0.4 Dataset / Diff / Versioning / Replay line.

```text
Dataset
  ↓
TargetLoadRequest
  ↓
Target
  ↓
PostgresTarget
  ↓
BEGIN
  ↓
parameterized APPEND (A1 foundation)
  ↓
COMMIT
  ↓
TargetLoadResult
```

On database failure the transaction is rolled back and a controlled `TargetLoadError` is raised.

## A1 public contract

```python
from pyingestkit import (
    LoadMode,
    PostgresTarget,
    Target,
    TargetCapabilities,
    TargetLoadRequest,
    TargetLoadResult,
    TargetLoadStatus,
)
```

A1 intentionally does **not** claim PostgreSQL COPY, staging, `truncate_load`, `replace`, upsert, idempotency, or target-load metadata. These remain later V0.5 milestones.

## Configuration boundary

```yaml
targets:
  warehouse:
    type: postgres
    target_id: postgres.demo.reference
    dsn_env: PYINGEST_TARGET_DATABASE_URL
    schema: public
    table: demo_dataset
    load_mode: append
```

The actual DSN is resolved by application/bootstrap code from the environment and is never a serialized target identity.

## Architectural invariants

- `Target != MetadataStore`;
- `Target != ArtifactStore`;
- `Target != DatasetVersionStore`;
- `PostgresTarget != ORM`;
- `target_id != DSN`;
- `Runner` has no psycopg coupling;
- V0.4 Dataset remains engine-neutral.
