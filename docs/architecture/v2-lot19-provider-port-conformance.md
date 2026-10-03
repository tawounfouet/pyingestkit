# LOT-19 — Provider / Port Conformance Matrix

## Status

Implemented on the PyIngestKit V2 line after LOT-18 semantic migration.

## Objective

LOT-19 makes provider interchangeability an executable contract. A provider is no longer considered
qualified merely because its own unit tests pass: it must satisfy the public port it implements and
must be represented in the canonical provider/port matrix.

This lot adds no new provider and no new ingestion capability.

## Canonical ports

The matrix covers the V2 extension boundaries already present in the repository:

- `SourceConnector`;
- `ArtifactStore`;
- `DatasetVersionStore`;
- `DatasetPublisher`;
- `DatasetTargetV2`;
- `Decoder`.

## Qualified providers

| Provider | Port(s) | Offline conformance | Service-backed evidence |
|---|---|---|---|
| File source | `SourceConnector` | yes | not required |
| HTTP source | `SourceConnector` | yes | HTTP runtime integration |
| File artifact store | `ArtifactStore` | yes | not required |
| S3 artifact store | `ArtifactStore` | yes | S3 / cross-host E2E |
| File dataset-version store | `DatasetVersionStore`, `DatasetPublisher` | yes | not required |
| S3 dataset-version store | `DatasetVersionStore`, `DatasetPublisher` | yes | S3 / cross-host E2E |
| PostgreSQL target | `DatasetTargetV2` | descriptor/lifecycle | real PostgreSQL E2E |
| CSV decoder | `Decoder` | yes | not required |
| JSON decoder | `Decoder` | yes | not required |

The machine-readable source of truth is
`tests/fixtures/conformance/v2/provider_port_matrix.json`.

## Executable invariants

The conformance suite proves shared semantics rather than provider internals.

### SourceConnector

Every qualified source provider must:

- satisfy the runtime-checkable `SourceConnector` protocol;
- expose a stable descriptor and source kind;
- advertise `ACQUIRE`;
- preserve ingestion-run and correlation identity;
- return structured success/failure results.

### ArtifactStore

Every qualified artifact store must:

- satisfy `ArtifactStore`;
- support create-once persistence;
- expose an integrity-verifying reader;
- round-trip exact bytes;
- report an immutable conflict instead of silently overwriting an existing artifact.

### DatasetVersionStore / DatasetPublisher

Every qualified version backend must:

- satisfy both persistence and publication ports;
- store immutable content-addressed versions;
- make repeated writes of the same version idempotent;
- round-trip the decoded representation;
- expose deterministic version history;
- make republishing the current version idempotent.

### DatasetTargetV2

The PostgreSQL adapter must:

- satisfy `DatasetTargetV2`;
- advertise transactional and bulk-load capabilities;
- advertise the complete supported load-mode set;
- keep credentials out of its safe DSN representation;
- support idempotent close semantics.

Its actual transaction, COPY and rollback semantics remain proven by the real PostgreSQL E2E job.

### Decoder

Qualified decoders must:

- satisfy `Decoder`;
- expose stable descriptor IDs;
- decode representative input successfully;
- return structured results without provider-specific objects crossing the boundary.

## Offline versus service-backed evidence

LOT-19 deliberately separates two proof levels.

`offline` proves the public Python contract without external infrastructure.

`offline+service` means the same provider also has a real-provider or compatible-service integration
test. S3 and PostgreSQL therefore retain their existing E2E evidence; LOT-19 does not replace those
tests with mocks.

## CI integration

The new matrix test lives under `tests/conformance/v2`, which is already part of:

```text
make v2-core
make v2-baseline
make check
foundation-verify
```

Any provider added to the matrix without executable evidence, or any evidence path removed from the
repository, therefore fails the normal V2 qualification path.

## Boundary rule

LOT-19 does not create a shared cross-framework core, a provider SDK, dynamic provider discovery or
workflow orchestration. It only turns the existing PyIngestKit provider ports into an explicit,
testable compatibility matrix.

## Next lot

LOT-20 can now build the full Customer 360 application E2E on top of providers whose boundaries are
qualified independently.
