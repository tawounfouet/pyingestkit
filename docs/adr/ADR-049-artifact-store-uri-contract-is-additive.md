# ADR-049 — ArtifactStore URI/read/materialize capabilities are additive

## Status
Accepted for V0.6.0-a1.

## Context

Adding abstract `uri_for`, `read_bytes` or `materialize_raw` methods would make every V0.5 third-party `ArtifactStore` implementation abstract and therefore unusable immediately after upgrading.

## Decision

The V0.6 ArtifactStore hardening keeps the four V0.5 abstract methods unchanged:

```text
prepare_run
write_raw
write_json
path_for
```

and adds conservative concrete defaults:

```text
uri_for         → file:// URI derived from path_for
read_bytes      → file:// only
materialize_raw → local materialization + SHA-256 verification
```

Remote stores override only the capabilities they own.

A1 deliberately leaves the V0.5 SQLite/PostgreSQL metadata schema unchanged. `ArtifactRecord.storage_uri` is optional so MemoryMetadataStore and future URI-aware adapters can expose the portable location without forcing an in-place SQL schema change at the contract-hardening milestone.

## Consequences

- existing custom ArtifactStore subclasses remain instantiable;
- pre-V0.6 artifact rows remain readable and replay falls back to their historical `path`;
- MemoryMetadataStore can preserve URI identity immediately;
- durable remote-location persistence for SQLite/PostgreSQL is introduced with Remote RAW in A2, when `s3://` becomes a real persisted location rather than a future-facing contract.
