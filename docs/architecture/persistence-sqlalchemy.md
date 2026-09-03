# Metadata persistence with SQLAlchemy 2.x

PyIngestKit V0.1.6 uses **SQLAlchemy Core** as the single internal persistence engine for queryable runtime metadata.

## Boundary

`MetadataStore` remains the framework contract. The runtime never imports a concrete SQLite/PostgreSQL driver and user jobs do not receive SQLAlchemy sessions or models.

```text
Runner / CLI
    ↓
MetadataStore
    ↓
internal SQLAlchemy Core repository
   ├── SQLiteMetadataStore
   └── PostgresMetadataStore
```

The persistent schema covers `runs`, `steps`, `artifacts`, `validations`, `publications`, and structural `events`. RAW payloads, reports and published datasets remain under `ArtifactStore`.

## SQLite

SQLite is the default local/single-node backend. The adapter enables foreign keys, WAL journal mode and a bounded busy timeout. A `NullPool` is used so short-lived CLI/test processes do not retain SQLite file descriptors.

## PostgreSQL

PostgreSQL uses the same SQLAlchemy Core schema/statements and the `psycopg` SQLAlchemy dialect. `psycopg` remains optional through `pyingestkit[postgres]`. DSNs are sourced through a configured environment-variable name.

## Guardrails

- SQLAlchemy is not exported from `pyingestkit` top-level API.
- domain metadata records remain plain dataclasses;
- Peewee is not introduced as a second ORM;
- hand-built dynamic SQL is avoided;
- Alembic is deferred until real schema migrations across released versions require it.
