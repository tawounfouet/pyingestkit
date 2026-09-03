# Tutorial — Install and run the declarative demo job pack

PyIngestKit contains no business jobs. The repository ships a separate job-pack distribution under `examples/plugin_package`.

```bash
python -m pip install -e .
python -m pip install -e examples/plugin_package
```

The package exposes a `JobDefinition`:

```toml
[project.entry-points."pyingestkit.jobs"]
demo-local-file = "pyingestkit_demo_jobs.local_file:job_definition"
```

The implementation uses `@step` and `@job`; discovery compiles it to the imperative model before Runner execution.

```bash
pyingest jobs
pyingest inspect demo.local_file
pyingest run demo.local_file --config examples/plugin_package/demo.yml
pyingest runs
pyingest status <run-id-prefix>
```

The demo uses the same default `.pyingest/` workspace as the framework; it does not create `.pyingest-demo/`.
