# PyIngestKit Demo Jobs

This directory is an independently installable job pack demonstrating the **recommended declarative API** and Python entry-point discovery.

```bash
python -m pip install -e examples/plugin_package
pyingest jobs
pyingest inspect demo.local_file
pyingest inspect demo.http_csv
pyingest inspect demo.http_json
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
pyingest runs
```

The pack exposes six `JobDefinition` entry points built with `@job` / `@step`. The three V0.2 reference jobs remain stable, and V0.3 adds NDJSON, Excel, and Parquet quality-format slices. Discovery compiles each definition into the imperative Job/Pipeline model before Runner execution.

Runtime values such as `path` come from `RunContext.parameters`; plugin discovery never requires execution-time constructor arguments.

The demo uses the normal `.pyingest/` workspace and does not create a separate demo workspace.

## V0.3 RC1 quality-format jobs

With the framework Excel and Parquet extras installed, this pack exposes six jobs:

```text
demo.local_file
demo.http_csv
demo.http_json
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
```

The quality-format jobs use `demo-quality.yml` and deterministic fixture generation. They are intended as executable end-to-end contracts, not production data sources.
