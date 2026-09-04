# PyIngestKit V0.4.0-rc1 — Diff / Replay / Versioning E2E

**Milestone:** `V0.4.0-rc1`  
**Scope:** release-candidate integration of V0.4 diff, versioning, publication and RAW replay.

## Purpose

RC1 proves the complete V0.4 lifecycle without opening V0.5 scope:

```text
RAW V1
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

RAW V2
  ↓
Dataset
  ↓
Validation + Profile
  ↓
Diff against Published V1
  ↓
Version V2
  ↓
Published V2

Replay run V2
  ↓
Historical RAW only
  ↓
Same Dataset fingerprint
  ↓
STRICT verification PASS
```

## Reference job

`demo.versioned_ndjson` is the seventh installable reference job.

Its two fixture revisions deliberately produce:

- 1 added row;
- 1 removed row;
- 1 changed row;
- 1 unchanged row.

The replay path installs a network-forbidden HTTP client. `HttpSource.fetch()` must therefore
resolve and materialize the historical RAW before any transport call. A successful replay proves
that no new source acquisition occurred.

## Release gates

RC1 is accepted only when:

- Python 3.11 / 3.12 / 3.13 CI is green;
- `make release-check` is green;
- Security workflow is green;
- clean wheel installation discovers all 7 reference jobs;
- real `openpyxl` and `pyarrow` imports succeed;
- the V1 → V2 diff report has the expected counts;
- exactly two content-addressed versions exist;
- `PublishedDataset` points to V2;
- `pyingest replay <run-v2>` runs in `STRICT` mode with `matched=true`;
- replay lineage records the source run and matching fingerprint.

No new target, scheduler, warehouse or streaming capability is part of RC1.
