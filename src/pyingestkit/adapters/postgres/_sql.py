"""Safe PostgreSQL SQL statement composition for target materialization."""

from __future__ import annotations

from typing import Any

try:
    from psycopg import sql
except ModuleNotFoundError:  # pragma: no cover
    sql = None  # type: ignore[assignment]


def _qualified_table(schema: str | None, table: str) -> Any:
    if sql is None:
        raise RuntimeError("psycopg is required to build PostgreSQL SQL statements.")
    return sql.Identifier(schema, table) if schema is not None else sql.Identifier(table)


def create_temp_staging_table_sql(
    staging_table: str,
    target_schema: str | None,
    target_table: str,
) -> Any:
    """Build CREATE TEMP TABLE _stg_xxx (LIKE target INCLUDING DEFAULTS) ON COMMIT DROP."""
    if sql is None:
        raise RuntimeError("psycopg is required to build PostgreSQL SQL statements.")
    staging = sql.Identifier(staging_table)
    target = _qualified_table(target_schema, target_table)
    return sql.SQL("CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(
        staging,
        target,
    )


def build_upsert_reconciliation_sql(
    target_schema: str | None,
    target_table: str,
    staging_table: str,
    columns: tuple[str, ...],
    key_columns: tuple[str, ...],
    update_columns: tuple[str, ...],
) -> Any:
    """Build atomic INSERT INTO target SELECT ... FROM staging ON CONFLICT ..."""
    if sql is None:
        raise RuntimeError("psycopg is required to build PostgreSQL SQL statements.")

    target = _qualified_table(target_schema, target_table)
    staging = sql.Identifier(staging_table)
    col_identifiers = sql.SQL(", ").join(sql.Identifier(col) for col in columns)
    key_identifiers = sql.SQL(", ").join(sql.Identifier(key) for key in key_columns)

    if update_columns:
        updates = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col))
            for col in update_columns
        )
        conflict_clause = sql.SQL("ON CONFLICT ({}) DO UPDATE SET {}").format(
            key_identifiers,
            updates,
        )
    else:
        conflict_clause = sql.SQL("ON CONFLICT ({}) DO NOTHING").format(key_identifiers)

    return sql.SQL("INSERT INTO {} ({}) SELECT {} FROM {} {}").format(
        target,
        col_identifiers,
        col_identifiers,
        staging,
        conflict_clause,
    )


def build_merge_reconciliation_sql(
    target_schema: str | None,
    target_table: str,
    staging_table: str,
    columns: tuple[str, ...],
    key_columns: tuple[str, ...],
    update_columns: tuple[str, ...],
    server_version_num: int = 150000,
) -> Any:
    """Build MERGE statement (PG15+) or CTE fallback (PG < 15)."""
    if sql is None:
        raise RuntimeError("psycopg is required to build PostgreSQL SQL statements.")

    target = _qualified_table(target_schema, target_table)
    staging = sql.Identifier(staging_table)

    if server_version_num >= 150000:
        join_conditions = sql.SQL(" AND ").join(
            sql.SQL("target.{} = staging.{}").format(sql.Identifier(k), sql.Identifier(k))
            for k in key_columns
        )
        insert_cols = sql.SQL(", ").join(sql.Identifier(c) for c in columns)
        insert_vals = sql.SQL(", ").join(
            sql.SQL("staging.{}").format(sql.Identifier(c)) for c in columns
        )

        clauses: list[Any] = []
        if update_columns:
            update_assignments = sql.SQL(", ").join(
                sql.SQL("{} = staging.{}").format(sql.Identifier(u), sql.Identifier(u))
                for u in update_columns
            )
            clauses.append(sql.SQL("WHEN MATCHED THEN UPDATE SET {}").format(update_assignments))

        clauses.append(
            sql.SQL("WHEN NOT MATCHED THEN INSERT ({}) VALUES ({})").format(
                insert_cols, insert_vals
            )
        )

        clauses_sql = sql.SQL(" ").join(clauses)
        return sql.SQL("MERGE INTO {} AS target USING {} AS staging ON {} {}").format(
            target, staging, join_conditions, clauses_sql
        )

    # CTE Fallback for PG < 15
    first_key = sql.Identifier(key_columns[0])
    join_cond = sql.SQL(" AND ").join(
        sql.SQL("target.{} = staging.{}").format(sql.Identifier(k), sql.Identifier(k))
        for k in key_columns
    )
    col_identifiers = sql.SQL(", ").join(sql.Identifier(c) for c in columns)
    staging_cols = sql.SQL(", ").join(
        sql.SQL("staging.{}").format(sql.Identifier(c)) for c in columns
    )

    if update_columns:
        update_assignments = sql.SQL(", ").join(
            sql.SQL("{} = staging.{}").format(sql.Identifier(u), sql.Identifier(u))
            for u in update_columns
        )
        not_exists_cond = sql.SQL(" AND ").join(
            sql.SQL("updated.{} = staging.{}").format(sql.Identifier(k), sql.Identifier(k))
            for k in key_columns
        )
        return sql.SQL(
            "WITH updated AS ("
            "UPDATE {} AS target SET {} FROM {} AS staging WHERE {} RETURNING target.{}"
            ") "
            "INSERT INTO {} ({}) SELECT {} FROM {} AS staging "
            "WHERE NOT EXISTS (SELECT 1 FROM updated WHERE {})"
        ).format(
            target,
            update_assignments,
            staging,
            join_cond,
            first_key,
            target,
            col_identifiers,
            staging_cols,
            staging,
            not_exists_cond,
        )

    # If no update_columns: simple ON CONFLICT DO NOTHING
    key_identifiers = sql.SQL(", ").join(sql.Identifier(k) for k in key_columns)
    return sql.SQL("INSERT INTO {} ({}) SELECT {} FROM {} ON CONFLICT ({}) DO NOTHING").format(
        target, col_identifiers, col_identifiers, staging, key_identifiers
    )


