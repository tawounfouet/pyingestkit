# Migration guide — V0.6 stable to the V1 contract

This guide describes the compatibility work required when moving a V0.6 integration toward the V1
stable contract candidate.

> The immutable `v0.6.0` release is the historical upgrade baseline. The source tree is now qualified
> as the real PEP 440 candidate `1.0.0rc1`; this does **not** mean that stable `v1.0.0` has been tagged
> or published. The final stable version/tag happens only after RC1 merge and post-merge qualification.

## 1. Migration posture

V1 is designed as a consolidation of the V0.6 framework rather than a provider expansion. Existing
V0.6 jobs should be reviewed against five governed layers:

```text
A1   public Python surface
A2   compatibility + persisted logical contracts
B1   plugin/config/error/CLI/observability behavior
B2   representative pilot qualification + documentation
RC1  package/install/upgrade/release qualification
```

The goal is to make accidental behavior explicit before 1.0.

## 2. Public imports

Use paths listed in `docs/reference/public-api.md` for code that must remain compatible through 1.x.
Anything not listed in the governed public manifest is internal by default even if Python can import
it today.

For controlled exceptions, prefer the canonical namespace:

```python
import pyingestkit.errors as errors

try:
    ...
except errors.ConfigurationError:
    ...
```

Historical public exception classes are re-exported by identity, so existing `except` clauses remain
compatible. The canonical namespace improves consistency without creating replacement exception
objects.

## 3. Configuration selectors are fail closed

V0.6-era projects that relied on permissive fallback should be corrected.

V1 candidate resolution is:

```text
--config
  -> PYINGEST_CONFIG
  -> PYINGEST_ENV -> pyingest.yml.<env>
  -> default project config files
  -> in-memory defaults
```

If `PYINGEST_CONFIG` names a missing file, configuration fails. If `PYINGEST_ENV=prod` is selected and
`pyingest.yml.prod` is missing, configuration fails. PyIngestKit does not silently substitute another
environment.

Action for migration:

```bash
pyingest config
```

Run this in every deployment environment and confirm the reported origin/backends before scheduling
production work.

## 4. Workspace precedence is explicit

V1 candidate workspace precedence is:

```text
--workspace
  -> PYINGEST_WORKSPACE
  -> runtime.workspace
  -> .pyingest
```

If a V0.6 deployment set `PYINGEST_WORKSPACE` expecting it to be merely documentation, re-check the
result: it is now an implemented stable override.

## 5. Dotenv templates are never runtime files

Files such as:

```text
envs/.env.dev.example
envs/.env.stg.example
envs/.env.prod.example
```

are templates only. Copy values into a real environment file or inject variables with the deployment
secret manager. The console entry point does not auto-load `*.example` files and does not search parent
directories for dotenv files.

This avoids accidentally treating sample values as runtime credentials/configuration.

## 6. Plugin discovery is deterministic

The V1 entry-point group remains:

```text
pyingestkit.jobs
```

Migration checks for external job packs:

- every exported logical `job.id` must be unique;
- entry points should not depend on installation order;
- broken plugins must be fixable independently from healthy packages;
- libraries calling `discover_jobs()` should account for strict-by-default behavior;
- CLI/operator flows may use tolerant registry loading so healthy jobs remain available.

Duplicate job IDs are explicit plugin failures. Deterministic entry-point ordering decides which first
entry is retained for diagnostics rather than relying on environment-specific package ordering.

## 7. Deprecations are visible

Public V1 deprecations use `PyIngestKitDeprecationWarning`, a `FutureWarning` subclass, so migration
messages are visible under normal Python warning filters.

If you maintain an extension package, use the canonical helper for public migration guidance:

```python
from pyingestkit.deprecations import warn_deprecated

warn_deprecated(
    "old.option",
    replacement="new.option",
    removal="2.0.0",
)
```

Stable V1 public paths are retained through 1.x and removed only in a later breaking major release,
except for explicitly governed security/correctness emergencies.

## 8. CLI compatibility is semantic

The stable command set is:

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

Generated Typer management options `--install-completion` and `--show-completion` are intentionally
not part of the V1 product surface.

Exit-code classes are:

```text
0  success/help/version/valid empty result
2  usage/argument/configuration/lookup-selection error
1  runtime/domain execution failure
```

Automation should rely on command semantics, structured payloads and exit codes rather than exact Rich
colors, wrapping or whitespace.

## 9. Logging changes to review

Python standard-library logging remains the framework/plugin contract.

Human terminal logs use local timestamps and short run IDs. Structured JSON uses timezone-aware UTC
ISO-8601 timestamps and full identifiers.

File logging accepts:

```text
plain
json
```

`rich` is a terminal renderer and is rejected for file logging. If a V0.6 config used `rich` under
`logging.file.format`, migrate it to `plain` or `json`.

Secret redaction applies to normal messages, exception text and URL-embedded credentials.

## 10. Persistence and replay compatibility

A2 governs logical persistence contracts and versioned portable schemas rather than freezing every
physical SQL implementation detail.

When upgrading a real environment, preserve and test:

- historical run/step/artifact records;
- durable artifact locations;
- DatasetVersion snapshots/publication pointers;
- target-load lineage/idempotency records;
- strict replay from historical RAW.

Do not delete or rewrite historical durable state merely to match an implementation layout.

## 11. RC1 upgrade evidence

RC1 now executes an actual package upgrade against the immutable release lineage. The repository
release-check checks out the exact `v0.6.0` tag, installs the historical framework and demo package into
a clean environment, creates real versioned run history, then upgrades the same environment to the
built `1.0.0rc1` wheels.

After upgrade it requires:

- historical V0.6 run status remains readable;
- both historical content-addressed DatasetVersion snapshots remain readable;
- the historical PublishedDataset pointer still identifies V2;
- strict replay succeeds from the historical RAW;
- expected and actual fingerprints still match the V0.6 published fingerprint.

The executable evidence is `scripts/upgrade_smoke_test.py`. See
`docs/guides/release-validation-v1.0.0rc1.md` for the complete RC gate.

## 12. Recommended migration qualification

Before stable adoption, run the same progressive ladder as the repository:

```bash
make quality
make check
make release-check
```

Then qualify the representative topology closest to your deployment:

- local filesystem + SQLite;
- HTTP + validation/profile/reporting;
- local diff/version/publish/replay;
- PostgreSQL metadata + PostgreSQL target;
- PostgreSQL + S3-compatible durable cross-host replay.

See `docs/reference/pilots-v1.md` for the B2 evidence matrix.

## 13. Upgrade checklist

A V0.6 consumer is ready for the V1 contract candidate when:

- imports use governed public paths;
- config/profile resolution is explicit and fail-closed behavior is accepted;
- workspace precedence is understood;
- dotenv templates are not used as runtime files;
- plugin job IDs are globally unique in the environment;
- automation handles the V1 CLI exit-code classes;
- file logging uses `plain` or `json`;
- stored historical data remains readable under the governed compatibility policy;
- at least one representative B2 pilot matching the deployment topology has passed;
- the RC1 package/install/upgrade gate passes against the exact V0.6 release baseline.

Final release adoption should still wait for the immutable `v1.0.0` tag and stable release assets.
