# PyIngestKit V2 — LOT-16 Canonical Serialization and Contract Migration

LOT-01 deliberately left portable values as in-memory contracts and deferred
canonical JSON codecs, envelope validation, migrations and golden byte fixtures
to LOT-16. LOT-16 closes that deferred boundary.

## Wire envelope

Every serialized V2 boundary value is wrapped in:

```json
{
  "contract_id": "pykit.resource_reference",
  "contract_version": "1",
  "envelope_version": "1",
  "payload": {}
}
```

The envelope has an exact field set. Unknown fields, malformed UTF-8/JSON,
unknown envelope versions and unsupported contract IDs fail closed.

## Canonical bytes

Writers use UTF-8 JSON with:

- lexicographically sorted object keys;
- no insignificant whitespace;
- JSON-native values only;
- no NaN or infinity;
- deterministic metadata pair ordering as supplied by the domain value.

The same domain value therefore produces the same bytes.

Golden byte fixtures are committed under
`tests/contract/fixtures/v2_wire/` and are release-blocking.

## Explicit contract registry

LOT-16 supports the ten portable contracts introduced by LOT-01:

- ResourceReference;
- CredentialReference;
- CorrelationContext;
- IdempotencyReference;
- ArtifactReference;
- DatasetReference;
- DatasetVersionReference;
- IngestionExecutionReference;
- FailureEvidence;
- Diagnostic.

Encoding and decoding are explicit. Payload data never chooses a Python module,
class or callable.

## Nested contracts

Nested portable values carry their own `contract_id`,
`contract_version` and payload. Their expected contract ID is fixed by the
parent codec before reconstruction.

## Migration

`ContractMigrationRegistryV2` registers explicit adjacent payload migrations:

```text
(contract_id, from_version)
          |
          v
(to_version, pure payload migration)
```

No migration is discovered dynamically. Missing paths and cycles fail closed.
The current contracts remain version `1`; the migration engine exists now so a
future schema change does not require ad-hoc persisted-data rewriting.

## Security boundary

The serialization layer does not use:

- pickle;
- marshal;
- cloudpickle/dill;
- importlib-based dynamic reconstruction;
- eval/exec;
- V1 Runner/core execution models.

This format serializes data contracts, never Python behavior.

## Plugin relationship

The migration manifest also maps V1 plugin coverage to LOT-16/LOT-18. LOT-16
establishes the safe wire-contract foundation plugins will consume. Final
V2 plugin discovery/migration acceptance remains part of LOT-18 rather than
coupling executable plugin loading to the serialization codec.

## Compatibility

The maintained V1 persisted/runtime formats are unchanged. LOT-16 is additive
and qualified through `pyingestkit.serialization` during the transition.
