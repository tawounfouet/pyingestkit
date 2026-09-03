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
