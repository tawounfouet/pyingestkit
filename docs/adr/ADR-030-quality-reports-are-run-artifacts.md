# ADR-030 — Quality reports are run artifacts

## Status

Accepted — PyIngestKit V0.3.0 Alpha 2.

## Context

Validation and profiling evidence must survive the Python objects that produced it, but
V0.3 does not yet need relational profile tables or a schema migration framework.

## Decision

Quality evidence is written as JSON run artifacts:

```text
reports/validation.json
reports/profile.json
```

The run manifest records small additive references to those files. Validation keeps its
existing MetadataStore records. Profiling is announced through `PROFILE_COMPLETED` and
`QUALITY_REPORT_WRITTEN` lifecycle events but is not relationalized in V0.3 Alpha 2.

`QualityReport` is an optional in-memory aggregate; `quality.json` is deferred until an
end-to-end use case demonstrates value.

## Consequences

- no SQL migration is required;
- reports are portable and inspectable beside RAW/manifest artifacts;
- the manifest remains a compact index rather than embedding full profile payloads;
- historical profile SQL queries remain a future decision based on demonstrated need.
