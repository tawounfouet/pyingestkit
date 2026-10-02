"""Internal metadata describing the PyIngestKit V2 public API target.

LOT-00 deliberately records the target contract without creating fake public
implementations. Symbols move from RESERVED to PROVISIONAL/STABLE only when the
owning implementation lot delivers real behavior.
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

V2_API_PHASE = "LOT-00_TARGET_RESERVED"
