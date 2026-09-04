# ADR-035 — Dataset diff is keyed when identity exists and multiset-based otherwise

## Status

Accepted — V0.4.0-a1.

## Decision

`DatasetDiffer` supports two deterministic modes. With `DiffPolicy.key_fields`, each dataset must contain unique, non-null, non-missing keys and the engine reports added, removed, changed and unchanged rows. Without keys, rows are compared as exact multisets: added and removed counts are meaningful, `changed_count` is always zero, and duplicate multiplicity is preserved.

Missing fields are distinct from explicit `None`. `ignore_fields` and `compare_fields` are mutually exclusive. Detailed entries are deterministically ordered and bounded by `max_entries`, while aggregate counts remain exact. Raw before/after values are not retained unless `capture_values=True` is explicitly requested.

## Consequences

- PyIngestKit never invents fuzzy row correspondence;
- duplicate or invalid keys fail explicitly through `DiffError`;
- schema changes are represented independently through `SchemaDiff`;
- the diff engine remains pure, in-memory and independent of runtime/metadata persistence in Alpha 1.
