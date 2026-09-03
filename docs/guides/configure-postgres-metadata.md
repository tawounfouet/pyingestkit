# Configure PostgreSQL metadata

PostgreSQL is an optional shared/concurrent MetadataStore backend. SQLAlchemy Core remains an internal implementation detail; jobs still depend only on PyIngestKit contracts.

Install the adapter dependency:

```bash
python -m pip install "pyingestkit[postgres]"
```

Expose the DSN through an environment variable rather than versioned YAML:

```bash
export PYINGEST_DATABASE_URL="postgresql://user:password@host/database"
```

Configure only the environment-variable name:

```yaml
metadata:
  backend: postgres
  postgres:
    dsn_env: PYINGEST_DATABASE_URL
```

PyIngestKit normalizes standard `postgres://` and `postgresql://` URLs to the SQLAlchemy `postgresql+psycopg://` dialect internally. Do not import SQLAlchemy sessions, tables, or engines into job code.

## Guardrails

- PostgreSQL remains a MetadataStore adapter, not a Runner dependency.
- `psycopg` remains optional via the `postgres` extra.
- credentials stay outside committed configuration.
- Peewee is not supported as a second ORM.
- Alembic remains deferred until released schema migrations require it.
