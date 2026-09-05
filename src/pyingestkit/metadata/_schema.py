from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)

from ._types import UTCDateTime

metadata = MetaData()

runs = Table(
    "runs",
    metadata,
    Column("run_id", String, primary_key=True),
    Column("job_id", String, nullable=False),
    Column("job_version", String, nullable=False),
    Column("status", String, nullable=False),
    Column("started_at", UTCDateTime(), nullable=False),
    Column("completed_at", UTCDateTime()),
    Column("duration_seconds", Float),
    Column("fixture_mode", Boolean, nullable=False),
    Column("parameters_json", JSON, nullable=False),
    Column("error", Text),
    Column("created_at", UTCDateTime(), nullable=False),
)
Index("idx_runs_job_started", runs.c.job_id, runs.c.started_at.desc())
Index("idx_runs_status_started", runs.c.status, runs.c.started_at.desc())

steps = Table(
    "steps",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False),
    Column("position", Integer, nullable=False),
    Column("step_name", String, nullable=False),
    Column("status", String, nullable=False),
    Column("started_at", UTCDateTime(), nullable=False),
    Column("completed_at", UTCDateTime(), nullable=False),
    Column("duration_seconds", Float, nullable=False),
    Column("error", Text),
    Column("metrics_json", JSON, nullable=False),
    UniqueConstraint("run_id", "position", name="uq_steps_run_position"),
)

artifacts = Table(
    "artifacts",
    metadata,
    Column("artifact_id", String, primary_key=True),
    Column("run_id", String, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False),
    Column("kind", String, nullable=False),
    Column("path", Text, nullable=False),
    Column("source_uri", Text, nullable=False),
    Column("content_type", String),
    Column("size_bytes", Integer, nullable=False),
    Column("sha256", String, nullable=False),
    Column("created_at", UTCDateTime(), nullable=False),
)
Index("idx_artifacts_run", artifacts.c.run_id)

