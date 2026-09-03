from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine
from sqlalchemy.pool import NullPool

from ._schema import metadata
from ._sqlalchemy import _SQLAlchemyMetadataStore


class SQLiteMetadataStore(_SQLAlchemyMetadataStore):
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

    def initialize(self) -> None:
        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode = WAL")
        metadata.create_all(self.engine)
