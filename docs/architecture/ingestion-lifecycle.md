# Ingestion lifecycle

The complete product vision is:

```text
DISCOVER → FETCH → RAW → PROVENANCE → PARSE → NORMALIZE → VALIDATE → CROSS-CHECK → DIFF → PUBLISH → LOAD
```

V0.1 implements the minimum foundation needed to execute and trace this lifecycle without pretending to implement all future stages.
