# MetadataStore

`MetadataStore` indexes runtime state while `ArtifactStore` stores payloads. SQLite is the default CLI adapter; PostgreSQL is optional. The contract covers runs, steps, artifacts, validations, publications and structural events. Secrets in runtime parameters are redacted before persistence.

The Runner accepts a `MetadataStore`; backend selection is performed by the application/configuration boundary.
