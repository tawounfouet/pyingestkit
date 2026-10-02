# PyIngestKit V2 — LOT-02 Source and IngestionDefinition

LOT-02 introduces the canonical clean-slate authoring root for PyIngestKit V2.

## Canonical model

```text
Source
    acquisition intent + semantics
        ↓
IngestionDefinition
    source
    decoder intent
    dataset family identity
    RAW policy
    validation policy hook
    versioning policy hook
    publication policy hook
    runtime-independent options
        ↓
deterministic definition fingerprint
```

No public `IngestionPlan` is introduced.

## Source

`Source` is an immutable declarative value. The initial source kinds are:

```text
file
http
object
database
custom
```

Typed factory methods construct each kind without performing I/O:

```python
Source.file(path="/data/customers.csv")
Source.http(url="https://example.test/customers.csv")
Source.object(uri="s3://bucket/customers.csv")
Source.database(connection="analytics", query="select * from customers")
Source.custom(connector_id="vendor.export")
```

`Source` may carry a `CredentialReference`, but never a resolved secret or active
provider client.

`Source != ResourceReference`. The source is acquisition intent; a
`ResourceReference` is portable resource identity/location produced or consumed
across boundaries.

## IngestionDefinition

`IngestionDefinition` is frozen and contains runtime-independent intent only:

```text
name
source
decoder
dataset
raw_policy
validation_policy
versioning_policy
publication_policy
options
metadata
```

The three policy hook fields are stable identifiers in LOT-02. Their richer
domain models are introduced by the owning later lots; LOT-02 does not
prematurely implement validation, versioning or publication engines.

The definition never owns:

```text
IngestionRunId
current status
retry counter
WorkflowRun / TaskAttempt state
provider session/client
resolved credentials
transformation DAG
```

## RAW policy

`RawPolicy` establishes only authoring intent:

```python
RawPolicy(
    enabled=True,
    retain=True,
    checksum="sha256",
)
```

The immutable RAW artifact lifecycle itself belongs to LOT-04.

## Definition fingerprint

Every definition exposes a deterministic SHA-256 fingerprint over its normalized
runtime-independent semantics.

The fingerprint:

- uses explicit JSON-compatible semantic fields only;
- normalizes Unicode to NFC;
- sorts mapping keys and metadata/options pairs;
- excludes runtime IDs, trace IDs, provider sessions and retry state.

This fingerprint is an internal domain-semantic hash, not the LOT-16 wire codec.

## V1 → V2 transition

The repository is still packaged as the maintained `1.0.1` line while the V2
alpha foundation is assembled.

Therefore LOT-02 makes the implemented V2 target-root values explicitly
importable:

```python
from pyingestkit import (
    ArtifactReference,
    DatasetVersionReference,
    IngestionDefinition,
    IngestionRunId,
    ResourceReference,
    Source,
)
```

but does not add them to the governed V1 `__all__` snapshot yet.

This preserves the V1 star-import contract while providing the real V2 authoring
API. The complete `__all__` cutover belongs to the V2 alpha package transition.

Because `pyingestkit.sources.Source` is still the governed V1 abstract source
during this compatibility interval, the clean-slate declaration is additionally
available as:

```python
from pyingestkit.sources.v2 import Source
```

That transitional module disappears from the design once the package moves fully
onto the V2 public namespace.

## LOT-02 exit evidence

LOT-02 is complete when CI proves:

- Source construction performs no I/O;
- Source is distinct from ResourceReference;
- obvious non-portable/credential-bearing source configuration is rejected;
- IngestionDefinition is immutable;
- the definition contains no runtime execution state;
- deterministic fingerprinting is stable;
- root explicit imports resolve to real V2 types;
- no public IngestionPlan exists;
- V1 exact `__all__` remains intact during the compatibility interval;
- architecture and core tests pass on Python 3.11–3.14;
- clean-wheel import remains provider-optional.
