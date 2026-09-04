# ADR-032 — Parquet is an optional materializing parser adapter

## Status
Accepted — V0.3.0-rc1.

## Decision
Parquet support is implemented by `ParquetParser` using PyArrow from the optional `parquet` extra. PyArrow is loaded lazily and is not a mandatory framework dependency. The parser materializes rows into the existing dependency-neutral `Dataset`.

`columns` is a structural projection option. `max_rows` is an explicit safety guard checked from Parquet metadata before row materialization.

## Consequences
- the V0.3 Dataset contract remains stable across CSV, JSON, NDJSON, Excel and Parquet;
- large-file streaming is not pretended: V0.3 Parquet parsing is explicitly in-memory;
- future buffered/streaming dataset work can evolve behind a separate contract without turning Dataset into a PyArrow table;
- Pandas and Polars remain absent from the framework core.
