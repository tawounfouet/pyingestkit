# ADR-033 — V0.3 keeps Dataset materialized and preserves a future streaming boundary

## Status
Accepted — V0.3.0-rc1.

## Context
V0.3 adds NDJSON, Excel and Parquet adapters. Parquet in particular can represent datasets much larger than the dependency-neutral in-memory `Dataset` introduced in V0.2. Replacing `Dataset` with a PyArrow/Pandas/Polars object in V0.3 would leak a backend into the public framework contract and destabilize all parsers and quality components.

## Decision
V0.3 remains explicitly materialized. Every structural parser returns `Dataset`. `ParquetParser.max_rows` is a defensive pre-materialization guard, not a streaming implementation. The public contracts introduced in V0.3 do not promise arbitrary-size ingestion.

Future buffered or streaming representations may be introduced behind distinct contracts without changing the meaning of the V0.3 `Dataset` type.

## Consequences
- CSV, JSON, NDJSON, Excel and Parquet share one neutral interchange contract;
- Pandas, Polars and PyArrow tables do not become framework-level Dataset semantics;
- callers can reason about V0.3 memory behavior explicitly;
- V0.4 diff/replay work can build on a stable materialized contract while later versions retain room for streaming abstractions.
