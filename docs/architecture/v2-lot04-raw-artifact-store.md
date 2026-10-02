# PyIngestKit V2 — LOT-04 RAW, ArtifactReference and FileArtifactStore

LOT-04 closes the first durable-evidence boundary of the V2 ingestion path.

## Flow

```text
Source
  ↓
SourceConnector
  ↓
AcquisitionResult
    exact bytes
    source ResourceReference
    SHA-256
  ↓
PutArtifactRequest.from_acquisition(...)
  ↓
ArtifactStore
  ↓
FileArtifactStore
  ↓
create-once durable bytes
  ↓
ArtifactReference
  +
RawArtifactEvidence
```

RAW remains material evidence. It is not a DatasetVersion and it is not a
publication target.

## ArtifactStore port

The V2 port follows the public API contract:

```python
class ArtifactStore(Protocol):
    def put(self, request: PutArtifactRequest) -> PutArtifactResult: ...
    def open(self, reference: ArtifactReference) -> ArtifactReader: ...
    def exists(self, reference: ArtifactReference) -> bool: ...
```

`ArtifactStore != Target`.

A backend may eventually implement both contracts explicitly, but neither
contract inherits from or implies the other.

## RAW immutability

The LOT-04 file profile uses create-only writes.

The final path is:

```text
<root>/runs/<IngestionRunId>/raw/<name>
```

The adapter writes exact bytes into a temporary file, flushes/fsyncs them and
creates the final path through a hard link. An existing final path therefore
produces a structured `CONFLICT` and is never overwritten.

This also avoids exposing a partially-written final RAW path.

## Integrity

SHA-256 is recomputed by the store.

When `PutArtifactRequest` originates from `AcquisitionResult`, the
acquisition checksum is treated as expected evidence. A mismatch fails before
durable bytes are created.

Every successful `ArtifactReference` contains:

```text
artifact_id
kind
storage ResourceReference
sha256 checksum
size
media type when known
created_at
portable metadata
```

`FileArtifactReader.read()` recomputes SHA-256 and checks byte size before
returning content. Durable tampering therefore raises `ArtifactIntegrityError`.

## RAW evidence

`RawArtifactEvidence` links the durable reference to:

```text
source ResourceReference
IngestionRunId
acquisition timestamp
persistence timestamp
retention intent
manifest artifact ID when known
```

This keeps source provenance and manifest linkage explicit without inflating the
portable `ArtifactReference` with provider/runtime state.

## Retention

`ArtifactRetention` is metadata-level intent:

```text
retain
retain_until?
policy_id?
```

LOT-04 records retention intent but does not implement background deletion or a
lifecycle scheduler.

## Security and portability

The file store:

- never resolves credentials;
- accepts only its own `file://` artifact namespace when reopening;
- rejects remote file authorities;
- rejects references resolving outside its configured root;
- verifies resource identity against the locator;
- rejects unverifiable references without SHA-256 evidence;
- exposes no provider client or database session.

## V1 transition

The governed V1 `pyingestkit.artifacts.__all__` remains unchanged.

V2 artifacts are available under:

```python
from pyingestkit.artifacts.v2 import (
    ArtifactKind,
    ArtifactReference,
    ArtifactRetention,
    PutArtifactRequest,
    RawArtifactEvidence,
)

from pyingestkit.stores import (
    ArtifactStore,
    FileArtifactStore,
)
```

The V1 `ArtifactStore`, `RawArtifact` and `ArtifactURI` continue to exist as
maintenance-line contracts only. They are not the canonical V2 persistence
model.

## LOT-04 exit evidence

LOT-04 is complete when CI proves:

- exact acquired bytes can be persisted and reopened;
- RAW writes are create-only;
- existing RAW bytes cannot be overwritten;
- acquisition/store SHA-256 evidence matches;
- tampering is detected by ArtifactReader;
- retention and manifest linkage remain explicit;
- ArtifactStore is distinct from Target;
- RAW evidence owns no DatasetVersion or transform state;
- V1 artifact star-import compatibility remains intact;
- Python 3.11–3.14 V2 tests pass;
- clean-wheel use requires no provider extras.
