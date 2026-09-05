# MetadataStore

`MetadataStore` indexes runtime state while `ArtifactStore` stores payloads. SQLite is the default CLI adapter; PostgreSQL is optional. The contract covers runs, steps, artifacts, validations, publications and structural events. Secrets in runtime parameters are redacted before persistence.

The Runner accepts a `MetadataStore`; backend selection is performed by the application/configuration boundary.


## HTTP artifact provenance (V0.2.0-a2)

The generic `artifacts` table remains unchanged. HTTP-only fields are stored in the additive one-to-one `artifact_http_provenance` table and exposed through `ArtifactRecord`. This preserves existing Alpha 1 run history while keeping source-specific metadata separate from the generic artifact index.

Persisted HTTP fields are deliberately allow-listed. Request/response header dictionaries are not persisted.

## Target-load audit metadata (V0.5.0-b1)

Target materialization history is exposed through the optional `TargetLoadMetadataCapability`.
The base `MetadataStore` contract is unchanged so third-party V0.4 implementations remain valid.

Built-in stores persist `TargetLoadRecord` values keyed by `load_id`, with query filters for run,
dataset, target and status. SQL backends use the additive `target_loads` table linked to `runs`.
This records what happened; B1 does not implement target-load idempotency or richer load modes.

