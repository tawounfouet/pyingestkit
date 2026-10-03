"""Explicit canonical codecs for PyIngestKit V2 portable boundary contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.datasets import DatasetReference, DatasetVersionReference
from pyingestkit.domain.resources import CredentialReference, ResourceReference
from pyingestkit.domain.runtime import (
    CorrelationContext,
    Diagnostic,
    DiagnosticSeverity,
    FailureCategory,
    FailureEvidence,
    IdempotencyReference,
    IngestionExecutionReference,
    IngestionStatus,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.shared import CorrelationId, IngestionRunId

from .envelope_v2 import (
    ContractEnvelopeV2,
    ContractMigrationRegistryV2,
    JsonValue,
)

SUPPORTED_BOUNDARY_CONTRACT_IDS: tuple[str, ...] = (
    ResourceReference.CONTRACT_ID,
    CredentialReference.CONTRACT_ID,
    CorrelationContext.CONTRACT_ID,
    IdempotencyReference.CONTRACT_ID,
    ArtifactReference.CONTRACT_ID,
    DatasetReference.CONTRACT_ID,
    DatasetVersionReference.CONTRACT_ID,
    IngestionExecutionReference.CONTRACT_ID,
    FailureEvidence.CONTRACT_ID,
    Diagnostic.CONTRACT_ID,
)


class BoundaryContractCodecV2:
    """Canonical JSON codec for the fixed LOT-01 portable contract set."""

    def __init__(
        self,
        *,
        migrations: ContractMigrationRegistryV2 | None = None,
    ) -> None:
        self._migrations = migrations or ContractMigrationRegistryV2()

    def encode(self, value: object) -> bytes:
        contract_id, contract_version, payload = _encode_contract(value)
        return ContractEnvelopeV2(
            contract_id=contract_id,
            contract_version=contract_version,
            payload=payload,
        ).canonical_bytes()

    def decode(self, content: bytes) -> object:
        envelope = ContractEnvelopeV2.parse(content)
        if envelope.contract_id not in SUPPORTED_BOUNDARY_CONTRACT_IDS:
            raise ValueError(f"Unsupported boundary contract id: {envelope.contract_id!r}.")
        if envelope.contract_version != "1":
            envelope = self._migrations.migrate(envelope, target_version="1")
        return _decode_contract(envelope)


def _encode_contract(value: object) -> tuple[str, str, dict[str, JsonValue]]:
    if isinstance(value, ResourceReference):
        return (
            value.CONTRACT_ID,
            value.contract_version,
            {
                "format": value.format,
                "locator": value.locator,
                "media_type": value.media_type,
                "metadata": _pairs_out(value.metadata),
                "namespace": value.namespace,
                "resource_id": value.resource_id,
                "schema_fingerprint": value.schema_fingerprint,
            },
        )
    if isinstance(value, CredentialReference):
        return (
            value.CONTRACT_ID,
            value.contract_version,
            {
                "credential_id": value.credential_id,
                "provider": value.provider,
            },
        )
    if isinstance(value, CorrelationContext):
        return (
            value.CONTRACT_ID,
            value.contract_version,
            {
                "causation_id": value.causation_id,
                "correlation_id": str(value.correlation_id),
                "ingestion_run_id": value.ingestion_run_id,
                "parent_execution_id": value.parent_execution_id,
                "span_id": value.span_id,
                "task_attempt_id": value.task_attempt_id,
                "task_run_id": value.task_run_id,
                "trace_id": value.trace_id,
                "transformation_execution_id": value.transformation_execution_id,
                "workflow_run_id": value.workflow_run_id,
            },
        )
    if isinstance(value, IdempotencyReference):
        return (
            value.CONTRACT_ID,
            value.contract_version,
            {
                "key": value.key,
                "namespace": value.namespace,
                "owner": value.owner,
                "scope": value.scope,
            },
        )
    if isinstance(value, ArtifactReference):
        return (
            value.CONTRACT_ID,
            value.contract_version,
            {
                "artifact_id": value.artifact_id,
                "checksum": value.checksum,
                "checksum_algorithm": value.checksum_algorithm,
                "created_at": _datetime_out(value.created_at),
                "kind": value.kind,
                "media_type": value.media_type,
                "metadata": _pairs_out(value.metadata),
                "owner": value.owner,
                "resource": _nested_out(value.resource),
                "size_bytes": value.size_bytes,
            },
        )
    if isinstance(value, DatasetReference):
        return (
            value.CONTRACT_ID,
            value.contract_version,
            {
                "dataset_id": value.dataset_id,
                "locator": _nested_out(value.locator),
                "metadata": _pairs_out(value.metadata),
                "namespace": value.namespace,
                "owner": value.owner,
                "schema_fingerprint": value.schema_fingerprint,
            },
        )
    if isinstance(value, DatasetVersionReference):
        return (
            value.CONTRACT_ID,
            value.contract_version,
            {
                "artifact_reference": _nested_out(value.artifact_reference),
                "content_fingerprint": value.content_fingerprint,
                "created_at": _datetime_out(value.created_at),
                "dataset_id": value.dataset_id,
                "locator": _nested_out(value.locator),
                "namespace": value.namespace,
                "owner": value.owner,
                "schema_fingerprint": value.schema_fingerprint,
                "version_id": value.version_id,
            },
        )
    if isinstance(value, IngestionExecutionReference):
        return (
            value.CONTRACT_ID,
            value.contract_version,
            {
                "ingestion_definition_id": value.ingestion_definition_id,
                "ingestion_run_id": str(value.ingestion_run_id),
                "namespace": value.namespace,
                "output_dataset_version": _nested_out(value.output_dataset_version),
                "owner": value.owner,
                "status": None if value.status is None else value.status.value,
            },
        )
    if isinstance(value, FailureEvidence):
        return (
            value.CONTRACT_ID,
            value.contract_version,
            {
                "category": value.category.value,
                "correlation_id": str(value.correlation_id),
                "details": _pairs_out(value.details),
                "error_code": value.error_code,
                "ingestion_run_id": str(value.ingestion_run_id),
                "message_summary": value.message_summary,
                "occurred_at": _datetime_out(value.occurred_at),
                "provider_code": value.provider_code,
                "retryability": value.retryability.value,
                "source_component": value.source_component,
                "source_framework": value.source_framework,
                "uncertainty": value.uncertainty.value,
            },
        )
    if isinstance(value, Diagnostic):
        return (
            value.CONTRACT_ID,
            value.contract_version,
            {
                "code": value.code,
                "correlation_id": (
                    None if value.correlation_id is None else str(value.correlation_id)
                ),
                "details": _pairs_out(value.details),
                "ingestion_run_id": (
                    None if value.ingestion_run_id is None else str(value.ingestion_run_id)
                ),
                "related_field": value.related_field,
                "related_rule": value.related_rule,
                "severity": value.severity.value,
                "source_component": value.source_context,
                "source_framework": value.source_framework,
                "stage": value.stage,
                "summary": value.summary,
                "target_context": value.target_context,
            },
        )
    raise TypeError(f"Unsupported V2 boundary contract type: {type(value).__name__}.")


def _decode_contract(envelope: ContractEnvelopeV2) -> object:
    payload = envelope.payload
    version = envelope.contract_version

    if envelope.contract_id == ResourceReference.CONTRACT_ID:
        _exact_keys(
            payload,
            {
                "format",
                "locator",
                "media_type",
                "metadata",
                "namespace",
                "resource_id",
                "schema_fingerprint",
            },
        )
        return ResourceReference(
            namespace=_required_text(payload["namespace"], "namespace"),
            resource_id=_required_text(payload["resource_id"], "resource_id"),
            locator=_optional_text(payload["locator"], "locator"),
            media_type=_optional_text(payload["media_type"], "media_type"),
            format=_optional_text(payload["format"], "format"),
            schema_fingerprint=_optional_text(
                payload["schema_fingerprint"],
                "schema_fingerprint",
            ),
            metadata=_pairs_in(payload["metadata"]),
            contract_version=version,
        )

    if envelope.contract_id == CredentialReference.CONTRACT_ID:
        _exact_keys(payload, {"credential_id", "provider"})
        return CredentialReference(
            credential_id=_required_text(payload["credential_id"], "credential_id"),
            provider=_optional_text(payload["provider"], "provider"),
            contract_version=version,
        )

    if envelope.contract_id == CorrelationContext.CONTRACT_ID:
        _exact_keys(
            payload,
            {
                "causation_id",
                "correlation_id",
                "ingestion_run_id",
                "parent_execution_id",
                "span_id",
                "task_attempt_id",
                "task_run_id",
                "trace_id",
                "transformation_execution_id",
                "workflow_run_id",
            },
        )
        return CorrelationContext(
            correlation_id=CorrelationId.parse(
                _required_text(payload["correlation_id"], "correlation_id")
            ),
            causation_id=_optional_text(payload["causation_id"], "causation_id"),
            parent_execution_id=_optional_text(
                payload["parent_execution_id"],
                "parent_execution_id",
            ),
            workflow_run_id=_optional_text(payload["workflow_run_id"], "workflow_run_id"),
            task_run_id=_optional_text(payload["task_run_id"], "task_run_id"),
            task_attempt_id=_optional_text(payload["task_attempt_id"], "task_attempt_id"),
            ingestion_run_id=_optional_text(
                payload["ingestion_run_id"],
                "ingestion_run_id",
            ),
            transformation_execution_id=_optional_text(
                payload["transformation_execution_id"],
                "transformation_execution_id",
            ),
            trace_id=_optional_text(payload["trace_id"], "trace_id"),
            span_id=_optional_text(payload["span_id"], "span_id"),
            contract_version=version,
        )

    if envelope.contract_id == IdempotencyReference.CONTRACT_ID:
        _exact_keys(payload, {"key", "namespace", "owner", "scope"})
        return IdempotencyReference(
            namespace=_required_text(payload["namespace"], "namespace"),
            key=_required_text(payload["key"], "key"),
            scope=_required_text(payload["scope"], "scope"),
            owner=_required_text(payload["owner"], "owner"),
            contract_version=version,
        )

    if envelope.contract_id == ArtifactReference.CONTRACT_ID:
        _exact_keys(
            payload,
            {
                "artifact_id",
                "checksum",
                "checksum_algorithm",
                "created_at",
                "kind",
                "media_type",
                "metadata",
                "owner",
                "resource",
                "size_bytes",
            },
        )
        resource = _nested_in(payload["resource"], ResourceReference.CONTRACT_ID)
        assert isinstance(resource, ResourceReference)
        return ArtifactReference(
            artifact_id=_required_text(payload["artifact_id"], "artifact_id"),
            kind=_required_text(payload["kind"], "kind"),
            resource=resource,
            checksum=_optional_text(payload["checksum"], "checksum"),
            checksum_algorithm=_optional_text(
                payload["checksum_algorithm"],
                "checksum_algorithm",
            ),
            media_type=_optional_text(payload["media_type"], "media_type"),
            size_bytes=_optional_int(payload["size_bytes"], "size_bytes"),
            created_at=_datetime_in(payload["created_at"], "created_at"),
            metadata=_pairs_in(payload["metadata"]),
            owner=_required_text(payload["owner"], "owner"),
            contract_version=version,
        )

    if envelope.contract_id == DatasetReference.CONTRACT_ID:
        _exact_keys(
            payload,
            {
                "dataset_id",
                "locator",
                "metadata",
                "namespace",
                "owner",
                "schema_fingerprint",
            },
        )
        locator = _nested_in(payload["locator"], ResourceReference.CONTRACT_ID)
        assert locator is None or isinstance(locator, ResourceReference)
        return DatasetReference(
            dataset_id=_required_text(payload["dataset_id"], "dataset_id"),
            schema_fingerprint=_optional_text(
                payload["schema_fingerprint"],
                "schema_fingerprint",
            ),
            locator=locator,
            metadata=_pairs_in(payload["metadata"]),
            owner=_required_text(payload["owner"], "owner"),
            namespace=_required_text(payload["namespace"], "namespace"),
            contract_version=version,
        )

    if envelope.contract_id == DatasetVersionReference.CONTRACT_ID:
        _exact_keys(
            payload,
            {
                "artifact_reference",
                "content_fingerprint",
                "created_at",
                "dataset_id",
                "locator",
                "namespace",
                "owner",
                "schema_fingerprint",
                "version_id",
            },
        )
        artifact = _nested_in(payload["artifact_reference"], ArtifactReference.CONTRACT_ID)
        locator = _nested_in(payload["locator"], ResourceReference.CONTRACT_ID)
        assert artifact is None or isinstance(artifact, ArtifactReference)
        assert locator is None or isinstance(locator, ResourceReference)
        return DatasetVersionReference(
            dataset_id=_required_text(payload["dataset_id"], "dataset_id"),
            version_id=_required_text(payload["version_id"], "version_id"),
            created_at=_datetime_in(payload["created_at"], "created_at"),
            schema_fingerprint=_optional_text(
                payload["schema_fingerprint"],
                "schema_fingerprint",
            ),
            content_fingerprint=_optional_text(
                payload["content_fingerprint"],
                "content_fingerprint",
            ),
            artifact_reference=artifact,
            locator=locator,
            owner=_required_text(payload["owner"], "owner"),
            namespace=_required_text(payload["namespace"], "namespace"),
            contract_version=version,
        )

    if envelope.contract_id == IngestionExecutionReference.CONTRACT_ID:
        _exact_keys(
            payload,
            {
                "ingestion_definition_id",
                "ingestion_run_id",
                "namespace",
                "output_dataset_version",
                "owner",
                "status",
            },
        )
        version_reference = _nested_in(
            payload["output_dataset_version"],
            DatasetVersionReference.CONTRACT_ID,
        )
        assert version_reference is None or isinstance(
            version_reference,
            DatasetVersionReference,
        )
        status_raw = _optional_text(payload["status"], "status")
        return IngestionExecutionReference(
            ingestion_run_id=IngestionRunId.parse(
                _required_text(payload["ingestion_run_id"], "ingestion_run_id")
            ),
            ingestion_definition_id=_optional_text(
                payload["ingestion_definition_id"],
                "ingestion_definition_id",
            ),
            output_dataset_version=version_reference,
            status=None if status_raw is None else IngestionStatus(status_raw),
            owner=_required_text(payload["owner"], "owner"),
            namespace=_required_text(payload["namespace"], "namespace"),
            contract_version=version,
        )

    if envelope.contract_id == FailureEvidence.CONTRACT_ID:
        _exact_keys(
            payload,
            {
                "category",
                "correlation_id",
                "details",
                "error_code",
                "ingestion_run_id",
                "message_summary",
                "occurred_at",
                "provider_code",
                "retryability",
                "source_component",
                "source_framework",
                "uncertainty",
            },
        )
        return FailureEvidence(
            error_code=_required_text(payload["error_code"], "error_code"),
            category=FailureCategory(_required_text(payload["category"], "category")),
            retryability=Retryability(
                _required_text(payload["retryability"], "retryability")
            ),
            uncertainty=OutcomeUncertainty(
                _required_text(payload["uncertainty"], "uncertainty")
            ),
            ingestion_run_id=IngestionRunId.parse(
                _required_text(payload["ingestion_run_id"], "ingestion_run_id")
            ),
            correlation_id=CorrelationId.parse(
                _required_text(payload["correlation_id"], "correlation_id")
            ),
            source_framework=_required_text(
                payload["source_framework"],
                "source_framework",
            ),
            source_component=_optional_text(
                payload["source_component"],
                "source_component",
            ),
            provider_code=_optional_text(payload["provider_code"], "provider_code"),
            message_summary=_optional_text(
                payload["message_summary"],
                "message_summary",
            ),
            occurred_at=_required_datetime(payload["occurred_at"], "occurred_at"),
            details=_pairs_in(payload["details"]),
            contract_version=version,
        )

    if envelope.contract_id == Diagnostic.CONTRACT_ID:
        _exact_keys(
            payload,
            {
                "code",
                "correlation_id",
                "details",
                "ingestion_run_id",
                "related_field",
                "related_rule",
                "severity",
                "source_component",
                "source_framework",
                "stage",
                "summary",
                "target_context",
            },
        )
        run_raw = _optional_text(payload["ingestion_run_id"], "ingestion_run_id")
        correlation_raw = _optional_text(payload["correlation_id"], "correlation_id")
        return Diagnostic(
            code=_required_text(payload["code"], "code"),
            severity=DiagnosticSeverity(
                _required_text(payload["severity"], "severity")
            ),
            summary=_required_text(payload["summary"], "summary"),
            stage=_optional_text(payload["stage"], "stage"),
            source_context=_optional_text(
                payload["source_component"],
                "source_component",
            ),
            target_context=_optional_text(payload["target_context"], "target_context"),
            related_rule=_optional_text(payload["related_rule"], "related_rule"),
            related_field=_optional_text(payload["related_field"], "related_field"),
            details=_pairs_in(payload["details"]),
            ingestion_run_id=None if run_raw is None else IngestionRunId.parse(run_raw),
            correlation_id=(
                None if correlation_raw is None else CorrelationId.parse(correlation_raw)
            ),
            source_framework=_required_text(
                payload["source_framework"],
                "source_framework",
            ),
            contract_version=version,
        )

    raise ValueError(f"Unsupported boundary contract id: {envelope.contract_id!r}.")


def _nested_out(value: object | None) -> JsonValue:
    if value is None:
        return None
    contract_id, contract_version, payload = _encode_contract(value)
    return {
        "contract_id": contract_id,
        "contract_version": contract_version,
        "payload": payload,
    }


def _nested_in(value: JsonValue, expected_contract_id: str) -> object | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Nested portable contract must be a JSON object.")
    _exact_keys(value, {"contract_id", "contract_version", "payload"})
    contract_id = _required_text(value["contract_id"], "nested contract_id")
    if contract_id != expected_contract_id:
        raise ValueError(
            f"Nested contract id mismatch: expected {expected_contract_id!r}, got {contract_id!r}."
        )
    version = _required_text(value["contract_version"], "nested contract_version")
    payload = value["payload"]
    if not isinstance(payload, dict):
        raise ValueError("Nested contract payload must be a JSON object.")
    return _decode_contract(
        ContractEnvelopeV2(
            contract_id=contract_id,
            contract_version=version,
            payload=payload,
        )
    )


def _pairs_out(values: tuple[tuple[str, str], ...]) -> list[JsonValue]:
    return [[key, value] for key, value in values]


def _pairs_in(value: JsonValue) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise ValueError("Metadata pairs must be a JSON array.")
    values: list[tuple[str, str]] = []
    for item in value:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], str)
        ):
            raise ValueError("Metadata entries must be [string, string] pairs.")
        values.append((item[0], item[1]))
    return tuple(values)


def _datetime_out(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _datetime_in(value: JsonValue, name: str) -> datetime | None:
    text = _optional_text(value, name)
    return None if text is None else _parse_datetime(text, name)


def _required_datetime(value: JsonValue, name: str) -> datetime:
    return _parse_datetime(_required_text(value, name), name)


def _parse_datetime(value: str, name: str) -> datetime:
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO 8601 datetime.") from exc
    if result.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware.")
    return result


def _required_text(value: JsonValue, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-blank text.")
    return value


def _optional_text(value: JsonValue, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name)


def _optional_int(value: JsonValue, name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer.")
    return value


def _exact_keys(payload: dict[str, Any], expected: set[str]) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"Contract payload fields mismatch: missing={missing}, extra={extra}.")
