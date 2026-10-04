# PyIngestKit 2.x Provider Compatibility Matrix

This matrix covers the frozen PyIngestKit 2.0 provider baseline plus the additive
2.1 governance providers. Capability claims are backed by CI evidence rather than
Protocol conformance alone.

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
| In-memory lifecycle ledger | `PublicationLedger` | base | shared ledger conformance |
| PostgreSQL lifecycle ledger | `PublicationLedger` | `[postgres]` / SQLAlchemy + psycopg | restart + transaction E2E |
| Filesystem conditional publisher | `ConditionalDatasetPublisher` | base | inter-process CAS, ABA, lock-timeout, reconciliation |
| S3 conditional publisher | `ConditionalDatasetPublisher` | `[s3]` / boto3 | endpoint capability probe, provider CAS races, reconciliation |
| Filesystem version GC | `DatasetVersionGarbageCollector` | base | stale-plan, symlink/path confinement, uncertain-delete reconciliation |
| S3 version GC | `DatasetVersionGarbageCollector` | `[s3]` / boto3 | bucket/prefix confinement, stale-plan, reconciliation |
| Governed rollback | qualified governance service over CAS | provider-composed | File/S3 + PostgreSQL rollback qualification |

## Compatibility rules

Providers MUST implement the framework-owned Protocol and pass the relevant
behavioral/conformance suite. Structural typing by itself is not a support claim.

The base installation remains provider-neutral. Optional provider packages are
not imported unless the relevant provider boundary is selected.

S3 qualification uses an S3-compatible endpoint and therefore does not make the
framework AWS-only. The 2.1 conditional-publisher profile additionally requires
provider-enforced conditional writes and fails closed when that capability cannot
be proven. PostgreSQL qualification targets PostgreSQL 16 in CI.

PyTransformKit remains a sibling framework rather than a base dependency.
Inter-framework handoff uses portable references; DataFrames, engines and live
provider clients are not durable compatibility contracts.
