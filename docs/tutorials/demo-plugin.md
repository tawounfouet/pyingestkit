# Tutorial — Install and run the demo job pack

PyIngestKit itself contains no business jobs. The repository ships a separate example distribution under `examples/plugin_package`.

## 1. Install the framework

```bash
python -m pip install -e .
```

At this point `pyingest jobs` may legitimately return no jobs.

## 2. Install the demo job pack

```bash
python -m pip install -e examples/plugin_package
```

The package declares:

```toml
[project.entry-points."pyingestkit.jobs"]
demo-local-file = "pyingestkit_demo_jobs.local_file:job"
```

## 3. Discover and inspect

```bash
pyingest jobs
pyingest inspect demo.local_file
```

## 4. Execute through YAML

```bash
pyingest run demo.local_file --config examples/plugin_package/demo.yml
```

## 5. Execute through runtime parameters

```bash
pyingest run demo.local_file \
  --param path=examples/plugin_package/data/sample.txt
```

The job is instantiated with zero arguments. The source path is resolved at execution time from `RunContext.parameters`.
