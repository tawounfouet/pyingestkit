# PyIngestKit 2.x Quickstart

This quickstart exercises the canonical 2.x root API:

```text
IngestionDefinition + IngestionRuntime.run(...)
```

It intentionally does not use the historical V1 Job/Pipeline/Step operator flow.

## 1. Install 2.1

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "pyingestkit==2.1.0"
```

## 2. Create a small source file

Create `customers.csv`:

```csv
customer_id,name
1,Ada
2,Grace
```

## 3. Build the runtime

Create `ingest.py`:

```python
from pathlib import Path

from pyingestkit import IngestionDefinition, IngestionRuntime, Source
from pyingestkit.adapters.filesystem import FileArtifactStore, FileSourceConnector
from pyingestkit.application.decoders import DecoderRegistry
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.decoders import CsvDecoder
from pyingestkit.stores import FileDatasetVersionStore


root = Path("./.pyingest-v2")

sources = SourceRegistry([FileSourceConnector()])
decoders = DecoderRegistry([CsvDecoder()])

runtime = IngestionRuntime(
    sources=sources,
    decoders=decoders,
    artifacts=FileArtifactStore(root=root / "artifacts"),
    versions=FileDatasetVersionStore(root=root / "datasets"),
)

definition = IngestionDefinition(
    name="customers",
    source=Source.file(path="./customers.csv"),
    decoder="csv",
    dataset="customers",
)

result = runtime.run(definition)
print(result.status)
```

## 4. Run the ingestion

```bash
python ingest.py
```

The runtime acquires the local file, preserves durable RAW evidence, decodes the CSV and creates the governed V2 ingestion result through the same stable runtime entry point qualified for 2.1.0.

## 5. Understand the lifecycle

The quickstart follows the stable V2 lifecycle:

```text
Source
  ↓
SourceConnector.acquire(...)
  ↓
durable RAW ArtifactReference
  ↓
Decoder
  ↓
validation / quality evidence
  ↓
immutable DatasetVersion
  ↓
DatasetVersionReference
  ├── explicit publication
  ├── explicit target materialization
  └── strict replay / verification
```

Publication and target materialization are explicit operations. Replay starts from preserved evidence and does not silently reacquire the original source.

## 6. Add providers only when needed

The base installation remains provider-neutral. Qualified optional provider families include:

```bash
python -m pip install "pyingestkit[http]==2.1.0"
python -m pip install "pyingestkit[postgres]==2.1.0"
python -m pip install "pyingestkit[s3]==2.1.0"
python -m pip install "pyingestkit[excel]==2.1.0"
python -m pip install "pyingestkit[parquet]==2.1.0"
```

See the [2.x provider compatibility matrix](../reference/provider-compatibility-v2.md) for the evidence-backed support boundaries.

## Next steps

- Read the [architecture overview](../architecture/overview.md).
- Review the [2.1.0 release notes](../releases/v2.1.0.md).
- Review the [stable qualification](../releases/v2.1.0-qualification.md).
- If you operate a V1 application, follow the [V1 → V2 migration guide](../guides/migrate-v1-to-v2.md).
