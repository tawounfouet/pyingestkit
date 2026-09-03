# ADR-018 — SQLAlchemy 2.x as metadata persistence engine

**Status:** Accepted — V0.1.6

## Decision

Use SQLAlchemy 2.x Core as the single internal persistence engine behind `MetadataStore` implementations.

`SQLiteMetadataStore` and `PostgresMetadataStore` share SQLAlchemy table definitions and statement construction while retaining backend-specific engine configuration.

## Rationale

The V0.1.5 direct-SQL implementation duplicated persistence logic and produced Bandit B608 findings around dynamically assembled PostgreSQL SELECT statements. SQLAlchemy Core provides bound parameters, dialect portability, transactions and a migration-compatible foundation without leaking ORM concepts into ingestion jobs.

## Guardrails

- no SQLAlchemy classes in the top-level PyIngestKit API;
- no SQLAlchemy declarative ORM requirement for domain records;
- `Runner` depends only on `MetadataStore`;
- ArtifactStore responsibilities remain separate.
