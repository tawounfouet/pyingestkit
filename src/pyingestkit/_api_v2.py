"""Internal metadata describing the PyIngestKit V2 public API target.

LOT-00 recorded the target contract. LOT-01 added portable boundary values.
LOT-02 added Source/IngestionDefinition. LOT-03 added acquisition, LOT-04
added durable RAW/ArtifactStore, LOT-05 added dependency-neutral CSV/JSON(L)
decoding, LOT-06 added bounded validation/quality evidence, LOT-07 added
immutable content-addressed DatasetVersion semantics, LOT-08 added durable
version storage plus atomic publication, LOT-09 added portable ingestion
run/result lifecycle evidence, and LOT-10 adds explicit V2 IngestionRuntime
composition while the V1 package keeps its exact star-import contract until
the 2.0 alpha cut.
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

V2_IMPLEMENTED_ARTIFACT_VALUES: tuple[str, ...] = (
    "ArtifactIntegrityError",
    "ArtifactKind",
    "ArtifactPutStatus",
    "ArtifactReader",
    "ArtifactReference",
    "ArtifactRetention",
    "ArtifactStore",
    "FileArtifactReader",
    "FileArtifactStore",
    "PutArtifactRequest",
    "PutArtifactResult",
    "RawArtifactEvidence",
)

V2_IMPLEMENTED_DECODER_VALUES: tuple[str, ...] = (
    "CsvDecoder",
    "CsvDecoderConfig",
    "DecodeRequest",
    "DecodeResult",
    "DecodeStatus",
    "DecodedArray",
    "DecodedObject",
    "DecodedRecord",
    "DecodedRepresentation",
    "DecodedType",
    "Decoder",
    "DecoderCapability",
    "DecoderDescriptor",
    "DecoderLimits",
    "DecoderRegistry",
    "EncodingPolicy",
    "JsonDecoder",
    "JsonDecoderConfig",
    "JsonMode",
    "SchemaEvidence",
    "SchemaFieldEvidence",
)

V2_IMPLEMENTED_VALIDATION_VALUES: tuple[str, ...] = (
    "MinimumRowsV2",
    "QualityEvidence",
    "RequiredFieldV2",
    "UniqueFieldV2",
    "ValidationIssue",
    "ValidationLimits",
    "ValidationRequest",
    "ValidationResult",
    "ValidationRuleV2",
    "ValidationSeverity",
    "validate_v2",
)

V2_IMPLEMENTED_DATASET_VERSION_VALUES: tuple[str, ...] = (
    "DatasetVersion",
    "DatasetVersionReference",
    "build_dataset_version",
    "dataset_content_fingerprint",
)

V2_IMPLEMENTED_VERSION_STORE_VALUES: tuple[str, ...] = (
    "DatasetPublisher",
    "DatasetVersionStore",
    "FileDatasetVersionStore",
    "PublishedDataset",
)

V2_IMPLEMENTED_RUNTIME_VALUES: tuple[str, ...] = (
    "IngestionResult",
    "IngestionRun",
    "IngestionRuntime",
)

V2_COMPLETED_LOTS: tuple[str, ...] = (
    "LOT-00",
    "LOT-01",
    "LOT-02",
    "LOT-03",
    "LOT-04",
    "LOT-05",
    "LOT-06",
    "LOT-07",
    "LOT-08",
    "LOT-09",
    "LOT-10",
)

V2_MILESTONE_CANDIDATE = "2.0.0a1"

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

V2_API_PHASE = "LOT-10_INGESTION_RUNTIME"
