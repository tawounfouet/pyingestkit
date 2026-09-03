# PyIngestKit Demo Jobs

This directory is a real installable Python job pack used to demonstrate PyIngestKit plugin discovery through Python entry points.

## Install

From the PyIngestKit repository root, after installing PyIngestKit itself:

```bash
python -m pip install -e examples/plugin_package
```

Then verify discovery:

```bash
pyingest jobs
pyingest inspect demo.local_file
```

Run with the provided YAML configuration:

```bash
pyingest run demo.local_file --config examples/plugin_package/demo.yml
```

Or provide the source file directly from the CLI:

```bash
pyingest run demo.local_file \
  --param path=examples/plugin_package/data/sample.txt
```

The job reads its `path` value from `RunContext.parameters`, so the plugin can be instantiated with zero arguments as required by the entry-point contract.
