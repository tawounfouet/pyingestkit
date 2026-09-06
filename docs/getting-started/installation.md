# Installation

PyIngestKit requires Python 3.11 or newer. Python 3.11, 3.12 and 3.13 are qualified by the project CI.

## Stable V1.0.0 release

The stable release is published on GitHub with a wheel, source distribution, demo-package artifacts and SHA-256 checksums.

Install the framework wheel after downloading it from the [V1.0.0 release](https://github.com/tawounfouet/pyingestkit/releases/tag/v1.0.0):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ./pyingestkit-1.0.0-py3-none-any.whl
```

Optional provider dependencies are deliberately separated from the runtime core. Install only what your ingestion needs:

```bash
python -m pip install "pyingestkit[s3]"
python -m pip install "pyingestkit[postgres]"
python -m pip install "pyingestkit[excel]"
python -m pip install "pyingestkit[parquet]"
```

If you install from a local checkout instead of a release wheel, the same extras are available with editable installs:

```bash
python -m pip install -e ".[s3,postgres,excel,parquet]"
```

## Demo jobs

The maintained demo package is distributed separately because production ingestion jobs are plugins rather than framework internals.

From a checkout:

```bash
python -m pip install -e examples/plugin_package
pyingest jobs
```

## Documentation contributors

Documentation tooling is isolated in the `docs` optional extra and is not part of PyIngestKit runtime dependencies:

```bash
python -m pip install -e ".[docs]"
make docs-build
```

For live preview while editing:

```bash
make docs-serve
```

## Verify the installation

```bash
pyingest --version
pyingest config
```

The stable V1 contract is documented in [Stable 1.x contract](../reference/stable-contract-v1.md).
