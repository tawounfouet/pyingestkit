# PyIngestKit V2 — LOT-17 Optional PyTransformKit Integration

LOT-17 implements the optional anti-corruption layer between governed
PyIngestKit DatasetVersion identity and PyTransformKit transformation execution.

The integration remains outside PyIngestKit core:

```text
PyIngestKit core
      |
      | no sibling import
      v
DatasetVersionReference
      |
      | optional adapter
      v
pyingestkit.integrations.pytransformkit
      |
      +--> PyTransformKit InputBinding
      |
      +<-- TransformationResult
              |
              +--> ResourceReference
              +--> TransformationExecutionReference evidence
              +--> CorrelationContext
              +--> FailureEvidence
      |
      v
TransformationPublicationInput
```

## Installation and activation

The integration is optional:

```bash
pip install "pyingestkit[transform]"
```

Importing `pyingestkit` or
`pyingestkit.integrations.pytransformkit` does not import PyTransformKit.
The sibling package is loaded only when an integration operation is invoked.

The supported sibling contract for LOT-17 is:

```text
PyTransformKit >=1.1,<2
```

Qualification is pinned to the stable public PyTransformKit 1.1.0 surface.

## DatasetVersionReference → InputBinding

`DatasetVersionInputAdapter` accepts one immutable
`DatasetVersionReference` and produces a resource-backed PyTransformKit
`InputBinding`.

Only portable resource identity crosses the boundary:

- dataset id;
- version id;
- optional schema fingerprint;
- physical ResourceReference locator/media type.

No PyIngestKit `DecodedRepresentation`, DataFrame, engine handle or private
repository object is passed to PyTransformKit.

When the version has no concrete resource locator, callers must supply an
explicit resolver:

```text
DatasetVersionReference
       |
       +--> locator
       |
       +--> artifact resource
       |
       +--> caller resolver
```

The integration never performs hidden provider discovery.

## Correlation

`CorrelationId` is preserved across the boundary.

PyIngestKit → PyTransformKit maps the common portable context:

- causation id;
- parent execution id;
- workflow/task ids;
- ingestion run id;
- trace/span ids.

The native PyTransformKit `TransformationExecutionId` remains owned by
PyTransformKit. On the return path it is attached to the PyIngestKit
correlation as `transformation_execution_id`.

## FailureEvidence

PyTransformKit failures are translated by enum value rather than by exception
message parsing. Category, retryability and outcome uncertainty remain
first-class.

If PyTransformKit introduces a semantic enum value that PyIngestKit does not
support, the adapter fails closed with `PyTransformKitMappingError`.

The original transformation execution id is retained in structured failure
details.

## TransformationResult → publication input

`TransformationPublicationAdapter` consumes only the public successful
`TransformationResult` contract.

The selected output must have a materialized public
`ResourceReference` in transformation lineage. The adapter produces a
PyIngestKit-owned `TransformationPublicationInput` containing:

- output resource;
- transformation execution id;
- semantic plan fingerprint when present;
- engine id when present;
- returned correlation context;
- bounded provenance pairs.

PyIngestKit does not import or persist PyTransformKit's internal logical
lineage graph.

The transformation execution identity, plan fingerprint and engine identity
survive the publication handoff as explicit provenance.

## Resource translation

PyTransformKit's resource `scheme` must match the URI scheme embedded in its
locator. Mismatched or scheme-less resources fail closed.

Credential-bearing URIs are rejected by the PyIngestKit
`ResourceReference` boundary.

## Customer 360 source-version handoff

LOT-17 qualifies the ecosystem handoff expected by the roadmap:

```text
customers DatasetVersionReference
            |
            v
DatasetVersionInputAdapter
            |
            v
PyTransformKit InputBinding(resource)
```

The handoff preserves the exact dataset/version identity in resource metadata.
This is the source-version boundary later Customer 360 E2E work builds on.

## Ownership boundary

PyIngestKit still owns:

- Source acquisition;
- durable RAW;
- decoding/validation;
- DatasetVersion identity;
- publication/replay.

PyTransformKit owns:

- joins;
- aggregates;
- windows;
- pivots;
- reusable business transformation semantics;
- transformation runtime/lineage.

LOT-17 does not add transformation operators to PyIngestKit.

## Deferred

LOT-17 does not implement:

- V1 semantic migration (LOT-18);
- provider/port conformance matrix (LOT-19);
- full Customer 360 application E2E (LOT-20);
- PyWorkflowKit orchestration;
- cross-framework shared-core package.
