from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("pytransformkit")
pytest.importorskip("pandas")
pytest.importorskip("polars")
pytest.importorskip("pyarrow")

from examples.customer_360.app import read_customer_mart, run_customer_360
from pyingestkit.boundaries.v2 import IngestionRunId
from pyingestkit.datasets import ResourceDatasetVersionRequestV2
from pyingestkit.resources import ResourceReference

_NOW = datetime(2026, 10, 3, 16, 0, tzinfo=UTC)


def _normalized_rows(workspace: Path, engine_id: str) -> list[dict[str, object]]:
    evidence = run_customer_360(workspace=workspace, engine_id=engine_id)
    values: list[dict[str, object]] = []
    for record in read_customer_mart(evidence).records:
        row = dict(record.fields)
        count = row["paid_order_count"]
        revenue = row["paid_revenue"]
        row["paid_order_count"] = None if count == "" else int(str(count))
        row["paid_revenue"] = None if revenue == "" else float(str(revenue))
        values.append(row)
    return values


def test_customer360_happy_path_preserves_versions_provenance_and_replay(
    tmp_path: Path,
) -> None:
    evidence = run_customer_360(
        workspace=tmp_path / "pandas",
        engine_id="pandas",
    )

    assert evidence.customers.published_dataset is not None
    assert evidence.orders.published_dataset is not None
    assert evidence.customers.dataset_version is not None
    assert evidence.orders.dataset_version is not None
    assert evidence.customers.raw_artifact is not None
    assert evidence.orders.raw_artifact is not None

    provenance = evidence.provenance
    assert provenance["source.customers.artifact_id"] == (
        evidence.customers.raw_artifact.artifact_id
    )
    assert provenance["source.customers.version_id"] == (
        evidence.customers.dataset_version.version_id
    )
    assert provenance["source.orders.artifact_id"] == (evidence.orders.raw_artifact.artifact_id)
    assert provenance["source.orders.version_id"] == (evidence.orders.dataset_version.version_id)
    assert provenance["transformation.execution_id"] == (evidence.transformation_execution_id)
    assert provenance["transformation.plan_fingerprint"] == (
        evidence.transformation_plan_fingerprint
    )
    assert provenance["transformation.engine_id"] == "pandas"

    assert evidence.customer_mart_version.locator is not None
    assert evidence.transformation_resource.locator is not None
    assert evidence.customer_mart_version.locator.locator != (
        evidence.transformation_resource.locator
    )
    assert evidence.customer_mart_version.locator.media_type == "application/json"
    assert evidence.transformation_resource.media_type == "text/csv"

    assert evidence.replay.matched is True
    assert evidence.replay.replay_run_id != evidence.replay.source_run_id
    assert evidence.replay.ingestion.dataset_version is not None
    assert evidence.replay.expected_dataset_version is not None
    assert evidence.replay.ingestion.dataset_version.identity == (
        evidence.replay.expected_dataset_version.identity
    )

    assert evidence.customers.run.correlation.correlation_id == evidence.correlation_id
    assert evidence.orders.run.correlation.correlation_id == evidence.correlation_id


def test_customer360_pandas_and_polars_produce_equivalent_governed_output(
    tmp_path: Path,
) -> None:
    pandas_rows = _normalized_rows(tmp_path / "pandas", "pandas")
    polars_rows = _normalized_rows(tmp_path / "polars", "polars")

    expected = [
        {
            "customer_id": "1",
            "customer_name": "Alice",
            "country": "FR",
            "normalized_email": "alice@example.com",
            "paid_order_count": 2,
            "paid_revenue": 15.5,
        },
        {
            "customer_id": "2",
            "customer_name": "Björk",
            "country": "IS",
            "normalized_email": "bjork@example.com",
            "paid_order_count": 1,
            "paid_revenue": 20.0,
        },
        {
            "customer_id": "3",
            "customer_name": "Chloé",
            "country": "FR",
            "normalized_email": "",
            "paid_order_count": None,
            "paid_revenue": None,
        },
    ]
    assert pandas_rows == expected
    assert polars_rows == expected


def test_customer360_publication_provenance_rejects_credential_like_metadata(
    tmp_path: Path,
) -> None:
    resource = ResourceReference(
        namespace="customer360.transform",
        resource_id="unsafe",
        locator=(tmp_path / "customer_mart.csv").resolve().as_uri(),
        media_type="text/csv",
        format="csv",
    )

    with pytest.raises(ValueError, match="credential-like"):
        ResourceDatasetVersionRequestV2(
            dataset_id="customer360.customer_mart",
            resource=resource,
            ingestion_run_id=IngestionRunId.new(),
            created_at=_NOW,
            provenance=(("api_key", "synthetic-secret"),),
        )
