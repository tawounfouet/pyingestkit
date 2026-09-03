from __future__ import annotations

import sqlite3
import tempfile
import tomllib
import unittest
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine

from pyingestkit.metadata import MetadataStore, PostgresMetadataStore, SQLiteMetadataStore


class SQLAlchemyPersistenceTests(unittest.TestCase):
    def test_sqlite_adapter_uses_sqlalchemy_engine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteMetadataStore(Path(tmp) / "state" / "pyingest.sqlite3")
            self.assertIsInstance(store.engine, Engine)
            self.assertEqual(store.engine.dialect.name, "sqlite")

    def test_sqlite_enables_wal_and_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state" / "pyingest.sqlite3"
            store = SQLiteMetadataStore(path)
            with store.engine.connect() as connection:
                journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()
                foreign_keys = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
            self.assertEqual(str(journal_mode).lower(), "wal")
            self.assertEqual(foreign_keys, 1)

    def test_runtime_depends_on_sqlalchemy_but_not_peewee(self) -> None:
        root = Path(__file__).resolve().parents[3]
        payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        dependencies = payload["project"]["dependencies"]
        self.assertTrue(any(item.startswith("SQLAlchemy") for item in dependencies))
        self.assertFalse(any("peewee" in item.lower() for item in dependencies))

    def test_postgres_adapter_normalizes_standard_dsn(self) -> None:
        from pyingestkit.metadata.postgres import _normalize_dsn

        self.assertEqual(
            _normalize_dsn("postgresql://user:pass@db.example/app"),
            "postgresql+psycopg://user:pass@db.example/app",
        )
        self.assertEqual(
            _normalize_dsn("postgres://user:pass@db.example/app"),
            "postgresql+psycopg://user:pass@db.example/app",
        )
        self.assertTrue(issubclass(PostgresMetadataStore, MetadataStore))

    def test_sqlite_reads_v015_text_schema_without_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state" / "pyingest.sqlite3"
            path.parent.mkdir(parents=True, exist_ok=True)
            started = datetime.now(UTC).isoformat()
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    """CREATE TABLE runs (
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
                    )"""
                )
                connection.execute(
                    """INSERT INTO runs(
                        run_id, job_id, job_version, status, started_at, completed_at,
                        duration_seconds, fixture_mode, parameters_json, error, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        "legacy-run",
                        "demo.legacy",
                        "0.1.0",
                        "SUCCESS",
                        started,
                        started,
                        0.1,
                        0,
                        "{}",
                        None,
                        started,
                    ),
                )
                connection.commit()

            store = SQLiteMetadataStore(path)
            record = store.get_run("legacy-run")

            self.assertEqual(record.job_id, "demo.legacy")
            self.assertEqual(record.status, "SUCCESS")
            self.assertIsInstance(record.started_at, datetime)
            self.assertEqual(record.started_at.utcoffset(), UTC.utcoffset(record.started_at))


if __name__ == "__main__":
    unittest.main()
