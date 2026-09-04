# Dataset, parsers and contracts — V0.2.0 Beta 1

Beta 1 introduces the first structured-data layer above immutable RAW artifacts.

```text
RawArtifact
     │
     ▼
   Parser
 ┌───┴────┐
 ▼        ▼
CSV      JSON
 └───┬────┘
     ▼
  Dataset
     │
     ▼
DatasetContract
     │
     ▼
ValidationResult
```

## Dataset boundary

`Dataset` is owned by PyIngestKit and intentionally remains a small Python container:

```text
Dataset
≠ Pandas DataFrame
≠ Polars DataFrame
≠ Arrow Table
```

The runtime representation is an ordered schema plus read-only row mappings. `Dataset.to_rows()` creates mutable copies only at an explicit interoperability boundary. A dataset may retain the `source_artifact_id` of the RAW artifact from which it was parsed.

This keeps the framework API stable without binding every ingestion job to one analytical dataframe engine. Job packs remain free to convert a `Dataset` to Pandas, Polars, Arrow, database rows, or another representation after the framework parsing boundary when their own use case requires it.

## Parser boundary

A `Parser` performs structural decoding only:

```text
Parser
= bytes/serialization structure -> records

Parser
≠ business normalization
```

The framework parsers therefore do not trim business fields, rename domain columns, map codes, convert identifiers, enrich records, apply business defaults, or implement domain-specific cleanup.

### CsvParser

`CsvParser` reads a header-based CSV artifact and preserves every cell as a string. It may be configured with encoding, delimiter, quote character, and strict CSV syntax because those are serialization concerns. Header duplication and row-width mismatches are rejected as ambiguous structure.

### JsonParser

`JsonParser` accepts a JSON object as one record or an array of objects as multiple records. An optional `records_path` can select a nested structural container. JSON scalar/list/object values inside records are preserved as decoded by the Python JSON implementation. The parser does not flatten nested objects or coerce values.

## Dataset contracts

`DatasetContract` validates the structural expectations of a parsed dataset without mutating it. `FieldContract` supports:

- required field presence;
- nullability;
- Python runtime type checks;
- uniqueness;
- optional rejection of extra fields;
- dataset minimum/maximum row counts.

Validation returns an immutable `ValidationResult` containing `ValidationIssue` records. Issues carry a stable rule/code plus optional field and row coordinates. Validation messages deliberately avoid embedding complete dataset rows.

## Lifecycle position

Beta 1 makes the following lifecycle concrete:

```text
HTTP / Local source
        ↓
RawArtifact + SHA-256 + provenance
        ↓
Parser
        ↓
Dataset
        ↓
DatasetContract
        ↓
Normalization / business logic (job-pack concern)
```

A contract is not a normalizer. It reports whether the parsed structure satisfies declared expectations; it does not rewrite the data to make the contract pass.
