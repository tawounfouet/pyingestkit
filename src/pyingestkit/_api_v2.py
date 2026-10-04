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
materialization for immutable dataset versions, LOT-15 added S3-compatible V2 artifact/version storage, and LOT-16 adds
canonical non-executable boundary serialization plus explicit migration
infrastructure, LOT-17 added the optional PyTransformKit anti-corruption
boundary, LOT-18 added explicit V1 semantic migration planning and persisted
reference conversion, LOT-19 qualified the provider/port conformance matrix,
and LOT-20 added the Customer 360 end-to-end beta gate with transformed-resource
publication, provenance, reconciliation, replay and built-artifact evidence.
LOT-21 cut the real 2.0 package root, froze the stable provider/runtime
contracts and qualified the release-candidate artifacts. LOT-22 promotes the
unchanged RC contract to the stable 2.0.0 release after full requalification.
LOT-23 opens the additive 2.1 line with provider-neutral publication/lifecycle
governance domain values and ports while preserving every frozen 2.0 surface.
LOT-24 adds the durable lifecycle ledger with in-memory reference semantics and
PostgreSQL persistence/restart recovery without changing the LOT-23 contracts.\nLOT-25 adds opt-in filesystem compare-and-swap publication with ABA-safe revisions,\ninter-process locking and reconciliation while preserving the frozen 2.0 publisher.\nLOT-26 adds endpoint-qualified S3 conditional publication using provider-enforced\ncreate-if-absent and compare-and-replace semantics without exposing ETags.\nLOT-27 adds deterministic retention planning, durable version holds and guarded\nfilesystem/S3 garbage collection with stale-plan detection and reconciliation.\nLOT-28 adds governed rollback to immutable historical versions, and LOT-29\nqualifies the complete 2.1 governance contract across providers, crashes,\nrestarts and built artifacts without adding new architecture.\n"""

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
    "S3ConditionalDatasetPublisher",
    "S3ConditionalWriteCapabilityErrorV2",
    "S3DatasetVersionGarbageCollector",
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

V2_RUNTIME_SURFACE = "pyingestkit.runtime"
V2_RUNTIME_SURFACE_EXPORTS: tuple[str, ...] = (
    "CorrelationContext",
    "CorrelationId",
    "Diagnostic",
    "DiagnosticSeverity",
    "FailureCategory",
    "FailureEvidence",
    "IdempotencyReference",
    "IngestionExecutionReference",
    "IngestionResult",
    "IngestionRun",
    "IngestionRunId",
    "IngestionRuntime",
    "IngestionStatus",
    "OutcomeUncertainty",
    "Retryability",
)

V2_IMPLEMENTED_RUNTIME_VALUES: tuple[str, ...] = V2_RUNTIME_SURFACE_EXPORTS

V2_IMPLEMENTED_REPLAY_VALUES: tuple[str, ...] = (
    "ReplayRequest",
    "ReplayResult",
    "ReplayServiceV2",
)

V2_IMPLEMENTED_SERIALIZATION_VALUES: tuple[str, ...] = (
    "BoundaryContractCodecV2",
    "ContractEnvelopeV2",
    "ContractMigrationRegistryV2",
    "SUPPORTED_BOUNDARY_CONTRACT_IDS",
)

V2_IMPLEMENTED_PYTRANSFORMKIT_VALUES: tuple[str, ...] = (
    "DatasetVersionInputAdapter",
    "PyTransformKitCompatibilityError",
    "PyTransformKitIntegrationError",
    "PyTransformKitMappingError",
    "PyTransformKitUnavailableError",
    "TransformationPublicationAdapter",
    "TransformationPublicationInput",
    "from_transform_correlation",
    "from_transform_failure",
    "pytransformkit_version",
    "to_transform_correlation",
)

V2_IMPLEMENTED_PUBLICATION_VALUES: tuple[str, ...] = (
    "PublicationOutcomeUnknownError",
    "PublicationReconciliationResultV2",
    "PublicationReconciliationStatusV2",
    "PublicationRequestV2",
    "PublicationResultV2",
    "PublicationServiceV2",
    "PublicationStatusV2",
)

V2_IMPLEMENTED_GOVERNANCE_VALUES: tuple[str, ...] = (
    "ConditionalDatasetPublisher",
    "ConditionalPublicationOutcome",
    "ConditionalPublicationStatus",
    "DatasetVersionDeletionReconciliationResult",
    "DatasetVersionDeletionReconciliationStatus",
    "DatasetVersionDeletionResult",
    "DatasetVersionDeletionStatus",
    "DatasetVersionGarbageCollector",
    "GarbageCollectionPlan",
    "GarbageCollectionPlanId",
    "PublicationIntent",
    "PublicationLedger",
    "PublicationLifecycleEvent",
    "PublicationLifecycleEventType",
    "PublicationOperationId",
    "PublicationRevision",
    "PublicationSnapshot",
    "RetentionPolicy",
    "VersionHold",
)

V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES: tuple[str, ...] = (
    "FileConditionalDatasetPublisher",
    "FileDatasetVersionGarbageCollector",
    "MemoryPublicationLedger",
    "PostgresPublicationLedger",
    "S3ConditionalDatasetPublisher",
    "S3DatasetVersionGarbageCollector",
)

V2_IMPLEMENTED_MATERIALIZATION_VALUES: tuple[str, ...] = (
    "DatasetVersionMaterializerV2",
    "FileCsvDatasetVersionMaterializerV2",
    "ResourceDatasetVersionRequestV2",
)

V2_IMPLEMENTED_MIGRATION_VALUES: tuple[str, ...] = (
    "MigrationDecisionV2",
    "MigrationDispositionV2",
    "V1PluginMigrationAssessment",
    "V1PostgresTargetMigrationV2",
    "V1ProjectMigrationPlan",
    "assess_v1_plugin_entry_point",
    "migrate_v1_artifact_record",
    "migrate_v1_dataset_version_record",
    "migrate_v1_postgres_target_config",
    "migrate_v1_published_dataset_record",
    "plan_v1_config_migration",
)

V2_IMPLEMENTED_QUALIFIED_MIGRATION_VALUES: tuple[str, ...] = (
    "CompatibilityShimDecision",
    "LegacyArtifactSnapshot",
    "LegacyDatasetVersionSnapshot",
    "LegacyJobMigrationHints",
    "LegacyJobMigrationResult",
    "LegacyPublishedDatasetSnapshot",
    "LegacyReplayMigrationEvidence",
    "LegacyReplaySnapshot",
    "LegacyStepAssessment",
    "MigrationDisposition",
    "MigrationIssue",
    "MigrationReport",
    "StepOwnership",
    "V1JobMigrator",
    "V1MigrationResult",
    "V1SemanticExport",
    "V1SemanticImporter",
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
    "LOT-16",
    "LOT-17",
    "LOT-18",
    "LOT-19",
    "LOT-20",
    "LOT-21",
    "LOT-22",
    "LOT-23",
    "LOT-24",
    "LOT-25",
    "LOT-26",
    "LOT-27",
    "LOT-28",
    "LOT-29",
)

V2_MILESTONE_CANDIDATE = "2.1.0rc1"

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
    "pyingestkit.boundaries",
    "pyingestkit.datasets",
    "pyingestkit.decoders",
    "pyingestkit.diagnostics",
    "pyingestkit.ingestion",
    "pyingestkit.governance",
    "pyingestkit.governance.retention",
    "pyingestkit.governance.rollback",
    "pyingestkit.integrations.pytransformkit",
    "pyingestkit.migration",
    "pyingestkit.plugins",
    "pyingestkit.ports",
    "pyingestkit.provenance",
    "pyingestkit.publication",
    "pyingestkit.replay",
    "pyingestkit.resources",
    "pyingestkit.runtime",
    "pyingestkit.serialization",
    "pyingestkit.sources",
    "pyingestkit.stores",
    "pyingestkit.validation",
    "pyingestkit.quality",
)

V2_API_PHASE = "LOT-29_RC"
