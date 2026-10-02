"""Internal metadata describing the PyIngestKit V2 public API target.

LOT-00 recorded the target contract. LOT-01 added portable boundary values.
LOT-02 added the real Source/IngestionDefinition authoring root. LOT-03 adds
the first acquisition port and local-file adapter while the V1 package keeps
its exact star-import contract until the 2.0 alpha cut.
"""

from __future__ import annotations

V2_TARGET_ROOT_EXPORTS: tuple[str, ...] = (
    "ArtifactReference",
    "DatasetVersion",
    "DatasetVersionReference",
    "IngestionDefinition",
    "IngestionResult",
    "IngestionRun",
    "IngestionRunId",
    "IngestionRuntime",
    "PublishedDataset",
    "ResourceReference",
    "Source",
)

V2_PROVISIONAL_ROOT_EXPORTS: tuple[str, ...] = (
    "ArtifactReference",
    "DatasetVersionReference",
    "IngestionDefinition",
    "IngestionRunId",
    "ResourceReference",
    "Source",
)

V2_IMPLEMENTED_BOUNDARY_VALUES: tuple[str, ...] = (
    "ArtifactReference",
    "CorrelationContext",
    "CorrelationId",
    "CredentialReference",
    "DatasetReference",
    "DatasetVersionReference",
    "Diagnostic",
    "DiagnosticSeverity",
    "FailureCategory",
    "FailureEvidence",
    "IdempotencyReference",
    "IngestionExecutionReference",
    "IngestionRunId",
    "IngestionStatus",
    "OutcomeUncertainty",
    "ResourceReference",
    "Retryability",
)

V2_IMPLEMENTED_AUTHORING_VALUES: tuple[str, ...] = (
    "DefinitionFingerprint",
    "IngestionDefinition",
    "RawPolicy",
    "Source",
    "SourceKind",
)

V2_IMPLEMENTED_ACQUISITION_VALUES: tuple[str, ...] = (
    "AcquisitionRequest",
    "AcquisitionResult",
    "AcquisitionStatus",
    "FileAccessPolicy",
    "FileSourceConnector",
    "SourceConnector",
    "SourceConnectorCapability",
    "SourceConnectorDescriptor",
    "SourceRegistry",
)

V2_COMPLETED_LOTS: tuple[str, ...] = (
    "LOT-00",
    "LOT-01",
    "LOT-02",
    "LOT-03",
)

V2_FORBIDDEN_LEGACY_ROOT_EXPORTS: frozenset[str] = frozenset(
    {
        "DeclarativeJob",
        "FunctionStep",
        "Job",
        "JobDefinition",
        "JobRegistry",
        "Pipeline",
        "PipelineBuilder",
        "RunContext",
        "RunResult",
        "Runner",
        "Step",
        "StepDefinition",
        "StepInvocation",
        "StepResult",
        "job",
        "step",
    }
)

V2_PUBLIC_NAMESPACE_BASELINE: tuple[str, ...] = (
    "pyingestkit",
    "pyingestkit.artifacts",
    "pyingestkit.datasets",
    "pyingestkit.decoders",
    "pyingestkit.diagnostics",
    "pyingestkit.integrations.pytransformkit",
    "pyingestkit.plugins",
    "pyingestkit.provenance",
    "pyingestkit.publication",
    "pyingestkit.replay",
    "pyingestkit.runtime",
    "pyingestkit.serialization",
    "pyingestkit.sources",
    "pyingestkit.stores",
    "pyingestkit.validation",
    "pyingestkit.quality",
)

V2_API_PHASE = "LOT-03_ACQUISITION_LOCAL_FILE"
