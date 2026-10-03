# PyIngestKit V2 — LOT-15 S3-Compatible Object Storage

LOT-15 introduces provider-isolated S3-compatible implementations of the V2
`ArtifactStore`, `DatasetVersionStore` and `DatasetPublisher` contracts.

## Storage topology

```text
<prefix>/
  runs/<run_id>/<kind>/<name>

  datasets/
    versions/<dataset path>/<version_id>/
      snapshot.json
      version.json

    published/<dataset path>/
      current.json
```

Run artifacts and dataset-version objects are create-once. The publication
pointer `current.json` is the only intentionally replaceable object.

## Integrity

Every object written by the V2 S3 layer stores
`pyingestkit-sha256` object metadata.

Reads verify that metadata before decoding or returning bytes. Artifact reads
also verify the portable `ArtifactReference` checksum and byte size.
Dataset-version reads additionally verify:

- dataset/version identity embedded in the snapshot;
- schema fingerprint;
- content-addressed `version_id`.

This means storage tampering fails closed before replay or materialization.

## Provider boundary

The V2 contracts and application/runtime layers do not import boto3.

`S3ClientV2` is a minimal protocol. Boto3 is imported lazily only by the
default client factory in `pyingestkit.adapters.s3._objects`. Tests can inject
an alternate S3-compatible client without importing a provider SDK.

## Publication

Publishing writes one complete JSON object to the deterministic
`current.json` key. S3-compatible object replacement is atomic at one object
key: readers see the old or new complete pointer, not a partially written file.

LOT-15 does not claim a multi-object distributed transaction or compare-and-swap
publisher lock.

## Cross-host semantics

Neither V2 S3 store depends on a local cache or workspace. A second process that
has only the same bucket/prefix can resolve artifact bytes, versions and the
published pointer.

This is the storage foundation needed for strict cross-host replay. Full
migration/reference acceptance remains part of LOT-18.

## Compatibility

The maintained V1 `S3ArtifactStore` and `S3DatasetVersionStore` remain
unchanged. V2 uses distinct types:

```python
from pyingestkit.stores import S3ArtifactStoreV2, S3DatasetVersionStoreV2
```

## Deferred

LOT-15 deliberately does not add:

- distributed locks;
- compare-and-swap publication;
- bucket lifecycle management;
- KMS policy orchestration;
- multipart-upload tuning;
- metadata database coupling;
- provider-specific IAM/bootstrap automation.
