# ADR-019 — One persistence engine; Peewee rejected

**Status:** Accepted — V0.1.6

## Decision

PyIngestKit uses SQLAlchemy as its only internal relational persistence toolkit. Peewee is not added.

## Rationale

Supporting two ORMs would create duplicate abstractions, tests, dependency governance and backend behavior without adding an ingestion capability. SQLAlchemy already covers SQLite, PostgreSQL, Core SQL construction, transactions and future migration tooling.

## Consequence

A consuming application may use any ORM it wants, but PyIngestKit's own `MetadataStore` adapters use SQLAlchemy Core only.
