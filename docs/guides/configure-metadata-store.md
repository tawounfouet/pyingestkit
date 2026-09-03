# Configure MetadataStore

`MetadataStore` is the queryable runtime-state contract. SQLAlchemy 2.x Core is internal and does not appear in job APIs.

## SQLite — default

```yaml
metadata:
  backend: sqlite
  sqlite:
    path: null
```

With `path: null`, the database resolves to `<workspace>/state/pyingest.sqlite3`. The adapter enables SQLite foreign keys, WAL journal mode and a bounded busy timeout.

An explicit path remains possible:

```yaml
metadata:
  backend: sqlite
  sqlite:
    path: .state/custom-pyingest.sqlite3
```

## PostgreSQL — optional

PostgreSQL uses a DSN environment variable; never version credentials in YAML. See [Configure PostgreSQL metadata](configure-postgres-metadata.md).

```yaml
metadata:
  backend: postgres
  postgres:
    dsn_env: PYINGEST_DATABASE_URL
```

## Persistence boundary

The database stores runs, steps, artifact metadata, validations, publications and structural events. RAW payloads, manifests, reports and published datasets remain owned by `ArtifactStore`.
