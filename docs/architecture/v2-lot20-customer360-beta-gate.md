# PyIngestKit V2 — LOT-20 Customer 360 and End-to-End Beta Gate

## Status

LOT-20 implements the PyIngestKit-owned Customer 360 beta gate defined by the
V2 roadmap. The milestone candidate is **2.0.0b2**.

The reference profile is executable architecture evidence rather than a tutorial.

## Scope

The local profile proves this sequence:

~~~text
customers.csv ──> IngestionRuntime ──> RAW ──> customers DatasetVersion ──┐
                                                                         │
orders.csv ─────> IngestionRuntime ──> RAW ──> orders DatasetVersion ─────┤
                                                                         ▼
                                                        PyTransformKit ACL
                                                                         │
                                                                         ▼
                                                        customer_mart.csv
                                                                         │
                                             physical write != publication
                                                                         │
                                                                         ▼
                                                    resource materializer
                                                                         │
                                                                         ▼
                                             customer_mart DatasetVersion
                                                                         │
                                                                         ▼
                                                   PublicationServiceV2
~~~

The same canonical Customer 360 transformation is qualified with Pandas and
Polars through the supported PyTransformKit 1.1.0 contract.

## Source ingestion

Both source datasets use ordinary V2 ingestion semantics:

- explicit FileSourceConnector;
- durable immutable RAW before decode;
- CSV decoding and validation;
- immutable DatasetVersion creation;
- explicit source publication.

Successful IngestionResult values retain the exact RAW ArtifactReference so
strict replay can be initiated through public evidence rather than private
store knowledge.

## Portable transform handoff

DatasetVersionReference remains the governed identity. The reference
application exports its decoded representation to a bounded local CSV resource
and supplies an explicit resolver to DatasetVersionInputAdapter.

The PyTransformKit boundary therefore receives ResourceReference-backed
InputBinding values. A DataFrame, Arrow Table, provider client or mutable store
object never becomes the cross-framework durable contract.

For local resources, the anti-corruption layer translates PyIngestKit
credential-safe file URIs to the absolute path form expected by the
PyTransformKit LocalFileReader. The output direction canonicalizes an absolute
PyTransformKit file path back into a PyIngestKit file URI.

## Transformation output is not publication

PyTransformKit writes customer_mart.csv. That physical write is not a
DatasetVersion and does not move a PublishedDataset pointer.

FileCsvDatasetVersionMaterializerV2 explicitly promotes the already-produced
CSV resource into a governed DatasetVersion. It:

- accepts only local file resources;
- rejects remote file hosts;
- rejects symbolic links;
- confines resolved paths to configured roots;
- applies the bounded CSV parser;
- fingerprints governed decoded content;
- records the transformation resource as transformation-output artifact evidence;
- preserves bounded portable provenance metadata.

Only after the version is persisted does PublicationServiceV2 update governed
publication state.

## Provenance

The final customer_mart DatasetVersionReference carries stable metadata linking
it to:

- customers RAW artifact id;
- customers DatasetVersion id;
- orders RAW artifact id;
- orders DatasetVersion id;
- TransformationExecution id;
- transformation plan fingerprint;
- transformation engine id;
- transformation output resource id.

This provenance survives File/S3 version-store persistence and V2 boundary
serialization.

## UNKNOWN_OUTCOME and reconciliation

PublicationServiceV2 preserves provider uncertainty.

~~~text
provider commits publication
        │
        └── acknowledgement lost
                    │
                    ▼
             UNKNOWN_OUTCOME
                    │
                    ▼
               reconcile()
                    │
                    ▼
        CONFIRMED_COMMITTED
~~~

A subsequent publication request first observes the current governed pointer.
The provider write is therefore not blindly repeated after an uncertain
outcome.

## Replay

The reference profile replays customers from the exact preserved RAW artifact.

Replay:

- allocates a new IngestionRunId;
- preserves the broader CorrelationId;
- verifies RAW SHA-256 evidence;
- performs decode/validate/version without pretending source reacquisition occurred;
- verifies that the expected immutable source DatasetVersion is reproduced.

## Security negatives

LOT-20 keeps the local profile fail-closed:

- transformed resources are root-confined;
- symlink escape is rejected;
- ResourceReference continues to reject credential-bearing locators;
- DatasetVersion provenance uses credential-safe metadata validation;
- a credential-like metadata key such as api_key is rejected;
- cross-framework transport remains non-executable portable references.

## Built-artifact gate

CI contains a dedicated customer360-built-artifact job. It:

1. builds the PyIngestKit wheel;
2. creates a clean virtual environment;
3. installs the wheel rather than the editable source tree;
4. installs the qualified PyTransformKit 1.1.0 Customer 360 profile;
5. executes the Customer 360 integration suite;
6. runs the installed reference runner.

The stable release gate depends on this job.

## Boundaries

LOT-20 implements the **PyIngestKit portions** of the ecosystem reference
application. It does not introduce PyWorkflowKit orchestration into
PyIngestKit, duplicate transformation operators, collapse native execution
identities or create a cross-framework shared private model.

Workflow coordination and recovery remain owned by PyWorkflowKit.

## Exit evidence

LOT-20 is accepted when all of the following are green:

- local Customer 360 happy path;
- Pandas/Polars logical-output parity;
- source RAW + DatasetVersion provenance traversal;
- write-versus-publish separation;
- UNKNOWN_OUTCOME reconciliation;
- strict replay;
- security-negative checks;
- built-wheel execution;
- existing V1, V2 architecture, provider and service-backed release gates.
