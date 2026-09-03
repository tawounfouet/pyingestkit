from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.context import RunContext
from pyingestkit.core.events import Event
from pyingestkit.core.result import RunResult, StepResult
from pyingestkit.logging.filters import redact_mapping

from .base import MetadataStore
from .models import ArtifactRecord, EventRecord, PublicationRecord, RunRecord, StepRecord, ValidationRecord

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    job_version TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_seconds REAL,
    fixture_mode INTEGER NOT NULL,
    parameters_json TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_job_started ON runs(job_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_status_started ON runs(status, started_at DESC);

CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    error TEXT,
    metrics_json TEXT NOT NULL,
    UNIQUE(run_id, position)
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    content_type TEXT,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(run_id);

CREATE TABLE IF NOT EXISTS validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    rule TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    dataset_id TEXT NOT NULL,
    status TEXT NOT NULL,
    candidate_path TEXT,
    published_path TEXT,
    published_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    job_id TEXT NOT NULL,
    step TEXT,
    event_type TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_run_timestamp ON events(run_id, timestamp);
"""


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _required_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _event_level(event: Event) -> str:
    return "ERROR" if event.type.value.endswith("FAILED") else "INFO"


class SQLiteMetadataStore(MetadataStore):
    """SQLite-backed runtime metadata store for local and single-node usage."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.initialize()

    @classmethod
    def for_workspace(cls, workspace: str | Path) -> "SQLiteMetadataStore":
        return cls(Path(workspace) / "state" / "pyingest.sqlite3")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(_SCHEMA)
            connection.commit()
        finally:
            connection.close()

    def start_run(self, context: RunContext) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO runs(
                    run_id, job_id, job_version, status, started_at, completed_at,
                    duration_seconds, fixture_mode, parameters_json, error, created_at
                ) VALUES (?, ?, ?, 'RUNNING', ?, NULL, NULL, ?, ?, NULL, ?)""",
                (
                    str(context.run_id),
                    context.job_id,
                    context.job_version,
                    _iso(context.started_at),
                    int(context.fixture_mode),
                    _json(redact_mapping(dict(context.parameters))),
                    _iso(datetime.now(timezone.utc)),
                ),
            )

    def finish_run(self, result: RunResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """UPDATE runs
                   SET status=?, completed_at=?, duration_seconds=?, error=?
                   WHERE run_id=?""",
                (
                    result.status.value,
                    _iso(result.completed_at),
                    result.duration_seconds,
                    result.error,
                    result.run_id,
                ),
            )

    def record_step(self, run_id: str, position: int, result: StepResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO steps(
                    id, run_id, position, step_name, status, started_at, completed_at,
                    duration_seconds, error, metrics_json
                ) VALUES (
                    (SELECT id FROM steps WHERE run_id=? AND position=?),
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )""",
                (
                    run_id,
                    position,
                    run_id,
                    position,
                    result.step_name,
                    result.status.value,
                    _iso(result.started_at),
                    _iso(result.completed_at),
                    result.duration_seconds,
                    result.error,
                    _json(result.metrics),
                ),
            )

    def record_artifact(self, run_id: str, artifact: RawArtifact, *, kind: str = "raw") -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO artifacts(
                    artifact_id, run_id, kind, path, source_uri, content_type,
                    size_bytes, sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    artifact.artifact_id,
                    run_id,
                    kind,
                    artifact.path,
                    artifact.source_uri,
                    artifact.content_type,
                    artifact.size_bytes,
                    artifact.sha256,
                    _iso(artifact.retrieved_at),
                ),
            )

    def record_event(self, event: Event) -> None:
        step = event.payload.get("step")
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO events(
                    run_id, job_id, step, event_type, level, message, timestamp, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.run_id,
                    event.job_id,
                    str(step) if step else None,
                    event.type.value,
                    _event_level(event),
                    event.type.value.replace("_", " ").title(),
                    _iso(event.timestamp),
                    _json(redact_mapping(dict(event.payload))),
                ),
            )


    def record_validation(self, run_id: str, *, rule: str, severity: str, status: str, message: str, metadata: dict[str, object] | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO validations(run_id, rule, severity, status, message, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (run_id, rule, severity, status, message, _json(redact_mapping(dict(metadata or {})))),
            )

    def record_publication(self, run_id: str, *, dataset_id: str, status: str, candidate_path: str | None = None, published_path: str | None = None, published_at: datetime | None = None) -> None:
        timestamp = published_at.isoformat() if published_at is not None else None
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO publications(run_id, dataset_id, status, candidate_path, published_path, published_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (run_id, dataset_id, status, candidate_path, published_path, timestamp),
            )

    def list_runs(self, *, job_id: str | None = None, status: str | None = None, limit: int = 50) -> tuple[RunRecord, ...]:
        safe_limit = max(1, limit)
        with self._connect() as connection:
            if job_id is not None and status is not None:
                rows = connection.execute(
                    "SELECT * FROM runs WHERE job_id = ? AND status = ? ORDER BY started_at DESC LIMIT ?",
                    (job_id, status.upper(), safe_limit),
                ).fetchall()
            elif job_id is not None:
                rows = connection.execute(
                    "SELECT * FROM runs WHERE job_id = ? ORDER BY started_at DESC LIMIT ?",
                    (job_id, safe_limit),
                ).fetchall()
            elif status is not None:
                rows = connection.execute(
                    "SELECT * FROM runs WHERE status = ? ORDER BY started_at DESC LIMIT ?",
                    (status.upper(), safe_limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?",
                    (safe_limit,),
                ).fetchall()
        return tuple(self._run_record(row) for row in rows)

    def get_run(self, run_id_or_prefix: str) -> RunRecord:
        with self._connect() as connection:
            exact = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id_or_prefix,)
            ).fetchone()
            if exact is not None:
                return self._run_record(exact)
            rows = connection.execute(
                "SELECT * FROM runs WHERE run_id LIKE ? ORDER BY started_at DESC LIMIT 2",
                (f"{run_id_or_prefix}%",),
            ).fetchall()
        if not rows:
            raise KeyError(run_id_or_prefix)
        if len(rows) > 1:
            raise ValueError(f"Ambiguous run ID prefix: {run_id_or_prefix}")
        return self._run_record(rows[0])

    def list_steps(self, run_id: str) -> tuple[StepRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM steps WHERE run_id=? ORDER BY position", (run_id,)
            ).fetchall()
        return tuple(
            StepRecord(
                id=row["id"],
                run_id=row["run_id"],
                position=row["position"],
                step_name=row["step_name"],
                status=row["status"],
                started_at=_required_dt(row["started_at"]),
                completed_at=_required_dt(row["completed_at"]),
                duration_seconds=row["duration_seconds"],
                error=row["error"],
                metrics=json.loads(row["metrics_json"]),
            )
            for row in rows
        )

    def list_artifacts(self, run_id: str) -> tuple[ArtifactRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE run_id=? ORDER BY created_at", (run_id,)
            ).fetchall()
        return tuple(
            ArtifactRecord(
                artifact_id=row["artifact_id"],
                run_id=row["run_id"],
                kind=row["kind"],
                path=row["path"],
                source_uri=row["source_uri"],
                content_type=row["content_type"],
                size_bytes=row["size_bytes"],
                sha256=row["sha256"],
                created_at=_required_dt(row["created_at"]),
            )
            for row in rows
        )

    def list_events(self, run_id: str) -> tuple[EventRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE run_id=? ORDER BY id", (run_id,)
            ).fetchall()
        return tuple(
            EventRecord(
                id=row["id"],
                run_id=row["run_id"],
                job_id=row["job_id"],
                step=row["step"],
                event_type=row["event_type"],
                level=row["level"],
                message=row["message"],
                timestamp=_required_dt(row["timestamp"]),
                metadata=json.loads(row["metadata_json"]),
            )
            for row in rows
        )


    def list_validations(self, run_id: str) -> tuple[ValidationRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM validations WHERE run_id=? ORDER BY id", (run_id,)
            ).fetchall()
        return tuple(
            ValidationRecord(
                id=row["id"], run_id=row["run_id"], rule=row["rule"],
                severity=row["severity"], status=row["status"], message=row["message"],
                metadata=json.loads(row["metadata_json"]),
            )
            for row in rows
        )

    def list_publications(self, run_id: str) -> tuple[PublicationRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM publications WHERE run_id=? ORDER BY id", (run_id,)
            ).fetchall()
        return tuple(
            PublicationRecord(
                id=row["id"], run_id=row["run_id"], dataset_id=row["dataset_id"],
                status=row["status"], candidate_path=row["candidate_path"],
                published_path=row["published_path"], published_at=_dt(row["published_at"]),
            )
            for row in rows
        )

    @staticmethod
    def _run_record(row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"],
            job_id=row["job_id"],
            job_version=row["job_version"],
            status=row["status"],
            started_at=_required_dt(row["started_at"]),
            completed_at=_dt(row["completed_at"]),
            duration_seconds=row["duration_seconds"],
            fixture_mode=bool(row["fixture_mode"]),
            parameters=json.loads(row["parameters_json"]),
            error=row["error"],
            created_at=_required_dt(row["created_at"]),
        )
