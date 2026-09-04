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

The pack exposes three `JobDefinition` entry points built with `@job` / `@step`: `demo.local_file`, `demo.http_csv`, and `demo.http_json`. Discovery compiles it into the imperative Job/Pipeline model before Runner execution.

Runtime values such as `path` come from `RunContext.parameters`; plugin discovery never requires execution-time constructor arguments.

The demo uses the normal `.pyingest/` workspace and does not create a separate demo workspace.
