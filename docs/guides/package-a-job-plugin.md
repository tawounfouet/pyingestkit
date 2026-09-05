# Package a job plugin

PyIngestKit keeps business ingestion jobs outside the framework distribution. External job packs are
normal Python packages discovered through the stable V1 entry-point group:

```text
pyingestkit.jobs
```

## 1. Create a package

A minimal layout is:

```text
my-ingestion-jobs/
├── pyproject.toml
└── src/
    └── my_ingestion_jobs/
        ├── __init__.py
        └── customers.py
```

Example `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-ingestion-jobs"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = ["pyingestkit>=1,<2"]

[project.entry-points."pyingestkit.jobs"]
customers = "my_ingestion_jobs.customers:job_definition"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
```

While V1.0.0 is still in B2/RC1 qualification, use a source/editable dependency or the currently
published compatible package version rather than declaring a PyPI range for a release that does not
exist yet. The `pyingestkit>=1,<2` example above represents the intended post-V1 stable consumer
constraint.

## 2. Define a declarative job

```python
from pyingestkit import RunContext, job, step


@step(name="FetchCustomers")
def fetch_customers(context: RunContext):
    ...


@step(name="ValidateCustomers")
def validate_customers(data):
    ...


@job(
    id="acme.customers",
    version="1.0.0",
    description="Ingest the customer reference dataset.",
)
def customers_job() -> None:
    fetch_customers()
    validate_customers()


job_definition = customers_job
```

The entry point should expose a definition or object that can be loaded without runtime constructor
arguments. Execution-time values belong in `RunContext.parameters` or validated project
configuration.

## 3. Accepted entry-point values

V1 accepts:

- `JobDefinition`;
- a `Job` instance;
- a `Job` subclass with a zero-argument constructor;
- a zero-argument factory returning `Job` or `JobDefinition`.

The declarative `JobDefinition` form is recommended for new job packs.

## 4. Install and verify discovery

```bash
python -m pip install -e .
pyingest jobs
pyingest inspect acme.customers
```

Every installed logical `job.id` must be unique across the environment. Discovery order is
deterministic by `(entry_point.name, entry_point.value)`. If two installed packages expose the same
logical job ID, the first deterministic entry point is retained and the later duplicate is reported
as a plugin failure.

Do not use duplicate IDs as an override mechanism.

## 5. Strict library discovery vs tolerant CLI discovery

Library callers can use:

```python
from pyingestkit.plugins import discover_jobs

jobs = discover_jobs()
```

`discover_jobs()` is strict by default: if any installed plugin fails to load, it raises a controlled
`PluginError`.

Operator-facing registry helpers are tolerant so one unrelated broken third-party package does not
hide healthy installed jobs:

```python
from pyingestkit.plugins import load_registry_with_diagnostics

registry, failures = load_registry_with_diagnostics()
```

Use the diagnostics when building custom operator tooling.

## 6. Declare backend requirements

A job that genuinely requires a backend should say so at definition time rather than failing deep in a
step. For example, a production slice may require S3-compatible artifacts and PostgreSQL metadata.

The runner validates declared requirements against active configuration before executing the pipeline.
This keeps dev/staging/prod mismatches fail-fast.

Do not declare a stronger requirement than the job actually needs; local filesystem/SQLite remain
first-class backends.

## 7. Keep credentials out of the job package

Plugin source and YAML configuration should contain logical configuration and names of environment
variables, not access keys, passwords or tokens.

Use provider-standard credential chains and the deployment secret manager. Log through Python's
standard `logging` package and rely on PyIngestKit's configured application boundary for handlers and
redaction.

## 8. Test the plugin as a package

At minimum, test:

1. the distribution declares the expected `pyingestkit.jobs` entry point;
2. importing/discovering the plugin has no execution side effects;
3. `job.id`, job version and pipeline order are intentional;
4. fixture/offline mode can exercise core logic deterministically;
5. backend requirements reject incompatible configuration before execution;
6. one broken optional integration does not corrupt unrelated job definitions;
7. the job runs against the oldest and newest Python versions supported by your package policy.

The repository's `examples/plugin_package` is the maintained reference implementation.

## 9. Versioning and compatibility

Treat these as public contracts of your own job pack:

- distribution name and entry-point name;
- logical `job.id`;
- externally documented runtime parameters;
- persisted dataset identity used by versioning/publication;
- output/target schemas consumed downstream.

Changing a Python package version does not automatically justify changing logical dataset identity.
Use explicit migration/deprecation guidance when downstream consumers are affected.

## 10. Framework boundary

A plugin may fetch, parse, validate, normalize and publish data through PyIngestKit. It should not turn
PyIngestKit into a scheduler or hide infrastructure provisioning inside the job definition.

External orchestration owns **when** the job runs. PyIngestKit owns **how** the ingestion execution is
made reliable and traceable.

See:

- `docs/architecture/plugin-model.md`;
- `docs/reference/stability-v1.md`;
- `docs/reference/pilots-v1.md`;
- `examples/plugin_package/README.md`.
