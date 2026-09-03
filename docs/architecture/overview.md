# Architecture overview

```text
External orchestrator
        │
        ▼
   PyIngestKit
        │
  Job → Pipeline → Steps
        │
        ├── Sources
        ├── RAW / Provenance
        ├── Validation
        └── Atomic Publication
```

V0.1 deliberately keeps HTTP, database targets, object storage, distributed execution and business-domain transformations out of the runtime.
