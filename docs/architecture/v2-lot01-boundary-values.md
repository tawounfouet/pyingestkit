# PyIngestKit V2 — LOT-01 shared boundary values and execution identity

LOT-01 implements the first real clean-slate V2 domain values after the LOT-00
architecture baseline.

## Scope delivered

The implementation introduces immutable, side-effect-free values for:

```text
IngestionRunId
CorrelationId
CorrelationContext
IngestionExecutionReference
ResourceReference
ArtifactReference
DatasetReference
DatasetVersionReference
CredentialReference
IdempotencyReference
IngestionStatus
FailureCategory
Retryability
OutcomeUncertainty
FailureEvidence
DiagnosticSeverity
Diagnostic
```

The design follows the same conventions already proven in PyTransformKit:
UUID-backed native execution identifiers, frozen/slotted dataclasses, structured
failure evidence, explicit uncertainty, portable references, typed diagnostics
and independent correlation identity.

PyIngestKit mirrors these semantics locally. It does **not** add a dependency on
PyTransformKit or introduce a shared-core package.

## Identity rule

```text
IngestionRunId
    != CorrelationId
    != trace_id
    != workflow_run_id
    != transformation_execution_id
```

Bounded internal retries retain one `IngestionRunId`. Replay will allocate a
new `IngestionRunId` when LOT-11 is implemented.

## Portable contract placeholders

LOT-01 reserves explicit contract identities and version `1` for the boundary
families implemented here:

```text
pykit.resource_reference
pykit.artifact_reference
pykit.dataset_reference
pykit.dataset_version_reference
pykit.credential_reference
pykit.idempotency_reference
pykit.correlation_context
pykit.failure_evidence
pykit.diagnostic
pykit.ingestion_execution_reference
```

These are in-memory contract placeholders. Canonical JSON codecs, envelope
validation, migrations and golden byte fixtures belong to LOT-16.

## Credential safety

`CredentialReference` stores identifiers only. Portable metadata rejects
credential-like field names, and `ResourceReference` rejects obvious URI
user-info credentials and known credential-bearing query parameters.

Credential resolution remains a runtime/infrastructure responsibility.

## DatasetVersionReference posture

LOT-01 implements only the portable reference skeleton:

```text
dataset_id
version_id
created_at?
schema_fingerprint?
content_fingerprint?
artifact_reference?
locator?
owner
namespace
contract_version
```

It does not implement DatasetVersion identity generation, storage or publication.
Those semantics belong to LOT-07 and LOT-08.

## V1 transition rule

The stable V1 root API remains intact while the V2 line is built. LOT-01
therefore does not add V2 names to the package root and does not modify the
governed V1 `pyingestkit.artifacts.__all__` or
`pyingestkit.runtime.__all__` contracts.

New V2 values are available from the domain packages and from additive qualified
modules such as:

```python
from pyingestkit.datasets import DatasetVersionReference
from pyingestkit.diagnostics import Diagnostic
from pyingestkit.artifacts.references import ArtifactReference
from pyingestkit.runtime.identity import IngestionRunId
```

The canonical V2 root promotion remains deferred until the owning roadmap lot
introduces the corresponding complete API.

## Exit criteria evidence

LOT-01 is complete when CI proves:

- all values are immutable;
- contract identity/version placeholders are frozen by a fixture;
- no raw credential fields exist;
- credential-like portable metadata is rejected;
- `IngestionRunId` is distinct from correlation/trace identity;
- uncertainty remains first-class through `UNKNOWN_OUTCOME`;
- domain layers remain provider- and sibling-framework-free;
- Python 3.11–3.14 V2 core tests pass;
- clean-wheel import remains provider-optional.
