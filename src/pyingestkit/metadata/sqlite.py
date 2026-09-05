from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine
from sqlalchemy.pool import NullPool

from pyingestkit.artifacts.raw import RawArtifact

from ._artifact_locations import enrich_artifact_locations, record_artifact_location
from ._sqlalchemy import _SQLAlchemyMetadataStore
from ._target_loads import SQLAlchemyTargetLoadMetadataMixin
from .models import ArtifactRecord


class SQLiteMetadataStore(SQLAlchemyTargetLoadMetadataMixin, _SQLAlchemyMetadataStore):
    """SQLite-backed metadata adapter using SQLAlchemy Core.

    SQLite remains the default for local/single-node execution. The adapter
    enables foreign keys, WAL mode, and a bounded busy timeout while keeping
    SQLAlchemy completely internal to the persistence layer.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        engine = self._create_engine(self.path)
        super().__init__(engine)

    @classmethod
    def for_workspace(cls, workspace: str | Path) -> SQLiteMetadataStore:
        return cls(Path(workspace) / "state" / "pyingest.sqlite3")

    @staticmethod
    def _create_engine(path: Path) -> Engine:
        engine = create_engine(
            URL.create("sqlite", database=str(path.resolve())),
            future=True,
            connect_args={"timeout": 5.0},
            poolclass=NullPool,
        )

        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys = ON")
                cursor.execute("PRAGMA busy_timeout = 5000")
            finally:
                cursor.close()

        return engine

    def record_artifact(self, run_id: str, artifact: RawArtifact, *, kind: str = "raw") -> None:
        _SQLAlchemyMetadataStore.record_artifact(self, run_id, artifact, kind=kind)
        record_artifact_location(self.engine, artifact)

    def list_artifacts(self, run_id: str) -> tuple[ArtifactRecord, ...]:
        records = _SQLAlchemyMetadataStore.list_artifacts(self, run_id)
        return enrich_artifact_locations(self.engine, records)

    def initialize(self) -> None:
        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode = WAL")
        super().initialize()
