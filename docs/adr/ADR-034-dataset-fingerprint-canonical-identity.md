# ADR-034 — Dataset fingerprint is a canonical content identity

## Status

Accepted — V0.4.0 stable (introduced in V0.4.0-a1).

## Decision

PyIngestKit distinguishes immutable RAW byte identity from parsed Dataset identity. `DatasetFingerprinter` hashes a versioned, type-aware canonical representation containing field order, values, duplicate multiplicity, and the configured row-order policy. It excludes run/provenance data such as URLs, timestamps and paths.

V0.4.0 stable freezes the canonical Dataset fingerprint codec at version `1`; changing this codec requires an explicit future version rather than silent reinterpretation.

The default policy is row-order insensitive. `order_sensitive=True` is explicit for datasets whose sequence is meaningful. Canonicalization distinguishes booleans, integers and floats; preserves Decimal precision; encodes bytes with Base64; preserves date/datetime type and timezone information; explicitly represents NaN/infinities/-0.0; recursively canonicalizes mappings independent of insertion order; and rejects unsupported types instead of falling back to arbitrary `repr()`.

## Consequences

- identical logical datasets have stable `sha256-...` identities across runs;
- RAW SHA-256 and Dataset fingerprint remain separate provenance concepts;
- V0.4 uses the same canonical identity for immutable Dataset versions;
- the core gains no dataframe dependency.
