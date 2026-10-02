from __future__ import annotations

from dataclasses import fields

import pyingestkit
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.sources import Source


def test_definition_has_no_execution_or_provider_state_fields() -> None:
    names = {field.name for field in fields(IngestionDefinition)}

    assert names.isdisjoint(
        {
            "ingestion_run_id",
            "run_id",
            "retry_attempt",
            "status",
            "workflow_run_id",
            "task_attempt_id",
            "provider_client",
            "connection",
            "session",
        }
    )


def test_source_has_no_active_resource_fields() -> None:
    names = {field.name for field in fields(Source)}

    assert names.isdisjoint(
        {
            "client",
            "connection",
            "file_handle",
            "session",
            "stream",
        }
    )


def test_v2_authoring_root_is_explicitly_importable_during_v1_transition() -> None:
    assert pyingestkit.IngestionDefinition is IngestionDefinition
    assert pyingestkit.Source is Source


def test_v2_provisional_root_does_not_change_v1_star_import_contract() -> None:
    assert "IngestionDefinition" not in pyingestkit.__all__
    assert "Source" not in pyingestkit.__all__
    assert "Job" in pyingestkit.__all__
    assert "Pipeline" in pyingestkit.__all__
