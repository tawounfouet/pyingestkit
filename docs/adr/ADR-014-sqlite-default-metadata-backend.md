# ADR-014 — SQLite as default metadata backend

**Status:** Accepted — V0.1.5

The CLI defaults to SQLite at `<workspace>/state/pyingest.sqlite3`. SQLite is appropriate for local development, CLI, CI and single-node execution. WAL and a busy timeout are enabled.

PostgreSQL is an adapter for shared/concurrent environments, not a dependency of Runner.
