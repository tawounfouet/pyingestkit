# Release validation — V0.3.0

Run from a clean checkout with Python 3.11, 3.12 or 3.13 available as required by the CI matrix.

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install -e examples/plugin_package
make release-check
```

The V0.3 distribution gate must install the built framework wheel with both `excel` and `parquet` extras and execute all six reference jobs in a fresh virtual environment.

Expected job set:

```text
demo.local_file
demo.http_csv
demo.http_json
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
```

Expected quality-format evidence for NDJSON, Excel and Parquet runs:

```text
reports/validation.json
reports/profile.json
manifest.json -> reports[] references
VALIDATION_COMPLETED
PROFILE_COMPLETED
QUALITY_REPORT_WRITTEN
```

No release should be tagged if Ruff, Mypy, Bandit, pip-audit, PyArrow/OpenPyXL extras smoke, package build, or wheel smoke is skipped in the official release environment.
