"""Explicit V2 ingestion runtime composition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from pyingestkit.application.decoders import DecoderRegistry
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.domain.acquisition import AcquisitionRequest, AcquisitionStatus
from pyingestkit.domain.artifacts import (
    ArtifactPutStatus,
    ArtifactReference,
    ArtifactRetention,
    PutArtifactRequest,
)
from pyingestkit.domain.datasets.version import build_dataset_version
from pyingestkit.domain.decoding import DecodeRequest, DecodeStatus
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.runtime import (
    CorrelationContext,
    Diagnostic,
    FailureCategory,
    FailureEvidence,
    IngestionResult,
    IngestionRun,
    IngestionStatus,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.ports.artifacts import ArtifactStore
from pyingestkit.ports.dataset_versions import DatasetPublisher, DatasetVersionStore
from pyingestkit.validation.result import ValidationResult
from pyingestkit.validation.v2 import ValidationRequest, ValidationRuleV2, validate_v2


class IngestionRuntime:
    """Compose one explicit V2 ingestion execution from framework-owned ports."""

    def __init__(
        self,
        *,
        sources: SourceRegistry,
        decoders: DecoderRegistry,
        artifacts: ArtifactStore,
        versions: DatasetVersionStore,
        publisher: DatasetPublisher | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(sources, SourceRegistry):
            raise TypeError("IngestionRuntime sources must be SourceRegistry.")
        if not isinstance(decoders, DecoderRegistry):
            raise TypeError("IngestionRuntime decoders must be DecoderRegistry.")
        if not isinstance(artifacts, ArtifactStore):
            raise TypeError("IngestionRuntime artifacts must implement ArtifactStore.")
        if not isinstance(versions, DatasetVersionStore):
            raise TypeError("IngestionRuntime versions must implement DatasetVersionStore.")
        if publisher is not None and not isinstance(publisher, DatasetPublisher):
            raise TypeError("IngestionRuntime publisher must implement DatasetPublisher.")

        self._sources = sources
        self._decoders = decoders
        self._artifacts = artifacts
        self._versions = versions
        self._publisher = publisher
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def artifact_store(self) -> ArtifactStore:
        """Return the exact artifact boundary used by this runtime."""
        return self._artifacts

    def execute(
        self,
        definition: IngestionDefinition,
        *,
        validation_rules: tuple[ValidationRuleV2, ...] = (),
        publish: bool = False,
        ingestion_run_id: IngestionRunId | None = None,
        correlation: CorrelationContext | None = None,
    ) -> IngestionResult:
        """Execute one synchronous ingestion without legacy Job/Pipeline/Step semantics."""
        self._validate_execution_inputs(definition, validation_rules, publish)
        run_id = self._run_id(ingestion_run_id)
        context = self._correlation(run_id, correlation)
        created_at = self._now()
        started_at = self._now()

        if not definition.raw_policy.enabled:
            return self._failed(
                definition=definition,
                run_id=run_id,
                correlation=context,
                created_at=created_at,
                started_at=started_at,
                failure=self._failure(
                    run_id,
                    context,
                    code="runtime.raw_required",
                    category=FailureCategory.CONFIGURATION,
                    summary="V2 runtime requires durable RAW before decoding.",
                ),
            )

        try:
            connector = self._sources.resolve(definition.source)
            acquisition = connector.acquire(
                AcquisitionRequest(
                    source=definition.source,
                    ingestion_run_id=run_id,
                    correlation=context,
                )
            )
        except (KeyError, LookupError, ValueError) as exc:
            return self._configuration_failure(
                definition,
                run_id,
                context,
                created_at,
                started_at,
                component="source",
                exc=exc,
            )

        if acquisition.status is not AcquisitionStatus.SUCCEEDED:
            if acquisition.failure is None:
                raise AssertionError("Acquisition failure invariant was not preserved.")
            return self._failed(
                definition=definition,
                run_id=run_id,
                correlation=context,
                created_at=created_at,
                started_at=started_at,
                failure=acquisition.failure,
                diagnostics=acquisition.diagnostics,
            )

        raw_put = self._artifacts.put(
            PutArtifactRequest.from_acquisition(
                acquisition,
                name="source.raw",
                retention=ArtifactRetention(retain=definition.raw_policy.retain),
            )
        )
        if raw_put.status is not ArtifactPutStatus.SUCCEEDED:
            if raw_put.failure is None:
                raise AssertionError("Artifact persistence failure invariant was not preserved.")
            return self._failed(
                definition=definition,
                run_id=run_id,
                correlation=context,
                created_at=created_at,
                started_at=started_at,
                failure=raw_put.failure,
                diagnostics=acquisition.diagnostics + raw_put.diagnostics,
            )
        if raw_put.reference is None:
            raise AssertionError("Successful RAW persistence did not expose ArtifactReference.")

        return self._execute_from_raw(
            definition=definition,
            raw_artifact=raw_put.reference,
            raw_content=acquisition.content or b"",
            validation_rules=validation_rules,
            publish=publish,
            run_id=run_id,
            correlation=context,
            created_at=created_at,
            started_at=started_at,
            diagnostics=acquisition.diagnostics + raw_put.diagnostics,
            expected_version_id=None,
        )

    def execute_from_raw(
        self,
        definition: IngestionDefinition,
        *,
        raw_artifact: ArtifactReference,
        raw_content: bytes,
        validation_rules: tuple[ValidationRuleV2, ...] = (),
        publish: bool = False,
        expected_version_id: str | None = None,
        ingestion_run_id: IngestionRunId | None = None,
        correlation: CorrelationContext | None = None,
    ) -> IngestionResult:
        """Execute decode-to-version from already durable RAW without source acquisition."""
        self._validate_execution_inputs(definition, validation_rules, publish)
        if not isinstance(raw_artifact, ArtifactReference):
            raise TypeError("IngestionRuntime raw_artifact must be ArtifactReference.")
        if raw_artifact.kind != "raw":
            raise ValueError("IngestionRuntime execute_from_raw requires kind='raw'.")
        if not isinstance(raw_content, bytes):
            raise TypeError("IngestionRuntime raw_content must be bytes.")
        if expected_version_id is not None:
            if not isinstance(expected_version_id, str) or not expected_version_id.strip():
                raise ValueError("IngestionRuntime expected_version_id must be non-blank text.")

        run_id = self._run_id(ingestion_run_id)
        context = self._correlation(run_id, correlation)
        return self._execute_from_raw(
            definition=definition,
            raw_artifact=raw_artifact,
            raw_content=raw_content,
            validation_rules=validation_rules,
            publish=publish,
            run_id=run_id,
            correlation=context,
            created_at=self._now(),
            started_at=self._now(),
            diagnostics=(),
            expected_version_id=expected_version_id,
        )

    def _execute_from_raw(
        self,
        *,
        definition: IngestionDefinition,
        raw_artifact: ArtifactReference,
        raw_content: bytes,
        validation_rules: tuple[ValidationRuleV2, ...],
        publish: bool,
        run_id: IngestionRunId,
        correlation: CorrelationContext,
        created_at: datetime,
        started_at: datetime,
        diagnostics: tuple[Diagnostic, ...],
        expected_version_id: str | None,
    ) -> IngestionResult:
        try:
            decoder = self._decoders.get(definition.decoder)
        except KeyError as exc:
            return self._configuration_failure(
                definition,
                run_id,
                correlation,
                created_at,
                started_at,
                component="decoder",
                exc=exc,
                diagnostics=diagnostics,
            )

        decode_request = DecodeRequest(
            ingestion_run_id=run_id,
            correlation=correlation,
            artifact=raw_artifact,
            content=raw_content,
        )
        decoded = decoder.decode(decode_request)
        diagnostics = diagnostics + decoded.diagnostics
        if decoded.status is not DecodeStatus.SUCCEEDED:
            if decoded.failure is None:
                raise AssertionError("Decode failure invariant was not preserved.")
            return self._failed(
                definition=definition,
                run_id=run_id,
                correlation=correlation,
                created_at=created_at,
                started_at=started_at,
                failure=decoded.failure,
                diagnostics=diagnostics,
            )
        if decoded.representation is None:
            raise AssertionError("Successful decode did not expose representation.")

        validation = validate_v2(
            ValidationRequest(
                ingestion_run_id=run_id,
                correlation=correlation,
                artifact=raw_artifact,
                decoder_id=decoded.decoder_id,
                representation=decoded.representation,
            ),
            validation_rules,
        )
        if not validation.is_valid:
            return self._validation_failure(
                definition,
                run_id,
                correlation,
                created_at,
                started_at,
                validation=validation,
                diagnostics=diagnostics,
            )

        version = build_dataset_version(
            dataset_id=definition.dataset,
            request=decode_request,
            result=decoded,
            created_at=self._now(),
        )
        if expected_version_id is not None and version.version_id != expected_version_id:
            return self._failed(
                definition=definition,
                run_id=run_id,
                correlation=correlation,
                created_at=created_at,
                started_at=started_at,
                failure=self._failure(
                    run_id,
                    correlation,
                    code="runtime.version_mismatch",
                    category=FailureCategory.INTEGRITY,
                    summary="Produced dataset version does not match expected replay identity.",
                    details=(
                        ("expected_version_id", expected_version_id),
                        ("actual_version_id", version.version_id),
                    ),
                ),
                diagnostics=diagnostics,
            )

        reference = self._versions.put(version)
        published = None
        if publish:
            if self._publisher is None:
                return self._failed(
                    definition=definition,
                    run_id=run_id,
                    correlation=correlation,
                    created_at=created_at,
                    started_at=started_at,
                    failure=self._failure(
                        run_id,
                        correlation,
                        code="runtime.publisher_required",
                        category=FailureCategory.CONFIGURATION,
                        summary="Publication was requested but no DatasetPublisher is configured.",
                    ),
                    diagnostics=diagnostics,
                )
            published = self._publisher.publish(
                reference,
                ingestion_run_id=run_id,
                published_at=self._now(),
            )

        run = IngestionRun(
            ingestion_run_id=run_id,
            ingestion_definition_name=definition.name,
            definition_fingerprint=str(definition.fingerprint),
            correlation=correlation,
            status=IngestionStatus.SUCCEEDED,
            created_at=created_at,
            started_at=started_at,
            ended_at=self._now(),
        )
        return IngestionResult(
            run=run,
            raw_artifact=raw_artifact,
            dataset_version=reference,
            published_dataset=published,
            diagnostics=diagnostics,
        )

    def _configuration_failure(
        self,
        definition: IngestionDefinition,
        run_id: IngestionRunId,
        correlation: CorrelationContext,
        created_at: datetime,
        started_at: datetime,
        *,
        component: str,
        exc: Exception,
        diagnostics: tuple[Diagnostic, ...] = (),
    ) -> IngestionResult:
        return self._failed(
            definition=definition,
            run_id=run_id,
            correlation=correlation,
            created_at=created_at,
            started_at=started_at,
            failure=self._failure(
                run_id,
                correlation,
                code=f"runtime.{component}.configuration",
                category=FailureCategory.CONFIGURATION,
                summary=f"Ingestion runtime could not resolve the configured {component}.",
                details=(("exception_type", type(exc).__name__),),
            ),
            diagnostics=diagnostics,
        )

    def _validation_failure(
        self,
        definition: IngestionDefinition,
        run_id: IngestionRunId,
        correlation: CorrelationContext,
        created_at: datetime,
        started_at: datetime,
        *,
        validation: ValidationResult,
        diagnostics: tuple[Diagnostic, ...],
    ) -> IngestionResult:
        return self._failed(
            definition=definition,
            run_id=run_id,
            correlation=correlation,
            created_at=created_at,
            started_at=started_at,
            failure=self._failure(
                run_id,
                correlation,
                code="runtime.validation.failed",
                category=FailureCategory.VALIDATION,
                summary="Decoded representation failed validation.",
                details=(("error_count", str(validation.error_count)),),
            ),
            diagnostics=diagnostics,
        )

    def _failed(
        self,
        *,
        definition: IngestionDefinition,
        run_id: IngestionRunId,
        correlation: CorrelationContext,
        created_at: datetime,
        started_at: datetime,
        failure: FailureEvidence,
        diagnostics: tuple[Diagnostic, ...] = (),
    ) -> IngestionResult:
        run = IngestionRun(
            ingestion_run_id=run_id,
            ingestion_definition_name=definition.name,
            definition_fingerprint=str(definition.fingerprint),
            correlation=correlation,
            status=IngestionStatus.FAILED,
            created_at=created_at,
            started_at=started_at,
            ended_at=self._now(),
        )
        return IngestionResult(run=run, diagnostics=diagnostics, failure=failure)

    @staticmethod
    def _failure(
        run_id: IngestionRunId,
        correlation: CorrelationContext,
        *,
        code: str,
        category: FailureCategory,
        summary: str,
        details: tuple[tuple[str, str], ...] = (),
    ) -> FailureEvidence:
        return FailureEvidence(
            error_code=code,
            category=category,
            retryability=Retryability.NON_RETRYABLE,
            uncertainty=OutcomeUncertainty.KNOWN,
            ingestion_run_id=run_id,
            correlation_id=correlation.correlation_id,
            source_component="IngestionRuntime",
            message_summary=summary,
            details=details,
        )

    @staticmethod
    def _validate_execution_inputs(
        definition: IngestionDefinition,
        validation_rules: tuple[ValidationRuleV2, ...],
        publish: bool,
    ) -> None:
        if not isinstance(definition, IngestionDefinition):
            raise TypeError("IngestionRuntime definition must be IngestionDefinition.")
        if not isinstance(validation_rules, tuple):
            raise TypeError("IngestionRuntime validation_rules must be a tuple.")
        if not isinstance(publish, bool):
            raise TypeError("IngestionRuntime publish must be bool.")

    @staticmethod
    def _run_id(value: IngestionRunId | None) -> IngestionRunId:
        run_id = value or IngestionRunId.new()
        if not isinstance(run_id, IngestionRunId):
            raise TypeError("IngestionRuntime ingestion_run_id must be IngestionRunId.")
        return run_id

    @staticmethod
    def _correlation(
        run_id: IngestionRunId,
        correlation: CorrelationContext | None,
    ) -> CorrelationContext:
        if correlation is None:
            return CorrelationContext(ingestion_run_id=str(run_id))
        if not isinstance(correlation, CorrelationContext):
            raise TypeError("IngestionRuntime correlation must be CorrelationContext.")
        if correlation.ingestion_run_id not in {None, str(run_id)}:
            raise ValueError("IngestionRuntime correlation run identity mismatch.")
        if correlation.ingestion_run_id is None:
            return replace(correlation, ingestion_run_id=str(run_id))
        return correlation

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("IngestionRuntime clock must return timezone-aware datetime.")
        return value
