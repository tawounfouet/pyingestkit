# PyIngestKit V2 — LOT-00 architecture baseline

LOT-00 establishes executable architecture constraints before V2 functional
implementation begins.

## Transition posture

The branch starts from the stable V1 implementation. Existing V1 runtime,
plugin, CLI and configuration packages may remain temporarily while V2 is
migrated lot by lot. New V2 packages must not depend on the legacy
Job/Pipeline/Step/Runner execution model.

The target package layers are:

```text
domain
application
runtime
ports
adapters
serialization
observability
plugins
integrations
```

LOT-00 creates the missing package boundaries without adding fake domain
implementations.

## Target root vocabulary

```text
ArtifactReference
DatasetVersion
DatasetVersionReference
IngestionDefinition
IngestionResult
IngestionRun
IngestionRunId
IngestionRuntime
PublishedDataset
ResourceReference
Source
```

The V2 canonical root must not preserve Job, Pipeline, Step or Runner aliases.

## Dependency baseline

PyIngestKit V2 does not pursue a stdlib-only core. Established production-grade
dependencies remain allowed when justified, but provider SDKs must stay outside
the domain.

Target Python baseline:

```text
3.11
3.12
3.13
3.14
```

Transitional packaging decisions during LOT-00:

- Typer, Rich, Pydantic, PyYAML, tenacity and python-dotenv remain base candidates.
- SQLAlchemy remains a transitional V1 base dependency pending the LOT-08/LOT-14 persistence split.
- httpx remains a transitional V1 base dependency; target placement is the HTTP capability at LOT-13.
- psycopg, boto3, openpyxl and pyarrow remain provider extras.
- PyTransformKit is reserved for an optional `transform` integration at LOT-17.
- PyWorkflowKit is not a PyIngestKit core dependency.

## Executable gates

```text
tests/architecture/
tests/contract/public_api/
tests/fixtures/migration/v1/manifest.json
```

The architecture suite checks provider isolation, sibling-framework isolation,
target public API vocabulary, optional provider dependency isolation,
serialization safety and migration-boundary isolation.
