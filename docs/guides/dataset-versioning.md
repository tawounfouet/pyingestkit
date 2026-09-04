# Dataset snapshots, versions and publication

V0.4.0-b1 adds a content-addressed Dataset history without changing the Dataset API.

```python
from pyingestkit import FilesystemDatasetVersionStore

store = FilesystemDatasetVersionStore(".pyingest")
version = store.create_version(dataset, dataset_id="public.postal_codes", created_from_run_id=run_id, job_id="public.postal_codes", job_version="1.0.0")
published = store.publish(version, run_id=run_id)
restored = store.load_dataset(version)
```

Workspace:

```text
.pyingest/versions/<namespace>/<dataset>/sha256-.../{dataset.snapshot.json,version.json}
.pyingest/published/<namespace>/<dataset>/current.json
```

Snapshots contain real source values and must be protected as data. They are never logs or release assets.
