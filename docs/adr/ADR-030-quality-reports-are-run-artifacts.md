# ADR-030 — Quality reports are run artifacts

## Status

Accepted — V0.3.0-a2.

## Context

V0.2 stores validation summaries in metadata and the manifest. V0.3 needs stable machine-readable quality evidence without widening the SQL schema for every evolving profiling field.

## Decision

Framework-observed validation and profiling outputs are materialized under:

```text
runs/<namespace>/<job>/<run-id>/reports/validation.json
runs/<namespace>/<job>/<run-id>/reports/profile.json
```

`RunManifest.reports` contains lightweight references. Report generation emits `QUALITY_REPORT_WRITTEN`; profiling emits `PROFILE_COMPLETED`.

The MetadataStore schema remains unchanged in Alpha 2. Existing validation metadata continues to be persisted as before.

## Consequences

- profile schema can evolve independently of SQL migrations;
- quality evidence is portable with the run workspace;
- the manifest remains an index rather than duplicating complete profiles;
- external catalogs/observability platforms can consume reports later without becoming framework requirements.
