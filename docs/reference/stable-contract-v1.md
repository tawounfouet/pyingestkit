# PyIngestKit V1 — Stable 1.x Contract

Status: **V1.0.0 stable contract**.

This document is the promotion layer over the historical A1/A2/B1/B2/RC1 evidence. It answers the
question that V1 was built to settle:

> What does PyIngestKit promise to keep compatible throughout the 1.x line?

## Promotion rule

The A1 inventory at `tests/contract/fixtures/public_api_v1.json` intentionally remains a historical
snapshot. At V1.0.0:

```text
PUBLIC_STABLE_CANDIDATE -> PUBLIC_STABLE
PUBLIC_EXPERIMENTAL      -> PUBLIC_EXPERIMENTAL
```

No `REMOVE_BEFORE_V1` module is allowed to survive the stable release. Explicit experimental symbols
inside otherwise stable namespaces remain experimental.

The machine-readable promotion policy is
`tests/contract/fixtures/stable_release_v1.json` and is enforced by `scripts/check_v1_stable.py`.

## Stable Python surface

All A1 `PUBLIC_STABLE_CANDIDATE` exports that survived A2, B1, B2 and RC1 are now stable 1.x surfaces.
This includes the common top-level authoring/runtime API and the governed specialized namespaces for
artifacts, configuration, contracts, declarative jobs, diff, errors, logging, parsers, plugins,
profiling, publication, quality, replay, retry, runtime, sources, targets, validation and versioning.

The exact symbol inventory remains the A1 JSON manifest; this document deliberately does not duplicate
its symbol list.

## Stable operational surface

The B1 contract is now binding across 1.x for:

- `pyingestkit.jobs` plugin discovery and deterministic duplicate handling;
- fail-closed configuration/profile selection;
- workspace precedence;
- canonical `pyingestkit.errors` identities;
- visible `PyIngestKitDeprecationWarning` migration warnings;
- CLI command names, option aliases, exit-code classes and successful JSON semantics;
- logging context, structured JSON fields, file formats and redaction behavior.

Presentation details such as Rich colors, terminal wrapping and spacing remain non-contractual.

## Stable persistence and replay surface

A2 compatibility policy remains binding for governed logical records, abstract/capability contracts and
portable persistent formats. Physical SQL table/layout details remain implementation details unless a
logical contract explicitly exposes them.

Schema-versioned portable formats remain governed. Incompatible semantic changes require a schema
version bump plus an upgrade path; package version changes alone do not justify rewriting historical
data.

V0.6.0 remains the executable historical upgrade baseline for the 1.0 release qualification.

## Python and packaging support

V1.0.0 qualifies Python 3.11, 3.12 and 3.13. Optional integrations remain behind the governed extras
`excel`, `parquet`, `postgres` and `s3`; `dev` remains the development extra.

The maintained demo job pack uses `pyingestkit>=1.0.0,<1.1` for the 1.0 release line.

## Deprecation and SemVer policy

A stable 1.x public surface is not silently removed or renamed. The normal path is:

```text
introduce replacement
-> retain old path/alias
-> emit PyIngestKitDeprecationWarning
-> document migration
-> preserve through 1.x
-> remove only in a later breaking major release
```

Additive behavior remains governed where callers may rely on exhaustive enums, strict configuration
models, serialized fields or protocol/ABC method sets.

## Explicitly not promised by V1

The stable contract does not turn PyIngestKit into a scheduler, DAG orchestration platform, worker
fleet, queue, cluster manager, IAM/RBAC platform, data catalog, GUI/SaaS product, ML platform or stream
processor.

Experimental surfaces remain outside the 1.x compatibility promise until explicitly promoted by a
later governed decision.
