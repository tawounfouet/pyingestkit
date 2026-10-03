# PyIngestKit V2 — LOT-18 V1 Semantic Migration

LOT-18 closes the repository-backed V1 migration evidence matrix for the areas
that were deliberately split across earlier V2 lots:

- replay (LOT-11 / LOT-18);
- PostgreSQL materialization (LOT-14 / LOT-18);
- S3/object storage (LOT-15 / LOT-18);
- plugin migration (LOT-16 / LOT-18);
- stable V1 configuration (LOT-00 / LOT-18).

The goal is **semantic migration**, not source-code translation.

## Migration dispositions

Every V1 configuration decision is classified explicitly:

```text
AUTOMATIC
  semantics map directly to an existing V2 contract

RETAINED_V1_ONLY
  stable V1 operational behavior remains readable/maintained but V2 currently
  has no equivalent portable contract

REWRITE_REQUIRED
  behavior is executable/job-specific and must be authored explicitly in V2

BLOCKED
  required migration identity/configuration is missing
```

No migration silently guesses a missing semantic.

## Configuration

`plan_v1_config_migration(PyIngestKitConfig)` consumes the already validated
stable V1 config object. It does not reimplement configuration precedence.

Safe automatic mappings include:

- V1 local artifact backend -> explicit V2 filesystem adapter roots;
- V1 S3 bucket/prefix/region/endpoint **environment variable name** ->
  `S3ArtifactStoreV2` / `S3DatasetVersionStoreV2` configuration;
- V1 PostgreSQL target identity/schema/table/load mode ->
  `PostgresTargetV2` / `TargetLoadRequestV2` semantics.

The planner never resolves DSN or endpoint secret values.

The current V2 runtime has no general MetadataStore replacement. V1
SQLite/PostgreSQL runtime metadata is therefore classified
`RETAINED_V1_ONLY` rather than falsely mapped.

## Persisted references

Stable V1 metadata rows can be converted data-only:

```text
ArtifactRecord
      -> ArtifactReference

DatasetVersionRecord
      -> DatasetVersionReference

PublishedDatasetRecord + migrated DatasetVersionReference
      -> PublishedDataset
```

The adapters preserve identity, durable locator, checksum/fingerprint, creation
timestamps and native UUID run identity where available.

V1 `source_uri` is deliberately not copied into the migrated
`ArtifactReference`: historical source URLs may contain information that does
not belong in a portable storage reference. The durable `storage_uri` is
preferred, with the historical local materialization path used only when no
storage URI exists.

## Plugins

LOT-18 does **not** load a V1 plugin to discover how to rewrite it.

`assess_v1_plugin_entry_point(name, value)` inspects only the declared entry
point strings and returns `REWRITE_REQUIRED`.

This is intentional. Stable V1 plugins expose executable
`Job / JobDefinition / Pipeline / Step` behavior. Automatically invoking that
code during migration would violate the V2 non-executable serialization
boundary and could not infer a correct `IngestionDefinition`.

Plugin authors must explicitly express:

- Source;
- decoder;
- validation;
- dataset identity;
- version/publication policy;
- target materialization;

through V2 contracts and registries.

LOT-18 therefore completes **plugin migration acceptance** without inventing a
new externally frozen entry-point group.

## Replay / PostgreSQL / S3 acceptance

The migration manifest targets these V1 behaviors at LOT-18. Their executable
V2 acceptance surfaces are now:

```text
V1 replay semantics
    -> ReplayServiceV2 + strict RAW-only replay

V1 PostgreSQL materialization
    -> PostgresTargetV2

V1 local/remote artifact and version identity
    -> ArtifactReference / DatasetVersionReference
    -> File/S3 V2 stores

V1 cross-host durable replay intent
    -> S3ArtifactStoreV2 + S3DatasetVersionStoreV2
    -> strict replay without live source/workspace
```

The earlier LOT-11/14/15 CI proofs remain authoritative; LOT-18 binds those
capabilities to the V1 migration evidence matrix rather than reimplementing
them.

## Security

LOT-18 migration tooling:

- does not call `importlib`;
- does not discover/load plugin entry points;
- does not execute V1 Job/Pipeline code;
- does not resolve secret environment variables;
- does not deserialize Python objects;
- does not mutate V1 persisted records;
- fails closed where V2 requires UUID execution identity.

## Compatibility

The V1 config, plugin, replay, target, metadata and versioning APIs remain
unchanged. LOT-18 is additive under:

```python
from pyingestkit.migration import ...
```

The package-root 2.0 breaking cut remains a separate milestone.
