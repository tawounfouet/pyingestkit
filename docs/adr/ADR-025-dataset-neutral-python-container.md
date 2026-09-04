# ADR-025 — Dataset is a dependency-neutral Python container

## Status

Accepted — V0.2.0 Beta 1.

## Context

PyIngestKit needs a structured representation between RAW parsing and validation. Binding this boundary to Pandas, Polars, or Arrow would impose a heavyweight analytical dependency and leak one ecosystem's semantics into every job pack.

## Decision

PyIngestKit owns a small `Dataset` type built from ordinary Python mappings plus an ordered field schema. The core package does not depend on Pandas, Polars, or Arrow.

`Dataset` is not intended to replace those libraries. It is the framework interchange contract at the ingestion boundary. Job packs may explicitly convert it to another representation after parsing when useful.

## Consequences

- the framework has a stable and lightweight structured-data contract;
- parsers and contracts can operate without dataframe-engine coupling;
- downstream jobs retain freedom to use Pandas, Polars, Arrow, SQLAlchemy rows, or domain models;
- dataframe-specific operations do not enter the framework API by accident.
