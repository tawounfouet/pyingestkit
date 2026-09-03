# PyIngestKit Demo Jobs

This directory is an independently installable job pack demonstrating the **recommended declarative API** and Python entry-point discovery.

```bash
python -m pip install -e examples/plugin_package
pyingest jobs
pyingest inspect demo.local_file
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest runs
```

The module exposes a `JobDefinition` built with `@job` / `@step`. Discovery compiles it into the imperative Job/Pipeline model before Runner execution.

Runtime values such as `path` come from `RunContext.parameters`; plugin discovery never requires execution-time constructor arguments.

The demo uses the normal `.pyingest/` workspace and does not create a separate demo workspace.
