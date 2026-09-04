# PyIngestKit V0.4.0 — Diff / Replay / Versioning Release

**Status:** Stable release  
**Date:** 2026-09-04  
**Baseline:** V0.3.0 Quality & Formats  
**Promotion source:** V0.4.0-rc1

## Stable vertical slice

```text
revision 1 RAW
  ↓
Dataset
  ↓
Validation + Profile
  ↓
Fingerprint
  ↓
Version V1
  ↓
Published V1

revision 2 RAW
  ↓
Dataset
  ↓
Fingerprint
  ↓
Diff against Published V1
  ↓
diff.json
  ↓
Version V2
  ↓
Published V2

Replay revision-2 run
  ↓
historical immutable RAW
  ↓
no live acquisition
  ↓
Fingerprint == V2
  ↓
STRICT verification PASS
```

## Stable freeze

V0.4.0 promotes the RC1 behavior without adding capabilities. The stable line freezes:

- public top-level API names;
- the CLI command set through `replay`;
- canonical Dataset fingerprint codec version `1`;
- Dataset snapshot version `"1"`;
- diff report version `"1"`;
- strict replay semantics: replay resolves historical RAW and never silently degrades to live acquisition;
- content-addressed Dataset version identity and atomic `PublishedDataset` pointer semantics.

## Reference proof

Seven installable reference jobs form the release suite. `demo.versioned_ndjson` is the V0.4 proof job: its V1/V2 fixtures produce one added, one removed, one changed and one unchanged row. V2 becomes the published dataset, then replay reconstructs V2 from its historical RAW with strict fingerprint equality.

## Non-regression boundary

V0.4.0 does not introduce warehouse targets, scheduling, streaming, CDC, three-way merge, branching data semantics or a new orchestration layer. The six V0.3 reference jobs remain executable from clean wheels.

## Qualification

Stable acceptance is defined by [`../guides/release-validation-v0.4.0.md`](../guides/release-validation-v0.4.0.md) and requires the full `make release-check`, Python 3.11/3.12/3.13 CI, Security, package build and clean-wheel proof.
