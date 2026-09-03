# ADR-021 — Defer Alembic until schema compatibility requires migrations

**Status:** Accepted — V0.1.6

## Decision

PyIngestKit does **not** introduce Alembic during the V0.1.x Foundation.
SQLAlchemy metadata tables remain the source of truth for creating a fresh metadata database, while V0.1.6 preserves compatibility with the existing V0.1.5 SQLite schema where practical.

Alembic becomes justified only when PyIngestKit must evolve an already released metadata schema in place while preserving user data across versions.

## Rationale

Adding SQLAlchemy does not automatically justify adding a migration framework. At this stage:

- the product is still pre-1.0;
- the relational metadata model is small and internal;
- V0.1.6 can read the V0.1.5 SQLite schema without a migration step;
- introducing migration scripts, revision governance and upgrade/downgrade testing now would increase Foundation complexity without solving a demonstrated production requirement.

## Trigger for reconsideration

Revisit this ADR when at least one released schema change requires one of the following:

- adding or changing columns while preserving existing run history;
- changing constraints or indexes in place;
- migrating persisted data values;
- coordinating schema upgrades for a shared PostgreSQL metadata database.

At that point, Alembic is the preferred migration candidate because SQLAlchemy is already the persistence engine.

## Guardrails

- Do not implement ad-hoc versioned `ALTER TABLE` chains in application code as a substitute for a migration strategy.
- Do not expose SQLAlchemy or migration mechanics through the job API.
- Keep schema evolution inside the metadata adapter boundary.
