# PyIngestKit V2 — LOT-05 CSV and JSONL Decode Foundation

LOT-05 closes the first V2 alpha foundation path:

```text
Source
  → Acquisition
  → immutable RAW
  → ArtifactReference
  → DecodeRequest
  → Decoder
  → DecodeResult
```

## Decoder contract

The extension port is deliberately small:

```python
class Decoder(Protocol):
    @property
    def descriptor(self) -> DecoderDescriptor: ...
    def decode(self, request: DecodeRequest) -> DecodeResult: ...
```

`DecoderRegistry` is explicit and instance-owned. Importing a decoder module
does not mutate a global registry or activate plugins.

Stable foundation IDs are:

```text
csv
json
jsonl
```

## Decode is not transform

LOT-05 allows representation-level interpretation of bytes only.

It does not own:

```text
join
aggregate
window
pivot
business-derived measures
multi-dataset enrichment
arbitrary relational reshaping
```

Those semantics remain outside PyIngestKit Decoder and belong to PyTransformKit
or application code.

## Dependency-neutral representation

Decode output is framework-owned and immutable:

```text
DecodedRepresentation
  └── DecodedRecord
        ├── scalar JSON/CSV values
        ├── DecodedObject
        └── DecodedArray
```

No Pandas, Polars, PyArrow, DuckDB or provider-native type crosses the boundary.

CSV foundation decoding intentionally preserves field values as strings. It does
not perform implicit business/type inference.

JSON decoding preserves JSON scalar types and wraps nested objects/arrays in
immutable PyIngestKit values.

## Schema evidence

`SchemaEvidence` records:

```text
field name
observed portable value types
nullable/missing evidence
deterministic SHA-256 fingerprint
```

The schema is observed decode evidence. It is not yet a governed DatasetVersion
schema; LOT-07 owns that semantic transition.

## Encoding policy

Text decoding is explicit through `EncodingPolicy`.

The foundation policy is strict: malformed bytes fail decoding instead of being
silently replaced. UTF-8 BOM handling may be enabled explicitly.

## Resource bounds

`DecoderLimits` bounds:

```text
bytes
rows
columns
field/string size
JSON nesting depth
JSON object key count
```

Limit violations produce structured `RESOURCE_EXHAUSTED` failure evidence.

Malformed CSV/JSON and encoding failures produce structured validation failure
evidence.

## RAW integrity handoff

Before decoding, foundation decoders verify available ArtifactReference byte-size
and SHA-256 evidence against the bytes supplied by `DecodeRequest`.

This preserves:

```text
acquired bytes
  == durable RAW evidence
  == decoded bytes
```

for the local reference path.

## CSV

`CsvDecoderConfig` exposes portable CSV structure and safety configuration.

Header mode requires unique, non-blank names and consistent row width.
Headerless mode assigns deterministic `column_1`, `column_2`, ... names.

## JSON and JSONL

`JsonDecoder` supports:

```text
JsonMode.JSON
JsonMode.NDJSON
```

JSON root values must be an object or array of objects.
JSONL nonblank lines must each contain one object.

Duplicate object keys and non-standard constants such as NaN/Infinity are
rejected rather than normalized silently.

## V1 transition

V1 parsers remain unchanged and governed by the maintained 1.0.x compatibility
surface.

The V2 API is additive under:

```python
from pyingestkit.decoders import (
    CsvDecoder,
    CsvDecoderConfig,
    Decoder,
    DecoderRegistry,
    JsonDecoder,
    JsonDecoderConfig,
    JsonMode,
)
```

The V2 root package is not fully cut over while the repository is still packaged
as 1.0.x.

## LOT-05 exit evidence

LOT-05 is complete when CI proves:

- CSV and JSON/JSONL fixtures decode deterministically;
- malformed content produces structured failure evidence;
- byte/row/column/nesting limits are enforced;
- invalid text encoding fails closed;
- decoded representation is immutable and engine-neutral;
- schema and row-count evidence are deterministic;
- Decoder has no relational business-transformation surface;
- decoder registration is explicit;
- Python 3.11–3.14 V2 qualification passes;
- clean-wheel Source → Acquisition → RAW → Decode works with no provider extras.

Closing LOT-05 makes the current foundation a candidate for the
`2.0.0a1` milestone. It does not publish or change the package version by
itself.
