# Installation

PyIngestKit 2.0 requires Python 3.11 or newer. The stable release is qualified on Python **3.11, 3.12, 3.13 and 3.14**.

## Install PyIngestKit 2.0

The canonical stable release is **2.0.0**.

If PyIngestKit is available from your configured Python package index:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "pyingestkit==2.0.0"
```

The GitHub release also publishes the qualified wheel and source distribution with SHA-256 checksums. You can install the downloaded wheel directly:

```bash
python -m pip install ./pyingestkit-2.0.0-py3-none-any.whl
```

See the [PyIngestKit 2.0.0 release notes](../releases/v2.0.0.md) and [stable qualification](../releases/v2.0.0-qualification.md).

## Optional providers

The base 2.0 installation is provider-neutral. Install only the provider families required by your application:

```bash
python -m pip install "pyingestkit[http]==2.0.0"
python -m pip install "pyingestkit[postgres]==2.0.0"
python -m pip install "pyingestkit[s3]==2.0.0"
python -m pip install "pyingestkit[excel]==2.0.0"
python -m pip install "pyingestkit[parquet]==2.0.0"
```

The base package does not require httpx, SQLAlchemy, psycopg, boto3, OpenPyXL, PyArrow or PyTransformKit.

For the qualified support boundaries, see the [2.0 provider compatibility matrix](../reference/provider-compatibility-v2.md).

## Install from a checkout

For framework development:

```bash
git clone https://github.com/tawounfouet/pyingestkit.git
cd pyingestkit
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,http,postgres,s3,excel,parquet]"
```

## Verify the installation

Verify the stable package version and V2 root imports:

```bash
python -c "import pyingestkit; print(pyingestkit.__version__)"
python -c "from pyingestkit import IngestionDefinition, IngestionRuntime, Source; print('PyIngestKit V2 API OK')"
```

The expected stable version is:

```text
2.0.0
```

## Documentation contributors

Documentation tooling is repository tooling rather than a runtime package requirement.

```bash
python -m pip install -r docs/requirements.txt
make docs-build
```

For live preview:

```bash
make docs-serve
```

Continue with the [2.0 Quickstart](quickstart.md).

## Existing V1 applications

Do not treat 2.0 as an alias-compatible V1 upgrade. Applications still depending on `Job`, `Pipeline`, `Step`, `Runner` or the V1 operator CLI should review the [V1 → V2 migration guide](../guides/migrate-v1-to-v2.md) before upgrading.
