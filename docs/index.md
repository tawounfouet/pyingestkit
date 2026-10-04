# PyIngestKit

**Reliable, traceable and replayable ingestion for Python.**

PyIngestKit is a focused framework for acquiring external data, preserving durable RAW evidence, decoding and validating it, creating immutable dataset versions, and publishing or materializing them explicitly.

!!! success "Stable release"
    The current stable release is **PyIngestKit 2.0.0**. The 2.0 package root, `IngestionRuntime.run(...)`, stable provider Protocols and version-1 portable wire contracts form the compatibility baseline for the maintained 2.x line.

!!! warning "2.1 development line"
    Repository `main` is currently **2.1.0b2 / LOT-28**. This beta adds governed rollback as CAS publication to an existing immutable DatasetVersion on top of the retention/holds/GC lifecycle, while the published stable release remains 2.0.0 and the frozen 2.0/LOT-23 contracts remain unchanged.

[Install 2.0](getting-started/installation.md){ .md-button .md-button--primary }
[2.0 Quickstart](getting-started/quickstart.md){ .md-button }
[Migrate V1 → V2](guides/migrate-v1-to-v2.md){ .md-button }
[Provider matrix](reference/provider-compatibility-v2.md){ .md-button }

## What PyIngestKit owns

PyIngestKit owns **how to ingest**. External orchestrators own **when to run**.

```text
Source
  -> acquisition
  -> durable immutable RAW ArtifactReference
  -> Decoder
  -> validation / quality evidence
  -> immutable DatasetVersion
  -> explicit publication or target materialization
  -> strict replay / verification
```

It is intentionally not a scheduler, distributed worker platform, generic DAG engine, IAM system, data catalog or cloud-provisioning framework.

## Stable 2.0 capabilities

- compact V2 root centered on `IngestionDefinition`, `IngestionRuntime`, `Source` and portable references;
- durable immutable RAW evidence with provenance;
- CSV / JSON(L) decoding and format-specific optional providers;
- validation and quality evidence;
- immutable `DatasetVersion` identity and explicit publication;
- strict replay without silent source reacquisition;
- local filesystem acquisition, artifacts and dataset-version storage;
- HTTP acquisition through the optional `[http]` provider;
- PostgreSQL target materialization through `[postgres]`;
- S3-compatible artifact and dataset-version storage through `[s3]`;
- canonical portable serialization across framework boundaries;
- optional PyTransformKit integration through portable references;
- explicit V1 → V2 semantic migration rather than compatibility aliases.

See the [2.0 release notes](releases/v2.0.0.md), [provider compatibility matrix](reference/provider-compatibility-v2.md) and [stable qualification](releases/v2.0.0-qualification.md).

## Start here

### New 2.0 users

1. [Install PyIngestKit 2.0](getting-started/installation.md).
2. Run the [2.0 Quickstart](getting-started/quickstart.md).
3. Review the [2.0 provider compatibility matrix](reference/provider-compatibility-v2.md).
4. Read the [architecture overview](architecture/overview.md).

### Migrating existing 1.x applications

PyIngestKit 2.0 is a major-version boundary. V1 `Job / Pipeline / Step / Runner` execution semantics are not aliases for the V2 runtime.

Use the [V1 → V2 migration guide](guides/migrate-v1-to-v2.md) to inventory V1 dependencies, convert supported persisted semantics, rebuild ingestion around `IngestionRuntime.run(...)`, and verify RAW, DatasetVersion and replay behavior.

### Qualification and release evidence

- [PyIngestKit 2.0.0 release notes](releases/v2.0.0.md)
- [Stable qualification](releases/v2.0.0-qualification.md)
- [Auditable qualification evidence](releases/v2.0.0-evidence.md)
- [Provider compatibility matrix](reference/provider-compatibility-v2.md)
- [Post-2.0 scope review](roadmap/post-2.0-scope-review.md)

## Architecture

- [Architecture overview](architecture/overview.md)
- [V2 baseline](architecture/v2-lot00-baseline.md)
- [Ingestion runtime](architecture/v2-lot10-ingestion-runtime.md)
- [Strict replay](architecture/v2-lot11-strict-replay.md)
- [HTTP acquisition](architecture/v2-lot13-http-acquisition.md)
- [PostgreSQL target](architecture/v2-lot14-postgres-target.md)
- [S3 object storage](architecture/v2-lot15-s3-object-storage.md)
- [Canonical serialization](architecture/v2-lot16-canonical-serialization.md)
- [PyTransformKit integration](architecture/v2-lot17-pytransformkit-integration.md)
- [V1 semantic migration](architecture/v2-lot18-v1-semantic-migration.md)
- [Provider / port conformance](architecture/v2-lot19-provider-port-conformance.md)
- [Customer 360 beta gate](architecture/v2-lot20-customer360-beta-gate.md)

## Historical V1.x documentation

The immutable V1 line remains available for applications that still depend on the V1 execution model. In the versioned documentation, **1.0** preserves the V1 stable line while **latest** follows the maintained 2.x documentation.

Within the current documentation tree, V1 material is grouped under **Historical V1.x** in the navigation. Start with:

- [V1 quickstart](guides/v1-quickstart.md)
- [V1 stable contract](reference/stable-contract-v1.md)
- [V1 compatibility contract](reference/compatibility-v1.md)
- [V1.0.0 release notes](releases/v1.0.0.md)
- [V0.6 → V1 migration guide](guides/migrate-v0.6-to-v1.md)

## Documentation versions

The online documentation is versioned with **Mike**:

- `latest` follows the maintained **2.x** documentation;
- `2.0` preserves the PyIngestKit 2.0 documentation line;
- `1.0` preserves the historical V1 stable documentation line.
