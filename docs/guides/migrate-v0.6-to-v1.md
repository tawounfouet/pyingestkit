# Migration guide — V0.6 stable to V1.0.0 stable

This guide describes the compatibility work required when moving a V0.6 integration to the stable V1
contract.

The immutable `v0.6.0` release remains the historical upgrade baseline. PyIngestKit `1.0.0` is the
stable package identity; official release publication is anchored to the annotated immutable `v1.0.0`
tag created only after the exact stable merge SHA passes post-merge CI and Security.

## 1. Migration posture

V1 is a consolidation of the V0.6 framework rather than a provider expansion. Existing V0.6 jobs
should be reviewed against the governed ladder:

```text
A1      public Python surface
A2      compatibility + persisted logical contracts
B1      plugin/config/error/CLI/observability behavior
B2      representative pilots + documentation
RC1     package/install/upgrade/release qualification
Stable  protected 1.x compatibility contract
```

## 2. Public imports

Use paths listed in `docs/reference/public-api.md` and the promotion policy in
`docs/reference/stable-contract-v1.md` for code that must remain compatible through 1.x. Anything not
listed in the governed public inventory is internal by default even if Python can import it today.

For controlled exceptions, prefer:

```python
import pyingestkit.errors as errors

try:
    ...
except errors.ConfigurationError:
    ...
```

Historical public exception classes are re-exported by identity, so existing `except` clauses remain
compatible.

## 3. Configuration selectors are fail closed

Stable V1 resolution is:

```text
--config
  -> PYINGEST_CONFIG
  -> PYINGEST_ENV -> pyingest.yml.<env>
  -> default project config files
  -> in-memory defaults
```

If `PYINGEST_CONFIG` names a missing file or a selected `PYINGEST_ENV` profile is absent, configuration
fails instead of silently falling through.

Migration action:

```bash
pyingest config
```

Confirm the reported origin/backends in every deployment environment.

## 4. Workspace precedence is explicit

```text
--workspace
  -> PYINGEST_WORKSPACE
  -> runtime.workspace
  -> .pyingest
```

`PYINGEST_WORKSPACE` is a real stable runtime override.

## 5. Dotenv templates are never runtime files

`envs/.env.dev.example`, `envs/.env.stg.example` and `envs/.env.prod.example` are templates only. The
console entry point does not auto-load `*.example` files and does not search parent directories for
dotenv files.

## 6. Plugin discovery is deterministic

The stable entry-point group is `pyingestkit.jobs`. External job packs must use globally unique logical
`job.id` values. Library discovery is strict by default; tolerant operator registry loading keeps
healthy jobs usable while reporting plugin failures.

## 7. Deprecations are visible

Public V1 deprecations use `PyIngestKitDeprecationWarning`, a `FutureWarning` subclass. Stable public
paths are retained through 1.x and removed only in a later breaking major release except for explicitly
governed security/correctness emergencies.

## 8. CLI compatibility is semantic

Stable command names are:

```text
config
help
inspect
jobs
published
replay
run
runs
status
versions
```

Exit-code classes are:

```text
0  success/help/version/valid empty result
2  usage/argument/configuration/lookup-selection error
1  runtime/domain execution failure
```

Automation should rely on command semantics, structured payloads and exit codes rather than exact Rich
colors, wrapping or whitespace.

## 9. Logging changes to review

Human terminal logs use local timestamps and short run IDs. Structured JSON uses timezone-aware UTC
ISO-8601 timestamps and full identifiers. Stable file logging formats are `plain` and `json`; `rich` is
terminal presentation only. Secret redaction applies to normal messages and exception text.

## 10. Persistence and replay compatibility

Preserve and test:

- historical run/step/artifact records;
- durable artifact locations;
- DatasetVersion snapshots/publication pointers;
- target-load lineage/idempotency records;
- strict replay from historical RAW.

Do not delete or rewrite historical durable state merely to match an implementation layout.

## 11. Executable V0.6 -> 1.0.0 evidence

`scripts/upgrade_smoke_test.py` checks out exact `v0.6.0`, installs the historical framework/demo pack,
creates real versioned run history and publication state, then upgrades that same environment to the
built `1.0.0` wheels.

After upgrade it requires:

- historical V0.6 run status remains readable;
- both content-addressed DatasetVersion snapshots remain readable;
- the PublishedDataset pointer still identifies historical V2;
- strict replay succeeds from historical RAW;
- expected and actual fingerprints still match the V0.6 published fingerprint.

See `docs/guides/release-validation-v1.0.0.md` for the complete stable gate.

## 12. Recommended migration qualification

```bash
make quality
make check
make release-check
```

Then qualify the topology closest to your deployment: local filesystem + SQLite, HTTP + quality,
local versioning/replay, PostgreSQL persistence and/or PostgreSQL + S3-compatible durable cross-host
replay.

## 13. Upgrade checklist

A V0.6 consumer is ready for V1.0.0 when:

- imports use governed public paths;
- config/profile selection and workspace precedence are explicit;
- dotenv templates are not used as runtime files;
- plugin job IDs are globally unique;
- automation handles stable CLI exit-code classes;
- file logging uses `plain` or `json`;
- stored historical data remains readable;
- the representative pilot closest to the deployment passes;
- the executable V0.6.0 -> 1.0.0 package upgrade/replay gate passes.

For production adoption, pin to the immutable published `v1.0.0` release lineage or a later compatible
1.x release according to your dependency policy.
