from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pyingestkit.adapters.filesystem import (
    FileCsvDatasetVersionMaterializerV2,
    FileDatasetVersionStore,
)
from pyingestkit.datasets import ResourceDatasetVersionRequestV2
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.publication.v2 import (
    PublicationOutcomeUnknownError,
    PublicationReconciliationStatusV2,
    PublicationRequestV2,
    PublicationServiceV2,
    PublicationStatusV2,
)

_NOW = datetime(2026, 10, 3, 14, 30, tzinfo=UTC)


class _CommitThenLoseAckPublisher:
    def __init__(self, delegate: FileDatasetVersionStore) -> None:
        self.delegate = delegate
        self.publish_calls = 0

    def publish(self, reference, *, ingestion_run_id, published_at):  # type: ignore[no-untyped-def]
        self.publish_calls += 1
        self.delegate.publish(
            reference,
            ingestion_run_id=ingestion_run_id,
            published_at=published_at,
        )
        raise PublicationOutcomeUnknownError(
            "provider acknowledgement lost",
            provider_operation_reference="op-customer-mart-42",
        )

    def get_published(self, dataset_id: str):  # type: ignore[no-untyped-def]
        return self.delegate.get_published(dataset_id)


def _stored_version(tmp_path: Path):
    output = tmp_path / "customer_mart.csv"
    output.write_text("customer_id,paid_revenue\n1,15.5\n", encoding="utf-8")
    run_id = IngestionRunId.new()
    materializer = FileCsvDatasetVersionMaterializerV2(allowed_roots=(tmp_path,))
    version = materializer.materialize(
        ResourceDatasetVersionRequestV2(
            dataset_id="customer360.customer_mart",
            resource=ResourceReference(
                namespace="customer360.transform",
                resource_id="customer-mart",
                locator=output.resolve().as_uri(),
                media_type="text/csv",
                format="csv",
            ),
            ingestion_run_id=run_id,
            created_at=_NOW,
            provenance=(("transformation.execution_id", "transform-42"),),
        )
    )
    store = FileDatasetVersionStore(root=tmp_path / "versions")
    return store, store.put(version), run_id


def test_unknown_publication_outcome_requires_reconciliation_before_safe_completion(
    tmp_path: Path,
) -> None:
    store, reference, run_id = _stored_version(tmp_path)
    publisher = _CommitThenLoseAckPublisher(store)
    service = PublicationServiceV2(
        publisher=publisher,
        clock=lambda: _NOW,
    )
    request = PublicationRequestV2(
        dataset_version=reference,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        requested_at=_NOW,
    )

    uncertain = service.publish(request)

    assert uncertain.status is PublicationStatusV2.UNKNOWN_OUTCOME
    assert uncertain.reconciliation_required is True
    assert uncertain.provider_operation_reference == "op-customer-mart-42"
    assert publisher.publish_calls == 1

    reconciled = service.reconcile(request)

    assert (
        reconciled.status
        is PublicationReconciliationStatusV2.CONFIRMED_COMMITTED
    )
    assert reconciled.published_dataset is not None
    assert reconciled.published_dataset.version.identity == reference.identity

    safe_completion = service.publish(request)
    assert safe_completion.status is PublicationStatusV2.SUCCEEDED
    assert publisher.publish_calls == 1
