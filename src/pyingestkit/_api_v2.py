"""Internal metadata describing the PyIngestKit V2 public API target.

LOT-00 recorded the target contract without fake implementations. LOT-01 adds
real boundary values while keeping the governed V1 package root unchanged until
the owning V2 API lots promote each symbol deliberately.
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

V2_API_PHASE = "LOT-01_BOUNDARY_VALUES"
