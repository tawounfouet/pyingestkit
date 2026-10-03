# Migrating PyIngestKit 1.x applications to 2.0

PyIngestKit 2.0 is a deliberate major-version boundary. The recommended
strategy is **semantic migration**, not alias-based execution compatibility.

## Decide whether to migrate now

Stay on the 1.x line when an application still depends on the V1
Job/Pipeline/Step runtime or its operator CLI and does not yet need the V2
resource/version contracts.

Move to 2.0 when the application can express ingestion as:

```text
Source
  -> durable RAW
  -> Decoder
  -> validation / quality evidence
  -> immutable DatasetVersion
  -> explicit publication / target materialization
```

## Root API changes

V1 execution names such as `Job`, `Pipeline`, `Step`, `Runner`,
`RunContext`, `job` and `step` are not exported from the 2.0 package root.

The canonical V2 authoring/execution pair is:

```python
from pyingestkit import IngestionDefinition, IngestionRuntime, Source

definition = IngestionDefinition(
    name="customers",
    source=Source.file(path="/data/customers.csv"),
    decoder="csv",
    dataset="customers",
)

result = runtime.run(definition)
```

## Persisted state and semantic conversion

Use `pyingestkit.migration` to assess V1 configuration and convert supported
V1 artifact/version/publication records into portable V2 references.

Migration tools do not execute V1 jobs and do not silently load executable
plugins. Unsupported semantics remain explicit migration decisions.

## Replay

V2 replay starts from preserved RAW evidence, allocates a new
`IngestionRunId`, and verifies the expected immutable DatasetVersion. It does
not silently reacquire the original source.

## Transformation handoff

Transformation belongs to PyTransformKit. Cross-framework handoff uses portable
references:

```text
DatasetVersionReference
  -> resolve ResourceReference
  -> PyTransformKit InputBinding
  -> physical transformation output
  -> PyIngestKit governed DatasetVersion
  -> publication
```

A DataFrame or provider client is not a durable inter-framework contract.

## Recommended rollout

1. Pin production V1 workloads to the latest 1.x release.
2. Inventory root imports and V1 plugin/CLI dependencies.
3. Convert source definitions and provider configuration.
4. Run migration fixtures against persisted metadata.
5. Rebuild ingestion with `IngestionRuntime.run`.
6. Verify RAW integrity, DatasetVersion identity and publication behavior.
7. Exercise strict replay.
8. Validate the migrated application against PyIngestKit 2.0.0 in a non-production environment before production rollout.
