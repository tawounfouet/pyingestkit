# ADR-032 — Parquet is an optional materializing parser adapter

## Status

Accepted — V0.3.0-b2.

## Decision

`ParquetParser` is backed by PyArrow through the optional `parquet` extra and converts the selected Parquet table to ordinary Python row mappings before constructing the framework `Dataset`.

PyArrow remains lazy and optional. The parser supports structural column projection and an explicit `max_rows` pre-materialization guard using Parquet metadata.

V0.3 does not expose `pyarrow.Table` as a core contract and does not claim streaming semantics.
