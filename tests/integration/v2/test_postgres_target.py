from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import Column, MetaData, String, Table, create_engine, select

from pyingestkit.adapters.postgres import PostgresTargetV2
from pyingestkit.datasets import DatasetVersionReference, dataset_content_fingerprint
from pyingestkit.domain.decoding import DecodedRecord, DecodedRepresentation
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.targets import (
    TargetLoadModeV2,
    TargetLoadRequestV2,
    TargetLoadStatusV2,
)

POSTGRES_DSN = os.getenv("PYINGEST_TEST_POSTGRES_DSN")

pytestmark = pytest.mark.skipif(
    not POSTGRES_DSN,
    reason="PYINGEST_TEST_POSTGRES_DSN is required for PostgreSQL V2 target E2E",
)


def _representation(*rows: tuple[str, str]) -> DecodedRepresentation:
    return DecodedRepresentation(
        records=tuple(
            DecodedRecord(fields=(("id", row[0]), ("name", row[1])))
            for row in rows
        )
    )


def _request(
    *,
    target_id: str,
    table: str,
    representation: DecodedRepresentation,
    mode: TargetLoadModeV2 = TargetLoadModeV2.APPEND,
) -> TargetLoadRequestV2:
    run_id = IngestionRunId.new()
    return TargetLoadRequestV2(
        target_id=target_id,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        dataset_version=DatasetVersionReference(
            dataset_id="demo.postgres_people",
            version_id=dataset_content_fingerprint(representation),
        ),
        representation=representation,
        table=table,
        schema="public",
        mode=mode,
    )


def _rows(engine, table: str) -> list[tuple[str, str]]:
    destination = Table(
        table,
        MetaData(),
        schema="public",
        autoload_with=engine,
    )
    with engine.connect() as connection:
        values = connection.execute(
            select(destination.c.id, destination.c.name).order_by(destination.c.id)
        ).all()
    return [(str(row[0]), str(row[1])) for row in values]


def test_postgres_target_v2_copy_modes_and_constraint_rollback() -> None:
    assert POSTGRES_DSN is not None
    suffix = uuid4().hex[:10]
    table_name = f"pyingestkit_v2_{suffix}"
    target_id = f"postgres.v2.{suffix}"
    engine = create_engine(POSTGRES_DSN, future=True)
    metadata = MetaData()
    table = Table(
        table_name,
        metadata,
        Column("id", String, primary_key=True),
        Column("name", String, nullable=False),
        schema="public",
    )
    metadata.create_all(engine)

    target = PostgresTargetV2(
        target_id=target_id,
        dsn=POSTGRES_DSN,
        default_schema="public",
    )
    try:
        first = target.load(
            _request(
                target_id=target_id,
                table=table_name,
                representation=_representation(("1", "Ada"), ("2", "Linus")),
            )
        )
        assert first.status is TargetLoadStatusV2.SUCCEEDED
        assert first.rows_loaded == 2
        assert _rows(engine, table_name) == [("1", "Ada"), ("2", "Linus")]

        duplicate = target.load(
            _request(
                target_id=target_id,
                table=table_name,
                representation=_representation(("2", "Duplicate")),
            )
        )
        assert duplicate.status is TargetLoadStatusV2.ROLLED_BACK
        assert duplicate.rows_loaded == 0
        assert duplicate.failure is not None
        assert duplicate.failure.error_code == "target.postgres.load_rolled_back"
        assert _rows(engine, table_name) == [("1", "Ada"), ("2", "Linus")]

        replaced = target.load(
            _request(
                target_id=target_id,
                table=table_name,
                representation=_representation(("3", "Grace")),
                mode=TargetLoadModeV2.REPLACE,
            )
        )
        assert replaced.status is TargetLoadStatusV2.SUCCEEDED
        assert _rows(engine, table_name) == [("3", "Grace")]

        truncated = target.load(
            _request(
                target_id=target_id,
                table=table_name,
                representation=_representation(("4", "Margaret")),
                mode=TargetLoadModeV2.TRUNCATE_LOAD,
            )
        )
        assert truncated.status is TargetLoadStatusV2.SUCCEEDED
        assert _rows(engine, table_name) == [("4", "Margaret")]
    finally:
        target.close()
        table.drop(engine, checkfirst=True)
        engine.dispose()


def test_postgres_target_v2_schema_mismatch_precedes_replace_mutation() -> None:
    assert POSTGRES_DSN is not None
    suffix = uuid4().hex[:10]
    table_name = f"pyingestkit_v2_schema_{suffix}"
    target_id = f"postgres.v2.schema.{suffix}"
    engine = create_engine(POSTGRES_DSN, future=True)
    metadata = MetaData()
    table = Table(
        table_name,
        metadata,
        Column("id", String, primary_key=True),
        Column("name", String, nullable=False),
        schema="public",
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(table.insert(), [{"id": "seed", "name": "Existing"}])

    target = PostgresTargetV2(
        target_id=target_id,
        dsn=POSTGRES_DSN,
        default_schema="public",
    )
    try:
        nested = DecodedRepresentation(
            records=(
                DecodedRecord(
                    fields=(
                        ("id", "new"),
                        ("name", "Ada"),
                        ("extra", "not-in-table"),
                    )
                ),
            )
        )
        result = target.load(
            _request(
                target_id=target_id,
                table=table_name,
                representation=nested,
                mode=TargetLoadModeV2.REPLACE,
            )
        )

        assert result.status is TargetLoadStatusV2.FAILED
        assert result.rows_loaded == 0
        assert result.failure is not None
        assert result.failure.error_code == "target.postgres.schema_mismatch"
        assert _rows(engine, table_name) == [("seed", "Existing")]
    finally:
        target.close()
        table.drop(engine, checkfirst=True)
        engine.dispose()
