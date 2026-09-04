# Parquet parsing

Install the optional adapter:

```bash
pip install "pyingestkit[parquet]"
```

Use the parser like the other structural adapters:

```python
from pyingestkit.parsers import ParquetParser

parser = ParquetParser(columns=("id", "name"), max_rows=1_000_000)
dataset = parser.parse(raw)
```

PyArrow is imported only when parsing. The Arrow table is an internal decoding representation and is converted to the framework's dependency-neutral `Dataset`.

`columns` performs structural projection. `max_rows` reads Parquet metadata first and raises `ParseError` before table materialization when the artifact exceeds the configured V0.3 in-memory boundary.

V0.3 deliberately does not promise streaming Parquet ingestion into the core Dataset. Large-data job packs may use an explicit Arrow/Polars/DuckDB path after RAW capture when materialization would be inappropriate.
