# NDJSON and Excel parsing

## NDJSON

`NdjsonParser` decodes one JSON object per non-empty line and returns the neutral framework `Dataset`.

```python
from pyingestkit.parsers import NdjsonParser

parser = NdjsonParser(skip_blank_lines=True)
dataset = parser.parse(raw)
```

JSON native values are preserved. The parser does not trim, rename, flatten, enrich or coerce business values. Malformed lines are reported with a line number without embedding the full source line in the exception.

## Excel / XLSX

Install the optional adapter:

```bash
pip install "pyingestkit[excel]"
```

Then:

```python
from pyingestkit.parsers import ExcelParser

parser = ExcelParser(sheet_name="Codes", header_row=1)
dataset = parser.parse(raw)
```

`sheet_name` accepts a worksheet name or zero-based worksheet index. `header_row` is one-based. OpenPyXL is used lazily in read-only mode by default and native cell values are preserved. Completely empty rows (`all cells is None`) are skipped by default.

Duplicate, empty or non-string headers are rejected as ambiguous structure. PyIngestKit does not calculate Excel formulas; `data_only=True` reads cached values available in the input workbook.
