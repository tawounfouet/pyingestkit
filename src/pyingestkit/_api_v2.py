"""Internal metadata describing the PyIngestKit V2 public API target.

LOT-00 recorded the target contract. LOT-01 added portable boundary values.
LOT-02 added Source/IngestionDefinition. LOT-03 added acquisition, LOT-04
added durable RAW/ArtifactStore, LOT-05 added dependency-neutral CSV/JSON(L)
decoding, LOT-06 added bounded validation/quality evidence, LOT-07 added
immutable content-addressed DatasetVersion semantics, LOT-08 added durable
version storage plus atomic publication, LOT-09 added portable ingestion
run/result lifecycle evidence, LOT-10 added explicit V2 IngestionRuntime
composition, LOT-11 added strict replay from durable historical RAW, LOT-12
cut V2 runtime callers over to the qualified runtime surface, LOT-13 added
secure HTTP acquisition/provenance, LOT-14 added transactional PostgreSQL
materialization for immutable dataset versions, and LOT-15 adds S3-compatible
V2 artifact/version storage while the V1 package keeps its exact star-import
contract until the 2.0 alpha cut.
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

V2_IMPLEMENTED_HTTP_VALUES: tuple[str, ...] = (
    "HttpAccessPolicy",
    "HttpClientV2",
    "HttpCredentialResolverV2",
    "HttpRequestV2",
    "HttpResponseTooLargeErrorV2",
    "HttpResponseV2",
    "HttpSourceConnector",
    "HttpTimeoutErrorV2",
    "HttpTransportErrorV2",
)

V2_IMPLEMENTED_TARGET_VALUES: tuple[str, ...] = (
    "DatasetTargetV2",
    "PostgresTargetV2",
    "TargetDescriptorV2",
    "TargetLoadModeV2",
    "TargetLoadRequestV2",
    "TargetLoadResultV2",
    "TargetLoadStatusV2",
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
    "S3ArtifactReaderV2",
    "S3ArtifactStoreV2",
    "PutArtifactRequest",
    "PutArtifactResult",
    "RawArtifactEvidence",
)

V2_IMPLEMENTED_S3_VALUES: tuple[str, ...] = (
    "S3ArtifactReaderV2",
    "S3ArtifactStoreV2",
    "S3ClientV2",
    "S3DatasetVersionStoreV2",
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
    "S3DatasetVersionStoreV2",
)

V2_RUNTIME_SURFACE = "pyingestkit.runtime.v2"
V2_RUNTIME_SURFACE_EXPORTS: tuple[str, ...] = (
    "IngestionResult",
    "IngestionRun",
    "IngestionRuntime",
)

V2_IMPLEMENTED_RUNTIME_VALUES: tuple[str, ...] = (
    "IngestionResult",
    "IngestionRun",
    "IngestionRuntime",
)

V2_IMPLEMENTED_REPLAY_VALUES: tuple[str, ...] = (
    "ReplayRequest",
    "ReplayResult",
    "ReplayServiceV2",
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
    "LOT-11",
    "LOT-12",
    "LOT-13",
    "LOT-14",
    "LOT-15",
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

V2_API_PHASE = "LOT-15_S3_OBJECT_STORAGE"
