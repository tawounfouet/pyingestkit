from __future__ import annotations

from pyingestkit.adapters.postgres._sql import (
    build_check_idempotence_sql,
    build_ensure_metadata_table_sql,
    build_merge_reconciliation_sql,
    build_record_target_load_sql,
    build_upsert_reconciliation_sql,
    create_temp_staging_table_sql,
)


def test_create_temp_staging_table_sql_rendering() -> None:
    query = create_temp_staging_table_sql("_stg_temp_123", "public", "orders")
    rendered = query.as_string(None)
    assert rendered == (
        'CREATE TEMP TABLE "_stg_temp_123" '
        '(LIKE "public"."orders" INCLUDING DEFAULTS) ON COMMIT DROP'
    )


def test_create_temp_staging_table_sql_without_schema() -> None:
    query = create_temp_staging_table_sql("_stg_temp_123", None, "orders")
    rendered = query.as_string(None)
    assert rendered == (
        'CREATE TEMP TABLE "_stg_temp_123" (LIKE "orders" INCLUDING DEFAULTS) ON COMMIT DROP'
    )


def test_build_upsert_reconciliation_with_updates() -> None:
    query = build_upsert_reconciliation_sql(
        target_schema="public",
        target_table="users",
        staging_table="_stg_users",
        columns=("id", "email", "name"),
        key_columns=("id",),
        update_columns=("email", "name"),
    )
    rendered = query.as_string(None)
    assert rendered == (
        'INSERT INTO "public"."users" ("id", "email", "name") '
        'SELECT "id", "email", "name" FROM "_stg_users" '
        'ON CONFLICT ("id") DO UPDATE SET "email" = EXCLUDED."email", "name" = EXCLUDED."name"'
    )


def test_build_upsert_reconciliation_do_nothing() -> None:
    query = build_upsert_reconciliation_sql(
        target_schema=None,
        target_table="tags",
        staging_table="_stg_tags",
        columns=("tag_id",),
        key_columns=("tag_id",),
        update_columns=(),
    )
    rendered = query.as_string(None)
    assert rendered == (
        'INSERT INTO "tags" ("tag_id") '
        'SELECT "tag_id" FROM "_stg_tags" '
        'ON CONFLICT ("tag_id") DO NOTHING'
    )


def test_build_merge_reconciliation_pg15_native() -> None:
    query = build_merge_reconciliation_sql(
        target_schema="analytics",
        target_table="metrics",
        staging_table="_stg_metrics",
        columns=("date", "metric_id", "value"),
        key_columns=("date", "metric_id"),
        update_columns=("value",),
        server_version_num=150002,
    )
    rendered = query.as_string(None)
    assert rendered == (
        'MERGE INTO "analytics"."metrics" AS target '
        'USING "_stg_metrics" AS staging '
        'ON target."date" = staging."date" AND target."metric_id" = staging."metric_id" '
        'WHEN MATCHED THEN UPDATE SET "value" = staging."value" '
        'WHEN NOT MATCHED THEN INSERT ("date", "metric_id", "value") '
        'VALUES (staging."date", staging."metric_id", staging."value")'
    )


def test_build_merge_reconciliation_pg14_cte_fallback() -> None:
    query = build_merge_reconciliation_sql(
        target_schema="analytics",
        target_table="metrics",
        staging_table="_stg_metrics",
        columns=("date", "metric_id", "value"),
        key_columns=("date", "metric_id"),
        update_columns=("value",),
        server_version_num=140005,
    )
    rendered = query.as_string(None)
    assert rendered == (
        "WITH updated AS ("
        'UPDATE "analytics"."metrics" AS target SET "value" = staging."value" '
        'FROM "_stg_metrics" AS staging '
        'WHERE target."date" = staging."date" AND target."metric_id" = staging."metric_id" '
        'RETURNING target."date"'
        ") "
        'INSERT INTO "analytics"."metrics" ("date", "metric_id", "value") '
        'SELECT staging."date", staging."metric_id", staging."value" FROM "_stg_metrics" AS staging '
        "WHERE NOT EXISTS (SELECT 1 FROM updated "
        'WHERE updated."date" = staging."date" AND updated."metric_id" = staging."metric_id")'
    )


def test_build_ensure_metadata_table_sql() -> None:
    query = build_ensure_metadata_table_sql("public")
    rendered = query.as_string(None)
    assert 'CREATE TABLE IF NOT EXISTS "public"."_pyingest_target_loads"' in rendered
    assert 'CREATE INDEX IF NOT EXISTS "ix_pyingest_target_loads_public_dedup"' in rendered
    assert "(target_id, destination, dataset_version_id, mode)" in rendered


def test_build_check_idempotence_and_record_sql() -> None:
    check_query = build_check_idempotence_sql("public")
    check_rendered = check_query.as_string(None)
    assert 'SELECT 1 FROM "public"."_pyingest_target_loads"' in check_rendered
    assert "dataset_version_id = %s" in check_rendered

    record_query = build_record_target_load_sql("public")
    record_rendered = record_query.as_string(None)
    assert 'INSERT INTO "public"."_pyingest_target_loads"' in record_rendered
