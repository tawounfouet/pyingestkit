# PyIngestKit V2 — LOT-10 IngestionRuntime Foundation

LOT-10 introduces the first active V2 application service. It composes the
framework-owned ports already implemented by LOT-03 through LOT-09 without
reusing the legacy Job/Pipeline/Step/Runner execution model.

## Reference flow

```text
IngestionDefinition
        |
        v
IngestionRuntime
        |
        +--> SourceRegistry -> SourceConnector.acquire
        |
        +--> ArtifactStore.put(RAW)
        |
        +--> DecoderRegistry -> Decoder.decode
        |
        +--> validate_v2
        |
        +--> build_dataset_version
        |
        +--> DatasetVersionStore.put
        |
        +--> optional DatasetPublisher.publish
        |
        v
IngestionResult
```

Every execution owns one native `IngestionRunId`. The same run identity and
`CorrelationContext` cross acquisition, RAW persistence, decoding, validation,
versioning and publication.

## Explicit composition

`IngestionRuntime` receives registries and ports through its constructor. It
does not discover providers from globals or imports and does not construct
filesystem, SQL, HTTP or object-storage clients.

Publication is caller-explicit. The runtime never infers publication merely
because a version was created.

## RAW-first invariant

The LOT-10 reference path requires durable RAW before decoding. A definition
with RAW disabled therefore fails closed in this first runtime slice. Replay is
not implemented by bypassing this rule; historical RAW replay belongs to
LOT-11.

## Failure semantics

Structured failures returned by acquisition, artifact persistence and decoding
are preserved. Configuration-resolution and validation failures are mapped to
framework-owned `FailureEvidence`.

Unexpected programming/provider exceptions are not silently converted into
success or partial outcomes.

## Compatibility

The stable V1 `pyingestkit.runtime` package still exports only `Runner`.
`IngestionRuntime` is exposed from the qualified `pyingestkit.runtime.v2`
surface during the transition.

## Deferred

LOT-10 does not add:

- replay;
- provider-specific orchestration;
- automatic retries;
- distributed scheduling;
- Job/Pipeline/Step abstractions;
- target/warehouse materialization;
- async execution.

Those concerns remain separate roadmap work.
