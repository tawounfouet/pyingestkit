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


def test_v2_authoring_root_is_canonical_at_rc() -> None:
    assert pyingestkit.IngestionDefinition is IngestionDefinition
    assert pyingestkit.Source is Source


def test_v2_root_freeze_removes_legacy_execution_aliases() -> None:
    assert "IngestionDefinition" in pyingestkit.__all__
    assert "Source" in pyingestkit.__all__
    assert "Job" not in pyingestkit.__all__
    assert "Pipeline" not in pyingestkit.__all__
    assert "Runner" not in pyingestkit.__all__


def test_no_public_ingestion_plan_is_introduced() -> None:
    assert not hasattr(pyingestkit, "IngestionPlan")
