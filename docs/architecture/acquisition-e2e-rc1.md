# V0.2.0 RC1 — Acquisition vertical slice E2E

The release candidate connects the V0.2 acquisition primitives into two installable reference jobs while preserving the Foundation and local-file demo.

```text
HttpSource
    ↓
RetryPolicy
    ↓
RawArtifact + SHA-256 + HTTP provenance
    ↓
CsvParser / JsonParser
    ↓
Dataset
    ↓
DatasetContract
    ↓
ValidationResult
    ↓
Manifest + MetadataStore + VALIDATION_COMPLETED event
```

## Reference jobs

- `demo.local_file` — Foundation/local-source non-regression.
- `demo.http_csv` — HTTP → RAW → CSV → Dataset → contract validation.
- `demo.http_json` — HTTP → RAW → JSON → Dataset → contract validation.

The HTTP jobs support two modes. Normal mode requires a runtime `url` and uses the framework `HttpxClient`. Fixture mode injects an in-process `HttpClient` implementation that deliberately returns `503` then `200`, proving the retry path without sockets or external services.

```bash
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
```

`demo-http.yml` enables fixture mode, so these reference runs are deterministic and offline by default.

## Runtime validation observation

When a step returns `ValidationResult`, `Runner` treats it as lifecycle metadata:

1. append the structured result to `manifest.json`;
2. persist a validation summary and individual issues in `MetadataStore`;
3. emit `VALIDATION_COMPLETED` with counts and step context;
4. fail the step/run only when at least one `ERROR` issue exists.

Warnings and review issues remain observable without failing the run.

## Offline HTTP test contract

Reference HTTP job tests patch `socket.socket.connect` to raise immediately. A successful test therefore proves the vertical slice does not touch the network. Existing lower-level HTTP tests continue to use injected clients / `httpx.MockTransport` only.

## Boundaries retained

- `Dataset` is not Pandas, Polars, or Arrow.
- parsers perform structural decoding, not business normalization.
- fixture transport belongs to the demo plugin package, not the framework runtime.
- PyIngestKit still does not become a scheduler or distributed orchestration engine.
