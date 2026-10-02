# PyIngestKit V2 — LOT-07 DatasetVersion Foundation

LOT-07 introduces the semantic transition from decoded evidence to an immutable
logical dataset version.

## Boundary

```text
LOT-05 DecodeResult
        |
        +--> DecodedRepresentation
        +--> SchemaEvidence
        |
        v
LOT-07 build_dataset_version
        |
        v
DatasetVersion
        |
        +--> DatasetVersionReference
        +--> deterministic content fingerprint
        +--> governed schema fingerprint
        +--> source RAW provenance
```

## Identity

Dataset identity remains the pair:

```text
(dataset_id, version_id)
```

The foundation version id is content-addressed:

```text
version_id == content_fingerprint == sha256-<digest>
```

The digest is computed only from the exact dependency-neutral decoded
representation. It excludes run ids, timestamps, storage locations and source
transport metadata, so repeated ingestion of the same decoded content yields the
same version id.

Schema identity remains distinct. LOT-05 `SchemaEvidence.fingerprint` becomes
the governed `schema_fingerprint` carried by `DatasetVersionReference`.

## Provenance

A logical version retains the RAW `ArtifactReference`, native
`IngestionRunId`, decoder id, schema evidence and decoded representation that
produced it.

Creation fails closed when decode request/result run or correlation identities
do not match, or when the decode did not succeed.

## Deferred to LOT-08

LOT-07 does not introduce:

- durable DatasetVersion storage;
- snapshot artifact creation;
- current/published pointers;
- publication or rollback;
- SQLAlchemy metadata persistence;
- S3/object-storage version adapters.

Those persistence/publication semantics are qualified separately in LOT-08.
The V1 versioning implementation remains untouched during this transition.

## Exit direction

The LOT-07 slice must prove:

- deterministic content-addressed identity;
- type-sensitive canonical content fingerprints;
- same content across runs => same version id;
- changed content => changed version id;
- schema fingerprint is carried exactly from decode evidence;
- source RAW provenance is retained;
- models are immutable and engine-neutral;
- V1 public versioning contracts remain unchanged;
- Python 3.11–3.14 architecture qualification remains green.