artifact_locations = Table(
    "artifact_locations",
    metadata,
    Column(
        "artifact_id",
        String,
        ForeignKey("artifacts.artifact_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("storage_uri", Text, nullable=False),
    Column("local_path", Text),
)
Index("idx_artifact_locations_uri", artifact_locations.c.storage_uri)

artifact_http_provenance = Table(
    "artifact_http_provenance",
    metadata,
    Column(
        "artifact_id",
        String,
        ForeignKey("artifacts.artifact_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("resolved_url", Text),
    Column("status_code", Integer, nullable=False),
    Column("etag", Text),
    Column("last_modified", Text),
)

validations = Table(
    "validations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False),
    Column("rule", String, nullable=False),
    Column("severity", String, nullable=False),
    Column("status", String, nullable=False),
    Column("message", Text, nullable=False),
    Column("metadata_json", JSON, nullable=False),
)

publications = Table(
    "publications",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False),
    Column("dataset_id", String, nullable=False),
    Column("status", String, nullable=False),
    Column("candidate_path", Text),
    Column("published_path", Text),
    Column("published_at", UTCDateTime()),
)

events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False),
    Column("job_id", String, nullable=False),
    Column("step", String),
    Column("event_type", String, nullable=False),
    Column("level", String, nullable=False),
    Column("message", Text, nullable=False),
    Column("timestamp", UTCDateTime(), nullable=False),
    Column("metadata_json", JSON, nullable=False),
)
Index("idx_events_run_timestamp", events.c.run_id, events.c.timestamp)


dataset_diffs = Table(
    "dataset_diffs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False),
    Column("step_name", String, nullable=False),
    Column("dataset_id", String, nullable=False),
    Column("previous_version_id", String, nullable=False),
    Column("candidate_fingerprint", String, nullable=False),
    Column("added_count", Integer, nullable=False),
    Column("removed_count", Integer, nullable=False),
    Column("changed_count", Integer, nullable=False),
    Column("unchanged_count", Integer, nullable=False),
    Column("entries_truncated", Boolean, nullable=False),
    Column("report_path", Text, nullable=False),
    Column("created_at", UTCDateTime(), nullable=False),
)
Index("idx_dataset_diffs_run", dataset_diffs.c.run_id)
Index(
    "idx_dataset_diffs_dataset_created",
    dataset_diffs.c.dataset_id,
    dataset_diffs.c.created_at.desc(),
)


dataset_versions = Table(
    "dataset_versions",
    metadata,
    Column("dataset_id", String, primary_key=True),
    Column("version_id", String, primary_key=True),
    Column("fingerprint", String, nullable=False),
    Column("snapshot_uri", Text, nullable=False),
    Column("created_from_run_id", String, nullable=False),
    Column("job_id", String, nullable=False),
    Column("job_version", String, nullable=False),
    Column("source_artifact_id", String),
    Column("source_raw_sha256", String),
    Column("created_at", UTCDateTime(), nullable=False),
)
Index(
    "idx_dataset_versions_dataset_created",
    dataset_versions.c.dataset_id,
    dataset_versions.c.created_at.desc(),
)

dataset_version_runs = Table(
    "dataset_version_runs",
    metadata,
    Column("dataset_id", String, primary_key=True),
    Column("version_id", String, primary_key=True),
    Column("run_id", String, primary_key=True),
    Column("created_at", UTCDateTime(), nullable=False),
)
Index("idx_dataset_version_runs_run", dataset_version_runs.c.run_id)

published_datasets = Table(
    "published_datasets",
    metadata,
    Column("dataset_id", String, primary_key=True),
    Column("version_id", String, nullable=False),
    Column("published_from_run_id", String, nullable=False),
    Column("published_at", UTCDateTime(), nullable=False),
)


target_loads = Table(
    "target_loads",
    metadata,
    Column("load_id", String, primary_key=True),
    Column("run_id", String, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False),
    Column("target_id", String, nullable=False),
    Column("dataset_id", String, nullable=False),
    Column("dataset_version_id", String),
    Column("mode", String, nullable=False),
    Column("status", String, nullable=False),
    Column("destination", Text, nullable=False),
    Column("rows_input", Integer, nullable=False),
    Column("rows_loaded", Integer, nullable=False),
    Column("rows_verified", Integer),
    Column("started_at", UTCDateTime(), nullable=False),
    Column("completed_at", UTCDateTime()),
    Column("duration_seconds", Float),
    Column("idempotency_action", String),
    Column("metrics_json", JSON, nullable=False),
    Column("error", Text),
    Column("created_at", UTCDateTime(), nullable=False),
)
Index("idx_target_loads_run_started", target_loads.c.run_id, target_loads.c.started_at.desc())
Index(
    "idx_target_loads_dataset_started",
    target_loads.c.dataset_id,
    target_loads.c.started_at.desc(),
)
Index(
    "idx_target_loads_target_destination_started",
    target_loads.c.target_id,
    target_loads.c.destination,
    target_loads.c.started_at.desc(),
)
Index("idx_target_loads_status_started", target_loads.c.status, target_loads.c.started_at.desc())


replay_runs = Table(
    "replay_runs",
    metadata,
    Column("run_id", String, primary_key=True),
    Column("source_run_id", String, nullable=False),
    Column("source_job_id", String, nullable=False),
    Column("source_job_version", String, nullable=False),
    Column("executed_job_version", String, nullable=False),
    Column("verification_mode", String, nullable=False),
    Column("expected_fingerprint", String),
    Column("actual_fingerprint", String),
    Column("status", String, nullable=False),
    Column("created_at", UTCDateTime(), nullable=False),
)
Index("idx_replay_runs_source", replay_runs.c.source_run_id)

run_reproducibility = Table(
    "run_reproducibility",
    metadata,
    Column("run_id", String, primary_key=True),
    Column("framework_version", String, nullable=False),
    Column("as_of", String),
    Column("parameters_fingerprint", String, nullable=False),
    Column("created_at", UTCDateTime(), nullable=False),
)
