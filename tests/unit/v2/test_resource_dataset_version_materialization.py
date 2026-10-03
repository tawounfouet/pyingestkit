from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyingestkit.adapters.filesystem import (
    FileCsvDatasetVersionMaterializerV2,
    FileDatasetVersionStore,
)
from pyingestkit.datasets import ResourceDatasetVersionRequestV2
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.serialization import BoundaryContractCodecV2

_NOW = datetime(2026, 10, 3, 14, 0, tzinfo=UTC)


def _resource(path: Path) -> ResourceReference:
    return ResourceReference(
        namespace="customer360.transform",
        resource_id="customer-mart-csv",
        locator=path.resolve().as_uri(),
        media_type="text/csv",
        format="csv",
    )


def test_file_csv_materializer_creates_governed_version_with_persisted_provenance(
    tmp_path: Path,
) -> None:
    output = tmp_path / "customer_mart.csv"
    output.write_text(
        "customer_id,email,paid_revenue\n1,alice@example.com,15.5\n",
        encoding="utf-8",
    )
    run_id = IngestionRunId.new()
    provenance = (
        ("source.customers.version_id", "sha256-" + "a" * 64),
        ("source.orders.version_id", "sha256-" + "b" * 64),
        ("transformation.execution_id", "transform-42"),
        ("transformation.plan_fingerprint", "sha256:" + "c" * 64),
    )

    materializer = FileCsvDatasetVersionMaterializerV2(
        allowed_roots=(tmp_path,),
    )
    version = materializer.materialize(
        ResourceDatasetVersionRequestV2(
            dataset_id="customer360.customer_mart",
            resource=_resource(output),
            ingestion_run_id=run_id,
            created_at=_NOW,
            provenance=provenance,
        )
    )

    assert version.dataset_id == "customer360.customer_mart"
    assert version.row_count == 1
    assert version.reference.metadata == provenance
    assert version.reference.artifact_reference is not None
    assert version.reference.artifact_reference.kind == "transformation_output"
    assert version.reference.locator == _resource(output)

    store = FileDatasetVersionStore(root=tmp_path / "versions")
    stored = store.put(version)
    assert stored.metadata == provenance
    assert store.read(stored) == version.representation

    codec = BoundaryContractCodecV2()
    assert codec.decode(codec.encode(stored)) == stored


def test_file_csv_materializer_rejects_resource_outside_allowed_root(
    tmp_path: Path,
) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("id\n1\n", encoding="utf-8")

    materializer = FileCsvDatasetVersionMaterializerV2(
        allowed_roots=(allowed,),
    )
    with pytest.raises(ValueError, match="escapes allowed roots"):
        materializer.materialize(
            ResourceDatasetVersionRequestV2(
                dataset_id="customer360.customer_mart",
                resource=_resource(outside),
                ingestion_run_id=IngestionRunId.new(),
                created_at=_NOW,
            )
        )
