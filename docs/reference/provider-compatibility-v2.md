# PyIngestKit 2.0 Provider Compatibility Matrix

This matrix is part of the PyIngestKit 2.0 stable qualification. Capability
claims are backed by CI evidence rather than Protocol conformance alone.

| Provider / boundary | Stable contract | Dependency profile | 2.0 evidence |
| --- | --- | --- | --- |
| Local file source | `SourceConnector` | base | architecture + V2 integration tests |
| HTTP source | `SourceConnector` | `[http]` / httpx | HTTP runtime + security boundary tests |
| CSV / JSON(L) decoder | `Decoder` | base | decoder conformance matrix |
| Filesystem artifact store | `ArtifactStore` | base | artifact conformance + clean-wheel smoke |
| S3-compatible artifact store | `ArtifactStore` | `[s3]` / boto3 | S3 cross-host replay |
| Filesystem dataset-version store | `DatasetVersionStore` | base | version-store conformance |
| S3-compatible dataset-version store | `DatasetVersionStore` | `[s3]` / boto3 | S3 cross-host replay |
| Dataset publisher | `DatasetPublisher` | provider-specific | publication/reconciliation tests |
| PostgreSQL target | `DatasetTargetV2` | `[postgres]` / SQLAlchemy + psycopg | PostgreSQL 16 E2E |
| Resource materializer | `DatasetVersionMaterializerV2` | base / format-specific | Customer 360 |
| PyTransformKit bridge | public anti-corruption layer | optional sibling install | pinned 1.1.0 integration + Customer 360 |

## Compatibility rules

Providers MUST implement the framework-owned Protocol and pass the relevant
behavioral/conformance suite. Structural typing by itself is not a support claim.

The base installation remains provider-neutral. Optional provider packages are
not imported unless the relevant provider boundary is selected.

S3 qualification uses an S3-compatible endpoint and therefore does not make the
framework AWS-only. PostgreSQL qualification targets PostgreSQL 16 in CI.

PyTransformKit remains a sibling framework rather than a base dependency.
Inter-framework handoff uses portable references; DataFrames, engines and live
provider clients are not durable compatibility contracts.
