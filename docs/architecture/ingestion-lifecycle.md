# Ingestion lifecycle

The complete product vision is:

```text
DISCOVER → FETCH → RAW → PROVENANCE → PARSE → NORMALIZE → VALIDATE → CROSS-CHECK → DIFF → PUBLISH → LOAD
```

V0.1 implements the minimum foundation needed to execute and trace this lifecycle without pretending to implement all future stages.

V0.2.0-a2 now makes the acquisition prefix concrete for HTTP:

```text
FETCH (HTTP + retry)
  ↓
RAW immutable bytes
  ↓
SHA-256 + provenance
  ↓
ArtifactStore / Manifest / MetadataStore
```

Parsing and dataset interpretation still begin only after this boundary.
