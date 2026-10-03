from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

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
from pyingestkit.serialization import (
    BoundaryContractCodecV2,
    ContractEnvelopeV2,
    ContractMigrationRegistryV2,
)

_GOLDEN = (
    Path(__file__).resolve().parents[2]
    / "contract"
    / "fixtures"
    / "v2_wire"
    / "resource_reference_v1.json"
)
_NOW = datetime(2026, 10, 3, 12, 30, tzinfo=UTC)
_RUN_ID = IngestionRunId.parse("11111111-1111-4111-8111-111111111111")
_CORRELATION_ID = CorrelationId.parse("22222222-2222-4222-8222-222222222222")


def _resource() -> ResourceReference:
    return ResourceReference(
        namespace="pyingestkit.resource.s3",
        resource_id="customers-2026-10-03",
        locator="s3://demo/raw/customers.csv",
        media_type="text/csv",
        format="csv",
        schema_fingerprint="schema-abc",
        metadata=(("source", "crm"), ("tenant", "demo")),
    )


def _artifact() -> ArtifactReference:
    return ArtifactReference(
        artifact_id="raw-1",
        kind="raw",
        resource=_resource(),
        checksum="a" * 64,
        checksum_algorithm="sha256",
        media_type="text/csv",
        size_bytes=17,
        created_at=_NOW,
        metadata=(("origin", "http"),),
    )


def _dataset_version() -> DatasetVersionReference:
    return DatasetVersionReference(
        dataset_id="demo.customers",
        version_id="sha256-" + "b" * 64,
        created_at=_NOW,
        schema_fingerprint="schema-abc",
        content_fingerprint="sha256-" + "b" * 64,
        artifact_reference=_artifact(),
        locator=ResourceReference(
            namespace="pyingestkit.dataset_version.s3",
            resource_id="version-1",
            locator="s3://demo/versions/customers/snapshot.json",
            media_type="application/json",
            format="json",
        ),
    )


def _values() -> tuple[object, ...]:
    return (
        _resource(),
        CredentialReference("crm-api", provider="vault"),
        CorrelationContext(
            correlation_id=_CORRELATION_ID,
            causation_id="cause-1",
            parent_execution_id="parent-1",
            workflow_run_id="workflow-1",
            task_run_id="task-1",
            task_attempt_id="attempt-1",
            ingestion_run_id=str(_RUN_ID),
            transformation_execution_id="transform-1",
            trace_id="trace-1",
            span_id="span-1",
        ),
        IdempotencyReference(
            namespace="demo",
            key="customer-42",
            scope="dataset-version",
        ),
        _artifact(),
        DatasetReference(
            dataset_id="demo.customers",
            schema_fingerprint="schema-abc",
            locator=_resource(),
            metadata=(("domain", "crm"),),
        ),
        _dataset_version(),
        IngestionExecutionReference(
            ingestion_run_id=_RUN_ID,
            ingestion_definition_id="demo.customers",
            output_dataset_version=_dataset_version(),
            status=IngestionStatus.SUCCEEDED,
        ),
        FailureEvidence(
            error_code="demo.failed",
            category=FailureCategory.VALIDATION,
            retryability=Retryability.NON_RETRYABLE,
            uncertainty=OutcomeUncertainty.KNOWN,
            ingestion_run_id=_RUN_ID,
            correlation_id=_CORRELATION_ID,
            source_component="decoder",
            provider_code="BAD_ROW",
            message_summary="Input did not satisfy the contract.",
            occurred_at=_NOW,
            details=(("field", "id"),),
        ),
        Diagnostic(
            code="demo.warning",
            severity=DiagnosticSeverity.WARNING,
            summary="One value required review.",
            stage="validate",
            source_context="csv",
            target_context="dataset",
            related_rule="required",
            related_field="id",
            details=(("row", "1"),),
            ingestion_run_id=_RUN_ID,
            correlation_id=_CORRELATION_ID,
        ),
    )


@pytest.mark.parametrize("value", _values())
def test_boundary_contract_codec_round_trips_supported_values(value: object) -> None:
    codec = BoundaryContractCodecV2()

    encoded = codec.encode(value)
    decoded = codec.decode(encoded)

    assert decoded == value
    assert codec.encode(decoded) == encoded


def test_resource_reference_matches_golden_canonical_bytes() -> None:
    codec = BoundaryContractCodecV2()

    assert codec.encode(_resource()) == _GOLDEN.read_bytes()


def test_envelope_rejects_unknown_or_extra_fields() -> None:
    with pytest.raises(ValueError, match="fields"):
        ContractEnvelopeV2.parse(
            b'{"contract_id":"pykit.resource_reference","contract_version":"1",'
            b'"envelope_version":"1","payload":{},"unexpected":true}'
        )


def test_codec_rejects_unknown_contract_id_without_dynamic_import() -> None:
    payload = ContractEnvelopeV2(
        contract_id="example.attacker.module",
        contract_version="1",
        payload={},
    ).canonical_bytes()

    with pytest.raises(ValueError, match="Unsupported boundary contract id"):
        BoundaryContractCodecV2().decode(payload)


def test_explicit_migration_registry_upgrades_payload_before_decode() -> None:
    migrations = ContractMigrationRegistryV2()
    migrations.register(
        contract_id=ResourceReference.CONTRACT_ID,
        from_version="0",
        to_version="1",
        migrate=lambda payload: {**payload, "schema_fingerprint": None},
    )
    old = ContractEnvelopeV2(
        contract_id=ResourceReference.CONTRACT_ID,
        contract_version="0",
        payload={
            "format": "csv",
            "locator": "s3://demo/raw/customers.csv",
            "media_type": "text/csv",
            "metadata": [],
            "namespace": "pyingestkit.resource.s3",
            "resource_id": "legacy-resource",
        },
    )

    decoded = BoundaryContractCodecV2(migrations=migrations).decode(old.canonical_bytes())

    assert decoded == ResourceReference(
        namespace="pyingestkit.resource.s3",
        resource_id="legacy-resource",
        locator="s3://demo/raw/customers.csv",
        media_type="text/csv",
        format="csv",
    )


def test_migration_fails_closed_when_path_is_missing() -> None:
    old = ContractEnvelopeV2(
        contract_id=ResourceReference.CONTRACT_ID,
        contract_version="0",
        payload={},
    )

    with pytest.raises(ValueError, match="No registered migration path"):
        BoundaryContractCodecV2().decode(old.canonical_bytes())
