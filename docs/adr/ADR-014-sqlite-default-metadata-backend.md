# ADR-014 — SQLite as default metadata backend

**Status:** Accepted — V0.1.5

The CLI defaults to SQLite at `<workspace>/state/pyingest.sqlite3`. SQLite is appropriate for local development, CLI, CI and single-node execution. WAL and a busy timeout are enabled.

PostgreSQL is an adapter for shared/concurrent environments, not a dependency of Runner.

## V0.1.6 implementation update

SQLite remains the default backend, but direct `sqlite3` repository SQL is replaced by SQLAlchemy 2.x Core. The adapter keeps SQLite-specific operational settings (foreign keys, WAL, busy timeout) while sharing the persistence schema/statements with PostgreSQL.
