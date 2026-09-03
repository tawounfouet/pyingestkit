from __future__ import annotations

import importlib
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.context import RunContext
from pyingestkit.core.events import Event
from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.core.result import RunResult, StepResult
from pyingestkit.logging.filters import redact_mapping

from .base import MetadataStore
from .models import ArtifactRecord, EventRecord, PublicationRecord, RunRecord, StepRecord, ValidationRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pyingest_runs (
    run_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    job_version TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_seconds DOUBLE PRECISION,
    fixture_mode BOOLEAN NOT NULL,
    parameters_json JSONB NOT NULL,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pyingest_runs_job_started ON pyingest_runs(job_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pyingest_runs_status_started ON pyingest_runs(status, started_at DESC);

CREATE TABLE IF NOT EXISTS pyingest_steps (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pyingest_runs(run_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    duration_seconds DOUBLE PRECISION NOT NULL,
    error TEXT,
    metrics_json JSONB NOT NULL,
    UNIQUE(run_id, position)
);

CREATE TABLE IF NOT EXISTS pyingest_artifacts (
    artifact_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pyingest_runs(run_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS pyingest_validations (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pyingest_runs(run_id) ON DELETE CASCADE,
    rule TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS pyingest_publications (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pyingest_runs(run_id) ON DELETE CASCADE,
    dataset_id TEXT NOT NULL,
    status TEXT NOT NULL,
    candidate_path TEXT,
    published_path TEXT,
    published_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS pyingest_events (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pyingest_runs(run_id) ON DELETE CASCADE,
    job_id TEXT NOT NULL,
    step TEXT,
    event_type TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    metadata_json JSONB NOT NULL
);
"""


def _event_level(event: Event) -> str:
    return "ERROR" if event.type.value.endswith("FAILED") else "INFO"


class PostgresMetadataStore(MetadataStore):
    """Optional PostgreSQL adapter implementing the same MetadataStore contract.

    Psycopg is imported lazily so PostgreSQL remains an optional deployment
    capability. Install it with ``pip install pyingestkit[postgres]``.
    """

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ConfigurationError("PostgreSQL MetadataStore requires a non-empty DSN")
        self.dsn = dsn
        self.initialize()

    def _psycopg(self) -> Any:
        try:
            return importlib.import_module("psycopg")
        except ImportError as exc:
            raise ConfigurationError(
                "PostgreSQL metadata backend requires psycopg. "
                "Install PyIngestKit with the 'postgres' extra."
            ) from exc

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        psycopg = self._psycopg()
        with psycopg.connect(self.dsn) as connection:
            yield connection

    def initialize(self) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            for statement in _SCHEMA.split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)

    def start_run(self, context: RunContext) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pyingest_runs(
                    run_id, job_id, job_version, status, started_at, fixture_mode,
                    parameters_json, created_at
                ) VALUES (%s,%s,%s,'RUNNING',%s,%s,%s::jsonb,%s)""",
                (
                    str(context.run_id), context.job_id, context.job_version, context.started_at,
                    context.fixture_mode,
                    json.dumps(redact_mapping(dict(context.parameters)), default=str),
                    datetime.now(timezone.utc),
                ),
            )

    def finish_run(self, result: RunResult) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE pyingest_runs SET status=%s, completed_at=%s,
                   duration_seconds=%s, error=%s WHERE run_id=%s""",
                (result.status.value, result.completed_at, result.duration_seconds, result.error, result.run_id),
            )

    def record_step(self, run_id: str, position: int, result: StepResult) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pyingest_steps(
                    run_id, position, step_name, status, started_at, completed_at,
                    duration_seconds, error, metrics_json
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT(run_id, position) DO UPDATE SET
                    step_name=EXCLUDED.step_name, status=EXCLUDED.status,
                    started_at=EXCLUDED.started_at, completed_at=EXCLUDED.completed_at,
                    duration_seconds=EXCLUDED.duration_seconds, error=EXCLUDED.error,
                    metrics_json=EXCLUDED.metrics_json""",
                (
                    run_id, position, result.step_name, result.status.value, result.started_at,
                    result.completed_at, result.duration_seconds, result.error,
                    json.dumps(result.metrics, default=str),
                ),
            )

    def record_artifact(self, run_id: str, artifact: RawArtifact, *, kind: str = "raw") -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pyingest_artifacts(
                    artifact_id, run_id, kind, path, source_uri, content_type,
                    size_bytes, sha256, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(artifact_id) DO NOTHING""",
                (
                    artifact.artifact_id, run_id, kind, artifact.path, artifact.source_uri,
                    artifact.content_type, artifact.size_bytes, artifact.sha256, artifact.retrieved_at,
                ),
            )

    def record_event(self, event: Event) -> None:
        step = event.payload.get("step")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pyingest_events(
                    run_id, job_id, step, event_type, level, message, timestamp, metadata_json
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                (
                    event.run_id, event.job_id, str(step) if step else None, event.type.value,
                    _event_level(event), event.type.value.replace("_", " ").title(),
                    event.timestamp, json.dumps(redact_mapping(dict(event.payload)), default=str),
                ),
            )


    def record_validation(self, run_id: str, *, rule: str, severity: str, status: str, message: str, metadata: dict[str, object] | None = None) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pyingest_validations(run_id, rule, severity, status, message, metadata_json)
                   VALUES (%s,%s,%s,%s,%s,%s::jsonb)""",
                (run_id, rule, severity, status, message, json.dumps(redact_mapping(dict(metadata or {})), default=str)),
            )

    def record_publication(self, run_id: str, *, dataset_id: str, status: str, candidate_path: str | None = None, published_path: str | None = None, published_at: datetime | None = None) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pyingest_publications(run_id, dataset_id, status, candidate_path, published_path, published_at)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (run_id, dataset_id, status, candidate_path, published_path, published_at),
            )

    def list_runs(self, *, job_id: str | None = None, status: str | None = None, limit: int = 50) -> tuple[RunRecord, ...]:
        safe_limit = max(1, limit)
        columns = (
            "run_id,job_id,job_version,status,started_at,completed_at,duration_seconds,"
            "fixture_mode,parameters_json,error,created_at"
        )
        with self._connect() as connection, connection.cursor() as cursor:
            if job_id is not None and status is not None:
                cursor.execute(
                    f"SELECT {columns} FROM pyingest_runs WHERE job_id=%s AND status=%s "
                    "ORDER BY started_at DESC LIMIT %s",
                    (job_id, status.upper(), safe_limit),
                )
            elif job_id is not None:
                cursor.execute(
                    f"SELECT {columns} FROM pyingest_runs WHERE job_id=%s ORDER BY started_at DESC LIMIT %s",
                    (job_id, safe_limit),
                )
            elif status is not None:
                cursor.execute(
                    f"SELECT {columns} FROM pyingest_runs WHERE status=%s ORDER BY started_at DESC LIMIT %s",
                    (status.upper(), safe_limit),
                )
            else:
                cursor.execute(
                    f"SELECT {columns} FROM pyingest_runs ORDER BY started_at DESC LIMIT %s",
                    (safe_limit,),
                )
            rows = cursor.fetchall()
        return tuple(self._run_record(row) for row in rows)

    def get_run(self, run_id_or_prefix: str) -> RunRecord:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_id,job_id,job_version,status,started_at,completed_at,duration_seconds,fixture_mode,parameters_json,error,created_at FROM pyingest_runs WHERE run_id=%s",
                (run_id_or_prefix,),
            )
            row = cursor.fetchone()
            if row:
                return self._run_record(row)
            cursor.execute(
                "SELECT run_id,job_id,job_version,status,started_at,completed_at,duration_seconds,fixture_mode,parameters_json,error,created_at FROM pyingest_runs WHERE run_id LIKE %s ORDER BY started_at DESC LIMIT 2",
                (f"{run_id_or_prefix}%",),
            )
            rows = cursor.fetchall()
        if not rows:
            raise KeyError(run_id_or_prefix)
        if len(rows) > 1:
            raise ValueError(f"Ambiguous run ID prefix: {run_id_or_prefix}")
        return self._run_record(rows[0])

    def list_steps(self, run_id: str) -> tuple[StepRecord, ...]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,run_id,position,step_name,status,started_at,completed_at,duration_seconds,error,metrics_json FROM pyingest_steps WHERE run_id=%s ORDER BY position",
                (run_id,),
            )
            rows = cursor.fetchall()
        return tuple(StepRecord(*row) for row in rows)

    def list_artifacts(self, run_id: str) -> tuple[ArtifactRecord, ...]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT artifact_id,run_id,kind,path,source_uri,content_type,size_bytes,sha256,created_at FROM pyingest_artifacts WHERE run_id=%s ORDER BY created_at",
                (run_id,),
            )
            rows = cursor.fetchall()
        return tuple(ArtifactRecord(*row) for row in rows)

    def list_events(self, run_id: str) -> tuple[EventRecord, ...]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,run_id,job_id,step,event_type,level,message,timestamp,metadata_json FROM pyingest_events WHERE run_id=%s ORDER BY id",
                (run_id,),
            )
            rows = cursor.fetchall()
        return tuple(EventRecord(*row) for row in rows)


    def list_validations(self, run_id: str) -> tuple[ValidationRecord, ...]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,run_id,rule,severity,status,message,metadata_json FROM pyingest_validations WHERE run_id=%s ORDER BY id",
                (run_id,),
            )
            rows = cursor.fetchall()
        return tuple(ValidationRecord(*row) for row in rows)

    def list_publications(self, run_id: str) -> tuple[PublicationRecord, ...]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,run_id,dataset_id,status,candidate_path,published_path,published_at FROM pyingest_publications WHERE run_id=%s ORDER BY id",
                (run_id,),
            )
            rows = cursor.fetchall()
        return tuple(PublicationRecord(*row) for row in rows)

    @staticmethod
    def _run_record(row: tuple[Any, ...]) -> RunRecord:
        parameters = row[8]
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
        return RunRecord(
            run_id=row[0], job_id=row[1], job_version=row[2], status=row[3],
            started_at=row[4], completed_at=row[5], duration_seconds=row[6],
            fixture_mode=bool(row[7]), parameters=dict(parameters), error=row[9], created_at=row[10],
        )
