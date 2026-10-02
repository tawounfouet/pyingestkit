# PyIngestKit V2 — LOT-03 Acquisition Port and Local File Source

LOT-03 introduces the first complete V2 acquisition path without crossing the
LOT-04 RAW persistence boundary.

## Architecture

```text
Source
  ↓
AcquisitionRequest
  ↓
SourceRegistry
  ↓ resolves
SourceConnector
  ↓
FileSourceConnector
  ↓
bounded filesystem read
  ↓
AcquisitionResult
    ResourceReference
    exact bytes (runtime-local)
    SHA-256
    size/media evidence
    diagnostics
    FailureEvidence
```

The acquired bytes are intentionally runtime-local evidence in LOT-03. They are
not yet persisted as RAW. LOT-04 will take the exact acquired bytes and create
an immutable `ArtifactReference` through `ArtifactStore`.

## SourceConnector port

The stable V2 port is defined inward under `pyingestkit.ports.sources`:

```python
class SourceConnector(Protocol):
    @property
    def descriptor(self) -> SourceConnectorDescriptor: ...

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult: ...
```

Reconciliation is capability-driven and is not required from the local-file
connector. `FileSourceConnector` advertises only `ACQUIRE`.

## Explicit registry

`SourceRegistry` is instance-owned:

```python
registry = SourceRegistry()
registry.register(file_connector)
connector = registry.resolve(source)
```

There is no import-time connector registration or mutable global registry.

## File access policy

`FileAccessPolicy` is declarative and performs no filesystem I/O at
construction time.

It defines:

```text
allowed_roots
max_bytes
allowed_extensions
allow_symlinks
```

The adapter validates configured roots only when `acquire()` executes. It
rejects paths outside configured roots, symbolic links by default, non-regular
files, disallowed extensions, missing files and payloads larger than the
configured byte budget.

The read itself is bounded to `max_bytes + 1` so a file that changes after
`stat()` cannot bypass the size limit.

## Acquisition evidence

A successful local-file acquisition records:

- the native `IngestionRunId`;
- the caller's `CorrelationContext`;
- a credential-free `ResourceReference`;
- exact acquired bytes;
- SHA-256 checksum;
- byte length;
- MIME type when detectable;
- file name and modification-time evidence;
- structured diagnostics;
- timezone-aware acquisition timestamp.

Operational failures return `AcquisitionResult(status=FAILED)` with
`FailureEvidence` rather than requiring callers to parse exception text.

## Identity and storage boundaries

The resource ID is derived from the resolved file URI, while the checksum is
derived from file content.

```text
resource identity != content checksum
```

LOT-03 does not create:

```text
RawArtifact
ArtifactReference from persisted RAW
DatasetVersion
PublishedDataset
Target writes
```

Those remain owned by later lots.

## V1 transition

The maintained V1 `pyingestkit.sources.__all__` remains exactly:

```text
LocalSource
Source
```

Additive V2 imports are available explicitly:

```python
from pyingestkit.sources import (
    FileAccessPolicy,
    FileSourceConnector,
    SourceRegistry,
)

from pyingestkit.sources.v2 import (
    AcquisitionRequest,
    AcquisitionResult,
    Source,
    SourceConnector,
)
```

The V2 package cut will later replace the transitional `sources.v2` split.

## Qualification

LOT-03 is complete when:

- file acquisition produces structured evidence;
- checksum/size/media evidence is deterministic;
- configured filesystem roots are enforced;
- symlink and oversize negative tests pass;
- connector registration is explicit;
- construction performs no I/O;
- local-file source connector conformance passes;
- no RAW persistence occurs in the adapter;
- Python 3.11–3.14 V2 tests pass;
- V1 stable gates remain green.