def build_ensure_metadata_table_sql(schema: str | None = "public") -> Any:
    """Build idempotent DDL for technical audit table _pyingest_target_loads."""
    if sql is None:
        raise RuntimeError("psycopg is required to build PostgreSQL SQL statements.")

    target = _qualified_table(schema, "_pyingest_target_loads")
    index_name = sql.Identifier(f"ix_pyingest_target_loads_{schema or 'public'}_dedup"[:63])
    return sql.SQL(
        "CREATE TABLE IF NOT EXISTS {} ("
        "load_id VARCHAR(36) PRIMARY KEY, "
        "target_id VARCHAR(128) NOT NULL, "
        "destination VARCHAR(256) NOT NULL, "
        "dataset_id VARCHAR(128) NOT NULL, "
        "dataset_version_id VARCHAR(128) NOT NULL, "
        "ingestion_run_id VARCHAR(36) NOT NULL, "
        "mode VARCHAR(32) NOT NULL, "
        "rows_loaded INTEGER NOT NULL, "
        "status VARCHAR(32) NOT NULL, "
        "started_at TIMESTAMPTZ NOT NULL, "
        "completed_at TIMESTAMPTZ NOT NULL"
        "); "
        "CREATE INDEX IF NOT EXISTS {} ON {} "
        "(target_id, destination, dataset_version_id, mode);"
    ).format(target, index_name, target)


def build_check_idempotence_sql(schema: str | None = "public") -> Any:
    """Check if exact dataset version was already materialized successfully."""
    if sql is None:
        raise RuntimeError("psycopg is required to build PostgreSQL SQL statements.")

    target = _qualified_table(schema, "_pyingest_target_loads")
    return sql.SQL(
        "SELECT 1 FROM {} WHERE target_id = %s AND destination = %s "
        "AND dataset_version_id = %s AND mode = %s AND status = 'succeeded' "
        "LIMIT 1"
    ).format(target)


def build_record_target_load_sql(schema: str | None = "public") -> Any:
    """Insert audit record into _pyingest_target_loads."""
    if sql is None:
        raise RuntimeError("psycopg is required to build PostgreSQL SQL statements.")

    target = _qualified_table(schema, "_pyingest_target_loads")
    return sql.SQL(
        "INSERT INTO {} ("
        "load_id, target_id, destination, dataset_id, dataset_version_id, "
        "ingestion_run_id, mode, rows_loaded, status, started_at, completed_at"
        ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    ).format(target)
