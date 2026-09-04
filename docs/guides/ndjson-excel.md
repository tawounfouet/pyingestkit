# NDJSON and Excel parsing — V0.3.0-b1

```python
from pyingestkit import ExcelParser, NdjsonParser

ndjson = NdjsonParser().parse(raw_artifact)
excel = ExcelParser(sheet="Data", header_row=1).parse(raw_artifact)
```

Install Excel support with `pip install "pyingestkit[excel]"`. Both parsers are structural only and return the same `Dataset` contract used by CSV/JSON.
