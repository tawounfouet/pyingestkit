from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import (
    CheckConstraint,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
)

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
    reason="PYINGEST_TEST_POSTGRES_DSN is required for PostgreSQL UPSERT/MERGE E2E",
)


def _build_request(
    *,
    target_id: str,
    table: str,
    representation: DecodedRepresentation,
    mode: TargetLoadModeV2 = TargetLoadModeV2.APPEND,
    key_columns: tuple[str, ...] = (),
    update_columns: tuple[str, ...] = (),
    idempotent: bool = False,
) -> TargetLoadRequestV2:
    run_id = IngestionRunId.new()
    return TargetLoadRequestV2(
        target_id=target_id,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        dataset_version=DatasetVersionReference(
            dataset_id=f"dataset.{table}",
            version_id=dataset_content_fingerprint(representation),
        ),
        representation=representation,
        table=table,
        schema="public",
        mode=mode,
        key_columns=key_columns,
        update_columns=update_columns,
        idempotent=idempotent,
    )


def test_postgres_target_v2_upsert_selective_update() -> None:
    assert POSTGRES_DSN is not None
    suffix = uuid4().hex[:10]
    table_name = f"pyingest_users_{suffix}"
    target_id = f"target.users.{suffix}"
    engine = create_engine(POSTGRES_DSN, future=True)
    metadata = MetaData()
    table = Table(
        table_name,
        metadata,
        Column("id", String, primary_key=True),
        Column("name", String, nullable=False),
        Column("status", String, nullable=False),
        Column("score", Integer, nullable=False),
        schema="public",
    )
    metadata.create_all(engine)

    target = PostgresTargetV2(
        target_id=target_id,
        dsn=POSTGRES_DSN,
        default_schema="public",
    )
    try:
        # 1. Initial insert
        initial_rep = DecodedRepresentation(
            records=(
                DecodedRecord(
                    fields=(("id", "1"), ("name", "Ada"), ("status", "active"), ("score", 100))
                ),
                DecodedRecord(
                    fields=(("id", "2"), ("name", "Bob"), ("status", "pending"), ("score", 50))
                ),
            )
        )
        res_initial = target.load(
            _build_request(
                target_id=target_id,
                table=table_name,
                representation=initial_rep,
                mode=TargetLoadModeV2.APPEND,
            )
        )
        assert res_initial.status is TargetLoadStatusV2.SUCCEEDED
        assert res_initial.rows_loaded == 2

        # 2. Upsert with selective update columns (only status and score are updated, name is preserved)
        upsert_rep = DecodedRepresentation(
            records=(
                DecodedRecord(
                    fields=(
                        ("id", "2"),
                        ("name", "Bob New Name"),
                        ("status", "active"),
                        ("score", 85),
                    )
                ),
                DecodedRecord(
                    fields=(
                        ("id", "3"),
                        ("name", "Charlie"),
                        ("status", "active"),
                        ("score", 90),
                    )
                ),
            )
        )
        res_upsert = target.load(
            _build_request(
                target_id=target_id,
                table=table_name,
                representation=upsert_rep,
                mode=TargetLoadModeV2.UPSERT,
                key_columns=("id",),
                update_columns=("status", "score"),
            )
        )
        assert res_upsert.status is TargetLoadStatusV2.SUCCEEDED
        assert res_upsert.rows_loaded == 2

        # 3. Verify target table content
        with engine.connect() as conn:
            rows = conn.execute(
                select(table.c.id, table.c.name, table.c.status, table.c.score).order_by(table.c.id)
            ).all()

        assert rows == [
            ("1", "Ada", "active", 100),
            ("2", "Bob", "active", 85),  # name untouched, status and score updated!
            ("3", "Charlie", "active", 90),  # fully inserted
        ]
    finally:
        target.close()
        table.drop(engine, checkfirst=True)
        engine.dispose()


