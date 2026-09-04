# ADR-024 — HTTP → immutable RAW provenance boundary

## Status
Accepted for PyIngestKit V0.2.0-a2.

## Context
Alpha 1 established reliable HTTP transport and retry behavior but deliberately stopped at `HttpResponse`. An ingestion framework becomes operationally useful only when successful acquisition bytes are captured immutably, hashed, traced and indexed without persisting transport credentials.

## Decision
`HttpSource` is now a framework `Source` and exposes two layers:

- `fetch_response()` remains the transport-level surface;
- `fetch(context)` is the ingestion surface and writes successful response bytes to the run `ArtifactStore` as an immutable `RawArtifact`.

The resulting acquisition path is:

```text
HTTP
 ↓
RAW bytes
 ↓
SHA-256
 ↓
ArtifactStore
 ↓
Manifest
 ↓
MetadataStore
```

Every HTTP RAW artifact carries the following normalized provenance:

- `source_uri`: requested effective URI after persistence-safe redaction;
- `resolved_url`: final response URL after redirects, also sanitized;
- `status_code`;
- `content_type`;
- `etag`;
- `last_modified`;
- `retrieved_at`;
- `size_bytes`;
- `sha256`.

Arbitrary request or response headers are never copied into `RawArtifact`, the manifest or `MetadataStore`. In particular, `Authorization`, `Cookie`, API-key headers and token headers are excluded. Secret-looking query parameter **values** are redacted before `source_uri` or `resolved_url` crosses a persistence/logging boundary.

## Metadata design
The generic `artifacts` table remains unchanged for Alpha 1 / V0.1.x compatibility. HTTP-specific persisted fields use a one-to-one additive table:

```text
artifacts
   │ 1
   │
   │ 0..1
   ▼
artifact_http_provenance
```

This avoids contaminating the generic artifact table with source-specific columns and lets SQLAlchemy `create_all()` add the new table safely to an existing metadata database without an in-place `ALTER TABLE` migration.

## Consequences
- Existing Alpha 1 SQLite metadata remains readable.
- Local-file artifacts continue to use the same generic artifact contract.
- HTTP acquisition is industrializable before CSV/JSON parsing exists.
- Dataset parsing, validation and publication remain out of scope for this alpha.
