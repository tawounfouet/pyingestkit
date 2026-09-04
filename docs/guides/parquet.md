# Parquet parsing — V0.3.0-rc1

Install the optional backend:

```bash
pip install "pyingestkit[parquet]"
```

Then parse a RAW artifact:

```python
from pyingestkit import ParquetParser

dataset = ParquetParser(columns=("id", "name"), max_rows=1_000_000).parse(raw_artifact)
```

V0.3 materializes Parquet rows into the neutral in-memory `Dataset`. `max_rows` is therefore recommended for untrusted or potentially very large inputs. No business coercion or dataframe semantics are introduced.