def test_postgres_target_v2_merge_composite_keys() -> None:
    assert POSTGRES_DSN is not None
    suffix = uuid4().hex[:10]
    table_name = f"pyingest_inv_{suffix}"
    target_id = f"target.inv.{suffix}"
    engine = create_engine(POSTGRES_DSN, future=True)
    metadata = MetaData()
    table = Table(
        table_name,
        metadata,
        Column("warehouse", String, primary_key=True),
        Column("item_id", String, primary_key=True),
        Column("quantity", Integer, nullable=False),
        schema="public",
    )
    metadata.create_all(engine)

    target = PostgresTargetV2(
        target_id=target_id,
        dsn=POSTGRES_DSN,
        default_schema="public",
    )
    try:
        # Seed initial records
        seed_rep = DecodedRepresentation(
            records=(
                DecodedRecord(
                    fields=(("warehouse", "WH1"), ("item_id", "ITEM1"), ("quantity", 10))
                ),
                DecodedRecord(
                    fields=(("warehouse", "WH1"), ("item_id", "ITEM2"), ("quantity", 20))
                ),
            )
        )
        target.load(
            _build_request(
                target_id=target_id,
                table=table_name,
                representation=seed_rep,
                mode=TargetLoadModeV2.APPEND,
            )
        )

        # Merge load: update WH1/ITEM2 to 25, insert WH2/ITEM3 as 50
        merge_rep = DecodedRepresentation(
            records=(
                DecodedRecord(
                    fields=(("warehouse", "WH1"), ("item_id", "ITEM2"), ("quantity", 25))
                ),
                DecodedRecord(
                    fields=(("warehouse", "WH2"), ("item_id", "ITEM3"), ("quantity", 50))
                ),
            )
        )
        res_merge = target.load(
            _build_request(
                target_id=target_id,
                table=table_name,
                representation=merge_rep,
                mode=TargetLoadModeV2.MERGE,
                key_columns=("warehouse", "item_id"),
            )
        )
        assert res_merge.status is TargetLoadStatusV2.SUCCEEDED

        with engine.connect() as conn:
            rows = conn.execute(
                select(table.c.warehouse, table.c.item_id, table.c.quantity).order_by(
                    table.c.warehouse, table.c.item_id
                )
            ).all()

        assert rows == [
            ("WH1", "ITEM1", 10),
            ("WH1", "ITEM2", 25),
            ("WH2", "ITEM3", 50),
        ]
    finally:
        target.close()
        table.drop(engine, checkfirst=True)
        engine.dispose()


def test_postgres_target_v2_idempotency_deduplication() -> None:
    assert POSTGRES_DSN is not None
    suffix = uuid4().hex[:10]
    table_name = f"pyingest_idemp_{suffix}"
    target_id = f"target.idemp.{suffix}"
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
        rep = DecodedRepresentation(
            records=(
                DecodedRecord(fields=(("id", "1"), ("name", "First"))),
                DecodedRecord(fields=(("id", "2"), ("name", "Second"))),
            )
        )
        request = _build_request(
            target_id=target_id,
            table=table_name,
            representation=rep,
            mode=TargetLoadModeV2.UPSERT,
            key_columns=("id",),
            idempotent=True,
        )

        # 1. First execution
        first_res = target.load(request)
        assert first_res.status is TargetLoadStatusV2.SUCCEEDED
        assert first_res.rows_loaded == 2
        assert any(d.code == "target.postgres.succeeded" for d in first_res.diagnostics)

        # 2. Second execution with identical dataset version & idempotent=True
        second_res = target.load(request)
        assert second_res.status is TargetLoadStatusV2.SUCCEEDED
        assert second_res.rows_loaded == 2
        assert any(d.code == "target.postgres.skipped_idempotent" for d in second_res.diagnostics)

        # 3. Check table row count remains exactly 2
        with engine.connect() as conn:
            rows = conn.execute(select(table.c.id, table.c.name).order_by(table.c.id)).all()
        assert rows == [("1", "First"), ("2", "Second")]
    finally:
        target.close()
        table.drop(engine, checkfirst=True)
        engine.dispose()


def test_postgres_target_v2_staging_rollback_on_constraint_violation() -> None:
    assert POSTGRES_DSN is not None
    suffix = uuid4().hex[:10]
    table_name = f"pyingest_chk_{suffix}"
    target_id = f"target.chk.{suffix}"
    engine = create_engine(POSTGRES_DSN, future=True)
    metadata = MetaData()
    table = Table(
        table_name,
        metadata,
        Column("id", String, primary_key=True),
        Column("balance", Integer, nullable=False),
        CheckConstraint("balance >= 0", name="chk_positive_balance"),
        schema="public",
    )
    metadata.create_all(engine)

    target = PostgresTargetV2(
        target_id=target_id,
        dsn=POSTGRES_DSN,
        default_schema="public",
    )
    try:
        # Seed initial valid record
        seed_rep = DecodedRepresentation(
            records=(DecodedRecord(fields=(("id", "1"), ("balance", 100))),)
        )
        target.load(
            _build_request(
                target_id=target_id,
                table=table_name,
                representation=seed_rep,
                mode=TargetLoadModeV2.APPEND,
            )
        )

        # Attempt an upsert with one valid update (id=1 -> 150) and one invalid insert (id=2 -> -50)
        invalid_rep = DecodedRepresentation(
            records=(
                DecodedRecord(fields=(("id", "1"), ("balance", 150))),
                DecodedRecord(fields=(("id", "2"), ("balance", -50))),
            )
        )
        res = target.load(
            _build_request(
                target_id=target_id,
                table=table_name,
                representation=invalid_rep,
                mode=TargetLoadModeV2.UPSERT,
                key_columns=("id",),
            )
        )
        assert res.status is TargetLoadStatusV2.ROLLED_BACK
        assert res.failure is not None
        assert res.failure.error_code == "target.postgres.load_rolled_back"

        # Verify table data was completely protected (id=1 still has balance 100)
        with engine.connect() as conn:
            rows = conn.execute(select(table.c.id, table.c.balance)).all()
        assert rows == [("1", 100)]
    finally:
        target.close()
        table.drop(engine, checkfirst=True)
        engine.dispose()
